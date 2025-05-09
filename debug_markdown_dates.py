#!/usr/bin/env python3
"""
Debug script to compare dates of Limitless data in the vector store with 
existing markdown files in the LIMITLESS_MD_TARGET directory.
This helps diagnose issues with markdown file generation.
"""
import sys
from pathlib import Path
from datetime import datetime
import calendar

# Add project root to sys.path to allow imports
project_root = Path(__file__).resolve().parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from storage.vector_store import FAISSVectorStore
from config import LIMITLESS_MD_TARGET

def get_vector_store_limitless_dates():
    """Get all dates from the vector store that have Limitless data."""
    # Initialize vector store
    vector_store = FAISSVectorStore()
    
    # Get all unique dates from Limitless documents
    limitless_dates = set()
    for doc in vector_store.documents:
        if doc.get("source") == "limitless" and doc.get("date"):
            limitless_dates.add(doc.get("date"))
    
    return limitless_dates

def get_existing_limitless_markdown_dates():
    """Get dates from existing Limitless markdown files."""
    existing_dates = set()
    
    try:
        limitless_md_path = Path(LIMITLESS_MD_TARGET)
        if not limitless_md_path.exists():
            print(f"Warning: Limitless markdown directory {LIMITLESS_MD_TARGET} does not exist")
            return existing_dates
        
        # Iterate through year/month-Month directories
        for year_dir in limitless_md_path.iterdir():
            if year_dir.is_dir():
                for month_dir in year_dir.iterdir():
                    if month_dir.is_dir():
                        for md_file in month_dir.iterdir():
                            if md_file.is_file() and md_file.suffix == ".md":
                                # Expected format: Month-DD-YYYY.md (e.g., May-07-2025.md)
                                try:
                                    parts = md_file.stem.split('-')
                                    if len(parts) == 3:
                                        month_name, day_str, year_str = parts
                                        
                                        # Convert month name to number (e.g., "May" → 5)
                                        month_num = datetime.strptime(month_name, "%B").month
                                        
                                        # Format as YYYY-MM-DD for comparison
                                        date_str = f"{year_str}-{month_num:02d}-{day_str}"
                                        existing_dates.add(date_str)
                                        print(f"Found markdown file for {date_str}: {md_file.name}")
                                except ValueError as e:
                                    print(f"Warning: Error parsing date from filename: {md_file.name} - {str(e)}")
    
    except Exception as e:
        print(f"Error scanning markdown directory: {str(e)}")
    
    return existing_dates

def get_limitless_data_by_date():
    """Get a count of Limitless documents for each date in the vector store."""
    vector_store = FAISSVectorStore()
    date_counts = {}
    
    for doc in vector_store.documents:
        if doc.get("source") == "limitless" and doc.get("date"):
            date = doc.get("date")
            date_counts[date] = date_counts.get(date, 0) + 1
    
    return date_counts

def check_specific_date(date_str):
    """Check if a specific date has data and/or markdown files."""
    vector_store = FAISSVectorStore()
    
    # Check if date exists in vector store
    date_docs = []
    for doc in vector_store.documents:
        if doc.get("source") == "limitless" and doc.get("date") == date_str:
            date_docs.append(doc)
    
    # Check if date exists in markdown files
    existing_dates = get_existing_limitless_markdown_dates()
    has_markdown = date_str in existing_dates
    
    print(f"\nDiagnosis for date {date_str}:")
    print(f"- Vector store documents: {len(date_docs)}")
    print(f"- Has markdown file: {has_markdown}")
    
    if len(date_docs) > 0 and not has_markdown:
        print("ISSUE DETECTED: This date has data but no markdown file!")
        
        # Show a sample of the data
        print("\nSample document:")
        doc = date_docs[0]
        print(f"- ID: {doc.get('id')}")
        print(f"- Timestamp: {doc.get('timestamp')}")
        if doc.get("summary"):
            print(f"- Summary: {doc.get('summary')}")

def main():
    """Main function to diagnose issues with markdown generation."""
    print("Debugging Limitless Markdown Generation")
    print("======================================")
    
    # Get LIMITLESS_MD_TARGET configuration
    print(f"LIMITLESS_MD_TARGET directory: {LIMITLESS_MD_TARGET}")
    
    # Get vector store stats
    vector_store = FAISSVectorStore()
    stats = vector_store.get_stats()
    total_docs = stats.get("total_documents", 0)
    limitless_count = stats.get("sources", {}).get("limitless", 0)
    
    print(f"\nVector Store Status:")
    print(f"- Total documents: {total_docs}")
    print(f"- Limitless documents: {limitless_count}")
    
    # Get dates with Limitless data
    limitless_dates = get_vector_store_limitless_dates()
    print(f"\nFound {len(limitless_dates)} unique dates with Limitless data:")
    for date in sorted(limitless_dates):
        print(f"- {date}")
    
    # Get dates with existing markdown files
    markdown_dates = get_existing_limitless_markdown_dates()
    print(f"\nFound {len(markdown_dates)} dates with existing markdown files:")
    for date in sorted(markdown_dates):
        print(f"- {date}")
    
    # Find missing markdown dates (dates that have data but no markdown)
    missing_dates = limitless_dates - markdown_dates
    print(f"\nFound {len(missing_dates)} dates with MISSING markdown files:")
    for date in sorted(missing_dates):
        print(f"- {date}")
    
    # Extra files (dates with markdown but no data)
    extra_dates = markdown_dates - limitless_dates
    if extra_dates:
        print(f"\nWARNING: Found {len(extra_dates)} dates with markdown files but NO corresponding data:")
        for date in sorted(extra_dates):
            print(f"- {date}")
    
    # Get document counts per date
    date_counts = get_limitless_data_by_date()
    print(f"\nDocument counts per date:")
    for date in sorted(date_counts.keys()):
        markdown_status = "✓" if date in markdown_dates else "✗"
        print(f"- {date}: {date_counts[date]} document(s) {markdown_status}")
    
    # Check a specific date if there are missing dates
    if missing_dates:
        # Check the first missing date as an example
        sample_date = sorted(missing_dates)[0]
        check_specific_date(sample_date)
        
        print("\nTroubleshooting Recommendations:")
        print("1. Check if the MarkdownGenerator's _get_conversations_by_date_source method is finding the documents")
        print("2. Check if date comparison in direct_markdown_generation.py is working correctly")
        print("3. Verify the directory structure in LIMITLESS_MD_TARGET exists and is writable")
        print("4. Try generating markdown manually for a specific date using direct_markdown_generation.py with a date argument")

if __name__ == "__main__":
    main()