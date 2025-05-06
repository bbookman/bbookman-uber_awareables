#!/usr/bin/env python3
"""
Script to generate markdown examples from data in the vector store.
This will generate files to the directories specified in the .env file.
"""
import os
import sys
from pathlib import Path
import json
from datetime import datetime, timedelta

# Add parent directory to path
sys.path.append(str(Path(__file__).parent))

# Import our modules
from storage.vector_store import FAISSVectorStore
from markdown.generator import MarkdownGenerator
from config import BEE_MD_TARGET, LIMITLESS_MD_TARGET

def create_directories():
    """Create the target directories if they don't exist"""
    # Create directories from config
    bee_dir = Path(BEE_MD_TARGET)
    limitless_dir = Path(LIMITLESS_MD_TARGET)
    
    # Print the target directories
    print(f"Bee markdown target directory: {bee_dir}")
    print(f"Limitless markdown target directory: {limitless_dir}")
    
    # Create the directories if they don't exist
    bee_dir.mkdir(exist_ok=True, parents=True)
    limitless_dir.mkdir(exist_ok=True, parents=True)
    
    return bee_dir, limitless_dir

def add_sample_data_to_vector_store():
    """Add sample conversations to the vector store"""
    # Initialize vector store
    vector_store = FAISSVectorStore()
    
    # Check if there's existing data
    existing_docs = len(vector_store.documents)
    print(f"Vector store has {existing_docs} existing documents")
    
    # If we already have enough data, skip adding more
    if existing_docs >= 5:
        print("Vector store already has enough data, skipping sample data creation")
        return
    
    # Clear existing data for a fresh start
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

def generate_markdown_files():
    """Generate markdown files for the data in the vector store"""
    # Create the target directories
    bee_dir, limitless_dir = create_directories()
    
    # Initialize the markdown generator with the target directories
    generator = MarkdownGenerator(
        limitless_output_path=limitless_dir,
        bee_output_path=bee_dir
    )
    
    # Generate markdown for the last few days
    today = datetime.now()
    
    # Track results
    results = []
    
    # Generate markdown for dates from May 3 to May 6
    for i in range(3, 7):
        date_str = f"2025-05-0{i}"
        print(f"Generating markdown for date: {date_str}")
        
        # Generate markdown for this date
        result = generator.generate_daily_markdown(date_str, force_regenerate=True)
        if result:
            results.extend(result)
            print(f"Generated {len(result)} markdown files for {date_str}")
        else:
            print(f"No conversations found for {date_str}")
    
    # Show summary of generated files
    print(f"\nGenerated {len(results)} markdown files in total:")
    for result in results:
        print(f"- {result.get('date')}: {result.get('source')} ({result.get('conversations_count', 0)} conversations)")
        print(f"  File: {result.get('file')}")
    
    return results

if __name__ == "__main__":
    print("Generating markdown examples from vector store data...")
    
    # Add sample data to vector store if needed
    add_sample_data_to_vector_store()
    
    # Generate markdown files
    generate_markdown_files()