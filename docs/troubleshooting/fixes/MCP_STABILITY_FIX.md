# MCP Stability Fix - Preventing Program Hangs

## Problem

The Atlassian Rovo MCP Server was causing stability issues:
- Jira MCP server connection failing
- Confluence MCP server connecting but program getting stuck
- Intent detection timing out
- No graceful recovery from partial MCP failures

## Root Causes

1. **No Timeout on MCP Initialization**: MCP initialization could hang indefinitely
2. **Blocking on Failed Servers**: If one server failed, it could block the entire initialization
3. **No Individual Server Timeouts**: Each server didn't have its own timeout
4. **Program Stuck**: System would hang waiting for MCP operations

## Solutions Implemented

### 1. Added Overall Timeout to MCP Initialization

**File**: `src/agent/agent_graph.py`

- Added **35-second overall timeout** for MCP initialization
- Prevents the program from hanging during startup

```python
asyncio.run(
    asyncio.wait_for(
        self.mcp_integration.initialize(),
        timeout=35.0
    )
)
```

### 2. Added Individual Server Timeouts

**File**: `src/mcp/mcp_integration.py`

- Each MCP server initialization has a **15-second timeout**
- If one server fails/times out, others can still initialize
- Graceful degradation - use what works

```python
async def initialize(self):
    await asyncio.wait_for(self._initialize_mcp_servers(), timeout=30.0)
```

### 3. Improved Server Initialization

**File**: `src/mcp/mcp_client.py`

- Each server in `initialize_all()` has individual timeout
- Failed servers don't block successful ones
- Better error messages for each server

```python
async def initialize_all(self):
    for name, adapter in self.adapters.items():
        try:
            await asyncio.wait_for(adapter.initialize(), timeout=15.0)
        except asyncio.TimeoutError:
            print(f"⚠ MCP server '{name}' initialization timeout (15s), skipping")
```

### 4. Partial Failure Handling

- If Jira MCP fails, Confluence MCP can still work
- If both fail, system falls back to custom tools
- System never hangs - always has a fallback

## Timeout Hierarchy

| Level | Timeout | Purpose |
|-------|---------|---------|
| Overall MCP Init | 35 seconds | Prevent program hang |
| Individual Server | 15 seconds | Allow partial success |
| MCP Connection | 20 seconds | Server connection |
| Tool Execution | 60 seconds | Jira operations |

## Benefits

✅ **No More Hanging**: Program won't get stuck during initialization  
✅ **Partial Success**: If one server works, use it  
✅ **Graceful Degradation**: Always falls back to custom tools  
✅ **Better Error Messages**: Clear indication of what failed  
✅ **Faster Startup**: Timeouts prevent long waits  

## Behavior Now

1. **Startup**: MCP initialization has 35-second timeout
2. **Jira Server**: 15-second timeout, if fails, continue
3. **Confluence Server**: 15-second timeout, if fails, continue
4. **Result**: Use whatever servers connected successfully
5. **Fallback**: If no servers work, use custom tools

## Testing

After these changes:
- ✅ Program starts even if MCP servers are slow
- ✅ Partial MCP failures don't block the system
- ✅ Clear error messages for each failure
- ✅ System always has a working fallback

## Configuration

To disable MCP entirely if it's causing issues:

```python
# In agent initialization
agent = ChatbotAgent(use_mcp=False)  # Disable MCP
```

Or set environment variable:
```env
USE_MCP=false
```

## Summary

The system is now much more resilient:
- **Never hangs** - always has timeouts
- **Partial success** - uses what works
- **Graceful fallback** - custom tools always available
- **Better UX** - clear error messages and fast startup

