import os
import json
from typing import List, Dict, Any, Union, Optional
from pathlib import Path
import numpy as np
from sentence_transformers import SentenceTransformer

class DocumentEmbedder:
    """
    Utility class for generating embeddings for documents and queries.
    """
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        """
        Initialize the document embedder.
        
        Args:
            model_name: Name of the sentence-transformers model to use for embeddings
        """
        self.model_name = model_name
        self.model = SentenceTransformer(model_name)
    
    def embed_documents(self, documents: List[Dict[str, Any]], text_field: str = "text") -> np.ndarray:
        """
        Generate embeddings for a list of documents.
        
        Args:
            documents: List of document dictionaries
            text_field: Field in the document containing the text to embed
            
        Returns:
            Numpy array of embeddings
        """
        texts = [doc.get(text_field, "") for doc in documents]
        return self.embed_texts(texts)
    
    def embed_texts(self, texts: List[str]) -> np.ndarray:
        """
        Generate embeddings for a list of texts.
        
        Args:
            texts: List of text strings
            
        Returns:
            Numpy array of embeddings
        """
        if not texts:
            return np.array([])
            
        embeddings = self.model.encode(texts)
        return np.array(embeddings).astype('float32')
    
    def embed_query(self, query: str) -> np.ndarray:
        """
        Generate embedding for a query string.
        
        Args:
            query: Query string
            
        Returns:
            Numpy array of embeddings
        """
        if not query:
            return np.array([])
            
        embedding = self.model.encode([query])
        return np.array(embedding).astype('float32')
    
    @staticmethod
    def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 200) -> List[str]:
        """
        Split text into overlapping chunks for better embedding.
        
        Args:
            text: Text to chunk
            chunk_size: Maximum size of each chunk
            overlap: Overlap between chunks
            
        Returns:
            List of text chunks
        """
        if not text or len(text) <= chunk_size:
            return [text] if text else []
            
        chunks = []
        start = 0
        
        while start < len(text):
            # Find a good breakpoint (preferably at the end of a sentence)
            end = min(start + chunk_size, len(text))
            
            # Try to end at a sentence boundary if possible
            if end < len(text):
                # Look for sentence endings (., !, ?) within the last 100 characters
                search_start = max(end - 100, start)
                last_period = max(
                    text.rfind('. ', search_start, end),
                    text.rfind('! ', search_start, end),
                    text.rfind('? ', search_start, end)
                )
                
                if last_period > start:
                    end = last_period + 2  # Include the period and space
            
            # Add the chunk
            chunks.append(text[start:end])
            
            # Advance with overlap
            start = end - overlap
            
            # Handle case where overlap would result in a tiny chunk at the end
            if start + chunk_size > len(text) and start < len(text) - overlap:
                # Just include the remainder in the last chunk
                chunks.append(text[start:])
                break
                
        return chunks
    
    def embed_chunked_document(self, text: str, metadata: Dict[str, Any] = None, 
                              chunk_size: int = 1000, overlap: int = 200) -> List[Dict[str, Any]]:
        """
        Chunk a document and generate embeddings and document objects for each chunk.
        
        Args:
            text: Full document text
            metadata: Metadata to include with each chunk
            chunk_size: Maximum size of each chunk
            overlap: Overlap between chunks
            
        Returns:
            List of document dictionaries with embeddings
        """
        if not text:
            return []
            
        # Create chunks
        chunks = self.chunk_text(text, chunk_size, overlap)
        
        # Create a document for each chunk
        documents = []
        for i, chunk_text in enumerate(chunks):
            # Create a copy of the metadata for this chunk
            chunk_metadata = dict(metadata) if metadata else {}
            
            # Add chunk specific information
            doc = {
                "id": f"{chunk_metadata.get('id', 'doc')}_chunk_{i}",
                "text": chunk_text,
                "chunk_index": i,
                "chunk_count": len(chunks),
                **chunk_metadata
            }
            
            documents.append(doc)
            
        return documents