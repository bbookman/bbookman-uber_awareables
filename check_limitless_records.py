#!/usr/bin/env python3
"""
Script to check for records in the limitless namespace in the vector store.
Displays up to 3 records if found, or prints "none found" if none exist.
"""
import sys
from pathlib import Path
from typing import List, Dict, Any

# Add project root to sys.path to allow imports
project_root = Path(__file__).resolve().parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from storage.vector_store import FAISSVectorStore

def check_limitless_records(limit: int = 3) -> List[Dict[str, Any]]:
    """
    Check for records in the limitless namespace of the vector store.
    
    Args:
        limit: Maximum number of records to retrieve
        
    Returns:
        List of records found (up to limit)
    """
    # Initialize vector store
    vector_store = FAISSVectorStore()
    
    # Get stats to check if there are any limitless records
    stats = vector_store.get_stats()
    limitless_count = stats.get("sources", {}).get("limitless", 0)
    
    if limitless_count == 0:
        return []
    
    # Find records from the limitless source
    limitless_records = []
    for doc in vector_store.documents:
        if doc.get("source") == "limitless":
            # Create a simplified version of the document with key information
            record = {
                "id": doc.get("id", "unknown"),
                "date": doc.get("date", "unknown"),
                "timestamp": doc.get("timestamp", ""),
                "summary": doc.get("summary", "No summary available")
            }
            
            # Add text snippet if available (truncated for readability)
            if "text" in doc:
                text = doc.get("text", "")
                record["text_snippet"] = text[:100] + "..." if len(text) > 100 else text
                
            limitless_records.append(record)
            
            # Stop once we've reached the limit
            if len(limitless_records) >= limit:
                break
                
    return limitless_records

def format_record(record: Dict[str, Any], index: int) -> str:
    """Format a record for display."""
    result = f"Record {index}:\n"
    result += f"  ID: {record.get('id')}\n"
    result += f"  Date: {record.get('date')}\n"
    result += f"  Time: {record.get('timestamp')}\n"
    result += f"  Summary: {record.get('summary')}\n"
    
    if "text_snippet" in record:
        result += f"  Text: {record.get('text_snippet')}\n"
        
    return result

def main():
    """Main function."""
    print("Checking for limitless records in the vector store...")
    
    # Get up to 3 limitless records
    records = check_limitless_records(limit=3)
    
    if not records:
        print("\nNone found")
        print("No records found in the limitless namespace in the vector store.")
        return
    
    print(f"\nFound {len(records)} record(s) in the limitless namespace:")
    
    # Display each record
    for i, record in enumerate(records, 1):
        print("\n" + format_record(record, i))
    
    # Print total count from stats
    vector_store = FAISSVectorStore()
    stats = vector_store.get_stats()
    total_limitless = stats.get("sources", {}).get("limitless", 0)
    
    if total_limitless > len(records):
        print(f"\nNote: {total_limitless - len(records)} additional limitless records exist in the vector store.")
    
    limitless_ids = {doc.get("id") for doc in vector_store.documents if doc.get("source") == "limitless"}
    print(f"Unique limitless IDs: {len(limitless_ids)}")

if __name__ == "__main__":
    main()