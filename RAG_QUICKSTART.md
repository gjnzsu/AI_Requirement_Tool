# RAG Quick Start Guide

## How to Use RAG Function

### Prerequisites

1. **Install dependencies:**
   ```bash
   pip install PyPDF2
   ```

2. **Set OpenAI API Key** (required for embeddings):
   ```bash
   # In your .env file
   OPENAI_API_KEY=your-openai-api-key
   ```

### Step 1: Ingest Documents

Create a Python script or use the interactive Python shell:

```python
from src.rag import RAGService

# Initialize RAG service
rag = RAGService()

# Option 1: Ingest a single file
rag.ingest_document("path/to/your/document.txt")

# Option 2: Ingest all files in a directory
rag.ingest_directory("path/to/documents/", recursive=True)

# Option 3: Ingest text directly
rag.ingest_text("Your text content here", metadata={'title': 'My Doc'})
```

### Step 2: Use RAG-Enabled Chatbot

```python
from src.chatbot import Chatbot

# Create chatbot with RAG (enabled by default)
chatbot = Chatbot(use_rag=True)

# Ask questions - RAG context is automatically included!
response = chatbot.get_response("What is Python?")
print(response)
```

### Step 3: Run the Test

```bash
python test_rag.py
```

This will:
- Create sample documents
- Ingest them
- Test retrieval
- Test chatbot with RAG

## Complete Example

```python
from src.rag import RAGService
from src.chatbot import Chatbot

# 1. Ingest documents
rag = RAGService()
rag.ingest_document("my_document.txt")

# 2. Create chatbot
chatbot = Chatbot(use_rag=True)

# 3. Ask questions
response = chatbot.get_response("What does the document say about Python?")
print(response)
```

## Supported File Formats

- ✅ **TXT files** (`.txt`)
- ✅ **Markdown files** (`.md`, `.markdown`)
- ✅ **PDF files** (`.pdf`) - requires PyPDF2

## Configuration

Add to `.env` file:

```bash
# Enable RAG (default: true)
USE_RAG=true

# Number of chunks to retrieve (default: 3)
RAG_TOP_K=3

# Chunk size (default: 1000 characters)
RAG_CHUNK_SIZE=1000

# Chunk overlap (default: 200 characters)
RAG_CHUNK_OVERLAP=200
```

## Troubleshooting

**Q: RAG not working?**
- Check `OPENAI_API_KEY` is set
- Verify `USE_RAG=true` in config
- Check console for error messages

**Q: No results retrieved?**
- Make sure documents are ingested first
- Try re-ingesting documents
- Check if query matches document content

**Q: How do I know if RAG is active?**
- Look for "✓ Initialized RAG Service" message on startup
- Check `chatbot.rag_service` is not None

## Next Steps

- See `RAG_GUIDE.md` for detailed documentation
- Run `python test_rag.py` to see it in action
- Check `example_rag.py` for more examples

