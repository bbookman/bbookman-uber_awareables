#!/usr/bin/env python3
"""
Test script to generate markdown examples for demonstration purposes.
This script will create sample markdown files for bee and limitless conversations.
"""
import os
import sys
from pathlib import Path
import json
from datetime import datetime, timedelta

# Add parent directory to path
sys.path.append(str(Path(__file__).parent))

# Import markdown generator
from markdown.generator import MarkdownGenerator
from config import BEE_MD_TARGET, LIMITLESS_MD_TARGET

def create_test_conversations():
    """Create sample conversations for testing the markdown generator"""
    
    # Sample Bee conversations
    bee_conversations = [
        {
            "id": "bee_test_1",
            "source": "bee",
            "timestamp": "2025-05-05T09:15:00Z",
            "text": "Speaker 1: Good morning! How are you today?\nSpeaker 2: I'm doing well, thanks for asking. I've been working on the project we discussed yesterday.\nSpeaker 1: That's great. How's it coming along?\nSpeaker 2: Really well actually. I've completed the first phase and I'm starting on the integration now.\nSpeaker 1: That's ahead of schedule. Nice work!",
            "summary": "Morning check-in about project progress. First phase completed and integration beginning, ahead of schedule.",
            "short_summary": "Project Progress Update",
            "date": "2025-05-05",
            "metadata": {
                "startTime": "2025-05-05T09:15:00Z",
                "endTime": "2025-05-05T09:25:30Z",
                "location": "Office - Conference Room B"
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
            "timestamp": "2025-05-03T15:00:00Z",
            "text": "Client meeting with Acme Corp:\n\nAttendees: John (Sales), Lisa (Product), Miguel (Client Lead), Sarah (Acme CTO)\n\nDiscussion points:\n- Reviewed Q2 roadmap and upcoming features\n- Client expressed interest in advanced analytics package\n- Concerns about data migration timeline\n- Need for additional training for new team members\n\nNext steps:\n- John to send pricing proposal for analytics upgrade by Friday\n- Lisa will coordinate with engineering on migration timeline\n- Schedule training session for week of 5/15",
            "summary": "Client meeting with Acme Corp discussing roadmap, analytics package interest, and data migration concerns. Follow-up actions include sending pricing proposal, coordinating on migration timeline, and scheduling training.",
            "date": "2025-05-03",
            "metadata": {
                "startTime": "2025-05-03T15:00:00Z",
                "endTime": "2025-05-03T16:15:00Z",
                "duration": 4500,
                "location": "Acme Corp HQ - 5th Floor Conference Room"
            }
        },
        {
            "id": "limitless_test_3",
            "source": "limitless",
            "timestamp": "2025-05-06T11:00:00Z",
            "text": "Research planning session:\n\nProject: AI Ethics Framework\n\nTopics covered:\n- Literature review of existing ethical frameworks\n- Defining scope and boundaries for our approach\n- Identifying key stakeholders for interviews\n- Methodology for testing bias in training data\n\nDecisions:\n- Focus on three vertical markets initially: healthcare, finance, education\n- Use mixed-methods approach combining qualitative interviews and quantitative analysis\n- Create review board with external experts\n- Timeline adjusted to accommodate expanded stakeholder interviews",
            "summary": "Planning session for AI Ethics Framework research project covering literature review, scope definition, stakeholder identification, and testing methodology. Decisions made on market focus, approach, review structure, and timeline.",
            "date": "2025-05-06",
            "metadata": {
                "startTime": "2025-05-06T11:00:00Z",
                "endTime": "2025-05-06T12:30:00Z",
                "duration": 5400,
                "location": "Research Lab - Building C"
            }
        }
    ]
    
    return {
        "bee": bee_conversations,
        "limitless": limitless_conversations
    }

def generate_markdown_directly():
    """Generate markdown examples directly using our sample data"""
    # Create sample conversations
    sample_data = create_test_conversations()
    print(f"Created {len(sample_data['limitless'])} Limitless conversations")
    print(f"Created {len(sample_data['bee'])} Bee conversations")
    
    # Create test output directories
    test_bee_dir = Path("./test_markdown_examples/bee")
    test_limitless_dir = Path("./test_markdown_examples/limitless")
    test_bee_dir.mkdir(exist_ok=True, parents=True)
    test_limitless_dir.mkdir(exist_ok=True, parents=True)
    
    # Group conversations by date and source for easy processing
    conversations_by_date_source = {}
    
    # Process Bee conversations
    for conv in sample_data["bee"]:
        date_str = conv.get("date")
        if date_str:
            if date_str not in conversations_by_date_source:
                conversations_by_date_source[date_str] = {}
            if "bee" not in conversations_by_date_source[date_str]:
                conversations_by_date_source[date_str]["bee"] = []
            conversations_by_date_source[date_str]["bee"].append(conv)
    
    # Process Limitless conversations
    for conv in sample_data["limitless"]:
        date_str = conv.get("date")
        if date_str:
            if date_str not in conversations_by_date_source:
                conversations_by_date_source[date_str] = {}
            if "limitless" not in conversations_by_date_source[date_str]:
                conversations_by_date_source[date_str]["limitless"] = []
            conversations_by_date_source[date_str]["limitless"].append(conv)
    
    # Generate markdown for each date and source
    results = []
    for date_str, sources in conversations_by_date_source.items():
        date_obj = datetime.strptime(date_str, '%Y-%m-%d')
        
        for source, conversations in sources.items():
            # Sort conversations by timestamp
            conversations.sort(key=lambda x: x.get("timestamp", ""))
            
            # Prepare output path
            if source == "limitless":
                output_dir = test_limitless_dir
            else:  # bee
                output_dir = test_bee_dir
            
            # Create year and month folders
            year = date_obj.year
            month = date_obj.month
            month_name = calendar_month_name(month)
            year_dir = output_dir / f"{year}"
            month_dir = year_dir / f"{month:02d}-{month_name}"
            month_dir.mkdir(exist_ok=True, parents=True)
            
            # Create filename
            filename = f"{month_name}-{date_obj.day:02d}-{year}.md"
            output_file = month_dir / filename
            
            # Generate markdown content
            content = generate_markdown_content(date_obj, conversations, source)
            
            # Write to file
            with open(output_file, 'w') as f:
                f.write(content)
            
            result = {
                "date": date_str,
                "source": source,
                "conversations_count": len(conversations),
                "file": str(output_file)
            }
            results.append(result)
            print(f"Generated markdown for {source} on {date_str} ({len(conversations)} conversations)")
    
    # Print summary
    print(f"\nGenerated {len(results)} markdown files in total")
    for result in results:
        print(f"- {result['date']}: {result['source']} ({result['conversations_count']} conversations)")
        print(f"  File: {result['file']}")
    
    # Display the contents of the generated files
    print("\n=== EXAMPLE MARKDOWN OUTPUTS ===\n")
    for result in results[:3]:  # Show only first 3 examples
        output_file = result.get('file')
        if output_file and os.path.exists(output_file):
            print(f"\n--- {result['source'].upper()} MARKDOWN FOR {result['date']} ---\n")
            with open(output_file, 'r') as f:
                content = f.read()
                if len(content) > 1500:
                    # Show first and last portion if too long
                    print(content[:750])
                    print("\n[...content truncated...]\n")
                    print(content[-750:])
                else:
                    print(content)

def calendar_month_name(month_number):
    """Get the name of the month from its number"""
    import calendar
    return calendar.month_name[month_number]

def format_timestamp(timestamp_str, format_str='%I:%M %p'):
    """Format a timestamp string to a readable time format"""
    try:
        dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        return dt.strftime(format_str)
    except Exception:
        return timestamp_str

def generate_markdown_content(date_obj, conversations, source):
    """
    Generate markdown content for conversations.
    This mimics the _generate_markdown_content method from MarkdownGenerator.
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
            content += "**Transcript:**\n\n"
            content += f"```\n{text}\n```\n\n"
        
        content += "---\n\n"
    
    # Add footer with generation time
    now = datetime.now()
    content += f"*Generated on {now.strftime('%Y-%m-%d %H:%M:%S')}*\n"
    
    return content

if __name__ == "__main__":
    print("Generating markdown examples directly...")
    generate_markdown_directly()