"""
Test script to verify logger functionality and ensure no duplicate messages.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.utils.logger import get_logger
from config.config import Config

# Use a separate logger for test output
test_logger = get_logger('test.logger')


def test_logger_no_duplicates():
    """Test that logger doesn't create duplicate messages."""
    test_logger.info("=" * 70)
    test_logger.info("Testing Logger - No Duplicate Messages")
    test_logger.info("=" * 70)
    test_logger.info("")
    
    # Ensure Config is set for testing
    Config.LOG_LEVEL = 'INFO'
    Config.ENABLE_DEBUG_LOGGING = False
    Config.LOG_FILE = None  # Ensure no file logging for this test
    
    # Get logger multiple times (simulating multiple imports)
    logger1 = get_logger('chatbot.agent')
    logger2 = get_logger('chatbot.agent')  # Should return the same instance
    logger3 = get_logger('chatbot.test')
    
    test_logger.info("Created 3 logger instances:")
    test_logger.info(f"  - logger1: {logger1.name}, handlers: {len(logger1.handlers)}")
    test_logger.info(f"  - logger2: {logger2.name}, handlers: {len(logger2.handlers)}")
    test_logger.info(f"  - logger3: {logger3.name}, handlers: {len(logger3.handlers)}")
    test_logger.info("")
    
    # Verify they're the same instance
    assert logger1 is logger2, "Same logger name should return same instance"
    assert logger1 is not logger3, "Different logger names should return different instances"
    
    test_logger.info("Testing log messages (should appear only once each):")
    test_logger.info("-" * 70)
    logger1.info("Test INFO message from logger1")
    logger3.warning("Test WARNING message from logger3")
    logger1.error("Test ERROR message from logger1")
    test_logger.info("-" * 70)
    test_logger.info("")
    
    # Verify handler counts
    test_logger.info("Handler verification:")
    test_logger.info(f"  logger1 handlers: {len(logger1.handlers)}")
    test_logger.info(f"  logger2 handlers: {len(logger2.handlers)}")
    test_logger.info(f"  logger3 handlers: {len(logger3.handlers)}")
    test_logger.info(f"  logger1.propagate: {logger1.propagate}")
    test_logger.info(f"  logger2.propagate: {logger2.propagate}")
    test_logger.info(f"  logger3.propagate: {logger3.propagate}")
    test_logger.info("")
    
    # Call get_logger again to ensure no duplicate handlers
    logger1_again = get_logger('chatbot.agent')
    test_logger.info(f"  After calling get_logger again: {len(logger1_again.handlers)} handlers")
    test_logger.info("")
    
    # Assertions
    assert len(logger1.handlers) == 1, f"Logger1 should have exactly 1 handler, got {len(logger1.handlers)}"
    assert len(logger2.handlers) == 1, f"Logger2 should have exactly 1 handler, got {len(logger2.handlers)}"
    assert len(logger3.handlers) == 1, f"Logger3 should have exactly 1 handler, got {len(logger3.handlers)}"
    assert logger1.propagate is False, "Logger1 propagation should be False"
    assert logger2.propagate is False, "Logger2 propagation should be False"
    assert logger3.propagate is False, "Logger3 propagation should be False"
    assert len(logger1_again.handlers) == 1, "Should still have 1 handler after calling get_logger again"
    
    test_logger.info("PASS: Each logger has exactly 1 handler (no duplicates)")
    test_logger.info("PASS: Propagation is disabled (prevents duplicate messages)")
    test_logger.info("PASS: Multiple calls to get_logger don't add duplicate handlers")
    
    test_logger.info("")
    test_logger.info("=" * 70)
    test_logger.info("Logger duplicate test completed successfully!")
    test_logger.info("=" * 70)


if __name__ == "__main__":
    test_logger_no_duplicates()

