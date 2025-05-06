import sys
import os
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import calendar
import pytz
import json

# Add parent directory to path so we can import from the root
sys.path.append(str(Path(__file__).parent.parent))

from config import MARKDOWN_OUTPUT_PATH, BEE_MD_TARGET, LIMITLESS_MD_TARGET, TIMEZONE
from storage.vector_store import FAISSVectorStore
from storage.data_ingestion import DataIngestion

class MarkdownGenerator:
    """
    Class to generate markdown files from stored conversation data.
    Handles both Bee and Limitless data with separate output directories.
    """
    
    def __init__(self, limitless_output_path=LIMITLESS_MD_TARGET, bee_output_path=BEE_MD_TARGET, debug=False):
        """
        Initialize the markdown generator.
        
        Args:
            limitless_output_path: Base directory for Limitless markdown files
            bee_output_path: Base directory for Bee markdown files
            debug: Whether to print debug information
        """
        self.limitless_output_path = Path(limitless_output_path)
        self.bee_output_path = Path(bee_output_path)
        self.debug = debug
        
        # Create output directories if they don't exist
        self.limitless_output_path.mkdir(exist_ok=True, parents=True)
        self.bee_output_path.mkdir(exist_ok=True, parents=True)
        
        self.vector_store = FAISSVectorStore()
        self.data_ingestion = DataIngestion()
        
        # Set up timezone
        try:
            self.timezone = pytz.timezone(TIMEZONE)
        except pytz.exceptions.UnknownTimeZoneError:
            print(f"Warning: Unknown timezone '{TIMEZONE}', falling back to America/New_York")
            self.timezone = pytz.timezone("America/New_York")
            
        if self.debug:
            print(f"Vector store has {len(self.vector_store.documents)} documents")
            stats = self.vector_store.get_stats()
            print(f"- Bee: {stats.get('sources', {}).get('bee', 0)} documents")
            print(f"- Limitless: {stats.get('sources', {}).get('limitless', 0)} documents")
            dates = sorted(list(stats.get('dates', {}).keys()))
            if dates:
                print(f"- Date range: {dates[0]} to {dates[-1]}")

    def _get_month_name(self, month_number):
        """
        Get the full month name for a month number.
        
        Args:
            month_number: Month as an integer (1-12)
            
        Returns:
            Full month name (e.g., "January")
        """
        return calendar.month_name[month_number]
    
    def _get_output_path(self, date_obj, source):
        """
        Get the appropriate output path for a date and source.
        
        Args:
            date_obj: Date as a datetime object
            source: Data source ("limitless" or "bee")
            
        Returns:
            Path object for the year/month directory
        """
        # Select the base path based on the source
        if source.lower() == "limitless":
            base_path = self.limitless_output_path
        else:  # Assume "bee" for any other source
            base_path = self.bee_output_path
        
        # Get year and month components
        year = date_obj.year
        month = date_obj.month
        month_name = self._get_month_name(month)
        
        # Create directory structure: YYYY/MM-MMMM/
        year_dir = base_path / f"{year}"
        month_dir = year_dir / f"{month:02d}-{month_name}"
        
        # Create directories if they don't exist
        month_dir.mkdir(exist_ok=True, parents=True)
        
        return month_dir
    
    def _get_filename(self, date_obj):
        """
        Generate a filename for a specific date.
        
        Args:
            date_obj: Date as a datetime object
            
        Returns:
            Filename in format MMMM-DD-YYYY.md
        """
        month_name = self._get_month_name(date_obj.month)
        return f"{month_name}-{date_obj.day:02d}-{date_obj.year}.md"
    
    def _format_timestamp(self, timestamp_str, format_str='%I:%M %p'):
        """
        Format a timestamp string in the configured timezone.
        
        Args:
            timestamp_str: Timestamp string in ISO format
            format_str: Format string for strftime
            
        Returns:
            Formatted timestamp string
        """
        if not timestamp_str:
            return ""
            
        try:
            # Parse the timestamp with timezone awareness
            dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            
            # Convert to the configured timezone
            localized_dt = dt.astimezone(self.timezone)
            
            # Format the timestamp
            return localized_dt.strftime(format_str)
        except Exception as e:
            print(f"Error formatting timestamp {timestamp_str}: {e}")
            return ""
    
    def generate_daily_markdown(self, date_str=None, force_regenerate=False):
        """
        Generate markdown files for a specific date for both Bee and Limitless data.
        
        Args:
            date_str: Date in YYYY-MM-DD format, defaults to today
            force_regenerate: Whether to regenerate existing files
            
        Returns:
            List of dictionaries with information about generated files
        """
        if not date_str:
            # Use the configured timezone to get today's date
            now = datetime.now(self.timezone)
            date_str = now.strftime('%Y-%m-%d')
            
        # Parse the date
        date_obj = datetime.strptime(date_str, '%Y-%m-%d')
        
        results = []
        
        # Generate Limitless markdown
        limitless_result = self._generate_source_markdown(date_obj, "limitless", force_regenerate)
        if limitless_result:
            results.append(limitless_result)
        
        # Generate Bee markdown
        bee_result = self._generate_source_markdown(date_obj, "bee", force_regenerate)
        if bee_result:
            results.append(bee_result)
        
        return results
    
    def _get_conversations_by_date_source(self, date_str, source):
        """
        Get all conversations for a specific date and source using direct vector store access.
        This is an alternative to using the search_conversations method which may not work correctly.
        
        Args:
            date_str: Date in YYYY-MM-DD format
            source: Data source ("limitless" or "bee")
            
        Returns:
            List of conversation objects
        """
        # Debug output
        if self.debug:
            print(f"Getting conversations for date: {date_str}, source: {source}")
            
        # Collect matching conversations
        results = []
        
        # Iterate through all documents in the vector store
        for doc in self.vector_store.documents:
            # Check if the document is from the requested source
            if doc.get("source") != source.lower():
                continue
                
            # Check if the document's date matches
            doc_date = doc.get("date")
            if doc_date != date_str:
                continue
                
            # This document matches both source and date
            results.append(doc)
            
        # Debug output
        if self.debug:
            print(f"Found {len(results)} conversations for {source} on {date_str}")
            # Print brief details about each conversation
            for i, conv in enumerate(results):
                if i < 3:  # Only show first 3 conversations to avoid overwhelming output
                    print(f"  {i+1}. ID: {conv.get('id', 'unknown')}, " 
                        f"Time: {conv.get('timestamp', 'unknown')}")
        
        return results

    def _generate_source_markdown(self, date_obj, source, force_regenerate=False):
        """
        Generate a markdown file for a specific date and source.
        
        Args:
            date_obj: Date as a datetime object
            source: Data source ("limitless" or "bee")
            force_regenerate: Whether to regenerate existing files
            
        Returns:
            Dictionary with information about the generated file
        """
        # Get the date string in YYYY-MM-DD format for searching conversations
        date_str = date_obj.strftime('%Y-%m-%d')
        
        # Get the output directory
        output_dir = self._get_output_path(date_obj, source)
        
        # Generate filename
        filename = self._get_filename(date_obj)
        
        # Full path to the output file
        output_file = output_dir / filename
        
        # Check if file already exists and we're not forcing regeneration
        if output_file.exists() and not force_regenerate:
            print(f"Markdown file {output_file} already exists. Use force_regenerate=True to overwrite.")
            return {
                "date": date_str,
                "source": source,
                "file": str(output_file),
                "status": "skipped",
                "conversations_count": 0
            }
        
        # Try multiple methods to find conversations
        results = self._get_conversations_by_date_source(date_str, source)
        
        # If no conversations found with direct access, try the search method as fallback
        if not results:
            if self.debug:
                print(f"No conversations found with direct access, trying search...")
            
            results = self.data_ingestion.search_conversations(
                query="",
                k=100,
                date=date_str,
                source=source
            )
        
        # If still no conversations found, return a result showing 0 conversations
        if not results:
            if self.debug:
                print(f"No {source} conversations found for date {date_str}")
            return {
                "date": date_str,
                "source": source,
                "file": None,
                "status": "no_conversations",
                "conversations_count": 0
            }
        
        # Sort results by timestamp
        results.sort(key=lambda x: x.get("timestamp", ""))
        
        # Generate markdown content
        markdown_content = self._generate_markdown_content(date_obj, results, source)
        
        # Write to file
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(markdown_content)
        
        print(f"Generated {source} markdown file: {output_file}")
        
        return {
            "date": date_str,
            "source": source,
            "file": str(output_file),
            "status": "generated",
            "conversations_count": len(results)
        }
    
    def generate_date_range(self, start_date=None, end_date=None, days=1, force_regenerate=False):
        """
        Generate markdown files for a range of dates.
        
        Args:
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            days: Number of days to generate if start_date is not provided
            force_regenerate: Whether to regenerate existing files
            
        Returns:
            List of dictionaries with information about generated files
        """
        # Set default dates if not provided, using the configured timezone
        now = datetime.now(self.timezone)
        
        if not start_date:
            if days > 1:
                start_date = (now - timedelta(days=days-1)).strftime('%Y-%m-%d')
            else:
                start_date = now.strftime('%Y-%m-%d')
                
        if not end_date:
            end_date = now.strftime('%Y-%m-%d')
        
        # Print date range being processed
        print(f"Generating markdown for date range: {start_date} to {end_date}")    
            
        # Parse dates
        start = datetime.strptime(start_date, '%Y-%m-%d')
        end = datetime.strptime(end_date, '%Y-%m-%d')
        
        results = []
        
        # Iterate through each day in the date range
        current_date = start
        while current_date <= end:
            date_str = current_date.strftime('%Y-%m-%d')
            print(f"\nProcessing date: {date_str}")
            
            # Generate markdown for this date
            day_results = self.generate_daily_markdown(date_str, force_regenerate)
            
            # If no results were generated, create "no conversation" results for reporting
            if not day_results:
                bee_result = {
                    "date": date_str,
                    "source": "bee",
                    "file": None,
                    "status": "no_conversations",
                    "conversations_count": 0
                }
                
                limitless_result = {
                    "date": date_str,
                    "source": "limitless",
                    "file": None,
                    "status": "no_conversations",
                    "conversations_count": 0
                }
                
                day_results = [bee_result, limitless_result]
            
            results.extend(day_results)
            
            # Move to next day
            current_date += timedelta(days=1)
        
        return results
    
    def _generate_markdown_content(self, date_obj, conversations, source):
        """
        Generate markdown content from conversation data.
        
        Args:
            date_obj: Date as a datetime object
            conversations: List of conversation objects
            source: Data source ("limitless" or "bee")
            
        Returns:
            Markdown content as a string
        """
        # Format the date as Month DD, YYYY
        date_formatted = date_obj.strftime('%B %d, %Y')
        
        # Capitalize the source name
        source_title = source.capitalize()
        
        # Start with header
        content = f"# {source_title} Conversations - {date_formatted}\n\n"
        
        # Add a table of contents
        content += "## Table of Contents\n\n"
        
        for i, conv in enumerate(conversations):
            # Use short_summary if available, otherwise fall back to regular summary
            short_summary = conv.get("short_summary", "")
            if not short_summary:
                summary = conv.get("summary", "No summary available")
                # Clean up summary by removing prefixes
                if summary.startswith("### Summary:"):
                    summary = summary[len("### Summary:"):].strip()
                elif summary.startswith("**Summary:**"):
                    summary = summary[len("**Summary:**"):].strip()
                
                # Limit length for regular summaries
                if summary and len(summary) > 100:
                    short_summary = summary[:97] + "..."
                else:
                    short_summary = summary
            
            # Create link to the conversation
            link = f"#conversation-{i+1}"
            
            # Add the entry to the table of contents (without time)
            content += f"- [{short_summary}]({link})\n"
        
        content += "\n---\n\n"
        
        # Add each conversation
        for i, conv in enumerate(conversations):
            # Add anchor for TOC
            content += f"<a id='conversation-{i+1}'></a>\n"
            
            # Get the short summary or regular summary for the heading
            short_summary = conv.get("short_summary", "")
            if not short_summary:
                summary = conv.get("summary", f"Conversation {i+1}")
                if summary.startswith("### Summary:"):
                    summary = summary[len("### Summary:"):].strip()
                elif summary.startswith("**Summary:**"):
                    summary = summary[len("**Summary:**"):].strip()
                
                # Use first part of summary if too long
                if summary and len(summary) > 70:
                    short_summary = summary[:67] + "..."
                else:
                    short_summary = summary
            
            # Add conversation header with just the short summary (no time)
            content += f"## {short_summary}\n\n"
            
            # Add full summary if available and different from short summary
            full_summary = conv.get("summary", "")
            if full_summary and full_summary != short_summary:
                content += f"**Summary:** {full_summary}\n\n"
            
            # Add transcript if available
            text = conv.get("text", "")
            if text:
                content += "**Transcript:**\n\n"
                content += f"```\n{text}\n```\n\n"
            
            content += "---\n\n"
        
        # Add footer with generation time in the configured timezone
        now = datetime.now(self.timezone)
        content += f"*Generated on {now.strftime('%Y-%m-%d %H:%M:%S %Z')}*\n"
        
        return content


if __name__ == "__main__":
    # Example usage
    generator = MarkdownGenerator()
    
    # Generate markdown for the past 7 days
    results = generator.generate_date_range(days=7, force_regenerate=True)
    
    print(f"Generated {len(results)} markdown files:")
    for result in results:
        print(f"- {result['date']}: {result['source']} ({result.get('conversations_count', 0)} conversations)")