"""
Test script to verify logger functionality and ensure no duplicate messages.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.utils.logger import get_logger

def test_logger_no_duplicates():
    """Test that logger doesn't create duplicate messages."""
    print("=" * 60)
    print("Testing Logger - No Duplicate Messages")
    print("=" * 60)
    print()
    
    # Create multiple logger instances
    logger1 = get_logger('chatbot.agent')
    logger2 = get_logger('chatbot.agent')
    logger3 = get_logger('chatbot.test')
    
    print("Created 3 logger instances:")
    print(f"  - logger1: {logger1.name}, handlers: {len(logger1.handlers)}")
    print(f"  - logger2: {logger2.name}, handlers: {len(logger2.handlers)}")
    print(f"  - logger3: {logger3.name}, handlers: {len(logger3.handlers)}")
    print()
    
    print("Testing log messages (should appear only once each):")
    print("-" * 60)
    
    logger1.info("Test INFO message from logger1")
    logger2.debug("Test DEBUG message from logger2")
    logger3.warning("Test WARNING message from logger3")
    logger1.error("Test ERROR message from logger1")
    
    print("-" * 60)
    print()
    
    # Verify handlers
    print("Handler verification:")
    print(f"  logger1 handlers: {len(logger1.handlers)}")
    print(f"  logger2 handlers: {len(logger2.handlers)}")
    print(f"  logger3 handlers: {len(logger3.handlers)}")
    print(f"  logger1.propagate: {logger1.propagate}")
    print(f"  logger2.propagate: {logger2.propagate}")
    print(f"  logger3.propagate: {logger3.propagate}")
    print()
    
    if len(logger1.handlers) == 1 and len(logger2.handlers) == 1 and len(logger3.handlers) == 1:
        print("✓ PASS: Each logger has exactly 1 handler (no duplicates)")
    else:
        print("✗ FAIL: Unexpected handler count")
    
    if logger1.propagate == False and logger2.propagate == False and logger3.propagate == False:
        print("✓ PASS: Propagation is disabled (prevents duplicate messages)")
    else:
        print("✗ FAIL: Propagation not properly disabled")
    
    print()
    print("=" * 60)
    print("Logger test completed!")
    print("=" * 60)

if __name__ == "__main__":
    test_logger_no_duplicates()

