import os
import json
import asyncio
from datetime import datetime
from pathlib import Path
from beeai import Bee
from config import BEE_API_KEY, JSON_TEST
from debug_json import save_json_response

async def get_conversations_async(api_key=BEE_API_KEY, limit=50, page=1):
    """
    Asynchronously fetch conversations from the Bee API using the beeai library.
    
    Args:
        api_key: Bee API key
        limit: Maximum number of conversations per page
        page: Page number for pagination
    
    Returns:
        List of conversation objects
    """
    bee = Bee(api_key)
    
    try:
        # The beeai library only supports page and limit parameters
        response = await bee.get_conversations("me", page=page, limit=limit)
        
        # Save the response to a JSON file if JSON_TEST is enabled
        save_json_response(response, "/v1/me/conversations", JSON_TEST)
        
        return response.get("conversations", [])
    except Exception as e:
        print(f"Error fetching conversations: {str(e)}")
        return []

async def get_conversation_details_async(conversation_id, api_key=BEE_API_KEY):
    """
    Asynchronously fetch details for a specific conversation from the Bee API using the beeai library.
    
    Args:
        conversation_id: ID of the conversation to fetch
        api_key: Bee API key
    
    Returns:
        Conversation details object
    """
    bee = Bee(api_key)
    
    try:
        response = await bee.get_conversation("me", conversation_id)
        
        # Save the response to a JSON file if JSON_TEST is enabled
        save_json_response(response, f"/v1/me/conversations/{conversation_id}", JSON_TEST)
        
        return response
    except Exception as e:
        print(f"Error fetching conversation details: {str(e)}")
        return {}

# Synchronous wrapper functions for compatibility with existing code
def get_conversations(api_key=BEE_API_KEY, limit=50, page=1, **kwargs):
    """
    Synchronous wrapper for get_conversations_async.
    
    Note: Other parameters like date and direction are ignored since the beeai 
    library doesn't support them directly.
    """
    return asyncio.run(get_conversations_async(api_key=api_key, limit=limit, page=page))

def get_conversation_details(conversation_id, api_key=BEE_API_KEY):
    """
    Synchronous wrapper for get_conversation_details_async.
    """
    return asyncio.run(get_conversation_details_async(conversation_id, api_key))