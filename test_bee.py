import asyncio
from beeai import Bee
from config import BEE_API_KEY
from api.bee_api import get_conversations, get_conversation_details

async def test_bee_async():
    """
    Test the Bee API using the beeai library directly
    """
    print("=== Testing Bee API with beeai library ===")
    
    # Initialize the Bee SDK client
    bee = Bee(BEE_API_KEY)
    
    try:
        # Get recent conversations - use only page and limit parameters
        print("\nFetching conversations...")
        conversations_response = await bee.get_conversations("me", page=1, limit=3)
        conversations = conversations_response.get("conversations", [])
        
        if not conversations:
            print("No conversations found.")
            return
            
        print(f"Retrieved {len(conversations)} conversations")
        
        # Print first conversation summary
        conversation = conversations[0]
        print(f"\nConversation ID: {conversation.get('id')}")
        print(f"Start time: {conversation.get('start_time')}")
        print(f"End time: {conversation.get('end_time')}")
        print(f"Short summary: {conversation.get('short_summary')}")
        
        # Get detailed information for the first conversation
        conversation_id = conversation.get('id')
        print(f"\nFetching details for conversation ID: {conversation_id}")
        
        details = await bee.get_conversation("me", conversation_id)
        print(f"Retrieved conversation details with {len(str(details))} characters")
        
        # Print transcript snippet if available
        transcript = details.get('transcript')
        if transcript:
            print("\nTranscript snippet (first 200 chars):")
            print(f"{transcript[:200]}...")
        else:
            print("No transcript found in the conversation details.")
        
    except Exception as e:
        print(f"Error during Bee API test: {str(e)}")

def test_bee_sync():
    """
    Test the Bee API using our synchronous wrapper functions
    """
    print("=== Testing Bee API with our wrapper functions ===")
    
    try:
        # Get recent conversations - use page and limit parameters
        print("\nFetching conversations...")
        conversations = get_conversations(page=1, limit=3)
        
        if not conversations:
            print("No conversations found.")
            return
            
        print(f"Retrieved {len(conversations)} conversations")
        
        # Print first conversation summary
        conversation = conversations[0]
        print(f"\nConversation ID: {conversation.get('id')}")
        print(f"Start time: {conversation.get('start_time')}")
        print(f"End time: {conversation.get('end_time')}")
        print(f"Short summary: {conversation.get('short_summary')}")
        
        # Get detailed information for the first conversation
        conversation_id = conversation.get('id')
        print(f"\nFetching details for conversation ID: {conversation_id}")
        
        details = get_conversation_details(conversation_id)
        print(f"Retrieved conversation details with {len(str(details))} characters")
        
        # Print transcript snippet if available
        transcript = details.get('transcript')
        if transcript:
            print("\nTranscript snippet (first 200 chars):")
            print(f"{transcript[:200]}...")
        else:
            print("No transcript found in the conversation details.")
        
    except Exception as e:
        print(f"Error during Bee API test: {str(e)}")

if __name__ == "__main__":
    # Test the async API
    asyncio.run(test_bee_async())
    
    print("\n" + "-" * 50 + "\n")
    
    # Test our synchronous wrapper functions
    test_bee_sync()