#!/usr/bin/env python3
"""
Script to update the vector store with new data from Limitless and Bee APIs.
"""
import os
import sys
from pathlib import Path

# Add the project root to the path so we can import our modules
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
sys.path.append(project_root)

from api.data_sync import DataSyncer
from storage.vector_store import FAISSVectorStore
from config import VECTOR_DB_PATH

def update_vector_store():
    """Update the vector store with new data from both APIs."""
    # Initialize vector store
    print("Initializing vector store")
    vector_store = FAISSVectorStore()
    
    # Create DataSyncer instance
    data_syncer = DataSyncer()
    
    # Fetch and synchronize new data from both APIs
    print("Fetching new data from APIs...")
    data = data_syncer.synchronize_data(vector_store=vector_store)
    
    if not data.get('limitless') and not data.get('bee', {}).get('conversations'):
        print("No new data found to add to vector store")
        return
    
    # Process new data for vector storage
    documents = data_syncer.combine_data_for_vector_storage(data)
    if not documents:
        print("No documents to add after processing")
        return
    
    print(f"Adding {len(documents)} new documents to vector store")
    
    # Group documents by source
    limitless_docs = [doc for doc in documents if doc['source'] == 'limitless']
    bee_docs = [doc for doc in documents if doc['source'] == 'bee']
    
    # Add documents to vector store with appropriate namespaces
    if limitless_docs:
        print(f"Adding {len(limitless_docs)} Limitless documents")
        vector_store.add_texts(limitless_docs, namespace="limitless")
    
    if bee_docs:
        print(f"Adding {len(bee_docs)} Bee documents")
        vector_store.add_texts(bee_docs, namespace="bee")
    
    print("Vector store update completed successfully")

if __name__ == "__main__":
    update_vector_store()
