import sys
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import numpy as np

# Add parent directory to path so we can import from the root
sys.path.append(str(Path(__file__).parent.parent))

from api.data_sync import DataSyncer
from storage.vector_store import FAISSVectorStore
from storage.embeddings import DocumentEmbedder

class DataIngestion:
    """
    Class to handle ingesting data from APIs into vector storage.
    """
    
    def __init__(self):
        """
        Initialize the data ingestion process.
        """
        self.data_syncer = DataSyncer()
        self.vector_store = FAISSVectorStore()
        self.embedder = DocumentEmbedder()
        
    def ingest_data(self, start_date=None, end_date=None, days=1, limit_per_day=50):
        """
        Fetch data from APIs and store it in the vector database.
        
        Args:
            start_date: Start date in ISO format (YYYY-MM-DD), defaults to today
            end_date: End date in ISO format (YYYY-MM-DD), defaults to today
            days: Number of days to synchronize if start_date is not provided
            limit_per_day: Maximum number of records to fetch per day per API
            
        Returns:
            Dictionary with information about the ingested data
        """
        print(f"Ingesting data from {start_date or 'today'} to {end_date or 'today'}")
        
        # Fetch data from both APIs
        data = self.data_syncer.synchronize_data(
            start_date=start_date,
            end_date=end_date,
            days=days,
            limit_per_day=limit_per_day
        )
        
        # Convert data to vector store format
        documents = self.data_syncer.combine_data_for_vector_storage(data)
        
        print(f"Prepared {len(documents)} documents for vector storage")
        
        # Process each document for better embedding by chunking long texts
        chunked_documents = []
        for doc in documents:
            # Skip documents without text
            if not doc.get('text'):
                print(f"Skipping document without text: {doc.get('id', 'unknown')}")
                continue
                
            text = doc.get('text')
            
            # For shorter texts (less than 2000 chars), store as is
            if len(text) < 2000:
                chunked_documents.append(doc)
            else:
                # For longer texts, create chunks with overlap
                print(f"Chunking document {doc.get('id', 'unknown')} ({len(text)} chars)")
                metadata = {k: v for k, v in doc.items() if k != 'text'}
                chunks = self.embedder.embed_chunked_document(
                    text=text,
                    metadata=metadata,
                    chunk_size=2000,
                    overlap=200
                )
                chunked_documents.extend(chunks)
        
        print(f"After chunking: {len(chunked_documents)} documents")
        
        if not chunked_documents:
            print("No valid documents to add to vector store")
            return {
                "total_documents": len(documents),
                "processed_documents": 0,
                "added_to_vector_store": 0,
            }
        
        # FIXED: Add documents directly instead of using the problematic add_documents method
        # Get the texts to embed
        texts = [doc.get("text", "") for doc in chunked_documents]
        
        # Generate embeddings directly
        model = self.vector_store.model
        embeddings = model.encode(texts)
        embeddings = np.array(embeddings).astype('float32')
        
        print(f"Generated embeddings with shape: {embeddings.shape}")
        
        # Add the embeddings to the index
        current_size = self.vector_store.index.ntotal
        self.vector_store.index.add(embeddings)
        
        # Add documents to the metadata store
        for i, doc in enumerate(chunked_documents):
            doc_with_idx = dict(doc)
            doc_with_idx["vector_id"] = current_size + i
            self.vector_store.documents.append(doc_with_idx)
            
        # Save the vector store
        self.vector_store._save()
        added_count = len(chunked_documents)
        
        print(f"Added {added_count} documents to vector store")
        
        return {
            "total_documents": len(documents),
            "processed_documents": len(chunked_documents),
            "added_to_vector_store": added_count,
        }
    
    def search_conversations(self, query, k=5, date=None, source=None):
        """
        Search for conversations in the vector store.
        
        Args:
            query: Search query
            k: Number of results to return
            date: Optional date filter (YYYY-MM-DD)
            source: Optional source filter ('limitless' or 'bee')
            
        Returns:
            List of matching documents
        """
        if date and source:
            def filter_fn(doc):
                doc_date = doc.get("date")
                return (doc_date and doc_date.startswith(date) and 
                        doc.get("source") == source)
            
            return self.vector_store.search(query, k, filter_fn)
        elif date:
            return self.vector_store.search_by_date(query, date, k)
        elif source:
            return self.vector_store.search_by_source(query, source, k)
        else:
            return self.vector_store.search(query, k)


if __name__ == "__main__":
    # Example usage
    ingestion = DataIngestion()
    
    # Ingest data from the last 7 days
    result = ingestion.ingest_data(days=7, limit_per_day=20)
    print(f"Ingestion result: {result}")
    
    # Test search
    print("\nTesting search functionality:")
    query = "What happened during my recent conversations?"
    results = ingestion.search_conversations(query, k=3)
    
    if results:
        print(f"Found {len(results)} results for query: {query}")
        for i, result in enumerate(results, 1):
            print(f"\nResult {i}:")
            print(f"Score: {result.get('score', 0):.4f}")
            print(f"Source: {result.get('source')}")
            print(f"Date: {result.get('date')}")
            print(f"Text snippet: {result.get('text', '')[:200]}...")
    else:
        print(f"No results found for query: {query}")
    
    # Get store stats
    stats = ingestion.vector_store.get_stats()
    print(f"\nVector Store Stats: {stats}")