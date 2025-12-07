"""
Embedding Generator for converting text to vector embeddings.

Uses OpenAI embeddings API for generating embeddings.
"""

from typing import List, Optional
import numpy as np
from config.config import Config


class EmbeddingGenerator:
    """Generate embeddings for text using OpenAI API."""
    
    def __init__(self, api_key: Optional[str] = None, model: str = "text-embedding-ada-002"):
        """
        Initialize the embedding generator.
        
        Args:
            api_key: OpenAI API key (uses Config.OPENAI_API_KEY if None)
            model: Embedding model name
        """
        self.api_key = api_key or Config.OPENAI_API_KEY
        self.model = model
        
        if not self.api_key:
            raise ValueError(
                "OpenAI API key is required. Set OPENAI_API_KEY in environment or .env file"
            )
    
    def generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding for a single text.
        
        Args:
            text: Text to embed
            
        Returns:
            List of floats representing the embedding vector
        """
        try:
            import openai
            import requests
            
            # Create client with timeout
            client = openai.OpenAI(
                api_key=self.api_key,
                timeout=10.0,  # 10 second timeout for embedding requests
                max_retries=1  # Limit retries to avoid long waits
            )
            
            # Clean text (remove extra whitespace)
            text = text.strip().replace('\n', ' ')
            
            response = client.embeddings.create(
                model=self.model,
                input=text
            )
            
            return response.data[0].embedding
            
        except ImportError:
            raise ImportError(
                "openai package is required. Install with: pip install openai>=1.12.0"
            )
        except requests.exceptions.Timeout:
            raise RuntimeError(f"Error generating embedding: Request timed out. Check network connection and API availability.")
        except Exception as e:
            raise RuntimeError(f"Error generating embedding: {e}")
    
    def generate_embeddings_batch(self, texts: List[str], 
                                  batch_size: int = 100) -> List[List[float]]:
        """
        Generate embeddings for multiple texts (batched).
        
        Args:
            texts: List of texts to embed
            batch_size: Number of texts to process in each batch
            
        Returns:
            List of embedding vectors
        """
        embeddings = []
        
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            batch_embeddings = self._generate_batch(batch)
            embeddings.extend(batch_embeddings)
        
        return embeddings
    
    def _generate_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for a batch of texts."""
        try:
            import openai
            import requests
            
            # Create client with timeout
            client = openai.OpenAI(
                api_key=self.api_key,
                timeout=15.0,  # 15 second timeout for batch requests (longer)
                max_retries=1  # Limit retries to avoid long waits
            )
            
            # Clean texts
            cleaned_texts = [text.strip().replace('\n', ' ') for text in texts]
            
            response = client.embeddings.create(
                model=self.model,
                input=cleaned_texts
            )
            
            return [item.embedding for item in response.data]
            
        except requests.exceptions.Timeout:
            raise RuntimeError(f"Error generating batch embeddings: Request timed out. Check network connection and API availability.")
        except Exception as e:
            raise RuntimeError(f"Error generating batch embeddings: {e}")
    
    def get_embedding_dimension(self) -> int:
        """Get the dimension of embeddings for this model."""
        # text-embedding-ada-002 has 1536 dimensions
        # text-embedding-3-small has 1536 dimensions
        # text-embedding-3-large has 3072 dimensions
        
        if "ada-002" in self.model or "3-small" in self.model:
            return 1536
        elif "3-large" in self.model:
            return 3072
        else:
            # Default to ada-002 dimensions
            return 1536

