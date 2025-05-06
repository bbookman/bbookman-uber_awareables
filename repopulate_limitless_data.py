#!/usr/bin/env python3
"""
Script to repopulate the Limitless data in the vector store.
This will fix issues with missing data for certain dates.
"""
import sys
from pathlib import Path
import json
from datetime import datetime, timedelta
import time
import traceback

# Add parent directory to path so we can import from the root
sys.path.append(str(Path(__file__).parent))

from config import LIMITLESS_API_KEY, TIMEZONE
from api.limitless_api import get_lifelogs
from storage.vector_store import FAISSVectorStore
from storage.embeddings import DocumentEmbedder

def extract_text_from_lifelog(lifelog):
    """Extract text content from a lifelog using multiple fallback methods"""
    try:
        # Try to extract from content nodes (preferred method)
        if lifelog.get('contents'):
            contents = []
            for node in lifelog['contents']:
                if node.get('content'):
                    content = node.get('content', '')
                    # Handle speaker content
                    if node.get('speakerName'):
                        content = f"{node['speakerName']}: {content}"
                    contents.append(content)
            if contents:
                return '\n'.join(contents)
        
        # Fallback to title if nothing else is available
        if lifelog.get('title'):
            return lifelog['title']
    except Exception as e:
        print(f"Error extracting text from lifelog: {e}")
        print(f"Lifelog keys: {list(lifelog.keys())}")
    
    return ""

def format_lifelog_for_vector_store(lifelog):
    """Format a lifelog entry for the vector store"""
    try:
        text = extract_text_from_lifelog(lifelog)
        
        # Extract date from startTime, with fallbacks
        date = None
        if 'startTime' in lifelog and lifelog['startTime']:
            try:
                date = lifelog['startTime'].split('T')[0]
            except (AttributeError, IndexError):
                pass
        
        # Create a summary from title
        summary = lifelog.get('title', '')
        if not summary and text:
            # Use first 100 chars of text as summary if no title
            summary = text[:100] + ('...' if len(text) > 100 else '')
        
        # Calculate duration
        duration = 0
        try:
            if 'startTime' in lifelog and 'endTime' in lifelog:
                start = datetime.fromisoformat(lifelog['startTime'].replace('Z', '+00:00'))
                end = datetime.fromisoformat(lifelog['endTime'].replace('Z', '+00:00'))
                duration = int((end - start).total_seconds())
        except Exception:
            pass
        
        return {
            "id": f"limitless_{lifelog.get('id', '')}",
            "source": "limitless",
            "text": text,
            "summary": summary,
            "date": date,
            "timestamp": lifelog.get('startTime', ''),
            "metadata": {
                "startTime": lifelog.get('startTime', ''),
                "endTime": lifelog.get('endTime', ''),
                "duration": duration,
                "title": lifelog.get('title', ''),
                "location": "Limitless"
            }
        }
    except Exception as e:
        print(f"Error formatting lifelog for vector store: {e}")
        return None

def get_date_range(days=30):
    """Get a range of dates ending today"""
    today = datetime.now()
    dates = []
    for i in range(days):
        date = today - timedelta(days=i)
        dates.append(date.strftime('%Y-%m-%d'))
    return dates

