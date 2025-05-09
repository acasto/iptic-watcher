#!/usr/bin/env python3
"""
A lightweight uptime monitoring system that checks systems 
and sends alerts when they're down.
"""

import configparser
import importlib
import time
import sys
import os
import argparse
import logging
import logging.handlers
from datetime import datetime

# Default values
CHECK_INTERVAL = 60  # seconds
CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.ini')

# State tracking to prevent alert spamming
system_states = {}  # Format: {system_name: {'status': bool, 'last_change': timestamp}}

# State persistence file for single-shot mode
STATE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.watcher_state')

# Logger setup
logger = logging.getLogger('iptic-watcher')

def setup_logging(config=None):
    """Setup logging based on configuration if provided."""
    # Default settings
    log_level = logging.INFO
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    log_file = None
    
    # If config exists, get values from it
    if config and 'logging' in config:
        # Get log level
        level_str = config['logging'].get('level', 'INFO').upper()
        log_level = getattr(logging, level_str, logging.INFO)
        
        # Get log format
        log_format = config['logging'].get('format', log_format)
        
        # Get log file
        log_file = config['logging'].get('file', None)

    # Configure root logger
    logging.basicConfig(
        level=log_level,
        format=log_format,
        handlers=[logging.StreamHandler()]
    )
    
    # Add file handler if configured
    if log_file:
        # Create directories if needed
        log_dir = os.path.dirname(log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir)
            
        # Add rotating file handler
        file_handler = logging.handlers.RotatingFileHandler(
            log_file, maxBytes=10*1024*1024, backupCount=5
        )
        file_handler.setFormatter(logging.Formatter(log_format))
        logging.getLogger().addHandler(file_handler)
    
    return logging.getLogger('iptic-watcher')

def load_config():
    """Load configuration from the config file."""
    config = configparser.ConfigParser()
    try:
        config.read(CONFIG_FILE)
        return config
    except Exception as e:
        logger.error(f"Error loading configuration: {e}")
        sys.exit(1)

def perform_check(system, check_type, host, **kwargs):
    """
    Dynamically load and execute the appropriate check module.
    
    Args:
        system (str): Name of the system being checked
        check_type (str): Type of check to perform (ping, http, etc.)
        host (str): Host to check
        
    Returns:
        bool: True if check passes, False otherwise
    """
    try:
        # Dynamically import check module
        check_module = importlib.import_module(f"checkers.{check_type}")
        logger.debug(f"Performing {check_type} check on {host} for system {system}")
        
        # Pass additional parameters if provided
        # Using kwargs from function parameters
            
        result = check_module.check(host, **kwargs)
        return result
    except (ImportError, AttributeError) as e:
        logger.error(f"Error: Check type '{check_type}' not supported or module not found: {e}")
        return None
    except Exception as e:
        logger.error(f"Error performing {check_type} check on {host}: {e}")
        return None

def send_alert(system, alert_type, host, message, down_timestamp=None):
    """
    Dynamically load and execute the appropriate alert module.
    
    Args:
        system (str): Name of the system that's down
        alert_type (str): Type of alert to send (email, sms, etc.)
        host (str): Host that was checked
        message (str): Alert message to send
        down_timestamp (float, optional): Timestamp when system went down, for recovery alerts
    """
    try:
        # Dynamically import alert module
        alert_module = importlib.import_module(f"alerts.{alert_type}")
        logger.info(f"Sending {alert_type} alert for {system} ({host})")
        
        # Check if the alert module supports down_timestamp parameter
        if "RECOVERED" in message and down_timestamp is not None and alert_type == 'email':
            alert_module.send_alert(system, host, message, down_timestamp=down_timestamp)
        else:
            alert_module.send_alert(system, host, message)
    except (ImportError, AttributeError) as e:
        logger.error(f"Error: Alert type '{alert_type}' not supported or module not found: {e}")
    except Exception as e:
        logger.error(f"Error sending {alert_type} alert for {system}: {e}")

def save_state():
    """Save the current state to a file for persistence between single-shot runs."""
    try:
        with open(STATE_FILE, 'w') as f:
            for system, state in system_states.items():
                f.write(f"{system}:{state['status']}:{state['last_change']}\n")
        logger.debug(f"Saved state for {len(system_states)} systems")
    except Exception as e:
        logger.error(f"Error saving state: {e}")

def load_state():
    """Load the previous state from file."""
    if not os.path.exists(STATE_FILE):
        logger.debug("No state file found, starting fresh")
        return {}
        
    states = {}
    try:
        with open(STATE_FILE, 'r') as f:
            for line in f:
                parts = line.strip().split(':')
                if len(parts) == 3:
                    system, status, last_change = parts
                    states[system] = {
                        'status': status.lower() == 'true',
                        'last_change': float(last_change)
                    }
        logger.debug(f"Loaded state for {len(states)} systems")
        return states
    except Exception as e:
        logger.error(f"Error loading state: {e}")
        return {}

