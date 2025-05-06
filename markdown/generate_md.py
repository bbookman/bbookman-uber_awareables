#!/usr/bin/env python3
"""
Command-line script to generate markdown files from conversation data.
"""
import sys
import argparse
from pathlib import Path
from datetime import datetime, timedelta
import pytz

# Add parent directory to path so we can import from the root
sys.path.append(str(Path(__file__).parent.parent))

from markdown.generator import MarkdownGenerator
from config import BEE_MD_TARGET, LIMITLESS_MD_TARGET, TIMEZONE

def parse_arguments():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description='Generate markdown files from conversation data.'
    )
    
    parser.add_argument(
        '--days', 
        type=int, 
        default=1, 
        help='Number of days to generate (default: 1)'
    )
    
    parser.add_argument(
        '--date',
        type=str,
        help='Specific date in YYYY-MM-DD format to generate markdown for'
    )
    
    parser.add_argument(
        '--start-date', 
        type=str, 
        help='Start date in YYYY-MM-DD format (default: today minus days-1)'
    )
    
    parser.add_argument(
        '--end-date', 
        type=str, 
        help='End date in YYYY-MM-DD format (default: today)'
    )
    
    parser.add_argument(
        '--source', 
        type=str, 
        choices=['all', 'limitless', 'bee'], 
        default='all',
        help='Data source to generate markdown for (default: all)'
    )
    
    parser.add_argument(
        '--force', 
        action='store_true', 
        help='Force regeneration of existing files'
    )
    
    parser.add_argument(
        '--limitless-path', 
        type=str, 
        default=LIMITLESS_MD_TARGET,
        help=f'Output path for Limitless markdown files (default: {LIMITLESS_MD_TARGET})'
    )
    
    parser.add_argument(
        '--bee-path', 
        type=str, 
        default=BEE_MD_TARGET,
        help=f'Output path for Bee markdown files (default: {BEE_MD_TARGET})'
    )
    
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Print debug information about conversations found'
    )
    
    return parser.parse_args()

def main():
    """Main function."""
    args = parse_arguments()
    
    # Initialize markdown generator
    generator = MarkdownGenerator(
        limitless_output_path=args.limitless_path,
        bee_output_path=args.bee_path,
        debug=args.debug
    )
    
    # Get current time in the configured timezone
    try:
        timezone = pytz.timezone(TIMEZONE)
        now = datetime.now(timezone)
        tz_name = now.strftime('%Z')
    except Exception:
        tz_name = TIMEZONE
        now = datetime.now()
    
    print(f"Generating markdown files")
    print(f"Using timezone: {TIMEZONE} ({tz_name})")
    print(f"Current time: {now.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    print(f"Limitless output path: {args.limitless_path}")
    print(f"Bee output path: {args.bee_path}")
    print(f"Force regenerate: {args.force}")
    
    # Generate markdown files
    results = []
    
    # Handle --date parameter for a specific date
    if args.date:
        print(f"Generating markdown for specific date: {args.date}")
        results = generator.generate_daily_markdown(
            args.date,
            force_regenerate=args.force
        )
    
    # Handle specific source
    elif args.source != 'all':
        # For a specific source, we'll override the generator method
        # to only generate markdown for that source
        if args.start_date and args.end_date:
            # Generate for date range
            start = datetime.strptime(args.start_date, '%Y-%m-%d')
            end = datetime.strptime(args.end_date, '%Y-%m-%d')
            
            results = []
            # Iterate through each day in the range
            current_date = start
            while current_date <= end:
                date_str = current_date.strftime('%Y-%m-%d')
                date_obj = datetime.strptime(date_str, '%Y-%m-%d')
                
                # Generate markdown for just this source and date
                result = generator._generate_source_markdown(date_obj, args.source, args.force)
                if result:
                    results.append(result)
                
                current_date += timedelta(days=1)
        else:
            # Generate for the specified number of days
            start_date = None
            end_date = None
            
            if args.start_date:
                start_date = args.start_date
            
            if args.end_date:
                end_date = args.end_date
                
            # Adapt our existing method to only handle one source
            results = []
            days = args.days
            
            # Set default dates if not provided
            if not start_date:
                if days > 1:
                    start_date = (now - timedelta(days=days-1)).strftime('%Y-%m-%d')
                else:
                    start_date = now.strftime('%Y-%m-%d')
                    
            if not end_date:
                end_date = now.strftime('%Y-%m-%d')
                
            # Parse dates
            start = datetime.strptime(start_date, '%Y-%m-%d')
            end = datetime.strptime(end_date, '%Y-%m-%d')
            
            # Iterate through each day in the date range
            current_date = start
            while current_date <= end:
                date_str = current_date.strftime('%Y-%m-%d')
                date_obj = datetime.strptime(date_str, '%Y-%m-%d')
                
                # Generate markdown for just this source and date
                result = generator._generate_source_markdown(date_obj, args.source, args.force)
                if result:
                    results.append(result)
                
                current_date += timedelta(days=1)
    else:
        # Generate for all sources
        if args.start_date and args.end_date:
            results = generator.generate_date_range(
                start_date=args.start_date,
                end_date=args.end_date,
                force_regenerate=args.force
            )
        else:
            results = generator.generate_date_range(
                days=args.days,
                force_regenerate=args.force
            )
    
    # Print results
    if results:
        print(f"\nGenerated {len(results)} markdown files:")
        for result in results:
            conversations = result.get('conversations_count', 0)
            source = result.get('source', 'unknown')
            date = result.get('date', 'unknown date')
            status = result.get('status', 'unknown status')
            print(f"- {date}: {source} ({status}, {conversations} conversations)")
    else:
        print("No markdown files were generated.")

if __name__ == "__main__":
    main()