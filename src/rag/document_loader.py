"""
Document Loader for RAG system.

Supports loading documents from various formats: TXT, PDF, Markdown.
"""

import os
from pathlib import Path
from typing import List, Dict, Optional
import mimetypes


class DocumentLoader:
    """Load documents from various file formats."""
    
    SUPPORTED_EXTENSIONS = {'.txt', '.md', '.markdown', '.pdf'}
    
    def __init__(self):
        """Initialize the document loader."""
        pass
    
    def load_file(self, file_path: str) -> Dict[str, any]:
        """
        Load a single file.
        
        Args:
            file_path: Path to the file
            
        Returns:
            Dictionary with 'content', 'metadata', 'file_path'
        """
        path = Path(file_path)
        
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        if path.suffix.lower() not in self.SUPPORTED_EXTENSIONS:
            raise ValueError(f"Unsupported file type: {path.suffix}")
        
        # Get file metadata
        stat = path.stat()
        metadata = {
            'file_path': str(path),
            'file_name': path.name,
            'file_size': stat.st_size,
            'file_type': path.suffix.lower(),
            'modified_time': stat.st_mtime
        }
        
        # Load content based on file type
        content = self._load_content(path)
        
        return {
            'content': content,
            'metadata': metadata
        }
    
    def _load_content(self, path: Path) -> str:
        """Load content from file based on extension."""
        suffix = path.suffix.lower()
        
        if suffix in {'.txt', '.md', '.markdown'}:
            return self._load_text_file(path)
        elif suffix == '.pdf':
            return self._load_pdf_file(path)
        else:
            raise ValueError(f"Unsupported file type: {suffix}")
    
    def _load_text_file(self, path: Path) -> str:
        """Load text file (TXT, Markdown)."""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return f.read()
        except UnicodeDecodeError:
            # Try with different encoding
            with open(path, 'r', encoding='latin-1') as f:
                return f.read()
    
    def _load_pdf_file(self, path: Path) -> str:
        """Load PDF file."""
        try:
            import PyPDF2
            content = []
            with open(path, 'rb') as f:
                pdf_reader = PyPDF2.PdfReader(f)
                for page in pdf_reader.pages:
                    content.append(page.extract_text())
            return '\n\n'.join(content)
        except ImportError:
            raise ImportError(
                "PyPDF2 is required for PDF support. Install with: pip install PyPDF2"
            )
        except Exception as e:
            raise ValueError(f"Error reading PDF file: {e}")
    
    def load_directory(self, directory_path: str, 
                      recursive: bool = False) -> List[Dict[str, any]]:
        """
        Load all supported files from a directory.
        
        Args:
            directory_path: Path to directory
            recursive: Whether to search recursively
            
        Returns:
            List of document dictionaries
        """
        directory = Path(directory_path)
        if not directory.exists():
            raise FileNotFoundError(f"Directory not found: {directory_path}")
        
        documents = []
        
        if recursive:
            pattern = '**/*'
        else:
            pattern = '*'
        
        for file_path in directory.glob(pattern):
            if file_path.is_file() and file_path.suffix.lower() in self.SUPPORTED_EXTENSIONS:
                try:
                    doc = self.load_file(str(file_path))
                    documents.append(doc)
                except Exception as e:
                    print(f"Warning: Failed to load {file_path}: {e}")
                    continue
        
        return documents
    
    def load_text(self, text: str, metadata: Optional[Dict] = None) -> Dict[str, any]:
        """
        Load text directly (for programmatic use).
        
        Args:
            text: Text content
            metadata: Optional metadata dictionary
            
        Returns:
            Document dictionary
        """
        return {
            'content': text,
            'metadata': metadata or {}
        }

