"""
Simple test script to verify input/output works correctly.
Run this to test if your terminal input is working.
"""

import sys

print("=" * 70)
print("Input/Output Test")
print("=" * 70)
print()
print("This script tests if input() works in your terminal.")
print("Type something and press Enter. Type 'quit' to exit.")
print()
sys.stdout.flush()

while True:
    try:
        user_input = input("You: ").strip()
        print(f"Received: '{user_input}'")
        sys.stdout.flush()
        
        if user_input.lower() in ['quit', 'exit', 'bye']:
            print("Goodbye!")
            break
            
    except KeyboardInterrupt:
        print("\n\nInterrupted. Goodbye!")
        break
    except EOFError:
        print("\n\nEOF. Goodbye!")
        break
    except Exception as e:
        print(f"\nError: {e}")
        break