def check_systems(config, single_shot=False, verbose=False, update_status_page=False):
    """Check all systems and send alerts if needed.
    
    Args:
        config: ConfigParser object with system configurations
        single_shot: If True, run once and exit
        verbose: If True, print more detailed output
        update_status_page: If True, update status page regardless of status change
        
    Returns:
        True if all systems are up, False otherwise
    """
    current_time = time.time()
    all_systems_up = True
    
    # Check if local connectivity check is configured
    local_check_host = None
    if 'general' in config and 'check_local_first' in config['general']:
        local_check_host = config['general'].get('check_local_first')
        if local_check_host and local_check_host.strip():
            # Perform local connectivity check
            logger.debug(f"Checking local connectivity to {local_check_host} before proceeding")
            try:
                from checkers.ping import check as ping_check
                local_status = ping_check(local_check_host)
                if not local_status:
                    logger.warning(f"Local connectivity check to {local_check_host} failed. Skipping all system checks.")
                    return False
                logger.debug(f"Local connectivity check to {local_check_host} passed. Proceeding with system checks.")
            except Exception as e:
                logger.error(f"Error performing local connectivity check: {e}")
                # Continue with checks anyway if local check raises an exception
    
    logger.debug(f"Starting system checks, monitoring {len(config.sections())} systems")
    
    for system in config.sections():
        # Skip non-system sections
        if system in ['logging', 'status_page', 'general']:
            continue
            
        # Get configuration for this system
        host = config[system].get('host')
        check_type = config[system].get('check')
        alert_type = config[system].get('alert')
        
        if not host or not check_type or not alert_type:
            logger.error(f"Missing configuration for {system}")
            continue
        
        # Get content check if configured
        content_check = config[system].get('content')
        
        # Perform the check
        if content_check and check_type == 'http':
            status = perform_check(system, check_type, host, content_check=content_check)
        else:
            status = perform_check(system, check_type, host)
        
        if status is None:
            continue  # Check failed to execute
            
        prev_status = system_states.get(system, {}).get('status')
        
        # Initialize state if not already present
        if system not in system_states:
            system_states[system] = {'status': status, 'last_change': current_time}
            if verbose:
                logger.info(f"Initial status for {system} ({host}): {'UP' if status else 'DOWN'}")
            elif not status:
                logger.warning(f"Initial status for {system} ({host}): DOWN")
            
            # Send alert on initial down state
            if not status:
                message = f"System {system} is DOWN. Check type: {check_type}"
                send_alert(system, alert_type, host, message)
                # Update status page for initial down status
                try:
                    if 'IPTIC_STATUS_PAGE' in os.environ:
                        send_alert(system, 'status_page', host, message)
                except Exception as e:
                    logger.error(f"Error updating status page for {system}: {e}")
                all_systems_up = False
            # Update status page if enabled for initial up state
            elif update_status_page:
                message = f"System {system} is UP. Check type: {check_type}"
                try:
                    if 'IPTIC_STATUS_PAGE' in os.environ:
                        send_alert(system, 'status_page', host, message)
                except Exception as e:
                    logger.error(f"Error updating status page for {system}: {e}")
            continue
            
        # Status changed
        if status != prev_status:
            # Store the previous last_change timestamp before updating it
            prev_timestamp = system_states[system]['last_change']
            
            # Update system state
            system_states[system]['status'] = status
            system_states[system]['last_change'] = current_time
            
            # If system went down or came back up, send alert
            if not status:
                message = f"System {system} is DOWN. Check type: {check_type}"
                send_alert(system, alert_type, host, message)
                # Also update status page if enabled
                try:
                    if 'IPTIC_STATUS_PAGE' in os.environ:
                        send_alert(system, 'status_page', host, message)
                except Exception as e:
                    logger.error(f"Error updating status page for {system}: {e}")
                logger.warning(f"ALERT: {system} ({host}) is DOWN")
                all_systems_up = False
            else:
                # System has recovered - send alert with down timestamp
                message = f"System {system} has RECOVERED. Check type: {check_type}"
                send_alert(system, alert_type, host, message, down_timestamp=prev_timestamp)
                # Also update status page if enabled
                try:
                    if 'IPTIC_STATUS_PAGE' in os.environ:
                        send_alert(system, 'status_page', host, message)
                except Exception as e:
                    logger.error(f"Error updating status page for {system}: {e}")
                logger.info(f"RECOVERED: {system} ({host}) is back UP")
        elif verbose:
            # In verbose mode, show status even if unchanged
            logger.debug(f"{system} ({host}) status: {'UP' if status else 'DOWN'}")
        
        # Update state for unchanged status
        if not status:
            all_systems_up = False
        
        # Always update status page for this system if enabled, even if status didn't change
        elif update_status_page and 'IPTIC_STATUS_PAGE' in os.environ:
            message = f"System {system} is UP. Check type: {check_type}"
            try:
                send_alert(system, 'status_page', host, message)
            except Exception as e:
                logger.error(f"Error updating status page for {system}: {e}")
    
    return all_systems_up

