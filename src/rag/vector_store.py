"""
Vector Store for storing and retrieving document embeddings.

Uses SQLite for metadata and numpy for vector operations.
"""

import sqlite3
import json
import numpy as np
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from contextlib import contextmanager
import pickle
import base64


class VectorStore:
    """Store and retrieve document embeddings."""
    
    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize the vector store.
        
        Args:
            db_path: Path to SQLite database (default: data/rag_vectors.db)
        """
        if db_path is None:
            project_root = Path(__file__).parent.parent.parent.parent
            data_dir = project_root / 'data'
            data_dir.mkdir(exist_ok=True)
            db_path = str(data_dir / 'rag_vectors.db')
        
        self.db_path = db_path
        self._initialize_database()
    
    def _initialize_database(self):
        """Initialize the SQLite database."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Documents table (metadata)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS documents (
                    id TEXT PRIMARY KEY,
                    file_path TEXT,
                    file_name TEXT,
                    content TEXT,
                    metadata TEXT,
                    created_at TEXT NOT NULL
                )
            """)
            
            # Chunks table (with embeddings stored as base64 pickle)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS chunks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    document_id TEXT NOT NULL,
                    chunk_index INTEGER NOT NULL,
                    content TEXT NOT NULL,
                    embedding BLOB NOT NULL,
                    metadata TEXT,
                    FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
                )
            """)
            
            # Create indexes
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_chunks_document 
                ON chunks(document_id)
            """)
            
            conn.commit()
    
    @contextmanager
    def _get_connection(self):
        """Get database connection with proper cleanup."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
    
    def add_document(self, document_id: str, file_path: str, file_name: str,
                    content: str, metadata: Optional[Dict] = None) -> bool:
        """
        Add a document to the store.
        
        Args:
            document_id: Unique document identifier
            file_path: Path to the document file
            file_name: Name of the file
            content: Full document content
            metadata: Optional metadata dictionary
            
        Returns:
            True if successful
        """
        from datetime import datetime
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO documents 
                (id, file_path, file_name, content, metadata, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                document_id,
                file_path,
                file_name,
                content,
                json.dumps(metadata) if metadata else None,
                datetime.now().isoformat()
            ))
        
        return True
    
    def add_chunk(self, document_id: str, chunk_index: int, content: str,
                 embedding: List[float], metadata: Optional[Dict] = None) -> int:
        """
        Add a chunk with its embedding.
        
        Args:
            document_id: Document identifier
            chunk_index: Index of chunk within document
            content: Chunk content
            embedding: Embedding vector
            metadata: Optional metadata
            
        Returns:
            Chunk ID
        """
        # Convert embedding to numpy array and serialize
        embedding_array = np.array(embedding, dtype=np.float32)
        embedding_blob = pickle.dumps(embedding_array)
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO chunks 
                (document_id, chunk_index, content, embedding, metadata)
                VALUES (?, ?, ?, ?, ?)
            """, (
                document_id,
                chunk_index,
                content,
                embedding_blob,
                json.dumps(metadata) if metadata else None
            ))
            
            return cursor.lastrowid
    
    def search_similar(self, query_embedding: List[float], top_k: int = 5,
                      document_id: Optional[str] = None) -> List[Dict]:
        """
        Search for similar chunks using cosine similarity.
        
        Args:
            query_embedding: Query embedding vector
            top_k: Number of results to return
            document_id: Optional filter by document ID
            
        Returns:
            List of similar chunks with similarity scores
        """
        query_vector = np.array(query_embedding, dtype=np.float32)
        query_norm = np.linalg.norm(query_vector)
        
        if query_norm == 0:
            return []
        
        query_vector = query_vector / query_norm  # Normalize
        
        results = []
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            if document_id:
                cursor.execute("""
                    SELECT id, document_id, chunk_index, content, embedding, metadata
                    FROM chunks
                    WHERE document_id = ?
                """, (document_id,))
            else:
                cursor.execute("""
                    SELECT id, document_id, chunk_index, content, embedding, metadata
                    FROM chunks
                """)
            
            rows = cursor.fetchall()
            
            for row in rows:
                # Deserialize embedding
                embedding_array = pickle.loads(row['embedding'])
                embedding_norm = np.linalg.norm(embedding_array)
                
                if embedding_norm == 0:
                    continue
                
                embedding_normalized = embedding_array / embedding_norm
                
                # Calculate cosine similarity
                similarity = np.dot(query_vector, embedding_normalized)
                
                results.append({
                    'id': row['id'],
                    'document_id': row['document_id'],
                    'chunk_index': row['chunk_index'],
                    'content': row['content'],
                    'similarity': float(similarity),
                    'metadata': json.loads(row['metadata']) if row['metadata'] else {}
                })
        
        # Sort by similarity (descending) and return top_k
        results.sort(key=lambda x: x['similarity'], reverse=True)
        return results[:top_k]
    
    def get_document(self, document_id: str) -> Optional[Dict]:
        """Get a document by ID."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM documents WHERE id = ?
            """, (document_id,))
            
            row = cursor.fetchone()
            if not row:
                return None
            
            return {
                'id': row['id'],
                'file_path': row['file_path'],
                'file_name': row['file_name'],
                'content': row['content'],
                'metadata': json.loads(row['metadata']) if row['metadata'] else {},
                'created_at': row['created_at']
            }
    
    def list_documents(self) -> List[Dict]:
        """List all documents."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT d.*, COUNT(c.id) as chunk_count
                FROM documents d
                LEFT JOIN chunks c ON d.id = c.document_id
                GROUP BY d.id
                ORDER BY d.created_at DESC
            """)
            
            rows = cursor.fetchall()
            return [
                {
                    'id': row['id'],
                    'file_path': row['file_path'],
                    'file_name': row['file_name'],
                    'chunk_count': row['chunk_count'],
                    'metadata': json.loads(row['metadata']) if row['metadata'] else {},
                    'created_at': row['created_at']
                }
                for row in rows
            ]
    
    def delete_document(self, document_id: str) -> bool:
        """Delete a document and all its chunks."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM documents WHERE id = ?", (document_id,))
        
        return True
    
    def get_statistics(self) -> Dict:
        """Get vector store statistics."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) FROM documents")
            doc_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM chunks")
            chunk_count = cursor.fetchone()[0]
            
            return {
                'total_documents': doc_count,
                'total_chunks': chunk_count,
                'average_chunks_per_document': round(chunk_count / doc_count, 2) if doc_count > 0 else 0
            }

