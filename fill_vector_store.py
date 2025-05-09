#!/usr/bin/env python3
"""
Script to fill the vector store with all available data from both APIs.
With enhanced debugging for date extraction and storage.
"""
import sys
import json
import pprint
from datetime import datetime, timedelta
from pathlib import Path
import argparse
import pytz

# Add parent directory to path so we can import from the root
sys.path.append(str(Path(__file__).parent))

from storage.data_ingestion import DataIngestion
from storage.vector_store import FAISSVectorStore
from config import TIMEZONE

def parse_arguments():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description='Fill the vector store with data from both APIs.'
    )
    
    parser.add_argument(
        '--days', 
        type=int, 
        default=60,  # Increased from 30 to 60 days
        help='Number of days to fetch (default: 60)'
    )
    
    parser.add_argument(
        '--start-date', 
        type=str, 
        help='Start date in YYYY-MM-DD format (default: today minus days)'
    )
    
    parser.add_argument(
        '--end-date', 
        type=str, 
        help='End date in YYYY-MM-DD format (default: today)'
    )
    
    parser.add_argument(
        '--limit', 
        type=int, 
        default=None,  # Changed default to None (no limit) for more comprehensive data fetching
        help='Limit per day per API (default: no limit, fetch all)'
    )
    
    parser.add_argument(
        '--stats', 
        action='store_true',
        help='Show vector store stats after ingestion'
    )
    
    parser.add_argument(
        '--debug', 
        action='store_true',
        help='Show detailed debugging information'
    )
    
    parser.add_argument(
        '--analyze-dates',
        action='store_true',
        help='Perform in-depth analysis of date fields in the vector store'
    )
    
    parser.add_argument(
        '--force',
        action='store_true',
        help='Force fetch data even for dates that already have markdown files'
    )
    
    parser.add_argument(
        '--historical',
        action='store_true',
        help='Fetch historical data (up to 180 days in the past)'
    )
    
    return parser.parse_args()

def debug_document_dates(vector_store, prefix=""):
    """
    Debug date fields in all documents in the vector store.
    """
    print(f"\n{prefix}Debugging document dates in vector store...")
    date_formats = {}
    missing_dates = 0
    timestamp_formats = {}
    missing_timestamps = 0
    
    # Track documents by source
    docs_by_source = {}
    
    for i, doc in enumerate(vector_store.documents):
        source = doc.get("source", "unknown")
        if source not in docs_by_source:
            docs_by_source[source] = []
        docs_by_source[source].append(doc)
        
        # Check date field
        date = doc.get("date")
        if date:
            date_format = classify_date_format(date)
            date_formats[date_format] = date_formats.get(date_format, 0) + 1
        else:
            missing_dates += 1
            
        # Check timestamp field
        timestamp = doc.get("timestamp")
        if timestamp:
            ts_format = classify_date_format(timestamp)
            timestamp_formats[ts_format] = timestamp_formats.get(ts_format, 0) + 1
        else:
            missing_timestamps += 1
    
    # Print summary
    print(f"{prefix}Date field formats found:")
    for fmt, count in date_formats.items():
        print(f"{prefix}- {fmt}: {count} documents")
    if missing_dates:
        print(f"{prefix}- Missing date field: {missing_dates} documents")
    
    print(f"\n{prefix}Timestamp field formats found:")
    for fmt, count in timestamp_formats.items():
        print(f"{prefix}- {fmt}: {count} documents")
    if missing_timestamps:
        print(f"{prefix}- Missing timestamp field: {missing_timestamps} documents")
    
    # Print source-specific info
    print(f"\n{prefix}Documents by source:")
    for source, docs in docs_by_source.items():
        dates_for_source = set(doc.get("date") for doc in docs if doc.get("date"))
        dates_list = sorted(list(dates_for_source))
        dates_display = ", ".join(dates_list) if len(dates_list) <= 5 else f"{', '.join(dates_list[:5])}... ({len(dates_list)} total)"
        print(f"{prefix}- {source}: {len(docs)} documents with {len(dates_for_source)} unique dates: {dates_display}")

