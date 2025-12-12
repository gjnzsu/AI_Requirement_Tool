# MCP Timeout Issue - Fixed

## Problem

When connecting to Jira MCP server, the system was experiencing timeout issues:
- "Error detecting intent: Request timed out."
- MCP tool calls timing out during execution

## Root Causes

1. **LLM Call Timeouts**: Intent detection and other LLM calls had no timeout handling
2. **MCP Tool Call Timeouts**: Tool execution timeout was too short (30 seconds)
3. **No Graceful Degradation**: System didn't handle timeouts gracefully

## Solutions Implemented

### 1. Increased MCP Tool Call Timeout

**File**: `src/mcp/mcp_client.py`

- Increased timeout from **30 seconds to 60 seconds** for MCP tool calls
- Jira operations can take longer, especially for complex issues

```python
# Before: timeout=30.0
# After: timeout=60.0
result = await asyncio.wait_for(
    session.call_tool(tool_name, arguments),
    timeout=60.0
)
```

### 2. Added Timeout Handling to LLM Calls

**File**: `src/agent/agent_graph.py`

- Added **30-second timeout** for intent detection
- Added **60-second timeout** for backlog generation
- Added **60-second timeout** for general chat responses
- Uses `ThreadPoolExecutor` to add timeout to sync LLM calls

```python
# Intent detection with timeout
with concurrent.futures.ThreadPoolExecutor() as executor:
    future = executor.submit(self.llm.invoke, [HumanMessage(...)])
    response = future.result(timeout=30.0)
```

### 3. Enhanced MCP Tool Wrapper Timeout

**File**: `src/mcp/mcp_integration.py`

- Added **60-second timeout** for MCP tool execution
- Better error messages for timeout scenarios

```python
result = await asyncio.wait_for(
    self.mcp_client.call_tool(self.tool_name, kwargs),
    timeout=60.0
)
```

## Timeout Values

| Operation | Timeout | Reason |
|-----------|---------|--------|
| Intent Detection | 30 seconds | Quick classification |
| Backlog Generation | 60 seconds | Complex LLM generation |
| General Chat | 60 seconds | Standard LLM response |
| MCP Tool Calls | 60 seconds | Jira operations can be slow |
| MCP Connection | 20 seconds | Server initialization |

## Benefits

✅ **No More Hanging**: System won't hang indefinitely on slow operations  
✅ **Graceful Degradation**: Falls back to default behavior on timeout  
✅ **Better Error Messages**: Clear timeout error messages  
✅ **Improved Reliability**: System continues working even if some operations timeout  

## Testing

After these changes:
1. ✅ Intent detection times out gracefully (defaults to general_chat)
2. ✅ MCP tool calls have sufficient time (60 seconds)
3. ✅ LLM calls won't hang indefinitely
4. ✅ System continues working even with timeouts

## Usage

The chatbot will now:
- Handle timeouts gracefully
- Provide clear error messages
- Continue functioning even if some operations timeout
- Use custom tools as fallback if MCP times out

## Future Improvements

- Make timeout values configurable via environment variables
- Add retry logic for transient timeouts
- Monitor timeout frequency to optimize values

