import os
import json
import pickle
import faiss
import numpy as np
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from sentence_transformers import SentenceTransformer
from config import VECTOR_DB_PATH

class FAISSVectorStore:
    """
    Vector store implementation using FAISS for efficient similarity search.
    """
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2", vector_dim: int = 384):
        """
        Initialize the FAISS vector store.
        
        Args:
            model_name: Name of the sentence-transformers model to use for embeddings
            vector_dim: Dimension of the embedding vectors
        """
        self.model_name = model_name
        self.vector_dim = vector_dim
        self.model = SentenceTransformer(model_name)
        
        # Initialize FAISS index
        self.index = faiss.IndexFlatL2(self.vector_dim)
        
        # Storage for document metadata
        self.documents = []
        
        # Create the vector DB directory if it doesn't exist
        self.db_path = Path(VECTOR_DB_PATH)
        self.db_path.mkdir(exist_ok=True, parents=True)
        
        # Paths for storing the index and documents
        self.index_path = self.db_path / "faiss_index.bin"
        self.docs_path = self.db_path / "documents.pkl"
        
        # Load existing data if available
        self._load()
    
    def _load(self):
        """
        Load existing index and documents if available.
        """
        if self.index_path.exists() and self.docs_path.exists():
            try:
                # Load FAISS index
                self.index = faiss.read_index(str(self.index_path))
                
                # Load document metadata
                with open(self.docs_path, 'rb') as f:
                    self.documents = pickle.load(f)
                
                print(f"Loaded {len(self.documents)} documents from vector store")
            except Exception as e:
                print(f"Error loading vector store: {str(e)}")
                # If loading fails, use empty index and documents
                self.index = faiss.IndexFlatL2(self.vector_dim)
                self.documents = []
    
    def _save(self):
        """
        Save the current index and documents.
        """
        try:
            # Save FAISS index
            faiss.write_index(self.index, str(self.index_path))
            
            # Save document metadata
            with open(self.docs_path, 'wb') as f:
                pickle.dump(self.documents, f)
            
            print(f"Saved {len(self.documents)} documents to vector store")
        except Exception as e:
            print(f"Error saving vector store: {str(e)}")
    
    def add_documents(self, documents: List[Dict[str, Any]]) -> int:
        """
        Add documents to the vector store.
        
        Args:
            documents: List of document dictionaries with at least 'id' and 'text' fields
            
        Returns:
            Number of documents added
        """
        # Check if documents is empty using the proper method
        if isinstance(documents, np.ndarray):
            if documents.size == 0:
                return 0
        elif not documents:
            return 0
            
        # Extract text for embedding
        texts = [doc.get("text", "") for doc in documents]
        if not any(texts):
            return 0
            
        # Generate embeddings
        embeddings = self.model.encode(texts)
        
        # Ensure embeddings are float32 (required by FAISS)
        embeddings = np.array(embeddings).astype('float32')
        
        # Current index size
        current_size = self.index.ntotal
        
        # Add documents to index
        self.index.add(embeddings)
        
        # Store document metadata
        for i, doc in enumerate(documents):
            # Add document with its index in the FAISS store
            doc_with_idx = dict(doc)
            doc_with_idx["vector_id"] = current_size + i
            self.documents.append(doc_with_idx)
        
        # Save updated store
        self._save()
        
        return len(documents)
    
    def add_texts(self, documents: List[Dict[str, Any]], namespace: str = None) -> int:
        """
        Add documents to the vector store with optional namespace.
        
        Args:
            documents: List of document dictionaries
            namespace: Optional namespace to categorize documents
            
        Returns:
            Number of documents added
        """
        if not documents:
            return 0
            
        # Add namespace to document metadata if provided
        if namespace:
            for doc in documents:
                if 'metadata' not in doc:
                    doc['metadata'] = {}
                doc['metadata']['namespace'] = namespace
        
        # Continue with adding documents to the store
        return self.add_documents(documents)
    
    def search(self, query: str, k: int = 5, filter_fn=None, namespace: str = None) -> List[Dict[str, Any]]:
        """
        Search for documents similar to the query.
        
        Args:
            query: Query string
            k: Number of results to return
            filter_fn: Optional function to filter results
            namespace: Optional namespace to search within
            
        Returns:
            List of document dictionaries with similarity scores
        """
        if not query or self.index.ntotal == 0:
            return []
            
        # Create a combined filter function if namespace is provided
        if namespace:
            original_filter = filter_fn
            
            def namespace_filter(doc):
                # Check if the document belongs to the specified namespace
                doc_namespace = doc.get('metadata', {}).get('namespace')
                namespace_match = doc_namespace == namespace
                
                # Apply the original filter if it exists
                if original_filter:
                    return namespace_match and original_filter(doc)
                return namespace_match
                
            filter_fn = namespace_filter
            
        # Generate query embedding
        query_embedding = self.model.encode([query])
        query_embedding = np.array(query_embedding).astype('float32')
        
        # Search for similar vectors
        distances, indices = self.index.search(query_embedding, min(k * 2, self.index.ntotal))
        
        # Get corresponding documents
        results = []
        for i, idx in enumerate(indices[0]):
            if idx >= 0 and idx < len(self.documents):
                doc = dict(self.documents[idx])
                doc["score"] = float(1 / (1 + distances[0][i]))  # Convert distance to similarity score
                results.append(doc)
        
        # Apply filter if provided
        if filter_fn:
            results = [doc for doc in results if filter_fn(doc)]
        
        # Sort by score and limit to k results
        results = sorted(results, key=lambda x: x.get("score", 0), reverse=True)[:k]
        
        return results
    
    def search_by_date(self, query: str, date: str, k: int = 5) -> List[Dict[str, Any]]:
        """
        Search for documents from a specific date.
        
        Args:
            query: Query string
            date: Date string in YYYY-MM-DD format
            k: Number of results to return
            
        Returns:
            List of document dictionaries with similarity scores
        """
        def date_filter(doc):
            doc_date = doc.get("date")
            return doc_date and doc_date.startswith(date)
            
        return self.search(query, k, date_filter)
    
    def search_by_source(self, query: str, source: str, k: int = 5) -> List[Dict[str, Any]]:
        """
        Search for documents from a specific source (limitless or bee).
        
        Args:
            query: Query string
            source: Source string ("limitless" or "bee")
            k: Number of results to return
            
        Returns:
            List of document dictionaries with similarity scores
        """
        def source_filter(doc):
            return doc.get("source") == source
            
        return self.search(query, k, source_filter)
    
    def get_document_by_id(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a document by its ID.
        
        Args:
            doc_id: Document ID
            
        Returns:
            Document dictionary or None if not found
        """
        for doc in self.documents:
            if doc.get("id") == doc_id:
                return doc
        return None
    
    def delete_document(self, doc_id: str) -> bool:
        """
        Delete a document from the store.
        Note: This is not efficient with FAISS as we have to rebuild the index.
        
        Args:
            doc_id: Document ID to delete
            
        Returns:
            True if document was deleted, False otherwise
        """
        # Find the document
        for i, doc in enumerate(self.documents):
            if doc.get("id") == doc_id:
                # Remove from documents list
                vector_id = doc.get("vector_id")
                del self.documents[i]
                
                # Rebuild the index (FAISS doesn't support removing individual vectors)
                if len(self.documents) > 0:
                    # Extract remaining document texts
                    texts = [doc.get("text", "") for doc in self.documents]
                    
                    # Generate embeddings
                    embeddings = self.model.encode(texts)
                    embeddings = np.array(embeddings).astype('float32')
                    
                    # Create new index
                    self.index = faiss.IndexFlatL2(self.vector_dim)
                    self.index.add(embeddings)
                    
                    # Update vector_ids
                    for i, doc in enumerate(self.documents):
                        doc["vector_id"] = i
                else:
                    # If no documents left, just reset the index
                    self.index = faiss.IndexFlatL2(self.vector_dim)
                
                # Save updated store
                self._save()
                
                return True
        
        return False
    
    def clear(self) -> bool:
        """
        Clear all documents from the store.
        
        Returns:
            True if the operation was successful
        """
        self.index = faiss.IndexFlatL2(self.vector_dim)
        self.documents = []
        self._save()
        return True
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get stats about the vector store.
        
        Returns:
            Dictionary with statistics
        """
        # Count documents by source
        sources = {}
        for doc in self.documents:
            source = doc.get("source", "unknown")
            sources[source] = sources.get(source, 0) + 1
        
        # Count documents by date
        dates = {}
        for doc in self.documents:
            date = doc.get("date")
            if date:
                dates[date] = dates.get(date, 0) + 1
        
        return {
            "total_documents": len(self.documents),
            "index_size": self.index.ntotal,
            "sources": sources,
            "dates": dates,
            "model_name": self.model_name,
            "vector_dim": self.vector_dim,
            "last_updated": datetime.now().isoformat()
        }