def analyze_vector_store_dates(vector_store):
    """
    Perform in-depth analysis of dates in the vector store.
    """
    print("\n=== Vector Store Date Analysis ===")
    
    # Analyze limitless documents
    limitless_docs = [doc for doc in vector_store.documents if doc.get("source") == "limitless"]
    print(f"Found {len(limitless_docs)} Limitless documents")
    
    # Group by date
    docs_by_date = {}
    date_extraction_fields = {}
    
    for doc in limitless_docs:
        # Check all the places where dates might be found
        date_from_date_field = doc.get("date")
        date_from_timestamp = extract_date_from_iso(doc.get("timestamp", ""))
        date_from_metadata_start = extract_date_from_iso(doc.get("metadata", {}).get("startTime", ""))
        
        # Record which field provided the date
        if date_from_date_field:
            if date_from_date_field not in docs_by_date:
                docs_by_date[date_from_date_field] = []
            docs_by_date[date_from_date_field].append(doc)
            
            # Log which field the date came from
            src_field = "date"
            if date_from_date_field == date_from_timestamp:
                src_field = "timestamp"
            elif date_from_date_field == date_from_metadata_start:
                src_field = "metadata.startTime"
                
            date_extraction_fields[date_from_date_field] = date_extraction_fields.get(date_from_date_field, {})
            date_extraction_fields[date_from_date_field][src_field] = date_extraction_fields[date_from_date_field].get(src_field, 0) + 1
    
    # Print date summary
    print(f"\nLimitless documents by date ({len(docs_by_date)} unique dates):")
    for date, docs in sorted(docs_by_date.items()):
        print(f"- {date}: {len(docs)} documents")
    
    # Print date extraction fields
    print("\nDate field sources:")
    for date, fields in date_extraction_fields.items():
        fields_str = ", ".join(f"{field}: {count}" for field, count in fields.items())
        print(f"- {date}: {fields_str}")
    
    # Sample document analysis
    if limitless_docs:
        print("\nSample document analysis:")
        sample_doc = limitless_docs[0]
        print("Document ID:", sample_doc.get("id", "N/A"))
        print("Source:", sample_doc.get("source", "N/A"))
        print("Date:", sample_doc.get("date", "N/A"))
        print("Timestamp:", sample_doc.get("timestamp", "N/A"))
        if "metadata" in sample_doc:
            print("Metadata fields:")
            for key, value in sample_doc["metadata"].items():
                print(f"  - {key}: {value}")
        
        # Check if the date is being extracted correctly
        date = sample_doc.get("date", "")
        timestamp = sample_doc.get("timestamp", "")
        if timestamp:
            extracted_date = extract_date_from_iso(timestamp)
            print(f"\nDate extraction check:")
            print(f"- Timestamp: {timestamp}")
            print(f"- Extracted date: {extracted_date}")
            print(f"- Stored date: {date}")
            print(f"- Match: {extracted_date == date}")

def extract_date_from_iso(iso_string):
    """Extract date from ISO datetime string."""
    if not iso_string:
        return ""
    parts = iso_string.split("T")
    if len(parts) > 0:
        return parts[0]
    return ""

def classify_date_format(date_string):
    """
    Classify the format of a date string.
    """
    if not date_string:
        return "empty"
    
    if "T" in date_string:
        if date_string.endswith("Z"):
            return "ISO8601 with Z"
        if "+" in date_string:
            return "ISO8601 with timezone"
        return "ISO8601"
    
    if "-" in date_string:
        parts = date_string.split("-")
        if len(parts) == 3:
            if len(parts[0]) == 4:
                return "YYYY-MM-DD"
            if len(parts[2]) == 4:
                return "DD-MM-YYYY"
    
    return "other"

