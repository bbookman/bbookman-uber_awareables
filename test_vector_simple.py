#!/usr/bin/env python3
"""
Simplified test script for the vector store
"""
import os
import sys
from pathlib import Path

# Add current directory to path
sys.path.append(str(Path(__file__).parent))

from storage.vector_store import FAISSVectorStore
from sentence_transformers import SentenceTransformer
import numpy as np

def test_vector_store_simple():
    """Test vector store with manually created embeddings"""
    print("Testing vector store with manual document creation...")
    
    # Initialize the vector store
    vector_store = FAISSVectorStore()
    print(f"Vector store initialized with {len(vector_store.documents)} documents")
    
    try:
        # Create a test document manually (bypassing the embedder)
        model = SentenceTransformer("all-MiniLM-L6-v2")
        test_text = "This is a test document for the vector store"
        embedding = model.encode([test_text])[0]  # Get just the array, not array of arrays
        
        # Create document with embedding manually
        test_doc = {
            "id": "test_123",
            "text": test_text,
            "source": "test",
            "date": "2025-05-06",
            "embedding": embedding
        }
        
        # Add to vector store directly (instead of using the embedder)
        print("Adding test document to vector store...")
        result = vector_store.add_documents([test_doc])
        print(f"Added {result} documents to vector store")
        
        # Save the store
        vector_store._save()
        print("Vector store saved")
        
        # Reload and check
        print("Reloading vector store...")
        new_store = FAISSVectorStore()
        print(f"Reloaded vector store has {len(new_store.documents)} documents")
        
        # Test search
        print("\nTesting search...")
        results = new_store.search("test document")
        print(f"Search found {len(results)} results")
        if results:
            print(f"First result: {results[0].get('text')[:50]}... with score {results[0].get('score'):.4f}")
        
        print("\nTest completed successfully!")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_vector_store_simple()