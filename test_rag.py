"""
Test script to demonstrate RAG functionality.

This script shows how to:
1. Create sample documents
2. Ingest them into the knowledge base
3. Use RAG-enabled chatbot to answer questions
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.rag import RAGService
from src.chatbot import Chatbot
from config.config import Config


def create_sample_documents():
    """Create sample documents for testing."""
    data_dir = Path("data")
    data_dir.mkdir(exist_ok=True)
    
    # Sample document 1: Python Guide
    python_doc = data_dir / "python_guide.txt"
    python_content = """
Python Programming Language Guide

Python is a high-level, interpreted programming language created by Guido van Rossum and first released in 1991.

Key Features:
- Simple and readable syntax
- Dynamically typed
- Object-oriented programming support
- Extensive standard library
- Cross-platform compatibility
- Large community and ecosystem

Common Use Cases:
- Web development (Django, Flask frameworks)
- Data science and machine learning (NumPy, Pandas, TensorFlow)
- Automation and scripting
- API development
- Scientific computing

Popular Python Libraries:
- NumPy: Numerical computing
- Pandas: Data manipulation
- Flask: Web framework
- Django: Full-featured web framework
- TensorFlow: Machine learning
- Requests: HTTP library
"""
    
    with open(python_doc, 'w', encoding='utf-8') as f:
        f.write(python_content)
    print(f"✓ Created: {python_doc}")
    
    # Sample document 2: Flask Guide
    flask_doc = data_dir / "flask_guide.txt"
    flask_content = """
Flask Web Framework Guide

Flask is a lightweight WSGI web application framework written in Python. It is designed to make getting started quick and easy, with the ability to scale up to complex applications.

Key Features:
- Minimal and flexible
- Built-in development server and debugger
- RESTful request dispatching
- Jinja2 templating engine
- Support for secure cookies
- Extensive documentation

Basic Flask Application:
```python
from flask import Flask
app = Flask(__name__)

@app.route('/')
def hello():
    return 'Hello, World!'

if __name__ == '__main__':
    app.run()
```

Common Flask Extensions:
- Flask-SQLAlchemy: Database ORM
- Flask-Login: User session management
- Flask-WTF: Form handling
- Flask-CORS: Cross-origin resource sharing
"""
    
    with open(flask_doc, 'w', encoding='utf-8') as f:
        f.write(flask_content)
    print(f"✓ Created: {flask_doc}")
    
    return [python_doc, flask_doc]


def test_rag_ingestion():
    """Test document ingestion."""
    print("\n" + "=" * 70)
    print("Step 1: Ingesting Documents into Knowledge Base")
    print("=" * 70)
    
    # Create sample documents
    print("\nCreating sample documents...")
    sample_files = create_sample_documents()
    
    # Initialize RAG service
    print("\nInitializing RAG service...")
    try:
        rag = RAGService()
        print("✓ RAG Service initialized")
    except Exception as e:
        print(f"✗ Failed to initialize RAG Service: {e}")
        print("\nMake sure OPENAI_API_KEY is set in your .env file")
        return None
    
    # Ingest documents
    print("\nIngesting documents...")
    document_ids = []
    for file_path in sample_files:
        try:
            doc_id = rag.ingest_document(str(file_path))
            document_ids.append(doc_id)
            print(f"✓ Ingested: {file_path.name}")
        except Exception as e:
            print(f"✗ Failed to ingest {file_path.name}: {e}")
    
    # Show statistics
    print("\nKnowledge Base Statistics:")
    stats = rag.get_statistics()
    print(f"  Total documents: {stats['total_documents']}")
    print(f"  Total chunks: {stats['total_chunks']}")
    print(f"  Average chunks per document: {stats['average_chunks_per_document']}")
    
    return rag


def test_rag_retrieval(rag_service):
    """Test retrieval functionality."""
    print("\n" + "=" * 70)
    print("Step 2: Testing Retrieval")
    print("=" * 70)
    
    test_queries = [
        "What is Python?",
        "Tell me about Flask framework",
        "What are the key features of Python?"
    ]
    
    for query in test_queries:
        print(f"\nQuery: '{query}'")
        print("-" * 70)
        
        try:
            results = rag_service.retrieve(query, top_k=2)
            
            if results:
                for i, result in enumerate(results, 1):
                    print(f"\n[{i}] Similarity Score: {result['similarity']:.3f}")
                    print(f"    Content: {result['content'][:150]}...")
                    if result.get('metadata', {}).get('file_name'):
                        print(f"    Source: {result['metadata']['file_name']}")
            else:
                print("  No results found")
        except Exception as e:
            print(f"  ✗ Error: {e}")


def test_rag_chatbot():
    """Test RAG-enabled chatbot."""
    print("\n" + "=" * 70)
    print("Step 3: Testing RAG-Enabled Chatbot")
    print("=" * 70)
    
    if not Config.OPENAI_API_KEY:
        print("\n⚠ OPENAI_API_KEY not configured.")
        print("   Set OPENAI_API_KEY in your .env file to test chatbot.")
        return
    
    # Create chatbot with RAG enabled
    print("\nCreating chatbot with RAG enabled...")
    try:
        chatbot = Chatbot(use_rag=True, rag_top_k=3)
        
        if not chatbot.rag_service:
            print("⚠ RAG service not available in chatbot")
            return
        
        print("✓ Chatbot created with RAG support")
    except Exception as e:
        print(f"✗ Failed to create chatbot: {e}")
        return
    
    # Test questions
    test_questions = [
        "What is Python?",
        "Tell me about Flask",
        "What are Python's key features?",
        "How do I create a Flask app?"
    ]
    
    print("\nAsking questions (RAG context will be automatically included):\n")
    
    for question in test_questions:
        print(f"Q: {question}")
        print("-" * 70)
        
        try:
            response = chatbot.get_response(question)
            print(f"A: {response}")
            print()
        except Exception as e:
            print(f"✗ Error: {e}\n")


def main():
    """Run all RAG tests."""
    print("=" * 70)
    print("RAG System Test")
    print("=" * 70)
    print("\nThis test will:")
    print("  1. Create sample documents")
    print("  2. Ingest them into the knowledge base")
    print("  3. Test retrieval functionality")
    print("  4. Test RAG-enabled chatbot")
    print()
    
    # Check prerequisites
    if not Config.OPENAI_API_KEY:
        print("⚠ Warning: OPENAI_API_KEY not found")
        print("   RAG requires OpenAI API key for embeddings.")
        print("   Set it in your .env file: OPENAI_API_KEY=your-key")
        print()
        response = input("Continue anyway? (y/n): ")
        if response.lower() != 'y':
            return
    
    # Step 1: Ingest documents
    rag_service = test_rag_ingestion()
    
    if not rag_service:
        print("\n⚠ Cannot continue without RAG service")
        return
    
    # Step 2: Test retrieval
    test_rag_retrieval(rag_service)
    
    # Step 3: Test chatbot
    test_rag_chatbot()
    
    print("\n" + "=" * 70)
    print("Test Complete!")
    print("=" * 70)
    print("\nTo use RAG in your chatbot:")
    print("  1. Ingest documents: rag_service.ingest_document('file.txt')")
    print("  2. Create chatbot: chatbot = Chatbot(use_rag=True)")
    print("  3. Ask questions: chatbot.get_response('your question')")
    print("\nRAG context is automatically included in responses!")
    print("=" * 70)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()

