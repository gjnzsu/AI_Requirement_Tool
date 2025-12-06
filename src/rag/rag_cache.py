"""
Cache for RAG queries to improve performance.

Caches:
- Query embeddings (avoid regenerating for same queries)
- Retrieval results (avoid re-searching for same queries)
"""

import hashlib
import json
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import sqlite3
from pathlib import Path
from contextlib import contextmanager


class RAGCache:
    """Cache for RAG queries and embeddings."""
    
    def __init__(self, db_path: Optional[str] = None, ttl_hours: int = 24):
        """
        Initialize the RAG cache.
        
        Args:
            db_path: Path to cache database (default: data/rag_cache.db)
            ttl_hours: Time-to-live for cache entries in hours (default: 24)
        """
        if db_path is None:
            project_root = Path(__file__).parent.parent.parent.parent
            data_dir = project_root / 'data'
            data_dir.mkdir(exist_ok=True)
            db_path = str(data_dir / 'rag_cache.db')
        
        self.db_path = db_path
        self.ttl_hours = ttl_hours
        self._initialize_database()
    
    def _initialize_database(self):
        """Initialize the cache database."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Query cache table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS query_cache (
                    query_hash TEXT PRIMARY KEY,
                    query_text TEXT NOT NULL,
                    embedding BLOB NOT NULL,
                    results TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    last_accessed TEXT NOT NULL,
                    access_count INTEGER DEFAULT 1
                )
            """)
            
            # Create indexes
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_cache_last_accessed 
                ON query_cache(last_accessed)
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
    
    def _hash_query(self, query: str) -> str:
        """Generate hash for a query."""
        return hashlib.md5(query.lower().strip().encode()).hexdigest()
    
    def get_cached_embedding(self, query: str) -> Optional[List[float]]:
        """
        Get cached embedding for a query.
        
        Args:
            query: Query string
            
        Returns:
            Cached embedding vector or None if not found/expired
        """
        query_hash = self._hash_query(query)
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT embedding, created_at FROM query_cache
                WHERE query_hash = ?
            """, (query_hash,))
            
            row = cursor.fetchone()
            if not row:
                return None
            
            # Check if cache is expired
            created_at = datetime.fromisoformat(row['created_at'])
            if datetime.now() - created_at > timedelta(hours=self.ttl_hours):
                # Cache expired, delete it
                cursor.execute("DELETE FROM query_cache WHERE query_hash = ?", (query_hash,))
                return None
            
            # Update access info
            cursor.execute("""
                UPDATE query_cache 
                SET last_accessed = ?, access_count = access_count + 1
                WHERE query_hash = ?
            """, (datetime.now().isoformat(), query_hash))
            
            # Deserialize embedding
            import pickle
            embedding = pickle.loads(row['embedding'])
            return embedding
    
    def cache_embedding(self, query: str, embedding: List[float]):
        """
        Cache an embedding for a query.
        
        Args:
            query: Query string
            embedding: Embedding vector
        """
        query_hash = self._hash_query(query)
        now = datetime.now().isoformat()
        
        import pickle
        embedding_blob = pickle.dumps(embedding)
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO query_cache
                (query_hash, query_text, embedding, results, created_at, last_accessed, access_count)
                VALUES (?, ?, ?, ?, ?, ?, 
                    COALESCE((SELECT access_count FROM query_cache WHERE query_hash = ?), 0) + 1)
            """, (query_hash, query[:500], embedding_blob, '', now, now, query_hash))
    
    def get_cached_results(self, query: str) -> Optional[List[Dict]]:
        """
        Get cached retrieval results for a query.
        
        Args:
            query: Query string
            
        Returns:
            Cached results or None if not found/expired
        """
        query_hash = self._hash_query(query)
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT results, created_at FROM query_cache
                WHERE query_hash = ? AND results != ''
            """, (query_hash,))
            
            row = cursor.fetchone()
            if not row:
                return None
            
            # Check if cache is expired
            created_at = datetime.fromisoformat(row['created_at'])
            if datetime.now() - created_at > timedelta(hours=self.ttl_hours):
                # Cache expired, delete it
                cursor.execute("DELETE FROM query_cache WHERE query_hash = ?", (query_hash,))
                return None
            
            # Update access info
            cursor.execute("""
                UPDATE query_cache 
                SET last_accessed = ?, access_count = access_count + 1
                WHERE query_hash = ?
            """, (datetime.now().isoformat(), query_hash))
            
            # Deserialize results
            results_json = row['results']
            if results_json:
                return json.loads(results_json)
            return None
    
    def cache_results(self, query: str, results: List[Dict]):
        """
        Cache retrieval results for a query.
        
        Args:
            query: Query string
            results: Retrieval results
        """
        query_hash = self._hash_query(query)
        now = datetime.now().isoformat()
        results_json = json.dumps(results)
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE query_cache
                SET results = ?, last_accessed = ?
                WHERE query_hash = ?
            """, (results_json, now, query_hash))
            
            # If no entry exists, create one (embedding should be cached first)
            if cursor.rowcount == 0:
                # Create entry with empty embedding (will be filled later)
                import pickle
                empty_embedding = pickle.dumps([])
                cursor.execute("""
                    INSERT INTO query_cache
                    (query_hash, query_text, embedding, results, created_at, last_accessed, access_count)
                    VALUES (?, ?, ?, ?, ?, ?, 1)
                """, (query_hash, query[:500], empty_embedding, results_json, now, now))
    
    def clear_expired(self):
        """Clear expired cache entries."""
        cutoff_time = (datetime.now() - timedelta(hours=self.ttl_hours)).isoformat()
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                DELETE FROM query_cache
                WHERE created_at < ?
            """, (cutoff_time,))
            return cursor.rowcount
    
    def clear_all(self):
        """Clear all cache entries."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM query_cache")
            return cursor.rowcount
    
    def get_statistics(self) -> Dict:
        """Get cache statistics."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) FROM query_cache")
            total_entries = cursor.fetchone()[0]
            
            cursor.execute("SELECT SUM(access_count) FROM query_cache")
            total_accesses = cursor.fetchone()[0] or 0
            
            cursor.execute("""
                SELECT COUNT(*) FROM query_cache
                WHERE results != ''
            """)
            cached_results = cursor.fetchone()[0]
            
            return {
                'total_cached_queries': total_entries,
                'total_accesses': total_accesses,
                'cached_results': cached_results,
                'cache_hit_rate': round(total_accesses / total_entries, 2) if total_entries > 0 else 0
            }

