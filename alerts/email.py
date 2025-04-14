import subprocess
import logging
import time
from datetime import datetime, timedelta

logger = logging.getLogger('iptic-watcher.alerts.email')

def send_alert(system, host, message, down_timestamp=None):
    """
    Send an email alert using the system's mail command.
    
    Args:
        system (str): Name of the system that's down or recovered
        host (str): Hostname or IP that was checked
        message (str): Alert message to send
        down_timestamp (float, optional): Timestamp when system went down, for recovery alerts
    
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
    
    # Calculate downtime for recovery alerts if timestamp is provided
    if "RECOVERED" in message and down_timestamp is not None:
        downtime_seconds = time.time() - down_timestamp
        downtime = timedelta(seconds=downtime_seconds)
        
        # Format downtime nicely (days, hours, minutes, seconds)
        days = downtime.days
        hours, remainder = divmod(downtime.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        
        downtime_str = ""
        if days > 0:
            downtime_str += f"{days} days, "
        if hours > 0 or days > 0:
            downtime_str += f"{hours} hours, "
        if minutes > 0 or hours > 0 or days > 0:
            downtime_str += f"{minutes} minutes, "
        downtime_str += f"{seconds} seconds"
        
        # Add downtime information to email body
        email_body += f"\n\nDowntime: {downtime_str}"
        
        # Add timestamp information
        down_time = datetime.fromtimestamp(down_timestamp).strftime('%Y-%m-%d %H:%M:%S')
        up_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        email_body += f"\nDown since: {down_time}\nRecovered at: {up_time}"
    
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