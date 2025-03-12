import urllib.request
import urllib.error
import time

def check(url, attempts=3, timeout=5, delay=1, content_check=None, acceptable_codes=None):
    """
    Check if a URL is accessible with multiple attempts and optionally contains specific content.
    
    Args:
        url (str): URL to check (should include http:// or https://)
        attempts (int): Number of retry attempts before considering the URL down
        timeout (int): Timeout in seconds for each attempt
        delay (int): Delay between retry attempts in seconds
        content_check (str, optional): String to check for in response
        acceptable_codes (list, optional): List of acceptable HTTP status codes, defaults to [200]
        
    Returns:
        bool: True if URL is accessible and content check passes (if specified)
    """
    # Add http:// prefix if missing
    if not url.startswith('http://') and not url.startswith('https://'):
        url = f'http://{url}'
    
    # Set default acceptable codes if none provided
    if acceptable_codes is None:
        acceptable_codes = [200]
    
    # Try multiple times
    for attempt in range(attempts):
        try:
            # Make the request
            response = urllib.request.urlopen(url, timeout=timeout)
            
            # Check status code
            if response.getcode() not in acceptable_codes:
                # If this isn't the last attempt, wait and retry
                if attempt < attempts - 1:
                    time.sleep(delay)
                    continue
                return False
                
            # If content check is specified, check for the string
            if content_check:
                content = response.read().decode('utf-8', errors='ignore')
                if content_check not in content:
                    # If this isn't the last attempt, wait and retry
                    if attempt < attempts - 1:
                        time.sleep(delay)
                        continue
                    return False
                    
            return True  # Success if we got here
            
        except (urllib.error.URLError, urllib.error.HTTPError, ConnectionRefusedError, 
                TimeoutError, ValueError):
            # If this isn't the last attempt, wait before trying again
            if attempt < attempts - 1:
                time.sleep(delay)
            else:
                return False
    
    # Should not reach here, but just in case
    return False