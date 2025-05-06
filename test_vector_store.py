#!/usr/bin/env python3
"""
Test script to verify vector store functionality
"""
import os
import sys
from pathlib import Path

# Add current directory to path so Python can find our modules
sys.path.append(str(Path(__file__).parent))

# Import our modules
from storage.vector_store import FAISSVectorStore
from storage.embeddings import DocumentEmbedder
from config import VECTOR_DB_PATH

def test_vector_store():
    """Test if the vector store can be initialized and add/retrieve documents"""
    print("Testing vector store functionality...")
    
    # Check if vector_db directory exists
    print(f"Vector DB path: {VECTOR_DB_PATH}")
    if os.path.exists(VECTOR_DB_PATH):
        print(f"Vector DB directory exists: {os.listdir(VECTOR_DB_PATH)}")
    else:
        print("Vector DB directory does not exist yet")
        os.makedirs(VECTOR_DB_PATH, exist_ok=True)
        print(f"Created directory: {VECTOR_DB_PATH}")
    
    # Initialize components
    try:
        print("Initializing vector store...")
        vector_store = FAISSVectorStore()
        print("Vector store initialized successfully")
        
        # Check if the vector store has any documents
        doc_count = len(vector_store.documents) if hasattr(vector_store, 'documents') else 0
        print(f"Vector store contains {doc_count} documents")
        
        # Try adding a test document
        print("\nAttempting to add a test document...")
        embedder = DocumentEmbedder()
        
        # Create a simple test document
        test_doc = {
            "id": "test_doc_1",
            "text": "This is a test document to verify vector store functionality",
            "source": "test",
            "date": "2025-05-06"
        }
        
        # Embed the document and add to vector store
        # Using embed_documents (plural) instead of embed_document
        # Avoid NumPy array check by not attempting to evaluate it as a boolean
        embedded_docs = embedder.embed_documents([test_doc])
        print(f"Successfully embedded documents")
        
        # Add to vector store
        added = vector_store.add_documents(embedded_docs)
        print(f"Added {added} documents to vector store")
        
        # Save the vector store
        vector_store.save()
        print("Vector store saved")
        
        # Reload the vector store
        print("\nReloading vector store to verify persistence...")
        new_vector_store = FAISSVectorStore()
        new_doc_count = len(new_vector_store.documents) if hasattr(new_vector_store, 'documents') else 0
        print(f"Reloaded vector store contains {new_doc_count} documents")
        
        # Try search
        print("\nTesting search functionality...")
        search_results = new_vector_store.search("test document", k=1)
        if isinstance(search_results, list) and search_results:
            print(f"Search successful! Found {len(search_results)} results")
            print(f"First result: {search_results[0].get('text', '')[:50]}...")
        else:
            print(f"Search returned no results: {search_results}")
        
        print("\nTest completed successfully!")
    
    except Exception as e:
        print(f"Error testing vector store: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_vector_store()