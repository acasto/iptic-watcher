import subprocess
import platform
import time

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
    
    # Try multiple times
    for attempt in range(attempts):
        try:
            # Run ping command with timeout
            subprocess.run(
                command, 
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=True,
                timeout=timeout
            )
            return True  # Success on first successful ping
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
            # If this isn't the last attempt, wait before trying again
            if attempt < attempts - 1:
                time.sleep(delay)
    
    # All attempts failed
    return False