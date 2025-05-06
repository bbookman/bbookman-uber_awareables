#!/usr/bin/env python3
"""
Script to fill the vector store with all available data from both APIs.
"""
import sys
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
        default=30, 
        help='Number of days to fetch (default: 30)'
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
        default=None,
        help='Limit per day per API (default: no limit, fetch all)'
    )
    
    parser.add_argument(
        '--stats', 
        action='store_true',
        help='Show vector store stats after ingestion'
    )
    
    return parser.parse_args()

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
    if args.stats:
        initial_stats = vector_store.get_stats()
        print(f"\nInitial vector store stats:")
        print(f"- Total documents: {initial_stats['total_documents']}")
        for source, count in initial_stats.get('sources', {}).items():
            print(f"- {source}: {count} documents")
        print(f"- Dates: {len(initial_stats.get('dates', {}))} unique dates")
        
        if initial_stats.get('dates'):
            dates = sorted(list(initial_stats['dates'].keys()))
            if dates:
                print(f"- Date range: {dates[0]} to {dates[-1]}")
    
    # Determine date range
    start_date = args.start_date
    end_date = args.end_date
    
    if not start_date:
        if args.days > 1:
            start_date = (now - timedelta(days=args.days-1)).strftime('%Y-%m-%d')
        else:
            start_date = now.strftime('%Y-%m-%d')
            
    if not end_date:
        end_date = now.strftime('%Y-%m-%d')
        
    print(f"\nIngesting data from {start_date} to {end_date} (limit per day: {args.limit or 'ALL'})...")
    
    # Ingest data
    result = ingestion.ingest_data(
        start_date=start_date,
        end_date=end_date,
        days=args.days,
        limit_per_day=args.limit  # None means no limit
    )
    
    # Print results
    print(f"\nIngestion complete!")
    print(f"- Total documents prepared: {result.get('total_documents', 0)}")
    print(f"- Documents processed: {result.get('processed_documents', 0)}")
    print(f"- Documents added to vector store: {result.get('added_to_vector_store', 0)}")
    
    # Show final stats if requested
    if args.stats:
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
            if dates:
                print(f"- Date range: {dates[0]} to {dates[-1]}")

if __name__ == "__main__":
    main()