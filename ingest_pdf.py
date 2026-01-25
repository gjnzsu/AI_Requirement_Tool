"""
Simple script to ingest PDF files into RAG knowledge base.

Usage:
    python ingest_pdf.py path/to/file.pdf
    python ingest_pdf.py path/to/pdf/folder/
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.rag import RAGService
from config.config import Config


def ingest_pdf_file(file_path: str):
    """Ingest a single PDF file."""
    path = Path(file_path)
    
    if not path.exists():
        print(f"✗ File not found: {file_path}")
        return False
    
    if path.suffix.lower() != '.pdf':
        print(f"✗ Not a PDF file: {file_path}")
        return False
    
    print(f"Processing PDF: {path.name}")
    print(f"File size: {path.stat().st_size / 1024:.2f} KB")
    
    try:
        # Use configured RAG vector store path from Config
        vector_store_path = Config.RAG_VECTOR_STORE_PATH if Config.RAG_VECTOR_STORE_PATH else None
        if vector_store_path:
            print(f"Using RAG database: {vector_store_path}")
        rag = RAGService(vector_store_path=vector_store_path)
        doc_id = rag.ingest_document(str(path))
        print(f"✓ Successfully ingested: {path.name}")
        print(f"  Document ID: {doc_id}")
        return True
    except ImportError as e:
        print(f"✗ Error: {e}")
        print("\nPyPDF2 is required for PDF support.")
        print("Install it with: pip install PyPDF2")
        return False
    except Exception as e:
        print(f"✗ Error ingesting PDF: {e}")
        return False


def ingest_pdf_directory(directory_path: str, recursive: bool = False):
    """Ingest all PDF files in a directory."""
    directory = Path(directory_path)
    
    if not directory.exists():
        print(f"✗ Directory not found: {directory_path}")
        return
    
    if not directory.is_dir():
        print(f"✗ Not a directory: {directory_path}")
        return
    
    # Find all PDF files
    if recursive:
        pdf_files = list(directory.rglob("*.pdf"))
    else:
        pdf_files = list(directory.glob("*.pdf"))
    
    if not pdf_files:
        print(f"✗ No PDF files found in: {directory_path}")
        return
    
    print(f"Found {len(pdf_files)} PDF file(s)")
    print("-" * 70)
    
    # Use configured RAG vector store path from Config
    vector_store_path = Config.RAG_VECTOR_STORE_PATH if Config.RAG_VECTOR_STORE_PATH else None
    if vector_store_path:
        print(f"Using RAG database: {vector_store_path}")
    rag = RAGService(vector_store_path=vector_store_path)
    success_count = 0
    
    for pdf_file in pdf_files:
        print(f"\nProcessing: {pdf_file.name}")
        try:
            doc_id = rag.ingest_document(str(pdf_file))
            print(f"✓ Ingested: {pdf_file.name}")
            success_count += 1
        except Exception as e:
            print(f"✗ Failed: {pdf_file.name} - {e}")
    
    print("\n" + "=" * 70)
    print(f"Summary: {success_count}/{len(pdf_files)} PDFs ingested successfully")
    print("=" * 70)
    
    # Show statistics
    stats = rag.get_statistics()
    print(f"\nKnowledge Base Statistics:")
    print(f"  Total documents: {stats['total_documents']}")
    print(f"  Total chunks: {stats['total_chunks']}")


def main():
    """Main function."""
    if len(sys.argv) < 2:
        print("=" * 70)
        print("PDF Ingestion Tool for RAG Knowledge Base")
        print("=" * 70)
        print("\nUsage:")
        print("  python ingest_pdf.py <pdf_file_path>")
        print("  python ingest_pdf.py <directory_path>")
        print("\nExamples:")
        print("  python ingest_pdf.py document.pdf")
        print("  python ingest_pdf.py ./pdfs/")
        print("  python ingest_pdf.py ./pdfs/ --recursive")
        print("\nOptions:")
        print("  --recursive    Search subdirectories (for directory mode)")
        print("=" * 70)
        return
    
    path = sys.argv[1]
    recursive = '--recursive' in sys.argv
    
    # Check if OPENAI_API_KEY is set
    if not Config.OPENAI_API_KEY:
        print("⚠ Warning: OPENAI_API_KEY not found")
        print("   RAG requires OpenAI API key for embeddings.")
        print("   Set it in your .env file: OPENAI_API_KEY=your-key")
        print()
        response = input("Continue anyway? (y/n): ")
        if response.lower() != 'y':
            return
    
    path_obj = Path(path)
    
    if path_obj.is_file():
        # Single file
        ingest_pdf_file(path)
    elif path_obj.is_dir():
        # Directory
        ingest_pdf_directory(path, recursive=recursive)
    else:
        print(f"✗ Path not found: {path}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()