def main():
    """Main function to run the watcher."""
    global CONFIG_FILE
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='IPTIC Watcher - lightweight system monitoring')
    parser.add_argument('--single-shot', '-s', action='store_true', 
                        help='Run once and exit (good for cron usage)')
    parser.add_argument('--config', '-c', type=str, default=CONFIG_FILE,
                        help=f'Configuration file path (default: {CONFIG_FILE})')
    parser.add_argument('--verbose', '-v', action='store_true',
                        help='Show detailed output for all checks')
    parser.add_argument('--log-level', '-l', type=str, choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
                        help='Set logging level (overrides config file)')
    parser.add_argument('--status-page', action='store_true',
                        help='Enable HTML status page generation')
    parser.add_argument('--status-file', type=str,
                        help='Path to the HTML status page file (default: ./status.html)')
    args = parser.parse_args()
    
    # Override config file if specified
    CONFIG_FILE = args.config
    
    config = load_config()
    
    # Setup logging
    global logger
    logger = setup_logging(config)
    
    # Override log level if specified in command line
    if args.log_level:
        log_level = getattr(logging, args.log_level)
        logger.setLevel(log_level)
        # Also set for root logger
        logging.getLogger().setLevel(log_level)
        logger.debug(f"Log level set to {args.log_level} from command line")
        
    # Set status page environment variable if specified from CLI or config
    status_page_enabled = args.status_page
    status_page_file = args.status_file
    
    # Check config for status page settings if not specified in CLI
    if not status_page_enabled and not status_page_file and 'status_page' in config:
        status_page_enabled = config['status_page'].getboolean('enabled', fallback=False)
        if status_page_enabled and not status_page_file:
            status_page_file = config['status_page'].get('file', './status.html')
    
    if status_page_enabled or status_page_file:
        if status_page_file:
            os.environ['IPTIC_STATUS_PAGE'] = status_page_file
            logger.debug(f"Status page will be generated at {status_page_file}")
        else:
            os.environ['IPTIC_STATUS_PAGE'] = './status.html'
            logger.debug("Status page will be generated at ./status.html")
        
        # Initialize the status page on startup
        try:
            from alerts.status_page import initialize_status_page
            if initialize_status_page():
                logger.info("Status page initialized successfully")
            else:
                logger.warning("Failed to initialize status page")
        except Exception as e:
            logger.error(f"Error initializing status page: {e}")
    
    # For single-shot mode, load previous state
    if args.single_shot:
        logger.debug("Running in single-shot mode")
        saved_state = load_state()
        system_states.update(saved_state)
        
        # Run checks once
        all_up = check_systems(config, single_shot=True, verbose=args.verbose, 
                           update_status_page=('IPTIC_STATUS_PAGE' in os.environ))
        
        # Save state for next run
        save_state()
        
        # Exit with status code (useful for cron/scripts)
        logger.debug(f"Single-shot run complete. Status: {'All UP' if all_up else 'Some systems DOWN'}")
        sys.exit(0 if all_up else 1)
    
    # Normal continuous mode
    num_systems = sum(1 for s in config.sections() if s != 'logging')
    logger.info(f"Starting IPTIC Watcher... Monitoring {num_systems} systems")
    
    try:
        # If status page is enabled, do a full update on first run
        update_status_page = 'IPTIC_STATUS_PAGE' in os.environ
        
        while True:
            check_systems(config, verbose=args.verbose, update_status_page=update_status_page)
            # After first run, only update status page when status changes
            update_status_page = False
            logger.debug(f"Sleeping for {CHECK_INTERVAL} seconds")
            time.sleep(CHECK_INTERVAL)
    except KeyboardInterrupt:
        logger.info("Watcher stopped by user")
    except Exception as e:
        logger.critical(f"Unexpected error: {e}", exc_info=True)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        # Already handled in main()
        sys.exit(0)
    except Exception as e:
        # In case exceptions escape main()
        if 'logger' in globals() and logger:
            logger.critical(f"Fatal error: {e}", exc_info=True)
        else:
            print(f"Fatal error: {e}")
        sys.exit(1)