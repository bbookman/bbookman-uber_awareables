#!/usr/bin/env python3
"""
Script to directly generate markdown files from the vector store data.
If a date is provided, it generates for that specific date.
If no date is provided, it checks for 'limitless' data in the vector store
and generates markdown files for any dates that are missing in the
LIMITLESS_MD_TARGET directory.
"""
import os
import sys
import argparse
from pathlib import Path
from datetime import datetime
import calendar

# Add project root to sys.path to allow imports from config and markdown
project_root = Path(__file__).resolve().parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))
# If this script is moved, or if config/markdown are not in the root, adjust path logic.

try:
    from config import LIMITLESS_MD_TARGET, BEE_MD_TARGET
    from markdown.generator import MarkdownGenerator
except ImportError as e:
    print(f"Error importing necessary modules: {e}", file=sys.stderr)
    print("Ensure that config.py exists (loading from .env) and markdown/generator.py is accessible.", file=sys.stderr)
    print(f"Current sys.path: {sys.path}", file=sys.stderr)
    sys.exit(1)

def get_dates_from_vector_store(generator):
    """
    Retrieves all unique dates from the vector store's stats.
    Note: These are all dates present in the store, not necessarily specific to 'limitless'.
    The generation step will need to handle filtering by source.
    """
    stats = generator.vector_store.get_stats()
    return set(stats.get('dates', {}).keys()) # Expects YYYY-MM-DD strings

def get_existing_markdown_file_dates(markdown_dir_path_str):
    """
    Scans the given directory for .md files and extracts dates from filenames.
    Assumes filenames are YYYY-MM-DD.md.
    """
    markdown_dir = Path(markdown_dir_path_str)
    existing_dates = set()
    if markdown_dir.exists() and markdown_dir.is_dir():
        for f in markdown_dir.iterdir():
            if f.is_file() and f.suffix.lower() == '.md':
                try:
                    # Validate that the filename stem is a valid date
                    date_str = f.stem
                    datetime.strptime(date_str, "%Y-%m-%d")
                    existing_dates.add(date_str)
                except ValueError:
                    if generator_debug_enabled: # Use a global or passed-in debug flag
                        print(f"Warning: Filename {f.name} is not a valid date format (YYYY-MM-DD.md). Skipping.", file=sys.stderr)
    return existing_dates

# Global debug flag for helper functions if needed, set in main
generator_debug_enabled = False

def get_existing_limitless_markdown_dates(limitless_md_path: Path) -> set[str]:
    """Scans the limitless markdown directory and returns a set of dates for existing files."""
    existing_dates = set()
    if not limitless_md_path.exists():
        return existing_dates

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
                                    month_name_str, day_str, year_str = parts[0], parts[1], parts[2]
                                    # Convert month name to number
                                    month_num = datetime.strptime(month_name_str, "%B").month
                                    # Format to YYYY-MM-DD
                                    date_str = f"{year_str}-{month_num:02d}-{day_str}"
                                    existing_dates.add(date_str)
                            except ValueError:
                                print(f"Warning: Could not parse date from filename: {md_file.name}")
    return existing_dates

def create_directories():
    """Create the target directories if they don't exist"""
    # Ensure we use correct paths - fix any environment variable issues
    bee_dir = Path("/Users/brucebookman/markdown/bee")
    limitless_dir = Path("/Users/brucebookman/markdown/limitless")  # Fixed the typo "imitless"
    
    # Print the target directories
    print(f"Bee markdown target directory: {bee_dir}")
    print(f"Limitless markdown target directory: {limitless_dir}")
    
    # Create the directories if they don't exist
    bee_dir.mkdir(exist_ok=True, parents=True)
    limitless_dir.mkdir(exist_ok=True, parents=True)
    
    return bee_dir, limitless_dir

