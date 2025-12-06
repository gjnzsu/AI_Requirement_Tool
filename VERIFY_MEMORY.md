# How to Verify Conversation Memory Persistence

This guide shows you multiple ways to verify that conversations are being saved successfully.

## Method 1: Run the Test Script (Recommended)

The easiest way to verify everything works:

```bash
python test_memory.py
```

This script will:
- ✅ Create test conversations
- ✅ Add messages
- ✅ Verify persistence across restarts
- ✅ Test search functionality
- ✅ Show database statistics

**Expected Output:**
- All tests should pass with ✓ checkmarks
- You'll see conversations being created and retrieved
- Database statistics will be displayed

## Method 2: Inspect the Database Directly

View all stored conversations:

```bash
python inspect_memory_db.py
```

View a specific conversation:

```bash
python inspect_memory_db.py <conversation_id>
```

**Example:**
```bash
python inspect_memory_db.py chatbot_test_20251206_170002
```

## Method 3: Manual Verification with Web UI

1. **Start the web server:**
   ```bash
   python app.py
   ```

2. **Have a conversation:**
   - Open http://localhost:5000
   - Send a few messages
   - Note the conversation ID (check browser console or network tab)

3. **Stop the server** (Ctrl+C)

4. **Restart the server:**
   ```bash
   python app.py
   ```

5. **Verify persistence:**
   - The conversation should still appear in the sidebar
   - Click on it - all messages should be there
   - Send a new message - it should have context from previous messages

## Method 4: Manual Verification with CLI Chatbot

1. **Start the chatbot:**
   ```bash
   python src/chatbot.py
   ```

2. **Have a conversation:**
   - Send a few messages
   - Note the conversation ID (it will be shown in logs)

3. **Stop the chatbot** (Ctrl+C)

4. **Restart and load the conversation:**
   ```python
   from src.chatbot import Chatbot
   
   chatbot = Chatbot(use_persistent_memory=True)
   chatbot.load_conversation("your_conversation_id")
   chatbot.run()
   ```

5. **Verify:**
   - Previous messages should be in context
   - Ask "Do you remember what we talked about?" - it should recall

## Method 5: Check Database File Directly

The database is stored at:
```
data/chatbot_memory.db
```

### Using SQLite Command Line:

```bash
# Windows (if SQLite is installed)
sqlite3 data/chatbot_memory.db

# Then run SQL queries:
.tables                    # Show all tables
SELECT COUNT(*) FROM conversations;  # Count conversations
SELECT COUNT(*) FROM messages;        # Count messages
SELECT * FROM conversations LIMIT 5;  # List conversations
SELECT * FROM messages WHERE conversation_id = 'your_id';  # View messages
```

### Using Python:

```python
import sqlite3
from pathlib import Path

db_path = Path("data/chatbot_memory.db")
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Count conversations
cursor.execute("SELECT COUNT(*) FROM conversations")
print(f"Conversations: {cursor.fetchone()[0]}")

# Count messages
cursor.execute("SELECT COUNT(*) FROM messages")
print(f"Messages: {cursor.fetchone()[0]}")

# List conversations
cursor.execute("SELECT id, title, created_at FROM conversations")
for row in cursor.fetchall():
    print(f"{row[0]}: {row[1]} ({row[2]})")

conn.close()
```

## Method 6: Programmatic Verification

```python
from src.services.memory_manager import MemoryManager

# Initialize memory manager
memory = MemoryManager()

# Get statistics
stats = memory.get_statistics()
print(f"Total conversations: {stats['total_conversations']}")
print(f"Total messages: {stats['total_messages']}")

# List all conversations
conversations = memory.list_conversations()
for conv in conversations:
    print(f"{conv['id']}: {conv['title']} ({conv.get('message_count', 0)} messages)")

# Get a specific conversation
conversation = memory.get_conversation("your_conversation_id")
if conversation:
    print(f"Found conversation with {len(conversation['messages'])} messages")
    for msg in conversation['messages']:
        print(f"  [{msg['role']}]: {msg['content'][:50]}...")
```

## What to Look For

✅ **Success Indicators:**
- Database file exists at `data/chatbot_memory.db`
- File size increases as you add conversations
- Conversations persist after restarting the server
- Messages are retrievable by conversation ID
- Search functionality finds conversations

❌ **Failure Indicators:**
- Database file doesn't exist (check if `USE_PERSISTENT_MEMORY=true`)
- Conversations disappear after restart
- Error messages about database connection
- Messages not found when loading conversation

## Troubleshooting

### Database not created?
- Check that `USE_PERSISTENT_MEMORY=true` in your `.env` file
- Ensure the `data/` directory exists and is writable
- Check for error messages in console output

### Conversations not persisting?
- Verify `USE_PERSISTENT_MEMORY=true` is set
- Check that the chatbot is using persistent memory:
  ```python
  chatbot = Chatbot(use_persistent_memory=True)
  ```
- Check database file permissions

### Can't find conversation?
- Use `inspect_memory_db.py` to list all conversations
- Check the conversation ID matches exactly
- Verify the conversation was actually saved (check database)

## Quick Test Checklist

- [ ] Run `python test_memory.py` - all tests pass
- [ ] Database file exists at `data/chatbot_memory.db`
- [ ] Can view conversations with `inspect_memory_db.py`
- [ ] Web UI conversations persist after restart
- [ ] CLI chatbot can load previous conversations
- [ ] Search functionality works

## Example Verification Session

```bash
# 1. Run test script
python test_memory.py

# 2. Check database
python inspect_memory_db.py

# 3. Start web server
python app.py

# 4. Have conversation in browser
# 5. Stop server (Ctrl+C)
# 6. Restart server
python app.py

# 7. Verify conversation still exists in browser
# 8. Check database again
python inspect_memory_db.py
```

All of these methods confirm that your conversations are being saved successfully! 🎉

