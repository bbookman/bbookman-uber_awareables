#!/usr/bin/env python3
"""
Script to delete the existing vector store and rebuild it from scratch with
properly processed data from both Limitless and Bee APIs.
"""
import os
import sys
import shutil
from datetime import datetime, timedelta
from pathlib import Path

# Add the project root to the path so we can import our modules
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
sys.path.append(project_root)

from api.data_sync import DataSyncer
from storage.vector_store import FAISSVectorStore
from api.bee_api import get_conversations, get_conversation_details
from config import VECTOR_DB_PATH

def extract_date_from_iso(iso_string):
    """Extract date from ISO datetime string."""
    if not iso_string:
        return ""
    return iso_string.split("T")[0]

def rebuild_vector_store():
    """Delete and rebuild the vector store from scratch."""
    # Step 1: Delete the existing vector store
    if os.path.exists(VECTOR_DB_PATH):
        print(f"Deleting existing vector store at {VECTOR_DB_PATH}")
        shutil.rmtree(VECTOR_DB_PATH)
        print("Vector store deleted successfully")
    
    # Step 2: Initialize a new vector store
    print("Initializing new vector store")
    vector_store = FAISSVectorStore()
    
    # Step 3: Create a DataSyncer instance
    data_syncer = DataSyncer()
    
    # Step 4: Fetch data from all sources
    # Setup collections for the different data sources
    limitless_docs = []
    bee_docs = []
    
    # Fetch Limitless data
    print("Fetching Limitless data...")
    limitless_data = data_syncer.fetch_limitless_data(limit=None)
    if limitless_data:
        print(f"Retrieved {len(limitless_data)} Limitless entries")
        
        # Process Limitless data for vector storage
        for lifelog in limitless_data:
            if 'id' not in lifelog:
                continue
                
            summary = ""
            short_summary = ""
            transcript = ""
            
            # Process contents array to extract summary, short_summary, and transcript
            for content_node in lifelog.get('contents', []):
                node_type = content_node.get('type')
                node_content = content_node.get('content', '')
                
                if node_type == 'heading1':
                    # heading1 is the main summary
                    summary = node_content
                elif node_type == 'heading2':
                    # heading2 is the short summary
                    if not short_summary:  # Take the first heading2 as short_summary
                        short_summary = node_content
                elif node_type == 'blockquote':
                    # blockquote entries make up the transcript
                    speaker_name = content_node.get('speakerName', '')
                    if speaker_name:
                        transcript += f"{speaker_name}: {node_content}\n"
                    else:
                        transcript += f"{node_content}\n"
            
            # If no transcript is constructed, skip this entry
            if not transcript:
                print(f"Warning: No transcript content found for Limitless lifelog {lifelog.get('id')}")
                continue
                
            # Create document for vector storage
            doc = {
                "id": lifelog.get('id'),
                "source": "limitless",
                "text": transcript,
                "summary": summary,
                "short_summary": short_summary,
                "date": extract_date_from_iso(lifelog.get('startTime')),
                "timestamp": lifelog.get('startTime'),
                "metadata": {
                    "startTime": lifelog.get('startTime'),
                    "endTime": lifelog.get('endTime'),
                    "source_type": "limitless"  # Add explicit source type for filtering
                }
            }
            
            limitless_docs.append(doc)
    
    # Fetch Bee data
    print("Fetching Bee data...")
    conversations = get_conversations(limit=None)
    if conversations:
        print(f"Retrieved {len(conversations)} Bee conversations")
        
        # Fetch details for each conversation
        for conversation in conversations:
            conversation_id = conversation.get('id')
            if not conversation_id:
                continue
            
            print(f"Fetching details for Bee conversation: {conversation_id}")
            conversation_details = get_conversation_details(conversation_id)
            
            # Extract text from conversation details
            text_content = ""
            
            # Check if conversation details has a 'conversation' field
            if 'conversation' in conversation_details:
                conversation_details = conversation_details['conversation']
            
            # Extract text from transcriptions and utterances
            if 'transcriptions' in conversation_details:
                utterances = []
                for transcription in conversation_details['transcriptions']:
                    if 'utterances' in transcription:
                        utterances.extend(transcription['utterances'])
                
                # Sort utterances by time for chronological order
                if utterances and all('start' in u for u in utterances):
                    utterances.sort(key=lambda u: u.get('start', 0))
                
                # Extract and join the text from all utterances
                text_parts = []
                for utterance in utterances:
                    if 'text' in utterance:
                        speaker = f"Speaker {utterance.get('speaker', 'unknown')}: " if 'speaker' in utterance else ""
                        text_parts.append(f"{speaker}{utterance['text']}")
                
                text_content = "\n".join(text_parts)
                
                if text_content:
                    print(f"Extracted {len(text_parts)} utterances from conversation {conversation_id}")
            
            # If no transcription found, try using summary
            if not text_content and conversation.get('summary'):
                text_content = conversation.get('summary')
                print(f"Using summary as text content for conversation {conversation_id}")
            
            # If still no text, try using short_summary
            if not text_content and conversation.get('short_summary'):
                text_content = conversation.get('short_summary')
                print(f"Using short_summary as text content for conversation {conversation_id}")
            
            # Skip if there's no text content to index
            if not text_content:
                print(f"Warning: No text content found for Bee conversation {conversation_id}")
                continue
            
            doc = {
                'id': f"bee_{conversation_id}",
                'source': 'bee',
                'timestamp': conversation.get('start_time'),
                'text': text_content,
                'summary': conversation.get('summary', ''),
                'short_summary': conversation.get('short_summary', ''),
                'date': extract_date_from_iso(conversation.get('start_time', '')),
                'metadata': {
                    'startTime': conversation.get('start_time'),
                    'endTime': conversation.get('end_time'),
                    'location': conversation.get('primary_location'),
                    'source_type': 'bee'  # Add explicit source type for filtering
                },
                'original': conversation
            }
            bee_docs.append(doc)
    
    # Step 5: Add documents to vector store with separate namespaces
    if limitless_docs:
        print(f"Adding {len(limitless_docs)} Limitless documents to vector store")
        vector_store.add_texts(limitless_docs, namespace="limitless")
        print("Limitless documents added successfully")
    
    if bee_docs:
        print(f"Adding {len(bee_docs)} Bee documents to vector store")
        vector_store.add_texts(bee_docs, namespace="bee")
        print("Bee documents added successfully")
    
    print("Vector store rebuild completed successfully")

if __name__ == "__main__":
    rebuild_vector_store()
