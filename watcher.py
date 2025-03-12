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
from datetime import datetime

# Default values
CHECK_INTERVAL = 60  # seconds
CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.ini')

# State tracking to prevent alert spamming
system_states = {}  # Format: {system_name: {'status': bool, 'last_change': timestamp}}

# State persistence file for single-shot mode
STATE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.watcher_state')

def load_config():
    """Load configuration from the config file."""
    config = configparser.ConfigParser()
    try:
        config.read(CONFIG_FILE)
        return config
    except Exception as e:
        print(f"Error loading configuration: {e}")
        sys.exit(1)

def perform_check(system, check_type, host):
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
        result = check_module.check(host)
        return result
    except (ImportError, AttributeError) as e:
        print(f"Error: Check type '{check_type}' not supported or module not found: {e}")
        return None
    except Exception as e:
        print(f"Error performing {check_type} check on {host}: {e}")
        return None

def send_alert(system, alert_type, host, message):
    """
    Dynamically load and execute the appropriate alert module.
    
    Args:
        system (str): Name of the system that's down
        alert_type (str): Type of alert to send (email, sms, etc.)
        host (str): Host that was checked
        message (str): Alert message to send
    """
    try:
        # Dynamically import alert module
        alert_module = importlib.import_module(f"alerts.{alert_type}")
        alert_module.send_alert(system, host, message)
    except (ImportError, AttributeError) as e:
        print(f"Error: Alert type '{alert_type}' not supported or module not found: {e}")
    except Exception as e:
        print(f"Error sending {alert_type} alert for {system}: {e}")

def save_state():
    """Save the current state to a file for persistence between single-shot runs."""
    try:
        with open(STATE_FILE, 'w') as f:
            for system, state in system_states.items():
                f.write(f"{system}:{state['status']}:{state['last_change']}\n")
    except Exception as e:
        print(f"Error saving state: {e}")

def load_state():
    """Load the previous state from file."""
    if not os.path.exists(STATE_FILE):
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
        return states
    except Exception as e:
        print(f"Error loading state: {e}")
        return {}

def check_systems(config, single_shot=False, verbose=False):
    """Check all systems and send alerts if needed.
    
    Args:
        config: ConfigParser object with system configurations
        single_shot: If True, run once and exit
        verbose: If True, print more detailed output
        
    Returns:
        True if all systems are up, False otherwise
    """
    current_time = time.time()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    all_systems_up = True
    
    for system in config.sections():
        # Get configuration for this system
        host = config[system].get('host')
        check_type = config[system].get('check')
        alert_type = config[system].get('alert')
        
        if not host or not check_type or not alert_type:
            print(f"[{timestamp}] Error: Missing configuration for {system}")
            continue
        
        # Perform the check
        status = perform_check(system, check_type, host)
        
        if status is None:
            continue  # Check failed to execute
            
        prev_status = system_states.get(system, {}).get('status')
        
        # Initialize state if not already present
        if system not in system_states:
            system_states[system] = {'status': status, 'last_change': current_time}
            if verbose or not status:
                print(f"[{timestamp}] Initial status for {system} ({host}): {'UP' if status else 'DOWN'}")
            
            # Send alert on initial down state
            if not status:
                message = f"System {system} is DOWN. Check type: {check_type}"
                send_alert(system, alert_type, host, message)
                all_systems_up = False
            continue
            
        # Status changed
        if status != prev_status:
            system_states[system]['status'] = status
            system_states[system]['last_change'] = current_time
            
            # If system went down or came back up, send alert
            if not status:
                message = f"System {system} is DOWN. Check type: {check_type}"
                send_alert(system, alert_type, host, message)
                print(f"[{timestamp}] ALERT: {system} ({host}) is DOWN")
                all_systems_up = False
            else:
                message = f"System {system} has RECOVERED. Check type: {check_type}"
                send_alert(system, alert_type, host, message)
                print(f"[{timestamp}] RECOVERED: {system} ({host}) is back UP")
        elif verbose:
            # In verbose mode, show status even if unchanged
            print(f"[{timestamp}] {system} ({host}) status: {'UP' if status else 'DOWN'}")
        
        # Update state for unchanged status
        if status != prev_status:
            system_states[system]['status'] = status
        
        # Track overall status
        if not status:
            all_systems_up = False
    
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
    args = parser.parse_args()
    
    # Override config file if specified
    CONFIG_FILE = args.config
    
    config = load_config()
    
    # For single-shot mode, load previous state
    if args.single_shot:
        saved_state = load_state()
        system_states.update(saved_state)
        
        # Run checks once
        all_up = check_systems(config, single_shot=True, verbose=args.verbose)
        
        # Save state for next run
        save_state()
        
        # Exit with status code (useful for cron/scripts)
        sys.exit(0 if all_up else 1)
    
    # Normal continuous mode
    print(f"Starting IPTIC Watcher... Monitoring {len(config.sections())} systems")
    
    while True:
        check_systems(config, verbose=args.verbose)
        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nExiting IPTIC Watcher...")
        sys.exit(0)