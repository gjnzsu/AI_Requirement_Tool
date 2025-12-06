# RAG Cache System

## Overview

The RAG system now includes intelligent caching to improve performance and reduce API costs.

## What Gets Cached

### 1. Query Embeddings
- **What**: Embedding vectors for queries
- **Why**: Avoid regenerating embeddings for the same questions
- **Benefit**: Saves API calls to OpenAI (cost savings)

### 2. Retrieval Results
- **What**: Complete retrieval results (chunks + similarity scores)
- **Why**: Avoid re-searching the database for identical queries
- **Benefit**: Faster responses for repeated questions

## How It Works

```
First Query: "What is Python?"
    ↓
1. Check cache → Not found
2. Generate embedding → Call OpenAI API
3. Search vector database
4. Cache embedding + results
5. Return results

Second Query: "What is Python?" (same question)
    ↓
1. Check cache → Found!
2. Return cached results immediately
3. No API call, no database search
```

## Configuration

Add to your `.env` file:

```bash
# Enable/disable RAG cache (default: true)
RAG_ENABLE_CACHE=true

# Cache time-to-live in hours (default: 24)
RAG_CACHE_TTL_HOURS=24
```

## Cache Storage

Cache is stored in:
```
data/rag_cache.db
```

This database contains:
- Query hashes (for fast lookup)
- Query text
- Cached embeddings
- Cached results
- Access statistics

## Benefits

✅ **Performance**: Repeated queries are instant  
✅ **Cost Savings**: Fewer OpenAI API calls  
✅ **Efficiency**: Less database load  
✅ **Automatic**: Works transparently  

## Cache Behavior

### Cache Hit (Same Query)
- Returns cached results immediately
- No API call
- No database search
- Very fast (< 10ms)

### Cache Miss (New Query)
- Generates embedding (API call)
- Searches database
- Caches results for future use
- Normal speed

### Cache Expiration
- Entries expire after TTL (default: 24 hours)
- Expired entries are automatically cleaned
- Fresh queries regenerate cache

## Example

```python
from src.rag import RAGService

rag = RAGService(enable_cache=True)

# First query - cache miss
results1 = rag.retrieve("What is Python?")  # API call + DB search

# Same query - cache hit
results2 = rag.retrieve("What is Python?")  # Instant from cache!

# Different query - cache miss
results3 = rag.retrieve("What is Flask?")  # API call + DB search
```

## Cache Statistics

```python
from src.rag import RAGService

rag = RAGService()
stats = rag.cache.get_statistics()

print(f"Total cached queries: {stats['total_cached_queries']}")
print(f"Total accesses: {stats['total_accesses']}")
print(f"Cache hit rate: {stats['cache_hit_rate']}")
```

## Cache Management

### Clear Expired Entries
```python
rag.cache.clear_expired()  # Remove expired entries
```

### Clear All Cache
```python
rag.cache.clear_all()  # Remove all cached entries
```

## Performance Impact

**Without Cache:**
- Every query: ~200-500ms (embedding generation + search)

**With Cache:**
- First query: ~200-500ms (cache miss)
- Repeated queries: ~5-10ms (cache hit)
- **10-50x faster** for repeated queries!

## When to Disable Cache

Disable cache if:
- You want always-fresh results
- Testing/debugging
- Knowledge base changes frequently

```python
rag = RAGService(enable_cache=False)
```

## Best Practices

1. **Keep cache enabled** (default) for best performance
2. **Adjust TTL** based on your needs:
   - Short TTL (1-6 hours): More fresh results
   - Long TTL (24-48 hours): Better performance
3. **Clear cache** when knowledge base is updated
4. **Monitor cache stats** to see hit rates

## Technical Details

- **Hash-based lookup**: Fast O(1) query matching
- **SQLite storage**: Persistent across restarts
- **Automatic expiration**: TTL-based cleanup
- **Access tracking**: Statistics for monitoring

The cache is transparent - your code doesn't need to change!

