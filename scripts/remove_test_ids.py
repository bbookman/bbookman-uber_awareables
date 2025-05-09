#!/usr/bin/env python3
"""
Script to remove specific test Bee IDs from the vector store.

This script identifies and removes test IDs that were added during development
or debugging sessions.
"""
import sys
from pathlib import Path
import re

# Add parent directory to path so we can import from the root
sys.path.append(str(Path(__file__).parent.parent))

from storage.vector_store import FAISSVectorStore

def remove_test_ids():
    """Remove specific test IDs from the vector store."""
    print("=== Cleaning Test IDs from Vector Store ===\n")
    
    # Initialize vector store
    print("Loading vector store...")
    vector_store = FAISSVectorStore()
    
    # Test IDs to remove - these came from testing or sample data
    test_ids_to_remove = [
        "bee_528954",
        "528954",
        " 528954",
        "528954 ",
        " 528954 "
    ]
    
    # Also remove any IDs with variations like spaces, newlines, etc.
    # We'll use regex to match these
    base_id = "528954"
    regex_pattern = re.compile(f"^\\s*bee_*{base_id}\\s*$")
    
    # Count how many documents we're starting with
    total_docs_before = len(vector_store.documents)
    bee_docs_before = len([d for d in vector_store.documents if d.get("source") == "bee"])
    
    print(f"Starting with {total_docs_before} total documents ({bee_docs_before} Bee documents)")
    
    # Track IDs that were successfully removed
    removed_ids = []
    
    # First, try direct ID matches
    for test_id in test_ids_to_remove:
        # Try both with and without the "bee_" prefix
        for id_variant in [test_id, f"bee_{test_id}" if not test_id.startswith("bee_") else test_id]:
            if vector_store.delete_document(id_variant):
                print(f"✓ Successfully removed document with ID: {id_variant}")
                removed_ids.append(id_variant)
    
    # Then use regex to catch any other variations
    remaining_docs = [doc for doc in vector_store.documents]
    for doc in remaining_docs:
        doc_id = doc.get("id", "")
        if regex_pattern.match(doc_id):
            if vector_store.delete_document(doc_id):
                print(f"✓ Removed document with regex-matched ID: {doc_id}")
                removed_ids.append(doc_id)
    
    # Count how many documents we have after cleanup
    total_docs_after = len(vector_store.documents)
    bee_docs_after = len([d for d in vector_store.documents if d.get("source") == "bee"])
    
    print(f"\nRemoved {len(removed_ids)} test documents")
    print(f"Now have {total_docs_after} total documents ({bee_docs_after} Bee documents)")
    
    # Print a summary of what was removed
    if removed_ids:
        print("\nRemoved the following IDs:")
        for id in removed_ids:
            print(f"  - {id}")
    else:
        print("\nNo test IDs were found in the vector store.")

def main():
    """Main function."""
    remove_test_ids()
    
    print("\nCleanup complete. The vector store no longer contains the specified test IDs.")

if __name__ == "__main__":
    main()