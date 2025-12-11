"""
Simple, fast RAG test without dead loops.

This version:
- Tests RAG retrieval only (no chatbot API calls)
- No user input prompts
- Quick verification
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from src.rag import RAGService
from config.config import Config
from src.utils.logger import get_logger

logger = get_logger('test.rag_simple')


def quick_rag_test():
    """Quick test to verify RAG is working."""
    logger.info("=" * 70)
    logger.info("Quick RAG Test")
    logger.info("=" * 70)
    
    # Check if documents exist
    rag = RAGService()
    stats = rag.get_statistics()
    
    logger.info(f"\nKnowledge Base Status:")
    logger.info(f"  Documents: {stats['total_documents']}")
    logger.info(f"  Chunks: {stats['total_chunks']}")
    
    if stats['total_documents'] == 0:
        logger.warning("\n⚠ No documents in knowledge base!")
        logger.info("   Ingest some documents first:")
        logger.info("   rag = RAGService()")
        logger.info("   rag.ingest_document('your_file.pdf')")
        return
    
    # Test retrieval
    logger.info("\n" + "=" * 70)
    logger.info("Testing Retrieval")
    logger.info("=" * 70)
    
    test_query = "Python programming"
    logger.info(f"\nQuery: '{test_query}'")
    
    try:
        results = rag.retrieve(test_query, top_k=3)
        
        if results:
            logger.info(f"\n✓ Found {len(results)} relevant chunks:\n")
            for i, result in enumerate(results, 1):
                logger.info(f"[{i}] Similarity: {result['similarity']:.3f}")
                logger.info(f"    Content: {result['content'][:150]}...")
                if result.get('metadata', {}).get('file_name'):
                    logger.info(f"    Source: {result['metadata']['file_name']}")
                logger.info("")
            
            logger.info("=" * 70)
            logger.info("✓ RAG is working! Retrieval successful.")
            logger.info("=" * 70)
            logger.info("\nTo use with chatbot:")
            logger.info("  chatbot = Chatbot(use_rag=True)")
            logger.info("  chatbot.get_response('your question')")
        else:
            logger.error("\n✗ No results found")
            logger.info("   Try ingesting more documents or different query")
            
    except Exception as e:
        logger.error(f"\n✗ Error: {e}")
        import traceback
        logger.error(traceback.format_exc())


if __name__ == "__main__":
    try:
        quick_rag_test()
    except KeyboardInterrupt:
        logger.info("\n\nTest interrupted")
    except Exception as e:
        logger.error(f"\n✗ Error: {e}")

