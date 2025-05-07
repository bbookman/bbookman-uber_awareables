import os
import json
import requests
import tzlocal
from datetime import datetime
from pathlib import Path
from config import LIMITLESS_INCLUDE_MARKDOWN, LIMITLESS_INCLUDE_HEADINGS, LIMITLESS_ROOT_URL, JSON_TEST, LIMITLESS_V1_LIFELOGS_ENDPOINT
from debug_json import save_json_response

def get_lifelogs(api_key, api_url=LIMITLESS_ROOT_URL, endpoint=LIMITLESS_V1_LIFELOGS_ENDPOINT, limit=50, batch_size=10, includeMarkdown=LIMITLESS_INCLUDE_MARKDOWN, includeHeadings=LIMITLESS_INCLUDE_HEADINGS, date=None, timezone=None, direction="desc"):
    """
    Fetch lifelogs from the Limitless API, stopping when we hit existing data.
    
    Args:
        api_key: Limitless API key
        api_url: Base API URL
        endpoint: API endpoint
        limit: Maximum number of lifelogs to fetch (None means fetch all)
        batch_size: Number of lifelogs to fetch per request
        includeMarkdown: Whether to include markdown in response
        includeHeadings: Whether to include headings in response
        date: Date to fetch lifelogs for (YYYY-MM-DD)
        timezone: Timezone for dates
        direction: Sort direction ("asc" or "desc")
    
    Returns:
        List of lifelog objects
    """
    all_lifelogs = []
    cursor = None
    latest_date = None
    
    # If limit is None, fetch all available lifelogs
    # Otherwise, set a batch size and fetch until we reach the limit
    if limit is not None:
        batch_size = min(batch_size, limit)
    
    while True:
        params = {  
            "limit": batch_size,
            "includeMarkdown": "true" if includeMarkdown else "false",
            "includeHeadings": "true" if includeHeadings else "false",
            "date": date,
            "direction": direction,
            "timezone": timezone if timezone else str(tzlocal.get_localzone())
        }
        
        # Add cursor for pagination if we have one
        if cursor:
            params["cursor"] = cursor
            
        response = requests.get(
            f"{api_url}/{endpoint}",
            headers={"X-API-Key": api_key},
            params=params,
        )

        if not response.ok:
            raise Exception(f"HTTP error! Status: {response.status_code}")

        data = response.json()
        
        # Save the response to a JSON file if JSON_TEST is enabled
        save_json_response(data, endpoint, JSON_TEST)
        
        lifelogs = data.get("data", {}).get("lifelogs", [])
        
        # Stop if we got no lifelogs
        if not lifelogs:
            break
            
        # Check dates to see if we have new data
        for lifelog in lifelogs:
            lifelog_date = lifelog.get('startTime', '').split('T')[0]
            
            # If this is our first batch, store the latest date
            if not latest_date:
                latest_date = lifelog_date
            
            # If we're in descending order and hit a date earlier than our latest,
            # we've found all new data
            elif direction == "desc" and lifelog_date < latest_date:
                return all_lifelogs
            
            # If we're in ascending order and hit a date later than our latest,
            # we've found all new data
            elif direction == "asc" and lifelog_date > latest_date:
                return all_lifelogs
            
            all_lifelogs.append(lifelog)
        
        # Check if we've reached the requested limit
        if limit is not None and len(all_lifelogs) >= limit:
            return all_lifelogs[:limit]
        
        # Get the next cursor from the response
        next_cursor = data.get("meta", {}).get("lifelogs", {}).get("nextCursor")
        
        # If there's no next cursor or we got fewer results than requested, we're done
        if not next_cursor or len(lifelogs) < batch_size:
            break
            
        print(f"Fetched {len(lifelogs)} lifelogs, next cursor: {next_cursor}")
        cursor = next_cursor
    
    return all_lifelogs
