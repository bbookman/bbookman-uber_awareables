#!/usr/bin/env python3
"""
Test script to make a single request to the Limitless API and validate
if data is received and properly stored in the vector database.
This script stops after a single page and provides detailed diagnostics.
"""
import os
import sys
import json
import time
import requests
import traceback
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta
import tzlocal

# Add parent directory to path
sys.path.append(str(Path(__file__).parent))

from config import LIMITLESS_API_KEY, LIMITLESS_ROOT_URL, LIMITLESS_V1_LIFELOGS_ENDPOINT
from storage.vector_store import FAISSVectorStore
from storage.embeddings import DocumentEmbedder
from api.limitless_api import get_lifelogs
from api.data_sync import DataSyncer

def make_direct_request(api_key, max_retries=3, retry_delay=2):
    """Make a direct request to the Limitless API for diagnostic purposes."""
    print("Making direct request to Limitless API...")
    
    # Set parameters for the request - keep it minimal
    params = {
        "includeMarkdown": "false", 
        "includeHeadings": "true",
        "direction": "desc",
        "timezone": str(tzlocal.get_localzone())
    }
    
    # Try the request with retries
    for attempt in range(max_retries):
        try:
            print(f"\nAttempt {attempt + 1} of {max_retries}")
            print(f"URL: {LIMITLESS_ROOT_URL}/{LIMITLESS_V1_LIFELOGS_ENDPOINT}")
            print(f"Params: {json.dumps(params, indent=2)}")
            
            start_time = time.time()
            response = requests.get(
                f"{LIMITLESS_ROOT_URL}/{LIMITLESS_V1_LIFELOGS_ENDPOINT}",
                headers={"X-API-Key": api_key},
                params=params,
                timeout=30  # Set a reasonable timeout
            )
            duration = time.time() - start_time
            
            print(f"Request completed in {duration:.2f} seconds")
            print(f"Status code: {response.status_code}")
            print(f"Headers: {json.dumps(dict(response.headers), indent=2)}")
            
            if response.ok:
                try:
                    data = response.json()
                    print(f"Response size: {len(response.content)} bytes")
                    
                    # Extract the interesting parts of the response
                    lifelogs = data.get("data", {}).get("lifelogs", [])
                    meta = data.get("meta", {}).get("lifelogs", {})
                    
                    print(f"Received {len(lifelogs)} lifelogs")
                    print(f"Meta info: {meta}")
                    
                    # Save the response to a file for inspection
                    with open("limitless_response.json", "w") as f:
                        json.dump(data, f, indent=2)
                    print("Response saved to limitless_response.json")
                    
                    return data
                except json.JSONDecodeError:
                    print("Error parsing JSON response:")
                    print(f"Raw response: {response.text[:500]}...")
            else:
                print(f"Error response: {response.text}")
            
        except requests.exceptions.Timeout:
            print(f"Request timed out after {attempt + 1} attempt(s)")
        except Exception as e:
            print(f"Error during request: {str(e)}")
            traceback.print_exc()
        
        # Wait before retrying
        if attempt < max_retries - 1:
            print(f"Retrying in {retry_delay} seconds...")
            time.sleep(retry_delay)
    
    print("All attempts failed")
    return None

def process_and_save_to_vector_store(data):
    """Process the response data and save to vector store."""
    if not data:
        print("No data to process")
        return 0
        
    lifelogs = data.get("data", {}).get("lifelogs", [])
    if not lifelogs:
        print("No lifelogs in response")
        return 0
    
    print(f"Processing {len(lifelogs)} lifelogs for vector store...")
    
    # Initialize vector store and data syncer
    vector_store = FAISSVectorStore()
    data_syncer = DataSyncer()
    
    # Prepare data in the format expected by the vector store
    data_for_syncer = {'limitless': lifelogs, 'bee': {}}
    processed_docs = data_syncer.combine_data_for_vector_storage(data_for_syncer)
    
    if not processed_docs:
        print("No documents extracted after processing")
        return 0
    
    print(f"Extracted {len(processed_docs)} documents to add to vector store")
    
    # Extract text and generate embeddings
    texts = [doc.get("text", "") for doc in processed_docs if doc.get("text")]
    if not texts:
        print("No text content found in documents")
        return 0
        
    print(f"Generating embeddings for {len(texts)} documents...")
    
    try:
        # Generate embeddings
        model = vector_store.model
        embeddings = model.encode(texts)
        embeddings = np.array(embeddings).astype('float32')
        
        # Add to index
        current_size = vector_store.index.ntotal
        vector_store.index.add(embeddings)
        
        # Add metadata
        for i, doc in enumerate(processed_docs):
            if i < len(texts):  # Only add docs that had text
                doc_with_idx = dict(doc)
                doc_with_idx["vector_id"] = current_size + i
                vector_store.documents.append(doc_with_idx)
        
        # Save changes
        vector_store._save()
        print(f"Added {len(texts)} documents to vector store")
        return len(texts)
    except Exception as e:
        print(f"Error adding documents to vector store: {str(e)}")
        traceback.print_exc()
        return 0

