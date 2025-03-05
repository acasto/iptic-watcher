import subprocess

def send_alert(system, host, message):
    """
    Send an email alert using the system's mail command.
    
    Args:
        system (str): Name of the system that's down
        host (str): Hostname or IP that was checked
        message (str): Alert message to send
    
    Returns:
        bool: True if email was sent successfully, False otherwise
    """
    subject = f"ALERT: {system} ({host}) is DOWN"
    email_body = f"{message}\n\nSystem: {system}\nHost: {host}"
    
    try:
        # Use system mail command
        subprocess.run(
            ['mail', '-s', subject, 'root'],
            input=email_body.encode(),
            check=True,
            stderr=subprocess.DEVNULL
        )
        return True
    except subprocess.CalledProcessError:
        return False