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
        """
        Initialize the DataSyncer with API keys.
        """
        self.limitless_api_key = limitless_api_key
        self.bee_api_key = bee_api_key
        
        # Ensure we have the required API keys
        if not self.limitless_api_key:
            print("Warning: Limitless API key not found. Limitless data will not be fetched.")
        if not self.bee_api_key:
            print("Warning: Bee API key not found. Bee data will not be fetched.")
    
    def fetch_limitless_data(self, date=None, limit=None):
        """
        Fetch data from Limitless API.
        
        Args:
            date: Date string in ISO format (YYYY-MM-DD)
            limit: Maximum number of lifelogs to fetch (None means fetch all)
            
        Returns:
            List of lifelogs
        """
        if not self.limitless_api_key:
            return []
            
        try:
            limit_str = str(limit) if limit is not None else "ALL"
            print(f"Fetching Limitless data for date: {date}, limit: {limit_str}")
            return get_lifelogs(api_key=self.limitless_api_key, date=date, limit=limit)
        except Exception as e:
            print(f"Error fetching Limitless data: {str(e)}")
            return []
    
    def fetch_bee_data(self, date=None, limit=None):
        """
        Fetch data from Bee API.
        
        Args:
            date: Date string in ISO format (YYYY-MM-DD) - Note: Not directly used as Bee API doesn't support date filtering
            limit: Maximum number of conversations to fetch (None means fetch all)
            
        Returns:
            Dictionary containing conversations and their detailed data
        """
        if not self.bee_api_key:
            return {}
            
        try:
            limit_str = str(limit) if limit is not None else "ALL"
            print(f"Fetching Bee data (will filter by date: {date} later if needed), limit: {limit_str}")
            
            # Initial fetch
            conversations = get_conversations(api_key=self.bee_api_key, limit=limit, page=1)
            
            # Filter conversations by date if specified
            if date and conversations:
                filtered_conversations = []
                for conv in conversations:
                    # Check if start_time contains the specified date
                    start_time = conv.get('start_time', '')
                    if start_time and start_time.startswith(date):
                        filtered_conversations.append(conv)
                conversations = filtered_conversations
                print(f"Filtered conversations by date {date}: {len(conversations)} results")
            
            # Fetch detailed data for each conversation
            conversation_details = {}
            for conversation in conversations:
                conversation_id = conversation.get('id')
                if conversation_id:
                    print(f"Fetching details for conversation ID: {conversation_id}")
                    details = get_conversation_details(conversation_id, self.bee_api_key)
                    conversation_details[conversation_id] = details
            
            return {
                'conversations': conversations,
                'details': conversation_details
            }
        except Exception as e:
            print(f"Error fetching Bee data: {str(e)}")
            return {}
    
    def synchronize_data(self, start_date=None, end_date=None, days=1, limit_per_day=None):
        """
        Synchronize data from both APIs for a date range.
        
        Args:
            start_date: Start date in ISO format (YYYY-MM-DD), defaults to today
            end_date: End date in ISO format (YYYY-MM-DD), defaults to today
            days: Number of days to synchronize if start_date is not provided
            limit_per_day: Maximum number of records to fetch per day per API (None means all)
            
        Returns:
            Dictionary containing unified data from both APIs
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
        
        # Initialize result container
        result = {
            'limitless': [],
            'bee': {}
        }
        
        # Iterate through each day in the date range
        current_date = start
        while current_date <= end:
            date_str = current_date.strftime('%Y-%m-%d')
            
            # Fetch data from both APIs
            limitless_data = self.fetch_limitless_data(date=date_str, limit=limit_per_day)
            bee_data = self.fetch_bee_data(date=date_str, limit=limit_per_day)
            
            # Add to results
            result['limitless'].extend(limitless_data)
            if 'conversations' in bee_data:
                if date_str not in result['bee']:
                    result['bee'][date_str] = {'conversations': [], 'details': {}}
                
                result['bee'][date_str]['conversations'].extend(bee_data.get('conversations', []))
                result['bee'][date_str]['details'].update(bee_data.get('details', {}))
            
            # Move to next day
            current_date += timedelta(days=1)
        
        return result
    
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
                "text": transcript,  # Use the constructed transcript
                "summary": summary,
                "short_summary": short_summary,
                "date": DataSyncer.extract_date_from_iso(lifelog.get('startTime')),
                "timestamp": lifelog.get('startTime'),
                "metadata": {
                    "startTime": lifelog.get('startTime'),
                    "endTime": lifelog.get('endTime')
                    # Add other metadata fields as needed
                }
            }
            
            documents.append(doc)
        
        # Process Bee data
        for date, bee_data in data.get('bee', {}).items():
            conversations = bee_data.get('conversations', [])
            details = bee_data.get('details', {})
            
            for conversation in conversations:
                if 'id' not in conversation:
                    continue
                    
                conversation_id = conversation['id']
                conversation_details = details.get(conversation_id, {})
                
                # Extract text from conversation details
                text_content = ""
                
                # Check if conversation details has a 'conversation' field (as shown in your example)
                if 'conversation' in conversation_details:
                    conversation_details = conversation_details['conversation']
                
                # Extract text from transcriptions and utterances - THIS IS THE KEY FIX
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
                    'date': conversation.get('start_time', '').split('T')[0] if 'start_time' in conversation else date,
                    'metadata': {
                        'startTime': conversation.get('start_time'),
                        'endTime': conversation.get('end_time'),
                        'location': conversation.get('primary_location')
                    },
                    'original': conversation
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