def get_documents_from_vector_store():
    """Get documents directly from the vector store"""
    # Initialize vector store
    vector_store = FAISSVectorStore()
    print(f"Vector store has {len(vector_store.documents)} documents")
    
    # Group documents by source and date
    docs_by_source_date = {}
    
    for doc in vector_store.documents:
        source = doc.get("source")
        date = doc.get("date")
        
        if not source or not date:
            continue
            
        if source not in docs_by_source_date:
            docs_by_source_date[source] = {}
            
        if date not in docs_by_source_date[source]:
            docs_by_source_date[source][date] = []
            
        docs_by_source_date[source][date].append(doc)
    
    # Print what we found
    for source, dates in docs_by_source_date.items():
        print(f"Source '{source}' has documents for {len(dates)} dates:")
        # Sort dates for consistent output
        sorted_dates = sorted(dates.keys())
        for date in sorted_dates:
            print(f"  - {date}: {len(dates[date])} documents")
    
    return docs_by_source_date

def generate_markdown_files(docs_by_source_date):
    """Generate markdown files directly from the documents"""
    # Create the target directories
    bee_dir, limitless_dir = create_directories()
    existing_limitless_dates = get_existing_limitless_markdown_dates(limitless_dir)
    print(f"Found {len(existing_limitless_dates)} existing Limitless markdown files: {sorted(list(existing_limitless_dates))}")

    # Track results
    results = []
    
    # Generate markdown for each source and date
    for source, dates in docs_by_source_date.items():
        for date_str, documents in dates.items():
            if not documents:
                print(f"No documents found for {source} on {date_str}")
                continue
                
            # Parse date
            try:
                date_obj = datetime.strptime(date_str, '%Y-%m-%d')
            except ValueError as e:
                print(f"Error parsing date {date_str}: {e}")
                continue
            
            # Choose output directory based on source
            if source.lower() == "bee":
                output_dir = bee_dir
            elif source.lower() == "limitless":
                output_dir = limitless_dir
                if date_str in existing_limitless_dates:
                    print(f"Skipping Limitless for {date_str}: Markdown file already exists.")
                    results.append({
                        "date": date_str,
                        "source": source,
                        "conversations_count": len(documents),
                        "file": "N/A - Skipped",
                        "status": "skipped"
                    })
                    continue
            else:
                print(f"Unknown source '{source}', skipping")
                continue
            
            # Create year and month folders
            year = date_obj.year
            month = date_obj.month
            month_name = calendar.month_name[month]
            year_dir = output_dir / f"{year}"
            month_dir = year_dir / f"{month:02d}-{month_name}"
            
            try:
                year_dir.mkdir(exist_ok=True, parents=True)
                month_dir.mkdir(exist_ok=True, parents=True)
            except Exception as e:
                print(f"Error creating directories for {source} on {date_str}: {e}")
                continue
            
            # Create filename
            filename = f"{month_name}-{date_obj.day:02d}-{year}.md"
            output_file = month_dir / filename
            
            # Sort conversations by timestamp
            documents.sort(key=lambda x: x.get("timestamp", ""))
            
            try:
                # Generate markdown content
                content = generate_markdown_content(date_obj, documents, source)
                
                # Write to file
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                print(f"Generated markdown for {source} on {date_str} ({len(documents)} conversations)")
                print(f"  File: {output_file}")
                
                # Track result
                results.append({
                    "date": date_str,
                    "source": source,
                    "conversations_count": len(documents),
                    "file": str(output_file),
                    "status": "success"
                })
            except Exception as e:
                print(f"Error generating markdown for {source} on {date_str}: {e}")
                results.append({
                    "date": date_str,
                    "source": source,
                    "conversations_count": len(documents),
                    "file": str(output_file),
                    "status": "error",
                    "error": str(e)
                })
    
    # Print summary
    success_count = len([r for r in results if r["status"] == "success"])
    error_count = len([r for r in results if r["status"] == "error"])
    skipped_count = len([r for r in results if r["status"] == "skipped"])
    print(f"\nMarkdown generation complete:")
    print(f"- Successfully generated: {success_count} files")
    if error_count > 0:
        print(f"- Failed to generate: {error_count} files")
    if skipped_count > 0:
        print(f"- Skipped: {skipped_count} files (already exist or unknown source)")
    
    for result in results:
        status_symbol = "✓" if result["status"] == "success" else ("✗" if result["status"] == "error" else "↷")
        print(f"{status_symbol} {result['date']}: {result['source']} ({result.get('conversations_count', 'N/A')} conversations)")
        print(f"  File: {result['file']}")
        if result["status"] == "error":
            print(f"  Error: {result['error']}")
    
    return results

