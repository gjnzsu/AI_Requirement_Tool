"""
Text Chunker for splitting documents into smaller pieces.

Implements chunking strategies with overlap for better context preservation.
"""

from typing import List, Dict
import re


class TextChunker:
    """Split documents into chunks for embedding."""
    
    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        """
        Initialize the text chunker.
        
        Args:
            chunk_size: Maximum size of each chunk (in characters)
            chunk_overlap: Number of characters to overlap between chunks
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        
        if chunk_overlap >= chunk_size:
            raise ValueError("chunk_overlap must be less than chunk_size")
    
    def chunk_document(self, document: Dict[str, any]) -> List[Dict[str, any]]:
        """
        Split a document into chunks.
        
        Args:
            document: Document dictionary with 'content' and 'metadata'
            
        Returns:
            List of chunk dictionaries
        """
        content = document['content']
        metadata = document.get('metadata', {})
        
        # Try to chunk by paragraphs first (better semantic boundaries)
        chunks = self._chunk_by_paragraphs(content, metadata)
        
        # If chunks are too large, fall back to character-based chunking
        if not chunks or max(len(c['content']) for c in chunks) > self.chunk_size * 1.5:
            chunks = self._chunk_by_characters(content, metadata)
        
        return chunks
    
    def _chunk_by_paragraphs(self, text: str, metadata: Dict) -> List[Dict[str, any]]:
        """Chunk text by paragraphs (preferred method)."""
        # Split by double newlines (paragraphs)
        paragraphs = re.split(r'\n\s*\n', text)
        
        chunks = []
        current_chunk = []
        current_size = 0
        
        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
            
            para_size = len(para)
            
            # If paragraph itself is too large, split it
            if para_size > self.chunk_size:
                # Add current chunk if exists
                if current_chunk:
                    chunks.append(self._create_chunk(
                        '\n\n'.join(current_chunk),
                        metadata,
                        len(chunks)
                    ))
                    current_chunk = []
                    current_size = 0
                
                # Split large paragraph
                para_chunks = self._chunk_by_characters(
                    para,
                    metadata,
                    start_index=len(chunks)
                )
                chunks.extend(para_chunks)
                continue
            
            # Check if adding this paragraph would exceed chunk size
            if current_size + para_size > self.chunk_size and current_chunk:
                # Save current chunk
                chunks.append(self._create_chunk(
                    '\n\n'.join(current_chunk),
                    metadata,
                    len(chunks)
                ))
                
                # Start new chunk with overlap
                if self.chunk_overlap > 0 and current_chunk:
                    # Include last part of previous chunk for overlap
                    overlap_text = current_chunk[-1][-self.chunk_overlap:]
                    current_chunk = [overlap_text, para]
                    current_size = len(overlap_text) + para_size
                else:
                    current_chunk = [para]
                    current_size = para_size
            else:
                current_chunk.append(para)
                current_size += para_size + 2  # +2 for '\n\n'
        
        # Add remaining chunk
        if current_chunk:
            chunks.append(self._create_chunk(
                '\n\n'.join(current_chunk),
                metadata,
                len(chunks)
            ))
        
        return chunks
    
    def _chunk_by_characters(self, text: str, metadata: Dict, 
                            start_index: int = 0) -> List[Dict[str, any]]:
        """Chunk text by characters (fallback method)."""
        chunks = []
        text_length = len(text)
        
        start = 0
        chunk_index = start_index
        
        while start < text_length:
            end = start + self.chunk_size
            
            # Try to break at sentence boundary
            if end < text_length:
                # Look for sentence endings
                sentence_endings = ['. ', '.\n', '! ', '!\n', '? ', '?\n']
                best_break = end
                
                for ending in sentence_endings:
                    last_occurrence = text.rfind(ending, start, end)
                    if last_occurrence != -1:
                        best_break = last_occurrence + len(ending)
                        break
                
                end = best_break
            
            chunk_text = text[start:end].strip()
            
            if chunk_text:
                chunks.append(self._create_chunk(chunk_text, metadata, chunk_index))
                chunk_index += 1
            
            # Move start position with overlap
            start = end - self.chunk_overlap if self.chunk_overlap > 0 else end
        
        return chunks
    
    def _create_chunk(self, content: str, metadata: Dict, chunk_index: int) -> Dict[str, any]:
        """Create a chunk dictionary."""
        chunk_metadata = metadata.copy()
        chunk_metadata['chunk_index'] = chunk_index
        chunk_metadata['chunk_size'] = len(content)
        
        return {
            'content': content,
            'metadata': chunk_metadata
        }

