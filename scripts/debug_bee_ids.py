#!/usr/bin/env python3
"""
Debug script to identify issues with Bee conversation ID duplication.

This script analyzes the FAISS vector store to identify Bee conversation IDs
that already exist but are being re-added during data ingestion.
"""
import sys
import json
from pathlib import Path
from pprint import pprint

# Add parent directory to path so we can import from the root
sys.path.append(str(Path(__file__).parent.parent))

from storage.vector_store import FAISSVectorStore
from api.bee_api import get_conversations, get_conversation_details
from api.data_sync import DataSyncer

def analyze_bee_ids():
    """
    Analyze Bee conversation IDs in the vector store and identify potential duplicates.
    """
    print("=== Bee Conversation ID Analysis ===\n")
    
    # Initialize vector store
    print("Loading vector store...")
    vector_store = FAISSVectorStore()
    
    # Get all Bee document IDs from the vector store
    bee_ids = vector_store.get_document_ids("bee")
    
    # Parse the IDs to remove the "bee_" prefix
    clean_ids = {id.replace('bee_', '') for id in bee_ids}
    
    print(f"Found {len(clean_ids)} Bee conversation IDs in vector store.\n")
    
    # Check for example IDs from logs - this is for demo purposes
    example_log_ids = [
        "1670048", "1668776", "1667013", "1666284", "1664656",
        "1663054", "1661984", "1660789", "1660417", "1658089",
        "1642679"
    ]
    
    print("Checking IDs from logs against stored IDs...")
    for id in example_log_ids:
        if id in clean_ids:
            print(f"⚠️ ID: {id} - ALREADY EXISTS in vector store, but was being re-added")
        else:
            print(f"✓ ID: {id} - New ID (not in vector store)")
    
    # Compare with most recent API results
    print("\nFetching first page of Bee conversations from API to compare...")
    try:
        # Initialize data syncer
        syncer = DataSyncer()
        
        # Get the first page of conversations (limited to 10 for quick comparison)
        conversations = get_conversations(limit=10)
        if conversations:
            print(f"Retrieved {len(conversations)} recent conversations from API")
            
            for conversation in conversations:
                conversation_id = conversation.get('id')
                if not conversation_id:
                    continue
                
                # Check if this ID already exists in our vector store
                if conversation_id in clean_ids:
                    print(f"⚠️ ID: {conversation_id} - EXISTS in vector store but would be re-fetched")
                else:
                    print(f"✓ ID: {conversation_id} - New ID (not in vector store)")
        else:
            print("No conversations returned from API")
    except Exception as e:
        print(f"Error fetching Bee conversations: {e}")
    
    # Debug ID extraction logic
    print("\n=== Debug ID Extraction Logic ===")
    print("Example document IDs from vector store:")
    
    # Get a few example documents
    bee_docs = [doc for doc in vector_store.documents if doc.get('source') == 'bee'][:5]
    
    for i, doc in enumerate(bee_docs, 1):
        print(f"\nDocument {i}:")
        print(f"  ID: {doc.get('id')}")
        print(f"  Raw ID without prefix: {doc.get('id', '').replace('bee_', '')}")
        print(f"  Source: {doc.get('source')}")
        print(f"  Date: {doc.get('date')}")
    
    print("\n=== Vector Store Function Analysis ===")
    # Print the actual implementation of key functions
    print("The get_document_ids function returns:")
    print("  {doc.get('id') for doc in self.documents if doc.get('source') == source and doc.get('id')}")
    
    # Verify how IDs are being compared in fetch_bee_data
    print("\n=== ID Comparison Test ===")
    test_id = next(iter(clean_ids)) if clean_ids else "example_id"
    
    test_cases = [
        test_id,                # Plain ID
        f"bee_{test_id}",       # With prefix
        f" {test_id} ",         # With whitespace
        f"{test_id}\n",         # With newline
    ]
    
    for case in test_cases:
        matches = case in clean_ids
        print(f"Testing '{case}' against ID set: {'✓ MATCH' if matches else '❌ NO MATCH'}")

def main():
    """Main function."""
    analyze_bee_ids()
    
    print("\n=== Recommendations ===")
    print("1. Ensure IDs are properly extracted and compared in fetch_bee_data")
    print("2. Check that existing_ids is correctly populated from vector_store.get_document_ids")
    print("3. Verify the data types match when comparing IDs (strings vs integers)")
    print("4. Add more debug logging around ID comparison in the fetch_bee_data method")
    print("5. Consider adding a script to deduplicate existing vector store entries")

if __name__ == "__main__":
    main()