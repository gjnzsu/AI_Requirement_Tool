"""
Simple test script to verify input/output works correctly.
Run this to test if your terminal input is working.
"""

import sys
from src.utils.logger import get_logger


logger.info("=" * 70)
logger.info("Input/Output Test")
logger.info("=" * 70)
logger.info("")
logger.info("This script tests if input() works in your terminal.")
logger.info("Type something and press Enter. Type 'quit' to exit.")
logger.info("")
sys.stdout.flush()

while True:
    try:
        user_input = input("You: ").strip()
        logger.info(f"Received: '{user_input}'")
        sys.stdout.flush()
        
        if user_input.lower() in ['quit', 'exit', 'bye']:
            logger.info("Goodbye!")
            break
            
    except KeyboardInterrupt:
        logger.info("\n\nInterrupted. Goodbye!")
        break
    except EOFError:
        logger.info("\n\nEOF. Goodbye!")
        break
    except Exception as e:
        logger.error(f"\nError: {e}")
        break

