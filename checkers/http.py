import urllib.request
import urllib.error
import time
import logging

logger = logging.getLogger('iptic-watcher.checkers.http')

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
        logger.debug(f"Added http:// prefix to URL: {url}")
        
    if content_check:
        logger.debug(f"Content check enabled, looking for: {content_check[:30]}...")
    
    # Set default acceptable codes if none provided
    if acceptable_codes is None:
        acceptable_codes = [200]
    
    logger.debug(f"Checking URL {url} with {attempts} attempts, timeout={timeout}s, delay={delay}s")
    logger.debug(f"Acceptable status codes: {acceptable_codes}")
    if content_check:
        logger.debug(f"Content check enabled, looking for: {content_check[:30]}...")
    
    # Try multiple times
    for attempt in range(attempts):
        try:
            logger.debug(f"HTTP attempt {attempt+1}/{attempts} for {url}")
            # Make the request
            response = urllib.request.urlopen(url, timeout=timeout)
            status_code = response.getcode()
            logger.debug(f"Got status code {status_code} for {url}")
            
            # Check status code
            if status_code not in acceptable_codes:
                logger.debug(f"Status code {status_code} not in acceptable codes {acceptable_codes}")
                # If this isn't the last attempt, wait and retry
                if attempt < attempts - 1:
                    time.sleep(delay)
                    continue
                return False
                
            # If content check is specified, check for the string
            if content_check:
                # Strip quotes from the content check if present
                if (content_check.startswith('"') and content_check.endswith('"')) or \
                   (content_check.startswith("'") and content_check.endswith("'")):
                    content_check = content_check[1:-1]
                    
                content = response.read().decode('utf-8', errors='ignore')
                if content_check not in content:
                    logger.debug(f"Content check failed for {url}")
                    # If this isn't the last attempt, wait and retry
                    if attempt < attempts - 1:
                        time.sleep(delay)
                        continue
                    return False
                logger.debug(f"Content check passed for {url}")
                    
            logger.debug(f"HTTP check successful for {url}")
            return True  # Success if we got here
            
        except (urllib.error.URLError, urllib.error.HTTPError, ConnectionRefusedError, 
                TimeoutError, ValueError) as e:
            logger.debug(f"HTTP attempt {attempt+1} failed for {url}: {type(e).__name__} - {str(e)}")
            # If this isn't the last attempt, wait before trying again
            if attempt < attempts - 1:
                time.sleep(delay)
            else:
                return False
    
    # Should not reach here, but just in case
    logger.debug(f"All HTTP attempts failed for {url}")
    return False