from _client import get_lifelogs
from config import LIMITLESS_API_KEY, JSON_TEST

def main():
    """
    Main function to fetch lifelog data using the client
    """
    print(f"Fetching lifelogs (JSON_TEST = {JSON_TEST})...")
    
    # Get a single lifelog entry (most recent)
    lifelogs = get_lifelogs(
        api_key=LIMITLESS_API_KEY,
        limit=3,
        direction="desc"  # Get newest first
    )
    
    if not lifelogs:
        print("No lifelogs found.")
        return
    
    # Print results summary
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