import subprocess

def send_alert(system, host, message):
    """
    Send an email alert using the system's mail command.
    
    Args:
        system (str): Name of the system that's down or recovered
        host (str): Hostname or IP that was checked
        message (str): Alert message to send
    
    Returns:
        bool: True if email was sent successfully, False otherwise
    """
    # Determine if this is a down or recovery alert
    if "DOWN" in message:
        subject = f"ALERT: {system} ({host}) is DOWN"
    elif "RECOVERED" in message:
        subject = f"RECOVERY: {system} ({host}) is back UP"
    else:
        subject = f"ALERT: {system} ({host})"
    
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