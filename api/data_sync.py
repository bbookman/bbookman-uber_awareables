import os
from datetime import datetime, timedelta
import sys
from pathlib import Path
import shutil

# Add parent directory to path so we can import from the root
sys.path.append(str(Path(__file__).parent.parent))

from config import (
    LIMITLESS_API_KEY, 
    BEE_API_KEY, 
    VECTOR_DB_PATH
)
from api.limitless_api import get_lifelogs
from api.bee_api import get_conversations, get_conversation_details
from storage.vector_store import FAISSVectorStore  # Changed from api.vector_store import VectorStore

class DataSyncer:
    """
    Class to synchronize and unify data from both Limitless and Bee APIs
    """
    
    def __init__(self, limitless_api_key=LIMITLESS_API_KEY, bee_api_key=BEE_API_KEY):
        """Initialize the DataSyncer with API keys."""
        self.limitless_api_key = limitless_api_key
        self.bee_api_key = bee_api_key
        
        # Ensure we have the required API keys
        if not self.limitless_api_key:
            print("Warning: Limitless API key not found. Limitless data will not be fetched.")
        if not self.bee_api_key:
            print("Warning: Bee API key not found. Bee data will not be fetched.")
    
    def fetch_limitless_data(self, vector_store=None, date=None, limit=None):
        """
        Fetch data from Limitless API, stopping when we hit existing data.
        
        Args:
            vector_store: Optional vector store to check for existing data
            date: Date string in ISO format (YYYY-MM-DD)
            limit: Maximum number of lifelogs to fetch (None means fetch all)
            
        Returns:
            List of lifelogs
        """
        if not self.limitless_api_key:
            return []
            
        try:
            # Get information about existing data if we have a vector store
            latest_date = None
            if vector_store:
                latest_date = vector_store.get_latest_document_date("limitless")
                print(f"Found latest Limitless document date: {latest_date}")

            # Get lifelogs, starting from the day after our latest date if we have one
            # This ensures we don't miss any data from the latest day
            start_date = None
            if latest_date:
                # Use the latest date as our starting point - the API will get everything after this
                # Since we're using descending order, we'll get newest first and can stop when we hit this date
                start_date = latest_date
                
            print(f"Fetching Limitless data starting from: {start_date if start_date else 'all time'}")
            
            limit_str = str(limit) if limit is not None else "ALL"
            print(f"Fetching Limitless data with limit: {limit_str}")
            
            return get_lifelogs(
                api_key=self.limitless_api_key,
                date=start_date,
                limit=limit,
                direction="desc"  # Get newest first so we can stop when we hit existing data
            )
        except Exception as e:
            print(f"Error fetching Limitless data: {str(e)}")
            return []

    def fetch_bee_data(self, vector_store=None, date=None, limit=None):
        """
        Fetch data from Bee API, stopping when we hit existing data.
        
        Args:
            vector_store: Optional vector store to check for existing data
            date: Date string in ISO format (YYYY-MM-DD)
            limit: Maximum number of conversations to fetch (None means fetch all)
            
        Returns:
            Dictionary containing conversations and details
        """
        if not self.bee_api_key:
            print("No Bee API key configured")
            return {}
            
        try:
            # Get information about existing data if we have a vector store
            existing_ids = set()
            latest_date = None
            if vector_store:
                existing_ids = {id.replace('bee_', '') for id in vector_store.get_document_ids("bee")}
                latest_date = vector_store.get_latest_document_date("bee")
                print(f"Found {len(existing_ids)} existing Bee documents, latest date: {latest_date}")

            conversations = []
            details = {}
            page = 1
            batch_size = min(50, limit) if limit else 50  # Use smaller batch size if limit < 50
            found_existing = False
            
            while not found_existing:
                try:
                    batch = get_conversations(api_key=self.bee_api_key, limit=batch_size, page=page)
                    if not batch:
                        break
                        
                    # Sort by date descending to ensure consistent ordering
                    batch.sort(key=lambda x: x.get('start_time', ''), reverse=True)
                    
                    # Process each conversation in the batch
                    for conversation in batch:
                        conversation_id = conversation.get('id')
                        if not conversation_id:
                            continue
                        
                        # If we hit an existing conversation ID, we can stop since they're ordered by date
                        if conversation_id in existing_ids:
                            print(f"Found existing conversation {conversation_id}, stopping fetch")
                            found_existing = True
                            break
                            
                        # Check the date if we have latest_date
                        if latest_date:
                            conversation_date = self.extract_date_from_iso(conversation.get('start_time'))
                            if not conversation_date:
                                print(f"Warning: Could not extract date from conversation {conversation_id}")
                                continue
                                
                            if conversation_date <= latest_date:
                                print(f"Reached existing date {conversation_date}, stopping fetch")
                                found_existing = True
                                break

                        print(f"Fetching details for conversation ID: {conversation_id}")
                        try:
                            conversation_details = get_conversation_details(conversation_id, self.bee_api_key)
                            if conversation_details:
                                details[conversation_id] = conversation_details
                                conversations.append(conversation)
                                print(f"Added new conversation {conversation_id}")
                                
                                # Check if we've hit the limit after adding a conversation
                                if limit and len(conversations) >= limit:
                                    print(f"Reached conversation limit of {limit}")
                                    found_existing = True
                                    break
                            else:
                                print(f"No details found for conversation {conversation_id}")
                        except Exception as e:
                            print(f"Error fetching details for conversation {conversation_id}: {e}")
                            continue
                    
                    if found_existing or len(batch) < batch_size:
                        break
                    
                    page += 1
                    print(f"Moving to page {page}")
                    
                except Exception as e:
                    print(f"Error fetching Bee conversations page {page}: {e}")
                    break
            
            if limit and len(conversations) > limit:
                conversations = conversations[:limit]
                print(f"Trimmed to {len(conversations)} conversations to match limit")
                
            if conversations:
                print(f"Retrieved {len(conversations)} new Bee conversations")
                
            return {
                'conversations': conversations,
                'details': details
            }
        except Exception as e:
            print(f"Error in fetch_bee_data: {e}")
            return {}

    def synchronize_data(self, vector_store=None, limit=None):
        """
        Fetch and synchronize all data from both APIs, skipping existing data.
        
        Args:
            vector_store: Optional vector store to check for existing data
            limit: Optional limit on number of entries to fetch per API
            
        Returns:
            Dictionary containing synchronized data from both sources
        """
        data = {
            'limitless': [],
            'bee': {}
        }
        
        # Fetch all Limitless data
        print("Fetching Limitless data...")
        limitless_data = self.fetch_limitless_data(vector_store=vector_store, limit=limit)
        if limitless_data:
            data['limitless'] = limitless_data
            print(f"Retrieved {len(limitless_data)} new entries from Limitless API")
        
        # Fetch all Bee data
        print("Fetching Bee data...")
        bee_data = self.fetch_bee_data(vector_store=vector_store, limit=limit)
        if bee_data:
            data['bee'] = bee_data
            print(f"Retrieved {len(bee_data.get('conversations', []))} new entries from Bee API")
        
        return data
    
    @staticmethod
    def extract_date_from_iso(iso_string):
        """Extract date from ISO datetime string."""
        if not iso_string:
            return ""
        return iso_string.split("T")[0]
    
    @staticmethod
    def combine_data_for_vector_storage(data):
        """
        Combine and format data from both APIs to prepare for vector storage.
        
        Args:
            data: Dictionary containing data from both APIs
            
        Returns:
            List of documents ready for vector embedding
        """
        documents = []
        
        # Process Limitless data
        for lifelog in data.get('limitless', []):
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
                "date": DataSyncer.extract_date_from_iso(lifelog.get('startTime')),
                "timestamp": lifelog.get('startTime'),
                "metadata": {
                    "startTime": lifelog.get('startTime'),
                    "endTime": lifelog.get('endTime'),
                    "source_type": "limitless"  # Add explicit source type for filtering
                }
            }
            
            documents.append(doc)
        
        # Process Bee data
        bee_data = data.get('bee', {})
        conversations = bee_data.get('conversations', [])
        details = bee_data.get('details', {})
        
        for conversation in conversations:
            conversation_id = conversation.get('id')
            if not conversation_id:
                continue
                
            conversation_details = details.get(conversation_id, {})
            
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
                'date': DataSyncer.extract_date_from_iso(conversation.get('start_time')),
                'metadata': {
                    'startTime': conversation.get('start_time'),
                    'endTime': conversation.get('end_time'),
                    'location': conversation.get('primary_location'),
                    'source_type': 'bee'  # Add explicit source type for filtering
                }
            }
            documents.append(doc)
        
        return documents


