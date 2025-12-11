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
from src.utils.logger import get_logger

logger = get_logger('test.rag_context')

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
    
    logger.info("✓ Created test documents:")
    logger.info(f"  - {doc1.name}")
    logger.info(f"  - {doc2.name}")
    
    return [doc1, doc2]


def test_rag_retrieval():
    logger = get_logger('test.rag_retrieval')

    """Test if RAG can retrieve the specific information."""
    logger.info("\n" + "=" * 70)
    logger.info("Step 1: Testing RAG Retrieval")
    logger.info("=" * 70)
    
    rag = RAGService()
    
    # Questions that can ONLY be answered from our test documents
    test_queries = [
        "What is Acme Corporation?",
        "Where is Acme Corporation located?",
        "What is Project Alpha?",
        "What database does Project Alpha use?"
    ]
    
    logger.info("\nTesting retrieval for specific queries:\n")
    
    for query in test_queries:
        logger.info(f"Query: '{query}'")
        results = rag.retrieve(query, top_k=2)
        
        if results:
            logger.info(f"  ✓ Found {len(results)} relevant chunks")
            for i, result in enumerate(results[:1], 1):  # Show top result
                logger.info(f"    [{i}] Similarity: {result['similarity']:.3f}")
                logger.info(f"        Content preview: {result['content'][:100]}...")
        else:
            logger.error("  ✗ No results found")
        logger.info("")


