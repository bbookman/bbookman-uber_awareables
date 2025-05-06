import os
import json
import requests
import tzlocal
from datetime import datetime
from pathlib import Path
from config import BEE_ROOT_URL, BEE_CONVERSATIONS_ENDPOINT, JSON_TEST
from debug_json import save_json_response

def get_conversations(api_key, api_url=BEE_ROOT_URL, endpoint=BEE_CONVERSATIONS_ENDPOINT, limit=50, batch_size=10, date=None, timezone=None, direction="asc"):
    """
    Fetch conversations from the Bee API.
    
    Args:
        api_key: Bee API key
        api_url: Base URL for the Bee API
        endpoint: API endpoint for conversations
        limit: Maximum number of conversations to fetch
        batch_size: Number of conversations to fetch per request
        date: Date to filter conversations by (ISO format)
        timezone: Timezone for the date filter
        direction: Sort direction ('asc' or 'desc')
    
    Returns:
        List of conversation objects
    """
    all_conversations = []
    cursor = None
    
    # If limit is None, fetch all available conversations
    # Otherwise, set a batch size and fetch until we reach the limit
    if limit is not None:
        batch_size = min(batch_size, limit)
    
    while True:
        params = {
            "limit": batch_size,
            "date": date,
            "direction": direction,
            "timezone": timezone if timezone else str(tzlocal.get_localzone())
        }
        
        # Add cursor for pagination if we have one
        if cursor:
            params["cursor"] = cursor
            
        response = requests.get(
            f"{api_url}{endpoint}",
            headers={"x-api-key": api_key},
            params=params,
        )

        if not response.ok:
            raise Exception(f"HTTP error! Status: {response.status_code}, Details: {response.text}")

        data = response.json()
        
        # Save the response to a JSON file if JSON_TEST is enabled
        save_json_response(data, endpoint, JSON_TEST)
        
        conversations = data.get("conversations", [])
        
        # Add conversations from this batch
        for conversation in conversations:
            all_conversations.append(conversation)
        
        # Check if we've reached the requested limit
        if limit is not None and len(all_conversations) >= limit:
            return all_conversations[:limit]
        
        # Get the next cursor from the response if available
        # Note: This might need adjustment based on actual Bee API pagination mechanism
        next_cursor = data.get("next_cursor")
        
        # If there's no next cursor or we got fewer results than requested, we're done
        if not next_cursor or len(conversations) < batch_size:
            break
            
        print(f"Fetched {len(conversations)} conversations, next cursor: {next_cursor}")
        cursor = next_cursor
    
    return all_conversations

def get_conversation_details(conversation_id, api_key, api_url=BEE_ROOT_URL, endpoint=BEE_CONVERSATIONS_ENDPOINT):
    """
    Fetch details for a specific conversation from the Bee API.
    
    Args:
        conversation_id: ID of the conversation to fetch
        api_key: Bee API key
        api_url: Base URL for the Bee API
        endpoint: API endpoint for conversations
    
    Returns:
        Conversation details object including transcriptions
    """
    response = requests.get(
        f"{api_url}{endpoint}/{conversation_id}",
        headers={"x-api-key": api_key}
    )
    
    if not response.ok:
        raise Exception(f"HTTP error! Status: {response.status_code}, Details: {response.text}")
    
    data = response.json()
    
    # Save the response to a JSON file if JSON_TEST is enabled
    save_json_response(data, f"{endpoint}/{conversation_id}", JSON_TEST)
    
    return data