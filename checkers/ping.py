import subprocess
import platform

def check(host):
    """
    Ping the specified host and return True if it responds, False otherwise.
    
    Args:
        host (str): Hostname or IP address to ping
        
    Returns:
        bool: True if host is reachable, False otherwise
    """
    # Adjust ping command based on platform
    param = '-n' if platform.system().lower() == 'windows' else '-c'
    command = ['ping', param, '1', host]
    
    try:
        # Run ping command with timeout
        subprocess.run(
            command, 
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True,
            timeout=5
        )
        return True
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return False