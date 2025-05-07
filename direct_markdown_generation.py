#!/usr/bin/env python3
"""
Script to directly generate markdown files from the vector store data,
bypassing the normal search mechanism.
"""
import os
import sys
from pathlib import Path
from datetime import datetime
import calendar

# Add parent directory to path
sys.path.append(str(Path(__file__).parent))

# Import our modules
from storage.vector_store import FAISSVectorStore
from config import BEE_MD_TARGET, LIMITLESS_MD_TARGET

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
        for date, docs in dates.items():
            print(f"  - {date}: {len(docs)} documents")
    
    return docs_by_source_date

def generate_markdown_files(docs_by_source_date):
    """Generate markdown files directly from the documents"""
    # Create the target directories
    bee_dir, limitless_dir = create_directories()
    
    # Track results
    results = []
    
    # Generate markdown for each source and date
    for source, dates in docs_by_source_date.items():
        for date_str, documents in dates.items():
            if not documents:
                continue
                
            # Parse date
            date_obj = datetime.strptime(date_str, '%Y-%m-%d')
            
            # Choose output directory based on source
            if source.lower() == "bee":
                output_dir = bee_dir
            elif source.lower() == "limitless":
                output_dir = limitless_dir
            else:
                print(f"Unknown source '{source}', skipping")
                continue
            
            # Create year and month folders
            year = date_obj.year
            month = date_obj.month
            month_name = calendar.month_name[month]
            year_dir = output_dir / f"{year}"
            month_dir = year_dir / f"{month:02d}-{month_name}"
            month_dir.mkdir(exist_ok=True, parents=True)
            
            # Create filename
            filename = f"{month_name}-{date_obj.day:02d}-{year}.md"
            output_file = month_dir / filename
            
            # Sort conversations by timestamp
            documents.sort(key=lambda x: x.get("timestamp", ""))
            
            # Generate markdown content
            content = generate_markdown_content(date_obj, documents, source)
            
            # Write to file
            with open(output_file, 'w') as f:
                f.write(content)
            
            print(f"Generated markdown for {source} on {date_str} ({len(documents)} conversations)")
            print(f"  File: {output_file}")
            
            # Track result
            results.append({
                "date": date_str,
                "source": source,
                "conversations_count": len(documents),
                "file": str(output_file)
            })
    
    # Print summary
    print(f"\nGenerated {len(results)} markdown files in total:")
    for result in results:
        print(f"- {result['date']}: {result['source']} ({result['conversations_count']} conversations)")
        print(f"  File: {result['file']}")
    
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

if __name__ == "__main__":
    print("Generating markdown examples directly from vector store data...")
    
    # Clear vector store and add fresh sample data
    clear_vector_store_and_add_sample_data()
    
    # Get documents from vector store
    docs_by_source_date = get_documents_from_vector_store()
    
    # Generate markdown files
    generate_markdown_files(docs_by_source_date)