def check_limitless_records():
    """Check if Limitless records exist in the vector store."""
    print("\nChecking for Limitless records in vector store...")
    
    vector_store = FAISSVectorStore()
    stats = vector_store.get_stats()
    limitless_count = stats.get("sources", {}).get("limitless", 0)
    
    print(f"Found {limitless_count} Limitless records in vector store")
    
    # Find a few examples if available
    if limitless_count > 0:
        limitless_docs = []
        for doc in vector_store.documents:
            if doc.get("source") == "limitless":
                # Create a simplified version of the document for display
                doc_info = {
                    "id": doc.get("id", "unknown"),
                    "date": doc.get("date", "unknown"),
                    "timestamp": doc.get("timestamp", ""),
                    "summary": doc.get("summary", "No summary available"),
                    "text_snippet": doc.get("text", "")[:100] + "..." if len(doc.get("text", "")) > 100 else doc.get("text", "")
                }
                limitless_docs.append(doc_info)
                
                # Only show first 3 examples
                if len(limitless_docs) >= 3:
                    break
        
        print(f"\nSample Limitless records ({min(3, len(limitless_docs))} of {limitless_count}):")
        for i, doc in enumerate(limitless_docs, 1):
            print(f"\nRecord {i}:")
            print(f"  ID: {doc.get('id')}")
            print(f"  Date: {doc.get('date')}")
            print(f"  Time: {doc.get('timestamp')}")
            print(f"  Summary: {doc.get('summary')}")
            print(f"  Text: {doc.get('text_snippet')}")
    
    return limitless_count

def main():
    """Main function."""
    print("=" * 80)
    print("LIMITLESS API TEST - SINGLE PAGE REQUEST")
    print("=" * 80)
    
    # Check if the API key is available
    if not LIMITLESS_API_KEY:
        print("Error: No Limitless API key found. Please set the LIMITLESS_API_KEY in your environment or config.")
        return
    
    # Get initial vector store stats
    vector_store = FAISSVectorStore()
    before_stats = vector_store.get_stats()
    limitless_count_before = before_stats.get("sources", {}).get("limitless", 0)
    print(f"Before request: {limitless_count_before} Limitless records in vector store")
    
    # Test 1: Direct API request with detailed logging
    print("\n=== TEST 1: Direct API Request ===")
    response_data = make_direct_request(LIMITLESS_API_KEY)
    
    # Test 2: Process and save to vector store
    print("\n=== TEST 2: Process and Save to Vector Store ===")
    docs_added = process_and_save_to_vector_store(response_data)
    
    # Test 3: Using built-in get_lifelogs function (single page)
    print("\n=== TEST 3: Built-in get_lifelogs Function (Single Page) ===")
    try:
        print("Calling get_lifelogs()...")
        start_time = time.time()
        lifelogs = get_lifelogs(
            api_key=LIMITLESS_API_KEY,
            batch_size=10,  # Limit to a small batch
            limit=10         # Only retrieve a few records
        )
        duration = time.time() - start_time
        
        print(f"get_lifelogs() completed in {duration:.2f} seconds")
        print(f"Retrieved {len(lifelogs)} lifelogs")
        
        # Show a sample if available
        if lifelogs:
            print("\nSample lifelog:")
            sample = lifelogs[0]
            print(f"  ID: {sample.get('id', 'unknown')}")
            print(f"  Start Time: {sample.get('startTime', 'unknown')}")
            print(f"  Contents: {len(sample.get('contents', []))} items")
    except Exception as e:
        print(f"Error in get_lifelogs(): {str(e)}")
        traceback.print_exc()
    
    # Check the final state of the vector store
    print("\n=== FINAL VECTOR STORE STATE ===")
    final_count = check_limitless_records()
    
    print("\n=" * 40)
    print(f"SUMMARY: Started with {limitless_count_before} Limitless records")
    print(f"         Processed and added {docs_added} new records")
    print(f"         Final count: {final_count} Limitless records")
    print(f"         Net change: {final_count - limitless_count_before} records")
    print("=" * 80)

if __name__ == "__main__":
    main()