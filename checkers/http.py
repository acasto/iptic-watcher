import urllib.request
import urllib.error

def check(url, timeout=5, content_check=None):
    """
    Check if a URL is accessible and optionally contains specific content.
    
    Args:
        url (str): URL to check (should include http:// or https://)
        timeout (int): Timeout in seconds
        content_check (str, optional): String to check for in response
        
    Returns:
        bool: True if URL is accessible and content check passes (if specified)
    """
    # Add http:// prefix if missing
    if not url.startswith('http://') and not url.startswith('https://'):
        url = f'http://{url}'
        
    try:
        # Make the request
        response = urllib.request.urlopen(url, timeout=timeout)
        
        # Check status code
        if response.getcode() != 200:
            return False
            
        # If content check is specified, check for the string
        if content_check:
            content = response.read().decode('utf-8', errors='ignore')
            return content_check in content
            
        return True
    except (urllib.error.URLError, urllib.error.HTTPError, ConnectionRefusedError, 
            TimeoutError, ValueError):
        return False