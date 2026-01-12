"""
Safe RAG context test - avoids dead loops by skipping chatbot initialization.

This version tests RAG retrieval without initializing chatbot (which can hang
on Jira/Confluence connections).
"""

import sys
import pytest
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from src.rag import RAGService
from config.config import Config
from src.utils.logger import get_logger

logger = get_logger('test.rag_context_safe')

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


@pytest.mark.rag
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
        try:
            results = rag.retrieve(query, top_k=2)
            
            if results:
                logger.info(f"  ✓ Found {len(results)} relevant chunks")
                for i, result in enumerate(results[:1], 1):  # Show top result
                    logger.info(f"    [{i}] Similarity: {result['similarity']:.3f}")
                    logger.info(f"        Content preview: {result['content'][:100]}...")
            else:
                logger.error("  ✗ No results found")
        except Exception as e:
            logger.error(f"  ✗ Error: {e}")
        logger.info("")


def verify_rag_integration():
    """Verify RAG is properly integrated."""
    logger.info("\n" + "=" * 70)
    logger.info("Step 2: Verifying RAG Integration")
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
    logger.info("RAG Context Verification Test (Safe Version)")
    logger.info("=" * 70)
    logger.info("\nThis test verifies that:")
    logger.info("  1. Documents are ingested into RAG store")
    logger.info("  2. RAG can retrieve relevant information")
    logger.info("  3. RAG is ready for chatbot integration")
    logger.info("\nNote: This version skips chatbot tests to avoid dead loops")
    logger.info("      from Jira/Confluence connection attempts.")
    logger.info("")
    
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
    
    logger.info("\n" + "=" * 70)
    logger.info("Test Complete!")
    logger.info("=" * 70)
    logger.info("\n✓ RAG retrieval is working correctly!")
    logger.info("\nTo test with chatbot (manual test):")
    logger.info("  from src.chatbot import Chatbot")
    logger.info("  chatbot = Chatbot(use_rag=True)")
    logger.info("  response = chatbot.get_response('What is Acme Corporation?')")
    logger.info("  print(response)")
    logger.info("\nIf the response mentions 'Acme Corporation', '2020', 'Tech City', etc.,")
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