def fetch_and_process_limitless_data(days=30, limit_per_day=10):
    """Fetch and process Limitless data for the specified number of days"""
    print(f"Fetching Limitless data for the past {days} days (up to {limit_per_day} entries per day)")
    
    # Get dates to process
    dates = get_date_range(days)
    
    # Set up for vector store
    vector_store = FAISSVectorStore()
    embedder = DocumentEmbedder()
    
    # Keep track of existing Limitless documents to replace
    limitless_doc_ids = set()
    for doc in vector_store.documents:
        if doc.get('source') == 'limitless':
            limitless_doc_ids.add(doc.get('id'))
    
    print(f"Found {len(limitless_doc_ids)} existing Limitless documents in vector store")
    
    # Process each date
    all_documents = []
    processed_dates = 0
    
    for date_str in dates:
        print(f"\nProcessing date: {date_str}")
        
        try:
            # Fetch data from Limitless API for this date
            lifelogs = get_lifelogs(
                api_key=LIMITLESS_API_KEY,
                date=date_str,
                limit=limit_per_day,
                includeHeadings=True  # We want headings for better content extraction
            )
            
            if not lifelogs:
                print(f"  No data found for {date_str}")
                continue
                
            print(f"  Retrieved {len(lifelogs)} lifelogs")
            
            # If this is the first date with data, print some debug info
            if processed_dates == 0 and lifelogs:
                sample = lifelogs[0]
                print("\nSample lifelog structure:")
                print(f"  Keys: {list(sample.keys())}")
                if 'contents' in sample and sample['contents']:
                    print(f"  Content node keys: {list(sample['contents'][0].keys())}")
                print("\n")
                
            processed_dates += 1
            
            # Process each lifelog
            date_documents = []
            for lifelog in lifelogs:
                document = format_lifelog_for_vector_store(lifelog)
                
                # Only add if we have some text content and a valid date
                if document and document['text'] and document['date']:
                    date_documents.append(document)
                else:
                    print(f"  Skipping lifelog {lifelog.get('id', 'unknown')} - missing text or date")
            
            all_documents.extend(date_documents)
            print(f"  Processed {len(lifelogs)} lifelogs into {len(date_documents)} documents")
            
            # Don't hammer the API
            time.sleep(0.5)
            
        except Exception as e:
            print(f"  Error processing date {date_str}: {e}")
            traceback.print_exc()
    
    print(f"\nFetched a total of {len(all_documents)} Limitless documents from {processed_dates} dates")
    
    if not all_documents:
        print("No documents to add to vector store. Exiting.")
        return
    
    # Remove existing Limitless documents from vector store
    if limitless_doc_ids:
        filtered_documents = []
        for doc in vector_store.documents:
            if doc.get('source') != 'limitless':
                filtered_documents.append(doc)
        
        removed_count = len(vector_store.documents) - len(filtered_documents)
        print(f"Removed {removed_count} existing Limitless documents")
        vector_store.documents = filtered_documents
    
    # Add the new documents to the vector store
    docs_to_embed = []
    texts_to_embed = []
    
    for document in all_documents:
        text = document.get('text', '')
        if text:
            docs_to_embed.append(document)
            texts_to_embed.append(text)
    
    print(f"Embedding {len(texts_to_embed)} documents")
    
    # Generate embeddings in batches to avoid memory issues
    batch_size = 32
    total_batches = (len(texts_to_embed) + batch_size - 1) // batch_size
    
    for i in range(0, len(texts_to_embed), batch_size):
        try:
            batch_texts = texts_to_embed[i:i+batch_size]
            batch_docs = docs_to_embed[i:i+batch_size]
            
            # Generate embeddings for this batch
            print(f"  Generating embeddings for batch {i//batch_size + 1}/{total_batches}")
            # Get embeddings for the batch
            embeddings = embedder.embed_texts(batch_texts)
            
            # Instead of adding documents one by one, prepare a batch with embeddings
            docs_with_embeddings = []
            for j, doc in enumerate(batch_docs):
                # Add the embedding directly to the document
                doc_copy = doc.copy()  # Create a copy to avoid modifying the original
                docs_with_embeddings.append(doc_copy)
            
            # Add the batch of documents to the vector store
            vector_store.add_documents(docs_with_embeddings)
            print(f"  Added batch {i//batch_size + 1}/{total_batches} to vector store")
            
        except Exception as e:
            print(f"  Error processing batch starting at index {i}: {e}")
            traceback.print_exc()
    
    # Save the updated vector store
    try:
        vector_store._save()
        print(f"Saved {len(vector_store.documents)} total documents to vector store")
    except Exception as e:
        print(f"Error saving vector store: {e}")
        traceback.print_exc()
    
    # Print some statistics
    try:
        # Count by source
        sources = {}
        for doc in vector_store.documents:
            source = doc.get('source')
            if source not in sources:
                sources[source] = 0
            sources[source] += 1
        
        print("\nVector store statistics:")
        for source, count in sources.items():
            print(f"  {source}: {count} documents")
        
        # Count by date
        dates = {}
        for doc in vector_store.documents:
            date = doc.get('date')
            source = doc.get('source')
            if not date:
                continue
                
            if date not in dates:
                dates[date] = {"bee": 0, "limitless": 0}
            if source in dates[date]:
                dates[date][source] += 1
        
        # Print distribution of the last 10 dates
        print("\nDate distribution (last 10 days):")
        last_ten_dates = sorted(list(dates.keys()))[-10:]
        for date in last_ten_dates:
            print(f"  {date}: Bee: {dates[date].get('bee', 0)}, Limitless: {dates[date].get('limitless', 0)}")
    except Exception as e:
        print(f"Error generating statistics: {e}")

if __name__ == "__main__":
    # Use command-line arguments if provided
    import argparse
    parser = argparse.ArgumentParser(description='Repopulate Limitless data in vector store')
    parser.add_argument('--days', type=int, default=30, help='Number of days to process')
    parser.add_argument('--limit', type=int, default=10, help='Maximum entries per day (max 10)')
    args = parser.parse_args()
    
    try:
        fetch_and_process_limitless_data(days=args.days, limit_per_day=args.limit)
    except Exception as e:
        print(f"Fatal error: {e}")
        traceback.print_exc()