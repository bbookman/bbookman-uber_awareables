from api.limitless_api import get_lifelogs
from api.bee_api import get_conversations, get_conversation_details
from api.data_sync import DataSyncer
from config import LIMITLESS_API_KEY, BEE_API_KEY, JSON_TEST

def main():
    """
    Main function to fetch data from both Limitless and Bee APIs
    """
    print("=== Testing API Clients ===")
    
    # Test Limitless API
    print("\n== Limitless API ==")
    print(f"Fetching lifelogs (JSON_TEST = {JSON_TEST})...")
    
    lifelogs = get_lifelogs(
        api_key=LIMITLESS_API_KEY,
        limit=3,
        direction="desc"  # Get newest first
    )
    
    if not lifelogs:
        print("No lifelogs found.")
    else:
        print(f"Retrieved {len(lifelogs)} lifelog entries")
        
        # Print first lifelog details
        lifelog = lifelogs[0]
        print(f"\nLifelog ID: {lifelog.get('id')}")
        print(f"Created at: {lifelog.get('createdAt')}")
        print(f"Updated at: {lifelog.get('updatedAt')}")
        
        # If markdown is included
        if "markdown" in lifelog:
            print("\nMarkdown content:")
            print("-----------------")
            print(lifelog["markdown"])

if __name__ == "__main__":
    main()