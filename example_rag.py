"""
Example script demonstrating RAG functionality.

This shows how to:
1. Ingest documents into the knowledge base
2. Use RAG-enabled chatbot to answer questions
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.rag import RAGService
from src.chatbot import Chatbot
from config.config import Config


def example_ingest_documents():
    """Example: Ingest documents into knowledge base."""
    print("=" * 70)
    print("Example: Ingesting Documents")
    print("=" * 70)
    
    # Initialize RAG service
    rag = RAGService()
    
    # Example 1: Ingest a single file
    print("\n1. Ingesting a single file...")
    # Create a sample text file for demonstration
    sample_file = Path("data/sample_document.txt")
    sample_file.parent.mkdir(exist_ok=True)
    
    sample_content = """
    Python Programming Guide
    
    Python is a high-level programming language known for its simplicity and readability.
    It was created by Guido van Rossum and first released in 1991.
    
    Key Features:
    - Easy to learn and use
    - Extensive standard library
    - Cross-platform compatibility
    - Strong community support
    
    Common Use Cases:
    - Web development (Django, Flask)
    - Data science and machine learning
    - Automation and scripting
    - API development
    """
    
    with open(sample_file, 'w', encoding='utf-8') as f:
        f.write(sample_content)
    
    try:
        doc_id = rag.ingest_document(str(sample_file))
        print(f"✓ Document ingested: {doc_id}")
    except Exception as e:
        print(f"✗ Error: {e}")
    
    # Example 2: Ingest text directly
    print("\n2. Ingesting text directly...")
    text_content = """
    Flask Web Framework
    
    Flask is a lightweight WSGI web application framework in Python.
    It is designed to make getting started quick and easy, with the ability to scale up to complex applications.
    
    Key Features:
    - Minimal and flexible
    - Built-in development server
    - RESTful request dispatching
    - Jinja2 templating
    """
    
    try:
        doc_id = rag.ingest_text(text_content, metadata={'title': 'Flask Guide'})
        print(f"✓ Text ingested: {doc_id}")
    except Exception as e:
        print(f"✗ Error: {e}")
    
    # Show statistics
    print("\n3. Knowledge Base Statistics:")
    stats = rag.get_statistics()
    print(f"  Total documents: {stats['total_documents']}")
    print(f"  Total chunks: {stats['total_chunks']}")
    print(f"  Avg chunks per document: {stats['average_chunks_per_document']}")


def example_rag_chatbot():
    """Example: Using RAG-enabled chatbot."""
    print("\n" + "=" * 70)
    print("Example: RAG-Enabled Chatbot")
    print("=" * 70)
    
    if not Config.OPENAI_API_KEY:
        print("\n⚠ OPENAI_API_KEY not configured. Skipping chatbot example.")
        print("   Set OPENAI_API_KEY in your .env file to test RAG chatbot.")
        return
    
    # Create chatbot with RAG enabled
    print("\nCreating chatbot with RAG enabled...")
    chatbot = Chatbot(
        use_rag=True,
        rag_top_k=3
    )
    
    if not chatbot.rag_service:
        print("⚠ RAG service not available. Check configuration.")
        return
    
    # Ask questions that should retrieve from knowledge base
    questions = [
        "What is Python?",
        "Tell me about Flask framework",
        "What are the key features of Python?"
    ]
    
    print("\nAsking questions with RAG context:\n")
    for question in questions:
        print(f"Q: {question}")
        try:
            response = chatbot.get_response(question)
            print(f"A: {response[:200]}...")
            print()
        except Exception as e:
            print(f"✗ Error: {e}\n")


def example_retrieval():
    """Example: Direct retrieval from knowledge base."""
    print("\n" + "=" * 70)
    print("Example: Direct Retrieval")
    print("=" * 70)
    
    rag = RAGService()
    
    query = "Python programming"
    print(f"\nSearching for: '{query}'")
    
    try:
        results = rag.retrieve(query, top_k=3)
        
        if results:
            print(f"\nFound {len(results)} relevant chunks:\n")
            for i, result in enumerate(results, 1):
                print(f"[{i}] Similarity: {result['similarity']:.3f}")
                print(f"    Content: {result['content'][:150]}...")
                print()
        else:
            print("No results found. Ingest some documents first.")
    except Exception as e:
        print(f"✗ Error: {e}")


if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("RAG System Examples")
    print("=" * 70)
    
    # Run examples
    example_ingest_documents()
    example_retrieval()
    example_rag_chatbot()
    
    print("\n" + "=" * 70)
    print("Examples Complete!")
    print("=" * 70)
    print("\nTo use RAG in your chatbot:")
    print("  1. Ingest documents: rag_service.ingest_document('path/to/file.txt')")
    print("  2. Create chatbot with RAG: Chatbot(use_rag=True)")
    print("  3. Ask questions - RAG context will be automatically included")
    print("=" * 70)

