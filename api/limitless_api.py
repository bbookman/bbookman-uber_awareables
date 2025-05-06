import os
import json
import requests
import tzlocal
from datetime import datetime
from pathlib import Path
from config import LIMITLESS_INCLUDE_MARKDOWN, LIMITLESS_INCLUDE_HEADINGS, LIMITLESS_ROOT_URL, JSON_TEST, LIMITLESS_V1_LIFELOGS_ENDPOINT
from debug_json import save_json_response

def get_lifelogs(api_key, api_url=LIMITLESS_ROOT_URL, endpoint=LIMITLESS_V1_LIFELOGS_ENDPOINT, limit=50, batch_size=10, includeMarkdown=LIMITLESS_INCLUDE_MARKDOWN, includeHeadings=LIMITLESS_INCLUDE_HEADINGS, date=None, timezone=None, direction="asc"):
    all_lifelogs = []
    cursor = None
    
    # If limit is None, fetch all available lifelogs
    # Otherwise, set a batch size (e.g., 10) and fetch until we reach the limit
    if limit is not None:
        batch_size = min(batch_size, limit)
    
    while True:
        params = {  
            "limit": batch_size,
            "includeMarkdown": "true" if includeMarkdown else "false",
            "includeHeadings": "false" if includeHeadings else "true",
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
        
        # Add transcripts from this batch
        for lifelog in lifelogs:
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