# Example usage
if __name__ == "__main__":
    syncer = DataSyncer()
    # Fetch data for the last 3 days
    data = syncer.synchronize_data(days=3, limit_per_day=None)  # None means fetch all available data
    
    # Prepare for vector storage
    documents = DataSyncer.combine_data_for_vector_storage(data)
    print(f"Processed {len(documents)} documents for vector storage")

import os
import sys
import shutil
from datetime import datetime, timedelta

# Add the project root to the path so we can import our modules
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
sys.path.append(project_root)

from api.data_sync import DataSyncer
from storage.vector_store import FAISSVectorStore  # Corrected import
from config import Config  # Corrected import to reference the root directory
from api.bee_api import get_conversations, get_conversation_details

def rebuild_vector_store():
    """Delete and rebuild the vector store from scratch."""
    config = Config()
    
    # Step 1: Delete the existing vector store
    vector_store_path = config.get_vector_store_path()
    if os.path.exists(vector_store_path):
        print(f"Deleting existing vector store at {vector_store_path}")
        shutil.rmtree(vector_store_path)
        print("Vector store deleted successfully")
    
    # Step 2: Initialize a new vector store
    print("Initializing new vector store")
    vector_store = FAISSVectorStore()
    
    # Step 3: Create a DataSyncer instance
    data_syncer = DataSyncer()
    
    # Step 4: Fetch data from all sources
    # Calculate a date range that covers a reasonable amount of historical data
    end_date = datetime.now()
    start_date = end_date - timedelta(days=90)  # Fetch up to 90 days of data
    
    print(f"Fetching data from {start_date.date()} to {end_date.date()}")
    
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
                "date": DataSyncer.extract_date_from_iso(lifelog.get('startTime')),
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
                'date': conversation.get('start_time', '').split('T')[0] if 'start_time' in conversation else '',
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