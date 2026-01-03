# Coze SDK Migration Guide

## Overview

The Coze integration has been updated to use the official `cozepy` SDK instead of direct HTTP requests. This provides better reliability, proper authentication handling, and official support.

## Installation

Install the official Coze SDK:

```bash
pip install cozepy
```

Or add to `requirements.txt`:
```
cozepy>=0.1.0,<1.0.0
```

## Changes

### Before (Direct HTTP)
- Used `requests` library for direct API calls
- Manual header construction
- Manual error parsing
- Custom response extraction

### After (Official SDK)
- Uses `cozepy` SDK
- Proper `TokenAuth` authentication
- Built-in error handling
- SDK handles response parsing

## Configuration

No changes needed to environment variables:

```bash
COZE_ENABLED=true
COZE_API_TOKEN=your-token-here
COZE_BOT_ID=your-bot-id-here
COZE_API_BASE_URL=https://api.coze.com  # Optional, defaults to COZE_BASE_URL
```

## API Usage

The `CozeClient` interface remains the same:

```python
from src.services.coze_client import CozeClient

client = CozeClient()
result = client.execute_agent(
    query="Hello",
    user_id="user123",
    conversation_id=None,  # Optional
    stream=False  # Set to True for streaming
)
```

## Benefits

1. **Proper Authentication**: SDK handles token authentication correctly
2. **Error Handling**: Better error messages and handling
3. **Official Support**: Maintained by Coze team
4. **Streaming Support**: Built-in streaming API support
5. **Type Safety**: Better type hints and validation

## Troubleshooting

If you see import errors:
```bash
pip install cozepy
```

If authentication still fails:
1. Verify token format (should work with any valid Coze token)
2. Check bot ID is correct
3. Ensure bot is published with API access enabled

## References

- Official SDK: https://github.com/coze-dev/coze-py
- Coze Documentation: https://coze.com/docs

