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
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.rag import RAGService
from config.config import Config


def quick_rag_test():
    """Quick test to verify RAG is working."""
    print("=" * 70)
    print("Quick RAG Test")
    print("=" * 70)
    
    # Check if documents exist
    rag = RAGService()
    stats = rag.get_statistics()
    
    print(f"\nKnowledge Base Status:")
    print(f"  Documents: {stats['total_documents']}")
    print(f"  Chunks: {stats['total_chunks']}")
    
    if stats['total_documents'] == 0:
        print("\n⚠ No documents in knowledge base!")
        print("   Ingest some documents first:")
        print("   rag = RAGService()")
        print("   rag.ingest_document('your_file.pdf')")
        return
    
    # Test retrieval
    print("\n" + "=" * 70)
    print("Testing Retrieval")
    print("=" * 70)
    
    test_query = "Python programming"
    print(f"\nQuery: '{test_query}'")
    
    try:
        results = rag.retrieve(test_query, top_k=3)
        
        if results:
            print(f"\n✓ Found {len(results)} relevant chunks:\n")
            for i, result in enumerate(results, 1):
                print(f"[{i}] Similarity: {result['similarity']:.3f}")
                print(f"    Content: {result['content'][:150]}...")
                if result.get('metadata', {}).get('file_name'):
                    print(f"    Source: {result['metadata']['file_name']}")
                print()
            
            print("=" * 70)
            print("✓ RAG is working! Retrieval successful.")
            print("=" * 70)
            print("\nTo use with chatbot:")
            print("  chatbot = Chatbot(use_rag=True)")
            print("  chatbot.get_response('your question')")
        else:
            print("\n✗ No results found")
            print("   Try ingesting more documents or different query")
            
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    try:
        quick_rag_test()
    except KeyboardInterrupt:
        print("\n\nTest interrupted")
    except Exception as e:
        print(f"\n✗ Error: {e}")

