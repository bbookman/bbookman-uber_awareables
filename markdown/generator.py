import sys
import os
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

# Add parent directory to path so we can import from the root
sys.path.append(str(Path(__file__).parent.parent))

from config import MARKDOWN_OUTPUT_PATH
from storage.vector_store import FAISSVectorStore
from storage.data_ingestion import DataIngestion

class MarkdownGenerator:
    """
    Class to generate markdown files from stored conversation data.
    """
    
    def __init__(self, output_path=MARKDOWN_OUTPUT_PATH):
        """
        Initialize the markdown generator.
        
        Args:
            output_path: Base directory to output markdown files
        """
        self.output_path = Path(output_path)
        self.output_path.mkdir(exist_ok=True, parents=True)
        self.vector_store = FAISSVectorStore()
        self.data_ingestion = DataIngestion()
    
    def generate_daily_markdown(self, date_str=None, force_regenerate=False):
        """
        Generate markdown files for a specific date.
        
        Args:
            date_str: Date in YYYY-MM-DD format, defaults to today
            force_regenerate: Whether to regenerate existing files
            
        Returns:
            Dictionary with information about generated files
        """
        if not date_str:
            date_str = datetime.now().strftime('%Y-%m-%d')
            
        # Create output directory structure
        date_obj = datetime.strptime(date_str, '%Y-%m-%d')
        year_month_dir = self.output_path / f"{date_obj.year:04d}/{date_obj.month:02d}"
        year_month_dir.mkdir(exist_ok=True, parents=True)
        
        # Filename for the markdown file
        output_file = year_month_dir / f"{date_obj.day:02d}.md"
        
        # Check if file already exists and we're not forcing regeneration
        if output_file.exists() and not force_regenerate:
            print(f"Markdown file {output_file} already exists. Use force_regenerate=True to overwrite.")
            return {
                "date": date_str,
                "file": str(output_file),
                "status": "skipped"
            }
        
        # Get all conversations for this date
        results = []
        
        # Search for Limitless data
        limitless_results = self.data_ingestion.search_conversations(
            query="",
            k=100,
            date=date_str,
            source="limitless"
        )
        
        if limitless_results:
            results.extend(limitless_results)
        
        # Search for Bee data
        bee_results = self.data_ingestion.search_conversations(
            query="",
            k=100,
            date=date_str,
            source="bee"
        )
        
        if bee_results:
            results.extend(bee_results)
        
        # Sort results by timestamp
        results.sort(key=lambda x: x.get("timestamp", ""))
        
        # Generate markdown content
        markdown_content = self._generate_markdown_content(date_str, results)
        
        # Write to file
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(markdown_content)
        
        print(f"Generated markdown file: {output_file}")
        
        return {
            "date": date_str,
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
        # Set default dates if not provided
        if not start_date:
            if days > 1:
                start_date = (datetime.now() - timedelta(days=days-1)).strftime('%Y-%m-%d')
            else:
                start_date = datetime.now().strftime('%Y-%m-%d')
                
        if not end_date:
            end_date = datetime.now().strftime('%Y-%m-%d')
            
        # Parse dates
        start = datetime.strptime(start_date, '%Y-%m-%d')
        end = datetime.strptime(end_date, '%Y-%m-%d')
        
        results = []
        
        # Iterate through each day in the date range
        current_date = start
        while current_date <= end:
            date_str = current_date.strftime('%Y-%m-%d')
            
            # Generate markdown for this date
            result = self.generate_daily_markdown(date_str, force_regenerate)
            results.append(result)
            
            # Move to next day
            current_date += timedelta(days=1)
        
        return results
    
    def _generate_markdown_content(self, date_str, conversations):
        """
        Generate markdown content from conversation data.
        
        Args:
            date_str: Date string in YYYY-MM-DD format
            conversations: List of conversation objects
            
        Returns:
            Markdown content as a string
        """
        date_obj = datetime.strptime(date_str, '%Y-%m-%d')
        date_formatted = date_obj.strftime('%B %d, %Y')
        
        # Start with header
        content = f"# Daily Conversations - {date_formatted}\n\n"
        
        # Add a table of contents
        content += "## Table of Contents\n\n"
        
        for i, conv in enumerate(conversations):
            timestamp = conv.get("timestamp", "")
            time_str = ""
            if timestamp:
                try:
                    time_obj = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                    time_str = time_obj.strftime('%I:%M %p')
                except:
                    pass
            
            title = f"{conv.get('source', 'unknown').title()} - {time_str}"
            summary = conv.get("summary", "No summary available")
            if summary and len(summary) > 100:
                summary = summary[:97] + "..."
            
            link = f"#{conv.get('source', 'unknown')}-{i+1}"
            content += f"- [{title}]({link}): {summary}\n"
        
        content += "\n---\n\n"
        
        # Add each conversation
        for i, conv in enumerate(conversations):
            source = conv.get("source", "unknown").title()
            timestamp = conv.get("timestamp", "")
            timestamp_formatted = ""
            
            if timestamp:
                try:
                    time_obj = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                    timestamp_formatted = time_obj.strftime('%I:%M %p')
                except:
                    pass
            
            # Add anchor for TOC
            content += f"<a id='{conv.get('source', 'unknown')}-{i+1}'></a>\n"
            
            # Add conversation header
            content += f"## {source} Conversation - {timestamp_formatted}\n\n"
            
            # Add summary if available
            if conv.get("summary"):
                content += f"**Summary:** {conv.get('summary')}\n\n"
            
            # Add metadata
            content += "**Details:**\n\n"
            content += f"- **Source**: {source}\n"
            content += f"- **Time**: {timestamp_formatted}\n"
            
            if conv.get("metadata", {}).get("duration"):
                duration_min = int(conv.get("metadata", {}).get("duration", 0) / 60)
                content += f"- **Duration**: {duration_min} minutes\n"
                
            if conv.get("metadata", {}).get("location"):
                location = str(conv.get("metadata", {}).get("location", ""))
                content += f"- **Location**: {location}\n"
            
            content += "\n"
            
            # Add transcript if available
            text = conv.get("text", "")
            if text:
                content += "**Transcript:**\n\n"
                content += f"```\n{text}\n```\n\n"
            
            content += "---\n\n"
        
        # Add footer
        content += f"*Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n"
        
        return content


if __name__ == "__main__":
    # Example usage
    generator = MarkdownGenerator()
    
    # Generate markdown for the past 7 days
    results = generator.generate_date_range(days=7, force_regenerate=True)
    
    print(f"Generated {len(results)} markdown files:")
    for result in results:
        print(f"- {result['date']}: {result['status']} ({result.get('conversations_count', 0)} conversations)")