def main():
    """Main function."""
    args = parse_arguments()
    
    print("=== Vector Store Data Ingestion ===")
    
    # Initialize data ingestion
    ingestion = DataIngestion()
    
    # Initialize vector store for stats
    vector_store = FAISSVectorStore()
    
    # Get timezone
    try:
        timezone = pytz.timezone(TIMEZONE)
        now = datetime.now(timezone)
        tz_name = now.strftime('%Z')
    except Exception:
        tz_name = TIMEZONE
        now = datetime.now()
        
    print(f"Using timezone: {TIMEZONE} ({tz_name})")
    print(f"Current time: {now.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    
    # Show initial stats if requested
    if args.stats or args.debug:
        initial_stats = vector_store.get_stats()
        print(f"\nInitial vector store stats:")
        print(f"- Total documents: {initial_stats['total_documents']}")
        for source, count in initial_stats.get('sources', {}).items():
            print(f"- {source}: {count} documents")
        print(f"- Dates: {len(initial_stats.get('dates', {}))} unique dates")
        
        if initial_stats.get('dates'):
            dates = sorted(list(initial_stats['dates'].keys()))
            date_counts = initial_stats.get('dates', {})
            if dates:
                print(f"- Date range: {dates[0]} to {dates[-1]}")
                print("- Documents per date:")
                for date in dates:
                    print(f"  - {date}: {date_counts.get(date, 0)} documents")
    
    # Run detailed date analysis if requested
    if args.analyze_dates:
        analyze_vector_store_dates(vector_store)
        return
    
    # Debug document dates before ingestion
    if args.debug:
        debug_document_dates(vector_store, "BEFORE: ")
    
    # For historical data, use a much longer time range
    days_to_fetch = 180 if args.historical else args.days
    
    # Determine date range
    start_date = args.start_date
    end_date = args.end_date
    
    if not start_date:
        if days_to_fetch > 1:
            # Start from days_to_fetch days ago
            start_date = (now - timedelta(days=days_to_fetch)).strftime('%Y-%m-%d')
        else:
            start_date = now.strftime('%Y-%m-%d')
            
    if not end_date:
        end_date = now.strftime('%Y-%m-%d')
        
    print(f"\nIngesting data from {start_date} to {end_date} (limit per day: {args.limit or 'ALL'})...")
    
    # If force is enabled, don't use existing markdown dates
    existing_dates = None if args.force else ingestion.data_syncer.get_existing_limitless_markdown_dates()
    if existing_dates:
        print(f"Found {len(existing_dates)} existing markdown dates. Use --force to ignore them.")
    elif args.force:
        print("Force mode enabled - will fetch all data regardless of existing markdown files")
    
    # Ingest data - split into multiple chunks for large date ranges
    total_days = (datetime.strptime(end_date, '%Y-%m-%d') - datetime.strptime(start_date, '%Y-%m-%d')).days + 1
    
    if total_days > 30:
        print(f"\nLarge date range detected ({total_days} days). Breaking into smaller chunks...")
        
        # Process in chunks of 30 days for better reliability
        chunk_size = 30
        current_date = datetime.strptime(start_date, '%Y-%m-%d')
        end_date_obj = datetime.strptime(end_date, '%Y-%m-%d')
        
        all_results = {
            "total_documents": 0,
            "processed_documents": 0,
            "added_to_vector_store": 0,
        }
        
        while current_date <= end_date_obj:
            chunk_end = min(current_date + timedelta(days=chunk_size-1), end_date_obj)
            
            chunk_start_str = current_date.strftime('%Y-%m-%d')
            chunk_end_str = chunk_end.strftime('%Y-%m-%d')
            
            print(f"\nProcessing chunk: {chunk_start_str} to {chunk_end_str}")
            
            # Ingest this chunk
            result = ingestion.ingest_data(
                start_date=chunk_start_str,
                end_date=chunk_end_str,
                limit_per_day=args.limit,
                existing_dates=existing_dates  # Pass existing dates to avoid duplicates
            )
            
            # Aggregate results
            all_results["total_documents"] += result.get("total_documents", 0)
            all_results["processed_documents"] += result.get("processed_documents", 0)
            all_results["added_to_vector_store"] += result.get("added_to_vector_store", 0)
            
            # Move to next chunk
            current_date = chunk_end + timedelta(days=1)
            
        result = all_results
    else:
        # Ingest data in one go for smaller ranges
        result = ingestion.ingest_data(
            start_date=start_date,
            end_date=end_date,
            days=days_to_fetch,
            limit_per_day=args.limit,  # None means no limit
            existing_dates=existing_dates
        )
    
    # Print results
    print(f"\nIngestion complete!")
    print(f"- Total documents prepared: {result.get('total_documents', 0)}")
    print(f"- Documents processed: {result.get('processed_documents', 0)}")
    print(f"- Documents added to vector store: {result.get('added_to_vector_store', 0)}")
    
    # Debug document dates after ingestion
    if args.debug:
        debug_document_dates(vector_store, "AFTER: ")
    
    # If debug mode and we added any documents, examine one
    if args.debug and result.get('added_to_vector_store', 0) > 0:
        print("\nExamining recently added document:")
        # Find a document from limitless source
        limitless_docs = [doc for doc in vector_store.documents if doc.get("source") == "limitless"]
        if limitless_docs:
            doc = limitless_docs[-1]  # Get the last one, likely recently added
            print(f"Document ID: {doc.get('id', 'N/A')}")
            print(f"Source: {doc.get('source', 'N/A')}")
            print(f"Date field: {doc.get('date', 'N/A')}")
            print(f"Timestamp field: {doc.get('timestamp', 'N/A')}")
            if doc.get('timestamp'):
                extracted_date = extract_date_from_iso(doc.get('timestamp'))
                print(f"Date extracted from timestamp: {extracted_date}")
                print(f"Matches date field: {extracted_date == doc.get('date', '')}")
            print(f"Metadata:")
            for k, v in doc.get('metadata', {}).items():
                print(f"- {k}: {v}")
    
    # Show final stats if requested
    if args.stats or args.debug:
        print("\nUpdating vector store stats...")
        final_stats = vector_store.get_stats()
        print(f"\nFinal vector store stats:")
        print(f"- Total documents: {final_stats['total_documents']}")
        for source, count in final_stats.get('sources', {}).items():
            print(f"- {source}: {count} documents")
        print(f"- Dates: {len(final_stats.get('dates', {}))} unique dates")
        
        # Show date range
        if final_stats.get('dates'):
            dates = sorted(list(final_stats['dates'].keys()))
            date_counts = final_stats.get('dates', {})
            if dates:
                print(f"- Date range: {dates[0]} to {dates[-1]}")
                print("- Documents per date:")
                for date in dates:
                    print(f"  - {date}: {date_counts.get(date, 0)} documents")
                
        # Count how many dates have markdown files and how many don't
        if 'limitless' in final_stats.get('sources', {}):
            existing_dates = ingestion.data_syncer.get_existing_limitless_markdown_dates() or set()
            limitless_dates = set()
            
            for doc in vector_store.documents:
                if doc.get("source") == "limitless" and doc.get("date"):
                    limitless_dates.add(doc.get("date"))
            
            dates_with_markdown = limitless_dates.intersection(existing_dates)
            dates_without_markdown = limitless_dates - existing_dates
            
            print(f"\n- Limitless dates with markdown files: {len(dates_with_markdown)}")
            print(f"- Limitless dates WITHOUT markdown files: {len(dates_without_markdown)}")
            
            if dates_without_markdown:
                print("\nDates missing markdown files:")
                for date in sorted(dates_without_markdown):
                    print(f"  - {date}")
                print("\nTo generate markdown for these dates, run:")
                print("python direct_markdown_generation.py")

if __name__ == "__main__":
    main()