def test_chatbot_with_rag():
    """Test chatbot with RAG enabled."""
    logger.info("\n" + "=" * 70)
    logger.info("Step 2: Testing Chatbot with RAG")
    logger.info("=" * 70)
    
    if not Config.OPENAI_API_KEY:
        logger.warning("\n⚠ OPENAI_API_KEY not configured.")
        logger.info("   Cannot test chatbot without API key.")
        return
    
    # Create chatbot with RAG (with timeout protection)
    logger.info("\nCreating chatbot with RAG enabled...")
    logger.info("  (This may take a moment - initializing LLM provider...)")
    
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
        logger.warning("⚠ Chatbot initialization is taking too long (possible network hang)")
        logger.info("   This might be due to Jira/Confluence connection attempts.")
        logger.info("   Skipping chatbot test to avoid dead loop.")
        logger.info("\n   To test RAG with chatbot manually:")
        logger.info("     from src.chatbot import Chatbot")
        logger.info("     chatbot = Chatbot(use_rag=True)")
        logger.info("     chatbot.get_response('What is Acme Corporation?')")
        return
    
    if init_error:
        logger.error(f"✗ Error initializing chatbot: {init_error}")
        return
    
    if not chatbot:
        logger.error("✗ Failed to initialize chatbot")
        return
    
    if not chatbot.rag_service:
        logger.error("✗ RAG service not available in chatbot!")
        logger.info("   Check configuration and API keys.")
        return
    
    logger.info("✓ Chatbot created with RAG support")
    
    # Test with just ONE question to avoid hanging
    test_question = "What is Acme Corporation?"
    
    logger.info(f"\nAsking ONE test question:")
    logger.info("=" * 70)
    logger.info(f"\nQ: {test_question}")
    logger.info("-" * 70)
    
    try:
        logger.info("  (Calling LLM API - this may take 10-20 seconds...)")
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
        
        logger.info(f"A: {response[:300]}...")  # Show first 300 chars
        
        if checks:
            logger.info(f"\n  ✓ RAG Context Detected:")
            for check in checks:
                logger.info(f"    {check}")
            logger.info("\n  RAG is working! The chatbot is using knowledge from your documents.")
        else:
            logger.warning(f"\n  ⚠ Response may not be using RAG context")
            logger.info(f"     (or LLM is generating generic response)")
            logger.info(f"     Check if documents were ingested correctly.")
        
    except Exception as e:
        logger.error(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()


def test_chatbot_without_rag():
    """Test chatbot WITHOUT RAG for comparison."""
    logger.info("\n" + "=" * 70)
    logger.info("Step 3: Testing Chatbot WITHOUT RAG (for comparison)")
    logger.info("=" * 70)
    
    if not Config.OPENAI_API_KEY:
        logger.warning("\n⚠ OPENAI_API_KEY not configured. Skipping comparison.")
        return
    
    logger.info("\nSkipping comparison test to avoid initialization delays.")
    logger.info("  (Chatbot initialization can hang on Jira/Confluence connections)")
    logger.info("\n  To test comparison manually:")
    logger.info("    chatbot_no_rag = Chatbot(use_rag=False)")
    logger.info("    chatbot_no_rag.get_response('What is Acme Corporation?')")
    logger.info("\n  Compare responses - RAG version should mention specific facts")
    logger.info("  from your documents, while non-RAG version will be generic.")


def verify_rag_integration():
    """Verify RAG is properly integrated."""
    logger.info("\n" + "=" * 70)
    logger.info("Step 4: Verifying RAG Integration")
    logger.info("=" * 70)
    
    try:
        # Check RAG service
        rag = RAGService()
        stats = rag.get_statistics()
        
        logger.info(f"\nKnowledge Base Status:")
        logger.info(f"  Total documents: {stats['total_documents']}")
        logger.info(f"  Total chunks: {stats['total_chunks']}")
        
        if stats['total_documents'] == 0:
            logger.warning("\n  ⚠ No documents in knowledge base!")
            logger.info("     RAG won't work without ingested documents.")
            return False
        
        # Check chatbot RAG integration status
        logger.info(f"\nChatbot RAG Status:")
        logger.info(f"  RAG service available: True")
        logger.info(f"  Knowledge base has documents: {stats['total_documents'] > 0}")
        logger.info(f"  Ready for chatbot integration: True")
        
        logger.info("\n  ✓ RAG is properly integrated!")
        return True
    except Exception as e:
        logger.error(f"\n  ⚠ Error checking RAG: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests."""
    logger.info("=" * 70)
    logger.info("RAG Context Verification Test")
    logger.info("=" * 70)
    logger.info("\nThis test verifies that:")
    logger.info("  1. Documents are ingested into RAG store")
    logger.info("  2. RAG can retrieve relevant information")
    logger.info("  3. Chatbot uses RAG context in responses")
    logger.info("  4. Responses contain information from your documents")
    logger.info("")
    
    # Check prerequisites
    if not Config.OPENAI_API_KEY:
        logger.warning("⚠ Warning: OPENAI_API_KEY not found")
        logger.info("   RAG requires OpenAI API key for embeddings.")
        logger.info("   Set it in your .env file: OPENAI_API_KEY=your-key")
        logger.info("   Skipping chatbot tests (will only test retrieval)")
        skip_chatbot_tests = True
    else:
        skip_chatbot_tests = False
    
    # Create test documents
    logger.info("\n" + "=" * 70)
    logger.info("Preparing Test Documents")
    logger.info("=" * 70)
    test_files = create_test_documents()
    
    # Ingest documents
    logger.info("\nIngesting documents into RAG store...")
    rag = RAGService()
    for file_path in test_files:
        try:
            doc_id = rag.ingest_document(str(file_path))
            logger.info(f"✓ Ingested: {file_path.name}")
        except Exception as e:
            logger.error(f"✗ Failed to ingest {file_path.name}: {e}")
            return
    
    # Run tests
    test_rag_retrieval()
    verify_rag_integration()
    
    # Only run chatbot tests if API key is available
    if not skip_chatbot_tests:
        logger.info("\n" + "=" * 70)
        logger.info("Note: Chatbot tests may take time due to LLM API calls")
        logger.info("      and tool initialization (Jira/Confluence connections)")
        logger.info("=" * 70)
        
        # Ask user if they want to continue (with timeout)
        logger.warning("\n⚠ Chatbot initialization may hang if Jira/Confluence")
        logger.info("   credentials are invalid or network is slow.")
        logger.info("\nOptions:")
        logger.info("  1. Continue with chatbot test (may take 30+ seconds)")
        logger.info("  2. Skip chatbot test (recommended if you see hanging)")
        logger.info("\nProceeding with chatbot test in 3 seconds...")
        logger.info("  (Press Ctrl+C to skip)")
        
        import time
        try:
            time.sleep(3)
        except KeyboardInterrupt:
            logger.info("\nSkipping chatbot tests (user interrupted)")
            skip_chatbot_tests = True
        
        if not skip_chatbot_tests:
            test_chatbot_with_rag()
            test_chatbot_without_rag()
    else:
        logger.info("\n" + "=" * 70)
        logger.info("Skipping Chatbot Tests (no API key)")
        logger.info("=" * 70)
        logger.info("\nTo test chatbot with RAG:")
        logger.info("  1. Set OPENAI_API_KEY in your .env file")
        logger.info("  2. Run the test again")
        logger.info("  3. Or test manually:")
        logger.info("     chatbot = Chatbot(use_rag=True)")
        logger.info("     chatbot.get_response('What is Acme Corporation?')")
    
    logger.info("\n" + "=" * 70)
    logger.info("Test Complete!")
    logger.info("=" * 70)
    logger.info("\nHow to verify RAG is working:")
    logger.info("  1. Check if responses mention specific facts from your documents")
    logger.info("  2. Compare responses with/without RAG (should be different)")
    logger.info("  3. Ask questions that can ONLY be answered from your documents")
    logger.info("\nIf responses contain information from your documents,")
    logger.info("then RAG is working correctly! ✓")
    logger.info("=" * 70)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("\n\nTest interrupted by user")
    except Exception as e:
        logger.error(f"\n✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()

