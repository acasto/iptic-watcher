import subprocess
import logging

logger = logging.getLogger('iptic-watcher.alerts.email')

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
        logger.debug(f"Preparing DOWN alert email for {system} ({host})")
    elif "RECOVERED" in message:
        subject = f"RECOVERY: {system} ({host}) is back UP"
        logger.debug(f"Preparing RECOVERY alert email for {system} ({host})")
    else:
        subject = f"ALERT: {system} ({host})"
        logger.debug(f"Preparing general alert email for {system} ({host})")
    
    email_body = f"{message}\n\nSystem: {system}\nHost: {host}"
    
    try:
        logger.debug(f"Sending email with subject: {subject}")
        # Use system mail command
        subprocess.run(
            ['mail', '-s', subject, 'root'],
            input=email_body.encode(),
            check=True,
            stderr=subprocess.DEVNULL
        )
        logger.info(f"Email alert sent successfully for {system} ({host})")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to send email alert for {system} ({host}): {e}")
        return False