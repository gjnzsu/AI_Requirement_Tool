# RAG (Retrieval-Augmented Generation) Guide

## Overview

The chatbot now includes RAG functionality that allows it to answer questions based on your own documents. The system retrieves relevant information from your knowledge base and includes it in the context when generating responses.

## How RAG Works

1. **Document Ingestion**: Load documents (TXT, PDF, Markdown) into the knowledge base
2. **Chunking**: Split documents into smaller chunks for better retrieval
3. **Embedding**: Convert chunks to vector embeddings using OpenAI
4. **Storage**: Store embeddings in a vector database
5. **Retrieval**: When you ask a question, find the most relevant chunks
6. **Generation**: Include retrieved context in the LLM prompt

## Basic Usage

### 1. Ingest Documents

```python
from src.rag import RAGService

# Initialize RAG service
rag = RAGService()

# Ingest a single file
rag.ingest_document("path/to/document.txt")

# Ingest all files in a directory
rag.ingest_directory("path/to/documents/", recursive=True)

# Ingest text directly
rag.ingest_text("Your text content here", metadata={'title': 'My Document'})
```

### 2. Use RAG-Enabled Chatbot

```python
from src.chatbot import Chatbot

# Create chatbot with RAG enabled (default)
chatbot = Chatbot(use_rag=True)

# Ask questions - RAG context is automatically included
response = chatbot.get_response("What is Python?")
```

### 3. Direct Retrieval

```python
from src.rag import RAGService

rag = RAGService()

# Search for relevant chunks
results = rag.retrieve("Python programming", top_k=5)

for result in results:
    print(f"Similarity: {result['similarity']:.3f}")
    print(f"Content: {result['content']}")
```

## Configuration

Add these to your `.env` file:

```bash
# Enable/disable RAG (default: true)
USE_RAG=true

# Chunk size for document splitting (default: 1000 characters)
RAG_CHUNK_SIZE=1000

# Overlap between chunks (default: 200 characters)
RAG_CHUNK_OVERLAP=200

# Embedding model (default: text-embedding-ada-002)
RAG_EMBEDDING_MODEL=text-embedding-ada-002

# Number of chunks to retrieve (default: 3)
RAG_TOP_K=3

# Custom vector store path (optional)
RAG_VECTOR_STORE_PATH=./data/rag_vectors.db
```

## Supported File Formats

- **TXT**: Plain text files
- **Markdown**: `.md`, `.markdown` files
- **PDF**: `.pdf` files (requires PyPDF2)

## Example Workflow

```python
from src.rag import RAGService
from src.chatbot import Chatbot

# Step 1: Ingest your documents
rag = RAGService()
rag.ingest_directory("./documents/")

# Step 2: Create chatbot with RAG
chatbot = Chatbot(use_rag=True)

# Step 3: Ask questions
response = chatbot.get_response("What are the key features mentioned in the documents?")
print(response)
```

## API Reference

### RAGService

#### Methods

- `ingest_document(file_path: str) -> str`: Ingest a single document file
- `ingest_directory(directory_path: str, recursive: bool = False) -> List[str]`: Ingest all documents in a directory
- `ingest_text(text: str, metadata: Optional[Dict] = None) -> str`: Ingest text directly
- `retrieve(query: str, top_k: int = 5) -> List[Dict]`: Retrieve relevant chunks
- `get_context(query: str, top_k: int = 3) -> str`: Get formatted context string
- `list_documents() -> List[Dict]`: List all ingested documents
- `delete_document(document_id: str) -> bool`: Delete a document
- `get_statistics() -> Dict`: Get knowledge base statistics

### Chatbot Integration

The chatbot automatically uses RAG when `use_rag=True` (default). Relevant context is automatically retrieved and included in prompts.

## Best Practices

1. **Chunk Size**: 
   - Smaller chunks (500-800) for precise retrieval
   - Larger chunks (1000-1500) for more context

2. **Overlap**: 
   - 10-20% of chunk size is recommended
   - Helps maintain context across chunk boundaries

3. **Top K**: 
   - Start with 3-5 chunks
   - Increase if you need more context
   - Too many chunks may dilute relevance

4. **Document Quality**:
   - Use well-structured documents
   - Include clear headings and sections
   - Remove unnecessary formatting

## Troubleshooting

### RAG not working?
- Check that `OPENAI_API_KEY` is set (required for embeddings)
- Verify `USE_RAG=true` in configuration
- Check console for initialization messages

### No results retrieved?
- Make sure documents are ingested first
- Try re-ingesting documents
- Check similarity threshold (results are sorted by similarity)

### Poor retrieval quality?
- Try adjusting chunk size
- Increase overlap between chunks
- Use more specific queries
- Consider re-ingesting with better chunking parameters

## Database Location

Vector embeddings are stored in:
```
data/rag_vectors.db
```

This database contains:
- Document metadata
- Text chunks
- Embedding vectors

## Example Script

See `example_rag.py` for a complete working example.

## Next Steps

- Add more document formats (DOCX, HTML, etc.)
- Implement semantic search improvements
- Add document versioning
- Support for multiple knowledge bases
- Fine-tune retrieval strategies

