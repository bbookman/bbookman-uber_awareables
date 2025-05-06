#!/usr/bin/env python3
"""
Script to add sample data directly to the vector store.
This bypasses the API integration and is useful for testing.
"""
import os
import sys
from pathlib import Path
import numpy as np
from datetime import datetime

# Add parent directory to path
sys.path.append(str(Path(__file__).parent))

from storage.vector_store import FAISSVectorStore
from storage.embeddings import DocumentEmbedder

def add_sample_data():
    """Add sample data directly to the vector store"""
    print("Adding sample data to vector store...")
    
    # Initialize components
    vector_store = FAISSVectorStore()
    embedder = DocumentEmbedder()
    
    # Create sample documents
    sample_docs = [
        {
            "id": "sample_limitless_1",
            "source": "limitless",
            "text": "This is a sample transcript from Limitless. The meeting was about project planning.",
            "summary": "Project planning discussion",
            "date": "2025-05-06",
            "timestamp": "2025-05-06T10:30:00Z"
        },
        {
            "id": "sample_limitless_2",
            "source": "limitless",
            "text": "Follow-up meeting discussing timeline adjustments for Q3 deliverables.",
            "summary": "Q3 timeline adjustments",
            "date": "2025-05-06",
            "timestamp": "2025-05-06T14:45:00Z"
        },
        {
            "id": "sample_bee_1",
            "source": "bee",
            "text": "Conversation with marketing team about upcoming campaign launch.",
            "summary": "Marketing campaign discussion",
            "date": "2025-05-06",
            "timestamp": "2025-05-06T11:15:00Z"
        }
    ]
    
    print(f"Created {len(sample_docs)} sample documents")
    
    # Process documents for embedding
    try:
        # Get the texts to embed
        texts = [doc.get("text", "") for doc in sample_docs]
        
        # Generate embeddings directly
        model = vector_store.model
        embeddings = model.encode(texts)
        embeddings = np.array(embeddings).astype('float32')
        
        print(f"Generated embeddings with shape: {embeddings.shape}")
        
        # Add the embeddings to the index
        current_size = vector_store.index.ntotal
        vector_store.index.add(embeddings)
        
        # Add documents to the metadata store
        for i, doc in enumerate(sample_docs):
            doc_with_idx = dict(doc)
            doc_with_idx["vector_id"] = current_size + i
            vector_store.documents.append(doc_with_idx)
            
        # Save the vector store
        vector_store._save()
        print(f"Added and saved {len(sample_docs)} documents to vector store")
        
        # Get vector store stats
        stats = vector_store.get_stats()
        print("\nVector store stats after adding sample data:")
        print(f"- Total documents: {stats['total_documents']}")
        for source, count in stats.get('sources', {}).items():
            print(f"- {source}: {count} documents")
        print(f"- Dates: {len(stats.get('dates', {}))} unique dates")
        
        # Test search functionality
        print("\nTesting search functionality:")
        results = vector_store.search("project planning", k=2)
        if results:
            print(f"Search found {len(results)} results")
            for i, result in enumerate(results):
                print(f"Result {i+1}: {result.get('text')[:50]}... (score: {result.get('score'):.4f})")
        else:
            print("Search returned no results")
        
    except Exception as e:
        print(f"Error adding sample data: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    add_sample_data()