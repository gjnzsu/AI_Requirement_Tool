# How to Ingest PDF Files into RAG Store

## Method 1: Using the Script (Easiest)

Use the provided script to ingest PDFs:

```bash
# Ingest a single PDF
python ingest_pdf.py your_document.pdf

# Ingest all PDFs in a folder
python ingest_pdf.py ./pdf_folder/

# Ingest PDFs recursively (including subfolders)
python ingest_pdf.py ./pdf_folder/ --recursive
```

## Method 2: Using Python Code

### Single PDF File

```python
from src.rag import RAGService

# Initialize RAG service
rag = RAGService()

# Ingest a PDF file
rag.ingest_document("path/to/your/document.pdf")
```

### Multiple PDF Files

```python
from src.rag import RAGService
from pathlib import Path

rag = RAGService()

# Ingest all PDFs in a directory
pdf_folder = Path("./pdfs")
for pdf_file in pdf_folder.glob("*.pdf"):
    print(f"Ingesting: {pdf_file.name}")
    rag.ingest_document(str(pdf_file))
    print(f"✓ Done: {pdf_file.name}")
```

### Recursive Directory Ingestion

```python
from src.rag import RAGService

rag = RAGService()

# Ingest all PDFs recursively
rag.ingest_directory("./pdf_folder/", recursive=True)
```

## Method 3: Using RAG Service Directly

```python
from src.rag import RAGService

rag = RAGService()

# Single PDF
doc_id = rag.ingest_document("document.pdf")
print(f"Ingested with ID: {doc_id}")

# All PDFs in directory
doc_ids = rag.ingest_directory("./pdfs/")
print(f"Ingested {len(doc_ids)} documents")
```

## Prerequisites

1. **Install PyPDF2** (if not already installed):
   ```bash
   pip install PyPDF2
   ```

2. **Set OpenAI API Key** (required for embeddings):
   ```bash
   # In your .env file
   OPENAI_API_KEY=your-openai-api-key
   ```

## Example Workflow

```python
from src.rag import RAGService
from src.chatbot import Chatbot

# Step 1: Ingest your PDFs
rag = RAGService()
rag.ingest_document("my_guide.pdf")
rag.ingest_document("another_doc.pdf")

# Step 2: Use chatbot - RAG works automatically!
chatbot = Chatbot(use_rag=True)

# Step 3: Ask questions about your PDFs
response = chatbot.get_response("What does the PDF say about Python?")
print(response)
```

## Verify PDFs are Ingested

```python
from src.rag import RAGService

rag = RAGService()

# List all documents
documents = rag.list_documents()
for doc in documents:
    print(f"- {doc['file_name']} ({doc['chunk_count']} chunks)")

# Get statistics
stats = rag.get_statistics()
print(f"Total documents: {stats['total_documents']}")
print(f"Total chunks: {stats['total_chunks']}")
```

## Troubleshooting

### "PyPDF2 is required"
```bash
pip install PyPDF2
```

### "OPENAI_API_KEY not found"
Set it in your `.env` file:
```bash
OPENAI_API_KEY=sk-your-key-here
```

### PDF not extracting text properly
- Some PDFs are image-based (scanned documents)
- You may need OCR (Optical Character Recognition) first
- Try a different PDF or convert to text first

### Large PDFs taking too long
- Large PDFs are split into chunks automatically
- First ingestion generates embeddings (can take time)
- Subsequent queries are fast

## Tips

1. **Organize PDFs**: Put all PDFs in one folder for easy ingestion
2. **Check file size**: Very large PDFs may take longer to process
3. **Verify ingestion**: Use `rag.list_documents()` to check
4. **Test retrieval**: Try `rag.retrieve("your query")` to test

## Quick Test

After ingesting, test if it works:

```python
from src.rag import RAGService

rag = RAGService()

# Search for content
results = rag.retrieve("your search query", top_k=3)
for result in results:
    print(f"Similarity: {result['similarity']:.3f}")
    print(f"Content: {result['content'][:200]}...")
```

That's it! Your PDFs are now in the RAG knowledge base and the chatbot can answer questions about them.

