import subprocess
import platform
import time
import logging

logger = logging.getLogger('iptic-watcher.checkers.ping')

def check(host, attempts=3, timeout=5, delay=1):
    """
    Ping the specified host multiple times and return True if it responds, False otherwise.
    
    Args:
        host (str): Hostname or IP address to ping
        attempts (int): Number of ping attempts before marking host as down
        timeout (int): Timeout for each ping attempt in seconds
        delay (int): Delay between ping attempts in seconds
        
    Returns:
        bool: True if host is reachable, False otherwise
    """
    # Adjust ping command based on platform
    system = platform.system().lower()
    
    if system == 'windows':
        # Windows: -n for count, -a for no DNS resolution
        command = ['ping', '-n', '1', '-a', host]
    else:
        # Unix/Linux/macOS: -c for count, -n for numeric output only (no DNS resolution)
        command = ['ping', '-c', '1', '-n', host]
    
    logger.debug(f"Pinging {host} with {attempts} attempts, timeout={timeout}s, delay={delay}s")
    
    # Try multiple times
    for attempt in range(attempts):
        try:
            logger.debug(f"Ping attempt {attempt+1}/{attempts} for {host}")
            # Run ping command with timeout
            subprocess.run(
                command, 
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=True,
                timeout=timeout
            )
            logger.debug(f"Ping successful for {host}")
            return True  # Success on first successful ping
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
            logger.debug(f"Ping attempt {attempt+1} failed for {host}: {type(e).__name__}")
            # If this isn't the last attempt, wait before trying again
            if attempt < attempts - 1:
                time.sleep(delay)
    
    # All attempts failed
    logger.debug(f"All ping attempts failed for {host}")
    return False