#!/usr/bin/env python3
"""
Test script to debug Limitless API data for May 3, 2025
This will help identify why the data isn't appearing in the vector store
"""
import sys
from pathlib import Path
import json
from datetime import datetime

# Add parent directory to path so we can import from the root
sys.path.append(str(Path(__file__).parent))

from config import LIMITLESS_API_KEY
from api.limitless_api import get_lifelogs
from api.data_sync import DataSyncer
from storage.vector_store import FAISSVectorStore

def inspect_limitless_data():
    """Fetch and inspect Limitless data for May 3, 2025"""
    print("=== Testing Limitless API for May 3, 2025 ===")
    
    # 1. Fetch data directly from Limitless API
    print("\n== Step 1: Direct API Fetch ==")
    target_date = "2025-05-03"
    print(f"Fetching lifelogs for date: {target_date}")
    
    try:
        lifelogs = get_lifelogs(
            api_key=LIMITLESS_API_KEY,
            date=target_date,
            limit=5  # Just get a few for testing
        )
        
        if not lifelogs:
            print("No lifelogs found from API for this date.")
        else:
            print(f"Retrieved {len(lifelogs)} lifelog entries from API")
            
            # Print first lifelog details with all fields
            print("\nFirst lifelog fields:")
            lifelog = lifelogs[0]
            for key, value in lifelog.items():
                if key != 'transcript' and key != 'markdown':  # Skip very long fields
                    print(f"  {key}: {value}")
            
            # Check specific fields needed for vector storage
            print("\nChecking specific needed fields:")
            print(f"  ID: {lifelog.get('id', 'MISSING')}")
            print(f"  Has transcript: {'Yes' if 'transcript' in lifelog else 'No'}")
            print(f"  Has text: {'Yes' if 'text' in lifelog else 'No'}")
            print(f"  Has content: {'Yes' if 'content' in lifelog else 'No'}")
            print(f"  Has markdown: {'Yes' if 'markdown' in lifelog else 'No'}")
            print(f"  Start time: {lifelog.get('startTime', 'MISSING')}")
            print(f"  Date field format:")
            for field in ['startTime', 'createdAt', 'date']:
                if field in lifelog:
                    print(f"    {field}: {lifelog[field]}")
                    
            # Test the date extraction logic
            print("\nTesting date extraction logic:")
            extracted_date = lifelog.get('startTime', '').split('T')[0] if 'startTime' in lifelog else None
            print(f"  Extracted date using current logic: {extracted_date}")
            
            # Try alternative date extraction approaches
            print("\nAlternative date extraction approaches:")
            if 'contents' in lifelog and lifelog['contents']:
                first_content = lifelog['contents'][0]
                if 'startTime' in first_content:
                    print(f"  From first content node: {first_content['startTime'].split('T')[0]}")
    except Exception as e:
        print(f"Error fetching from API: {e}")
    
    # 2. Process the data using DataSyncer
    print("\n== Step 2: Data Processing ==")
    syncer = DataSyncer()
    try:
        data = syncer.synchronize_data(
            start_date=target_date, 
            end_date=target_date, 
            limit_per_day=5
        )
        
        limitless_data = data.get('limitless', [])
        if not limitless_data:
            print("No Limitless data processed by DataSyncer.")
        else:
            print(f"DataSyncer processed {len(limitless_data)} Limitless entries")
    except Exception as e:
        print(f"Error in data sync: {e}")
    
    # 3. Convert to vector store format
    print("\n== Step 3: Vector Store Document Conversion ==")
    try:
        documents = DataSyncer.combine_data_for_vector_storage(data)
        
        limitless_docs = [doc for doc in documents if doc.get('source') == 'limitless']
        if not limitless_docs:
            print("No Limitless documents created for vector store.")
        else:
            print(f"Created {len(limitless_docs)} Limitless documents for vector store")
            print("\nFirst document fields:")
            for key, value in limitless_docs[0].items():
                if key != 'text' and key != 'original':  # Skip very long fields
                    print(f"  {key}: {value}")
                    
            # Check if date field is set correctly
            print(f"\nDate field in document: {limitless_docs[0].get('date')}")
    except Exception as e:
        print(f"Error converting data: {e}")
    
    # 4. Check what's in the vector store
    print("\n== Step 4: Checking Vector Store ==")
    vector_store = FAISSVectorStore()
    print(f"Vector store has {len(vector_store.documents)} total documents")
    
    # Count by source
    sources = {}
    dates = {}
    for doc in vector_store.documents:
        source = doc.get('source')
        date = doc.get('date')
        
        if source not in sources:
            sources[source] = 0
        sources[source] += 1
        
        if date:
            if date not in dates:
                dates[date] = {"bee": 0, "limitless": 0}
            if source in dates[date]:
                dates[date][source] += 1
    
    for source, count in sources.items():
        print(f"  {source}: {count} documents")
    
    # Look for May 3 documents
    print("\nDate distribution in vector store:")
    date_list = sorted(list(dates.keys()))
    for date in date_list[-10:]:  # Show last 10 dates
        print(f"  {date}: Bee: {dates[date].get('bee', 0)}, Limitless: {dates[date].get('limitless', 0)}")
    
    # Look for May 3 Limitless documents specifically
    may3_limitless = [
        doc for doc in vector_store.documents 
        if doc.get('source') == 'limitless' and doc.get('date') == target_date
    ]
    
    print(f"\nFound {len(may3_limitless)} Limitless documents for {target_date} in vector store")
    
    # 5. Suggest fixes
    print("\n== Step 5: Diagnosis ==")
    if not lifelogs:
        print("PROBLEM: No data from Limitless API for May 3, 2025.")
        print("SOLUTION: Check your API key and make sure the API can return data for that date.")
    elif not limitless_docs:
        print("PROBLEM: Data exists in API but not being processed correctly.")
        print("SOLUTION: Update the data_sync.py to match the actual fields in the Limitless API response.")
        print("          Try this fix:")
        print("""
        In data_sync.py, modify the date extraction logic:
        
        # Original code
        'date': lifelog.get('startTime', '').split('T')[0] if 'startTime' in lifelog else None,
        
        # Modified code with more fallbacks:
        'date': (
            lifelog.get('startTime', '').split('T')[0] if lifelog.get('startTime') else
            lifelog.get('date') if lifelog.get('date') else
            None
        ),
        """)
    elif not may3_limitless:
        print("PROBLEM: Data processed correctly but not found in vector store.")
        print("SOLUTION: Re-run data ingestion to add the documents to the vector store:")
        print("          python -c 'from api.data_sync import DataSyncer; syncer = DataSyncer(); data = syncer.synchronize_data(start_date=\"2025-05-03\", end_date=\"2025-05-03\"); from storage.vector_store import FAISSVectorStore; from storage.data_ingestion import DataIngestion; data_ingestion = DataIngestion(); data_ingestion.ingest_synchronized_data(data)'")
    else:
        print("No issues detected. Limitless data for May 3, 2025 is being processed correctly.")
    
    return lifelogs, limitless_docs, may3_limitless

if __name__ == "__main__":
    inspect_limitless_data()