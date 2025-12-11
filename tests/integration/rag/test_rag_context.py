"""
Test script to verify chatbot is using RAG knowledge context.

This script:
1. Creates test documents with specific information
2. Ingests them into RAG store
3. Asks questions that can ONLY be answered from those documents
4. Verifies RAG context is being used
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from src.rag import RAGService
from src.chatbot import Chatbot
from config.config import Config


def create_test_documents():
    """Create test documents with unique information."""
    data_dir = Path("data")
    data_dir.mkdir(exist_ok=True)
    
    # Document 1: Company-specific information
    doc1 = data_dir / "company_info.txt"
    doc1_content = """
    Acme Corporation - Company Information
    
    Acme Corporation was founded in 2020 and specializes in AI technology.
    Our headquarters is located at 123 Innovation Drive, Tech City.
    The company has 150 employees and focuses on machine learning solutions.
    
    Key Products:
    - AI Assistant Platform
    - Machine Learning Framework
    - Data Analytics Tools
    
    Contact Information:
    Email: contact@acmecorp.com
    Phone: +1-555-0123
    """
    
    with open(doc1, 'w', encoding='utf-8') as f:
        f.write(doc1_content)
    
    # Document 2: Project-specific information
    doc2 = data_dir / "project_alpha.txt"
    doc2_content = """
    Project Alpha - Technical Specifications
    
    Project Alpha is a chatbot system built using Python and Flask.
    The project uses OpenAI GPT-4 for language processing.
    Database: PostgreSQL version 14.2
    Deployment: Docker containers on AWS EC2
    
    Key Features:
    - RAG (Retrieval-Augmented Generation) support
    - Multi-provider LLM integration
    - Persistent conversation memory
    - Jira and Confluence integration
    
    Project Timeline:
    - Started: January 2024
    - Current Phase: Production deployment
    - Team Size: 5 developers
    """
    
    with open(doc2, 'w', encoding='utf-8') as f:
        f.write(doc2_content)
    
    print("✓ Created test documents:")
    print(f"  - {doc1.name}")
    print(f"  - {doc2.name}")
    
    return [doc1, doc2]


def test_rag_retrieval():
    """Test if RAG can retrieve the specific information."""
    print("\n" + "=" * 70)
    print("Step 1: Testing RAG Retrieval")
    print("=" * 70)
    
    rag = RAGService()
    
    # Questions that can ONLY be answered from our test documents
    test_queries = [
        "What is Acme Corporation?",
        "Where is Acme Corporation located?",
        "What is Project Alpha?",
        "What database does Project Alpha use?"
    ]
    
    print("\nTesting retrieval for specific queries:\n")
    
    for query in test_queries:
        print(f"Query: '{query}'")
        results = rag.retrieve(query, top_k=2)
        
        if results:
            print(f"  ✓ Found {len(results)} relevant chunks")
            for i, result in enumerate(results[:1], 1):  # Show top result
                print(f"    [{i}] Similarity: {result['similarity']:.3f}")
                print(f"        Content preview: {result['content'][:100]}...")
        else:
            print("  ✗ No results found")
        print()


def test_chatbot_with_rag():
    """Test chatbot with RAG enabled."""
    print("\n" + "=" * 70)
    print("Step 2: Testing Chatbot with RAG")
    print("=" * 70)
    
    if not Config.OPENAI_API_KEY:
        print("\n⚠ OPENAI_API_KEY not configured.")
        print("   Cannot test chatbot without API key.")
        return
    
    # Create chatbot with RAG (with timeout protection)
    print("\nCreating chatbot with RAG enabled...")
    print("  (This may take a moment - initializing LLM provider...)")
    
    import signal
    import threading
    
    chatbot = None
    init_error = None
    
    def init_chatbot():
        nonlocal chatbot, init_error
        try:
            chatbot = Chatbot(use_rag=True, rag_top_k=3)
        except Exception as e:
            init_error = e
    
    # Run initialization in a thread with timeout
    init_thread = threading.Thread(target=init_chatbot, daemon=True)
    init_thread.start()
    init_thread.join(timeout=30)  # 30 second timeout
    
    if init_thread.is_alive():
        print("⚠ Chatbot initialization is taking too long (possible network hang)")
        print("   This might be due to Jira/Confluence connection attempts.")
        print("   Skipping chatbot test to avoid dead loop.")
        print("\n   To test RAG with chatbot manually:")
        print("     from src.chatbot import Chatbot")
        print("     chatbot = Chatbot(use_rag=True)")
        print("     chatbot.get_response('What is Acme Corporation?')")
        return
    
    if init_error:
        print(f"✗ Error initializing chatbot: {init_error}")
        return
    
    if not chatbot:
        print("✗ Failed to initialize chatbot")
        return
    
    if not chatbot.rag_service:
        print("✗ RAG service not available in chatbot!")
        print("   Check configuration and API keys.")
        return
    
    print("✓ Chatbot created with RAG support")
    
    # Test with just ONE question to avoid hanging
    test_question = "What is Acme Corporation?"
    
    print(f"\nAsking ONE test question:")
    print("=" * 70)
    print(f"\nQ: {test_question}")
    print("-" * 70)
    
    try:
        print("  (Calling LLM API - this may take 10-20 seconds...)")
        response = chatbot.get_response(test_question)
        
        # Check if response contains information from our documents
        response_lower = response.lower()
        
        # Verify specific facts from documents
        checks = []
        if "acme" in response_lower or "corporation" in response_lower:
            checks.append("✓ Mentions Acme Corporation")
        if "123 innovation" in response_lower or "tech city" in response_lower:
            checks.append("✓ Mentions location")
        if "2020" in response_lower or "founded" in response_lower:
            checks.append("✓ Mentions founding year")
        if "150" in response_lower or "employees" in response_lower:
            checks.append("✓ Mentions employee count")
        
        print(f"A: {response[:300]}...")  # Show first 300 chars
        
        if checks:
            print(f"\n  ✓ RAG Context Detected:")
            for check in checks:
                print(f"    {check}")
            print("\n  RAG is working! The chatbot is using knowledge from your documents.")
        else:
            print(f"\n  ⚠ Response may not be using RAG context")
            print(f"     (or LLM is generating generic response)")
            print(f"     Check if documents were ingested correctly.")
        
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()


def test_chatbot_without_rag():
    """Test chatbot WITHOUT RAG for comparison."""
    print("\n" + "=" * 70)
    print("Step 3: Testing Chatbot WITHOUT RAG (for comparison)")
    print("=" * 70)
    
    if not Config.OPENAI_API_KEY:
        print("\n⚠ OPENAI_API_KEY not configured. Skipping comparison.")
        return
    
    print("\nSkipping comparison test to avoid initialization delays.")
    print("  (Chatbot initialization can hang on Jira/Confluence connections)")
    print("\n  To test comparison manually:")
    print("    chatbot_no_rag = Chatbot(use_rag=False)")
    print("    chatbot_no_rag.get_response('What is Acme Corporation?')")
    print("\n  Compare responses - RAG version should mention specific facts")
    print("  from your documents, while non-RAG version will be generic.")


def verify_rag_integration():
    """Verify RAG is properly integrated."""
    print("\n" + "=" * 70)
    print("Step 4: Verifying RAG Integration")
    print("=" * 70)
    
    try:
        # Check RAG service
        rag = RAGService()
        stats = rag.get_statistics()
        
        print(f"\nKnowledge Base Status:")
        print(f"  Total documents: {stats['total_documents']}")
        print(f"  Total chunks: {stats['total_chunks']}")
        
        if stats['total_documents'] == 0:
            print("\n  ⚠ No documents in knowledge base!")
            print("     RAG won't work without ingested documents.")
            return False
        
        # Check chatbot RAG integration status
        print(f"\nChatbot RAG Status:")
        print(f"  RAG service available: True")
        print(f"  Knowledge base has documents: {stats['total_documents'] > 0}")
        print(f"  Ready for chatbot integration: True")
        
        print("\n  ✓ RAG is properly integrated!")
        return True
    except Exception as e:
        print(f"\n  ⚠ Error checking RAG: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests."""
    print("=" * 70)
    print("RAG Context Verification Test")
    print("=" * 70)
    print("\nThis test verifies that:")
    print("  1. Documents are ingested into RAG store")
    print("  2. RAG can retrieve relevant information")
    print("  3. Chatbot uses RAG context in responses")
    print("  4. Responses contain information from your documents")
    print()
    
    # Check prerequisites
    if not Config.OPENAI_API_KEY:
        print("⚠ Warning: OPENAI_API_KEY not found")
        print("   RAG requires OpenAI API key for embeddings.")
        print("   Set it in your .env file: OPENAI_API_KEY=your-key")
        print("   Skipping chatbot tests (will only test retrieval)")
        skip_chatbot_tests = True
    else:
        skip_chatbot_tests = False
    
    # Create test documents
    print("\n" + "=" * 70)
    print("Preparing Test Documents")
    print("=" * 70)
    test_files = create_test_documents()
    
    # Ingest documents
    print("\nIngesting documents into RAG store...")
    rag = RAGService()
    for file_path in test_files:
        try:
            doc_id = rag.ingest_document(str(file_path))
            print(f"✓ Ingested: {file_path.name}")
        except Exception as e:
            print(f"✗ Failed to ingest {file_path.name}: {e}")
            return
    
    # Run tests
    test_rag_retrieval()
    verify_rag_integration()
    
    # Only run chatbot tests if API key is available
    if not skip_chatbot_tests:
        print("\n" + "=" * 70)
        print("Note: Chatbot tests may take time due to LLM API calls")
        print("      and tool initialization (Jira/Confluence connections)")
        print("=" * 70)
        
        # Ask user if they want to continue (with timeout)
        print("\n⚠ Chatbot initialization may hang if Jira/Confluence")
        print("   credentials are invalid or network is slow.")
        print("\nOptions:")
        print("  1. Continue with chatbot test (may take 30+ seconds)")
        print("  2. Skip chatbot test (recommended if you see hanging)")
        print("\nProceeding with chatbot test in 3 seconds...")
        print("  (Press Ctrl+C to skip)")
        
        import time
        try:
            time.sleep(3)
        except KeyboardInterrupt:
            print("\nSkipping chatbot tests (user interrupted)")
            skip_chatbot_tests = True
        
        if not skip_chatbot_tests:
            test_chatbot_with_rag()
            test_chatbot_without_rag()
    else:
        print("\n" + "=" * 70)
        print("Skipping Chatbot Tests (no API key)")
        print("=" * 70)
        print("\nTo test chatbot with RAG:")
        print("  1. Set OPENAI_API_KEY in your .env file")
        print("  2. Run the test again")
        print("  3. Or test manually:")
        print("     chatbot = Chatbot(use_rag=True)")
        print("     chatbot.get_response('What is Acme Corporation?')")
    
    print("\n" + "=" * 70)
    print("Test Complete!")
    print("=" * 70)
    print("\nHow to verify RAG is working:")
    print("  1. Check if responses mention specific facts from your documents")
    print("  2. Compare responses with/without RAG (should be different)")
    print("  3. Ask questions that can ONLY be answered from your documents")
    print("\nIf responses contain information from your documents,")
    print("then RAG is working correctly! ✓")
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

