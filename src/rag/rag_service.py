"""
RAG (Retrieval-Augmented Generation) Service.

Main service that coordinates document ingestion, embedding, and retrieval.
"""

import hashlib
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime

from src.rag.document_loader import DocumentLoader
from src.rag.text_chunker import TextChunker
from src.rag.embedding_generator import EmbeddingGenerator
from src.rag.vector_store import VectorStore
from src.rag.rag_cache import RAGCache


class RAGService:
    """Main RAG service for document ingestion and retrieval."""
    
    def __init__(self, 
                 chunk_size: int = 1000,
                 chunk_overlap: int = 200,
                 embedding_model: str = "text-embedding-ada-002",
                 vector_store_path: Optional[str] = None,
                 enable_cache: bool = True,
                 cache_ttl_hours: int = 24):
        """
        Initialize the RAG service.
        
        Args:
            chunk_size: Size of text chunks
            chunk_overlap: Overlap between chunks
            embedding_model: OpenAI embedding model name
            vector_store_path: Path to vector store database
            enable_cache: Whether to enable query caching (default: True)
            cache_ttl_hours: Cache time-to-live in hours (default: 24)
        """
        self.document_loader = DocumentLoader()
        self.text_chunker = TextChunker(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
        self.embedding_generator = EmbeddingGenerator(model=embedding_model)
        self.vector_store = VectorStore(db_path=vector_store_path)
        
        # Initialize cache if enabled
        self.cache = None
        self.enable_cache = enable_cache
        if self.enable_cache:
            try:
                self.cache = RAGCache(ttl_hours=cache_ttl_hours)
            except Exception as e:
                print(f"⚠ Failed to initialize RAG cache: {e}")
                self.enable_cache = False
    
    def ingest_document(self, file_path: str) -> str:
        """
        Ingest a document into the knowledge base.
        
        Args:
            file_path: Path to the document file
            
        Returns:
            Document ID
        """
        # Load document
        document = self.document_loader.load_file(file_path)
        
        # Generate document ID (hash of file path)
        document_id = self._generate_document_id(file_path)
        
        # Store document metadata
        self.vector_store.add_document(
            document_id=document_id,
            file_path=file_path,
            file_name=Path(file_path).name,
            content=document['content'],
            metadata=document['metadata']
        )
        
        # Chunk the document
        chunks = self.text_chunker.chunk_document(document)
        
        print(f"Processing {len(chunks)} chunks from {Path(file_path).name}...")
        
        # Generate embeddings and store chunks
        chunk_contents = [chunk['content'] for chunk in chunks]
        embeddings = self.embedding_generator.generate_embeddings_batch(chunk_contents)
        
        for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            self.vector_store.add_chunk(
                document_id=document_id,
                chunk_index=i,
                content=chunk['content'],
                embedding=embedding,
                metadata=chunk['metadata']
            )
        
        print(f"✓ Ingested document: {Path(file_path).name} ({len(chunks)} chunks)")
        return document_id
    
    def ingest_directory(self, directory_path: str, recursive: bool = False) -> List[str]:
        """
        Ingest all documents from a directory.
        
        Args:
            directory_path: Path to directory
            recursive: Whether to search recursively
            
        Returns:
            List of document IDs
        """
        documents = self.document_loader.load_directory(directory_path, recursive=recursive)
        document_ids = []
        
        print(f"Found {len(documents)} documents to ingest...")
        
        for doc in documents:
            file_path = doc['metadata']['file_path']
            try:
                doc_id = self.ingest_document(file_path)
                document_ids.append(doc_id)
            except Exception as e:
                print(f"⚠ Failed to ingest {file_path}: {e}")
                continue
        
        return document_ids
    
    def ingest_text(self, text: str, metadata: Optional[Dict] = None, document_id: Optional[str] = None) -> str:
        """
        Ingest text directly (for programmatic use).
        
        Args:
            text: Text content
            metadata: Optional metadata
            document_id: Optional custom document ID for deduplication (e.g., 'jira:PROJ-123')
                        If not provided, generates from text hash.
            
        Returns:
            Document ID
        """
        document = self.document_loader.load_text(text, metadata)
        
        # Use custom document ID if provided, otherwise generate from text hash
        if document_id is None:
            document_id = hashlib.md5(text.encode()).hexdigest()
        
        # Store document
        self.vector_store.add_document(
            document_id=document_id,
            file_path="inline_text",
            file_name=metadata.get('title', 'Inline Text') if metadata else 'Inline Text',
            content=text,
            metadata=metadata or {}
        )
        
        # Chunk and embed
        chunks = self.text_chunker.chunk_document(document)
        chunk_contents = [chunk['content'] for chunk in chunks]
        embeddings = self.embedding_generator.generate_embeddings_batch(chunk_contents)
        
        for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            self.vector_store.add_chunk(
                document_id=document_id,
                chunk_index=i,
                content=chunk['content'],
                embedding=embedding,
                metadata=chunk['metadata']
            )
        
        return document_id
    
    def retrieve(self, query: str, top_k: int = 5) -> List[Dict]:
        """
        Retrieve relevant document chunks for a query.
        
        Args:
            query: Search query
            top_k: Number of results to return
            
        Returns:
            List of relevant chunks with similarity scores
        """
        # Check cache first
        if self.enable_cache and self.cache:
            cached_results = self.cache.get_cached_results(query)
            if cached_results is not None:
                # Return cached results (limit to top_k)
                return cached_results[:top_k]
        
        # Generate query embedding (check cache first)
        if self.enable_cache and self.cache:
            query_embedding = self.cache.get_cached_embedding(query)
            if query_embedding is None:
                # Generate and cache embedding
                query_embedding = self.embedding_generator.generate_embedding(query)
                self.cache.cache_embedding(query, query_embedding)
        else:
            query_embedding = self.embedding_generator.generate_embedding(query)
        
        # Search for similar chunks
        results = self.vector_store.search_similar(query_embedding, top_k=top_k)
        
        # Cache results
        if self.enable_cache and self.cache:
            self.cache.cache_results(query, results)
        
        return results
    
    def get_context(self, query: str, top_k: int = 3) -> str:
        """
        Get formatted context string from retrieved chunks.
        
        Args:
            query: Search query
            top_k: Number of chunks to include
            
        Returns:
            Formatted context string
        """
        results = self.retrieve(query, top_k=top_k)
        
        if not results:
            return ""
        
        context_parts = ["Relevant context from knowledge base:"]
        
        for i, result in enumerate(results, 1):
            context_parts.append(f"\n[{i}] {result['content']}")
            if result.get('metadata', {}).get('file_name'):
                context_parts.append(f"   (Source: {result['metadata']['file_name']})")
        
        return "\n".join(context_parts)
    
    def _generate_document_id(self, file_path: str) -> str:
        """Generate a unique document ID from file path."""
        # Use hash of file path + modification time for uniqueness
        path_str = str(Path(file_path).absolute())
        stat = Path(file_path).stat()
        unique_str = f"{path_str}_{stat.st_mtime}"
        return hashlib.md5(unique_str.encode()).hexdigest()
    
    def list_documents(self) -> List[Dict]:
        """List all ingested documents."""
        return self.vector_store.list_documents()
    
    def delete_document(self, document_id: str) -> bool:
        """Delete a document from the knowledge base."""
        return self.vector_store.delete_document(document_id)
    
    def get_statistics(self) -> Dict:
        """Get RAG service statistics."""
        return self.vector_store.get_statistics()

