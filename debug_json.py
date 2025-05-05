import json
from datetime import datetime
from pathlib import Path

def save_json_response(data, endpoint, json_test=False):
    """
    Save API response to JSON file if JSON_TEST is enabled
    """
    if not json_test:
        return
    
    # Create json_test directory if it doesn't exist
    json_dir = Path("./json_test")
    json_dir.mkdir(exist_ok=True, parents=True)
    
    # Create a timestamp for the filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Create a filename based on the endpoint and timestamp
    endpoint_name = endpoint.replace('/', '_').strip('_')
    filename = f"{endpoint_name}_{timestamp}.json"
    filepath = json_dir / filename
    
    # Write JSON response to file
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)
    
    print(f"Saved API response to {filepath}")