def format_timestamp(timestamp_str, format_str='%I:%M %p'):
    """Format a timestamp string to a readable time format"""
    try:
        dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        return dt.strftime(format_str)
    except Exception:
        return timestamp_str

def clean_transcript_text(text):
    """
    Clean transcript text by removing duplicate consecutive lines.
    
    Args:
        text: Raw transcript text
        
    Returns:
        Cleaned transcript text
    """
    if not text:
        return ""
    
    lines = text.split("\n")
    cleaned_lines = []
    prev_line = None
    
    for line in lines:
        # Only add the line if it's different from the previous one
        if line != prev_line:
            cleaned_lines.append(line)
        prev_line = line
        
    return "\n".join(cleaned_lines)

def generate_markdown_content(date_obj, conversations, source):
    """
    Generate markdown content for conversations.
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
        timestamp = conv.get("timestamp", "")
        time_str = format_timestamp(timestamp)
        
        title = f"Conversation {i+1} - {time_str}"
        summary = conv.get("summary", "No summary available")
        if summary and len(summary) > 100:
            summary = summary[:97] + "..."
        
        link = f"#conversation-{i+1}"
        content += f"- [{title}]({link}): {summary}\n"
    
    content += "\n---\n\n"
    
    # Add each conversation
    for i, conv in enumerate(conversations):
        timestamp = conv.get("timestamp", "")
        timestamp_formatted = format_timestamp(timestamp)
        
        # Add anchor for TOC
        content += f"<a id='conversation-{i+1}'></a>\n"
        
        # Add conversation header
        content += f"## Conversation {i+1} - {timestamp_formatted}\n\n"
        
        # Add summary if available
        if conv.get("summary"):
            content += f"**Summary:** {conv.get('summary')}\n\n"
        
        # Add metadata
        content += "**Details:**\n\n"
        
        # Add time
        content += f"- **Time**: {timestamp_formatted}\n"
        
        # For Limitless, use 'duration' from metadata
        if source.lower() == "limitless" and conv.get("metadata", {}).get("duration"):
            duration_min = int(conv.get("metadata", {}).get("duration", 0) / 60)
            content += f"- **Duration**: {duration_min} minutes\n"
        
        # For Bee, use end_time - start_time if available
        elif source.lower() == "bee" and conv.get("metadata", {}).get("startTime") and conv.get("metadata", {}).get("endTime"):
            try:
                start_time = datetime.fromisoformat(conv.get("metadata", {}).get("startTime").replace('Z', '+00:00'))
                end_time = datetime.fromisoformat(conv.get("metadata", {}).get("endTime").replace('Z', '+00:00'))
                duration = end_time - start_time
                duration_min = int(duration.total_seconds() / 60)
                content += f"- **Duration**: {duration_min} minutes\n"
            except Exception as e:
                print(f"Error calculating duration: {e}")
            
        if conv.get("metadata", {}).get("location"):
            location = str(conv.get("metadata", {}).get("location", ""))
            content += f"- **Location**: {location}\n"
        
        content += "\n"
        
        # Add transcript if available
        text = conv.get("text", "")
        if text:
            # Clean the transcript by removing duplicate lines
            clean_text = clean_transcript_text(text)
            content += "**Transcript:**\n\n"
            content += f"```\n{clean_text}\n```\n\n"
        
        content += "---\n\n"
    
    # Add footer with generation time
    now = datetime.now()
    content += f"*Generated on {now.strftime('%Y-%m-%d %H:%M:%S')}*\n"
    
    return content

def clear_vector_store_and_add_sample_data():
    """Clear the vector store and add fresh sample data"""
    # Initialize vector store
    vector_store = FAISSVectorStore()
    
    # Clear existing data
    vector_store.clear()
    print("Cleared vector store")
    
    # Sample Bee conversations
    bee_conversations = [
        {
            "id": "bee_test_1",
            "source": "bee", 
            "timestamp": "2025-05-04T09:15:00Z",
            "text": "Speaker 1: Good morning! How's the product launch preparation going?\nSpeaker 2: We're on track. Marketing materials are ready, and the website updates are scheduled.\nSpeaker 1: Great. Any concerns about the demo?\nSpeaker 2: None at this point. We've run through it several times, and it's solid.\nSpeaker 1: Perfect. Let's do one final review tomorrow.",
            "summary": "Product launch preparation status update. Marketing materials and website updates ready. Demo tested successfully. Final review scheduled for tomorrow.",
            "short_summary": "Product Launch Prep",
            "date": "2025-05-04",
            "metadata": {
                "startTime": "2025-05-04T09:15:00Z",
                "endTime": "2025-05-04T09:30:00Z",
                "location": "Office - Meeting Room A"
            }
        },
        {
            "id": "bee_test_2",
            "source": "bee",
            "timestamp": "2025-05-05T13:45:00Z",
            "text": "Speaker 1: Have you reviewed the latest user feedback?\nSpeaker 2: Yes, I did. There are some interesting patterns emerging.\nSpeaker 1: What stands out to you?\nSpeaker 2: Users are really loving the new interface, but they're finding the export functionality confusing.\nSpeaker 1: That's helpful to know. Let's prioritize improving those export flows.\nSpeaker 2: Agreed. I'll draft some mockups for our next design review.",
            "summary": "Discussion about user feedback indicating positive reception of the new interface but confusion about export functionality. Decision to prioritize improving export flows and create mockups for the next design review.",
            "short_summary": "User Feedback Review",
            "date": "2025-05-05",
            "metadata": {
                "startTime": "2025-05-05T13:45:00Z",
                "endTime": "2025-05-05T14:05:15Z",
                "location": "Office - Design Lab"
            }
        },
        {
            "id": "bee_test_3",
            "source": "bee",
            "timestamp": "2025-05-06T10:00:00Z",
            "text": "Speaker 1: Let's review our goals for this quarter.\nSpeaker 2: We committed to launching three new features and improving our onboarding flow.\nSpeaker 1: Where do we stand with the onboarding improvements?\nSpeaker 2: The new tutorial is implemented, and early metrics show a 15% increase in completion rates.\nSpeaker 1: That's impressive! What about the other features?\nSpeaker 2: Two are complete, and the third is in final QA now. We should be able to release next week.\nSpeaker 1: Sounds like we're on track to meet all our quarterly objectives.",
            "summary": "Quarterly goals review showing strong progress. Onboarding improvements have increased completion rates by 15%. Two features complete and third in final QA for release next week. Team is on track to meet all quarterly objectives.",
            "short_summary": "Quarterly Goals Review",
            "date": "2025-05-06",
            "metadata": {
                "startTime": "2025-05-06T10:00:00Z",
                "endTime": "2025-05-06T10:30:00Z",
                "location": "Virtual Meeting"
            }
        }
    ]
    
    # Sample Limitless conversations
    limitless_conversations = [
        {
            "id": "limitless_test_1",
            "source": "limitless",
            "timestamp": "2025-05-04T10:30:00Z",
            "text": "Team standup meeting notes:\n- Alex completed the database migration\n- Sarah fixed three critical bugs in the authentication module\n- James is working on the new recommendation algorithm\n- Emma will be out tomorrow for a conference\n\nAction items:\n1. Review pull request #234 by EOD\n2. Schedule performance testing for Thursday\n3. Update documentation for the new API endpoints",
            "summary": "Team standup with updates on database migration, bug fixes, and ongoing work on recommendation algorithm. Action items include PR review, performance testing scheduling, and documentation updates.",
            "date": "2025-05-04",
            "metadata": {
                "startTime": "2025-05-04T10:30:00Z",
                "endTime": "2025-05-04T10:45:00Z",
                "duration": 900,
                "location": "Virtual Meeting"
            }
        },
        {
            "id": "limitless_test_2",
            "source": "limitless",
            "timestamp": "2025-05-05T15:00:00Z",
            "text": "Budget review meeting:\n\nAttendees: Finance team, Department heads\n\nQ2 Budget Analysis:\n- Engineering department is currently 5% under budget\n- Marketing campaigns exceeded budget by 8% but delivered 20% above target ROI\n- Operations costs aligned with projections\n- New hiring slightly delayed, resulting in 12% personnel budget surplus\n\nAdjustments for Q3:\n- Reallocate $50K from personnel surplus to infrastructure upgrades\n- Increase marketing budget by 10% based on strong Q2 performance\n- Set aside contingency fund for potential supply chain disruptions\n- Approve additional budget for team building activities",
            "summary": "Budget review showing Engineering under budget by 5%, Marketing over budget but with strong ROI, and a personnel budget surplus due to delayed hiring. Q3 adjustments include reallocating funds to infrastructure, increasing marketing budget, and creating contingency funds.",
            "date": "2025-05-05",
            "metadata": {
                "startTime": "2025-05-05T15:00:00Z",
                "endTime": "2025-05-05T16:30:00Z",
                "duration": 5400,
                "location": "Finance Conference Room"
            }
        }
    ]
    
    # Combine all sample conversations
    all_conversations = bee_conversations + limitless_conversations
    print(f"Created {len(all_conversations)} sample conversations")
    
    # Add conversations to vector store
    successful_embeddings = 0
    for doc in all_conversations:
        try:
            # Get the text to embed
            text = doc.get("text", "")
            if not text:
                continue
                
            # Generate embedding
            model = vector_store.model
            embedding = model.encode([text])[0]  # Get just the array
            
            # Add embedding to index
            embeddings = embedding.reshape(1, -1).astype('float32')  # Reshape for faiss
            current_size = vector_store.index.ntotal
            vector_store.index.add(embeddings)
            
            # Add document to metadata store
            doc_with_idx = dict(doc)
            doc_with_idx["vector_id"] = current_size
            vector_store.documents.append(doc_with_idx)
            successful_embeddings += 1
        except Exception as e:
            print(f"Error embedding document {doc.get('id')}: {e}")
    
    # Save the vector store
    vector_store._save()
    print(f"Added {successful_embeddings} sample conversations to vector store")
    
    return successful_embeddings

def main():
    global generator_debug_enabled

    parser = argparse.ArgumentParser(
        description="Generate markdown files from vector store data.",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument(
        "date_str",
        nargs='?',
        default=None,
        help="Optional: Date string in YYYY-MM-DD format.\n"
             "If provided, generates markdown for this specific date (all sources, unless generator filters).\n"
             "If not provided, checks for missing 'limitless' source markdown files\n"
             "based on vector store data and generates them."
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug output from the MarkdownGenerator and this script."
    )
    args = parser.parse_args()

    generator_debug_enabled = args.debug

    if not LIMITLESS_MD_TARGET:
        print("Error: LIMITLESS_MD_TARGET is not configured. Check your .env and config.py.", file=sys.stderr)
        sys.exit(1)
    
    # Ensure BEE_MD_TARGET is also available if MarkdownGenerator requires it
    if not BEE_MD_TARGET:
        print("Warning: BEE_MD_TARGET is not configured. This might be an issue for MarkdownGenerator.", file=sys.stderr)


    generator = MarkdownGenerator(
        limitless_output_path=LIMITLESS_MD_TARGET,
        bee_output_path=BEE_MD_TARGET, # Pass even if primary focus is limitless
        debug=args.debug
    )

    if args.date_str:
        print(f"Generating markdown for specific date: {args.date_str}")
        try:
            date_obj = datetime.strptime(args.date_str, "%Y-%m-%d").date()
            # This call might generate for all sources for that date,
            # depending on MarkdownGenerator's default behavior.
            generator.generate_markdown_for_date(date_obj)
            print(f"Markdown generation initiated for {args.date_str}.")
        except ValueError:
            print(f"Error: Invalid date format '{args.date_str}'. Please use YYYY-MM-DD.", file=sys.stderr)
            sys.exit(1)
        except Exception as e:
            print(f"Error generating markdown for {args.date_str}: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        print(f"Checking for missing Limitless markdown files in: {LIMITLESS_MD_TARGET}")
        print("Comparing against dates with data in the vector store...")

        vector_store_dates = get_dates_from_vector_store(generator)

        if not vector_store_dates:
            print("No dates found in vector store stats. Nothing to process.")
            return

        if args.debug:
            print(f"Dates found in vector store stats: {sorted(list(vector_store_dates))}")

        existing_limitless_files_dates = get_existing_markdown_file_dates(LIMITLESS_MD_TARGET)
        if args.debug:
            print(f"Dates of existing Limitless MD files: {sorted(list(existing_limitless_files_dates))}")

        missing_dates_for_limitless = []
        for date_str_from_vector in vector_store_dates:
            try:
                # Ensure date string from vector store is valid before comparison
                datetime.strptime(date_str_from_vector, "%Y-%m-%d") 
                if date_str_from_vector not in existing_limitless_files_dates:
                    missing_dates_for_limitless.append(date_str_from_vector)
            except ValueError:
                if args.debug:
                    print(f"Warning: Invalid date string format '{date_str_from_vector}' in vector store stats. Skipping.", file=sys.stderr)
        
        if not missing_dates_for_limitless:
            print("No missing Limitless markdown files found. All appear to be up-to-date.")
        else:
            print(f"Found {len(missing_dates_for_limitless)} date(s) potentially missing Limitless markdown files.")
            print("Attempting to generate them now...")
            generated_count = 0
            for date_str_to_generate in sorted(missing_dates_for_limitless):
                print(f"Attempting to generate Limitless markdown for date: {date_str_to_generate}...")
                try:
                    date_obj_to_generate = datetime.strptime(date_str_to_generate, "%Y-%m-%d").date()
                    
                    # IMPORTANT ASSUMPTION:
                    # generator.generate_markdown_for_date can accept a 'source_filter'
                    # and will only process/write data for 'limitless' into its designated path.
                    # If it writes an empty file when no 'limitless' data exists for that date,
                    # that might be acceptable. The key is it shouldn't mix sources or fail.
                    generator.generate_markdown_for_date(date_obj_to_generate, source_filter=["limitless"])
                    
                    # To be more robust, one might check if the file was actually created,
                    # and if it has content, but this depends on generator's specific behavior.
                    print(f"Limitless markdown generation initiated for {date_str_to_generate}.")
                    generated_count += 1
                except Exception as e:
                    print(f"Error generating Limitless markdown for {date_str_to_generate}: {e}", file=sys.stderr)
            
            if generated_count > 0:
                print(f"Finished attempting to generate {generated_count} missing Limitless markdown file(s).")
            else:
                # This could happen if all "missing" dates actually had no 'limitless' data
                print("No new Limitless files were generated (possibly no 'limitless' data for those dates, or errors occurred).")

if __name__ == "__main__":
    main()