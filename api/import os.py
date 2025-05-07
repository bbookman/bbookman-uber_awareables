import os
import sys
import shutil
from datetime import datetime, timedelta

# Add the project root to the path so we can import our modules
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
sys.path.append(project_root)

from api.data_sync import DataSyncer
from api.vector_store import VectorStore
from api.config import Config

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
    vector_store = VectorStore()
    
    # Step 3: Create a DataSyncer instance
    data_syncer = DataSyncer()
    
    # Step 4: Fetch data from all sources
    # Calculate a date range that covers a reasonable amount of historical data
    # (adjust as needed based on your requirements)
    end_date = datetime.now()
    start_date = end_date - timedelta(days=365)  # Fetch up to a year of data
    
    print(f"Fetching data from {start_date.date()} to {end_date.date()}")
    
    # Fetch data from all your sources
    data = {}
    
    # Fetch Limitless data
    print("Fetching Limitless data...")
    limitless_data = data_syncer.fetch_limitless_data(start_date, end_date)
    if limitless_data:
        data['limitless'] = limitless_data
        print(f"Retrieved {len(limitless_data)} Limitless entries")
    
    # Fetch data from other sources as needed
    # data['other_source'] = data_syncer.fetch_other_source_data(start_date, end_date)
    
    # Step 5: Process and add data to the vector store
    print("Processing data for vector storage...")
    documents = data_syncer.combine_data_for_vector_storage(data)
    
    if documents:
        print(f"Adding {len(documents)} documents to vector store")
        vector_store.add_texts(documents)
        print("Documents added successfully")
    else:
        print("No documents to add to vector store")
    
    print("Vector store rebuild completed successfully")

if __name__ == "__main__":
    rebuild_vector_store()