# Changelog

## [Latest] - LangGraph Agent Framework Integration

### Major Changes

#### ✅ LangGraph Agent Framework
- **Implemented**: Full LangGraph-based agent framework for intelligent tool orchestration
- **Features**:
  - Intent detection (keyword-based, fast and reliable)
  - Tool routing (Jira, RAG, General Chat)
  - State management with AgentState
  - Conditional edge routing based on intent
- **Benefits**: Better orchestration, clearer workflow, easier to extend

#### ✅ MCP Integration (Disabled)
- **Status**: MCP protocol integration built but currently disabled
- **Reason**: Stability issues with external MCP servers
- **Fallback**: Using custom tools (JiraTool, ConfluenceTool) directly
- **Files**: 
  - `src/mcp/mcp_client.py` - MCP client implementation
  - `src/mcp/mcp_integration.py` - MCP integration layer
  - `src/mcp/jira_mcp_server.py` - Custom Python-based Jira MCP server

#### ✅ Intent Detection Improvements
- **Changed**: From LLM-based to keyword-based detection
- **Reason**: LLM calls were timing out, causing delays
- **Benefits**: 
  - Instant intent detection (no API calls)
  - No timeout issues
  - More reliable
- **Keywords**:
  - Jira creation: `create jira`, `create issue`, `new jira`, etc.
  - RAG queries: `what is`, `how to`, `explain`, etc.
  - General chat: `hello`, `hi`, `who are you`, etc.

#### ✅ Timeout Handling
- **LLM Calls**: Added comprehensive timeout handling
  - LLM constructor: 15 seconds
  - ThreadPoolExecutor: 20 seconds
  - Reduced retries: 2 → 1
- **RAG Embeddings**: Added timeout (10s single, 15s batch)
- **MCP**: Disabled to avoid timeout issues

#### ✅ Error Handling & Diagnostics
- **Added**: Better error messages and diagnostics
- **Added**: API connection test script (`test_openai_api.py`)
- **Added**: Model name validation
- **Added**: LangGraph execution logging

### Files Modified

#### Core Agent Framework
- `src/agent/agent_graph.py` - Main LangGraph agent implementation
  - Intent detection (keyword-based)
  - Tool orchestration
  - State management
  - Logging for verification

#### MCP Integration
- `src/mcp/mcp_client.py` - MCP client (disabled)
- `src/mcp/mcp_integration.py` - MCP integration (disabled)
- `src/mcp/jira_mcp_server.py` - Custom Jira MCP server (not used)

#### RAG Service
- `src/rag/embedding_generator.py` - Added timeout handling

#### Chatbot
- `src/chatbot.py` - Updated to use LangGraph agent

#### Configuration
- `config/config.py` - MCP settings

### Files Created

- `test_openai_api.py` - API connection test script
- `CHANGELOG.md` - This file

### Files Removed/Disabled

- MCP functionality disabled (can be re-enabled if needed)
- LLM-based intent detection removed (replaced with keywords)

### Configuration Changes

- `USE_MCP=false` - MCP disabled by default
- Intent detection: Pure keyword-based (no LLM calls)

### Known Issues Resolved

1. ✅ Intent detection timeout - Fixed with keyword-based detection
2. ✅ LLM call timeouts - Fixed with better timeout handling and proxy configuration
3. ✅ RAG embedding timeouts - Fixed with timeout handling
4. ✅ MCP instability - Disabled, using custom tools instead

### Testing

To verify LangGraph is working:
1. Check startup logs: `✓ Initialized LangGraph Agent`
2. Check runtime logs: `🔄 LangGraph: Processing input...`
3. Test different intents:
   - General chat: "Hello"
   - Jira creation: "Create a Jira issue"
   - RAG query: "What is authentication?"

### Next Steps

- [ ] Re-enable MCP if stability improves
- [ ] Add more intent keywords as needed
- [ ] Enhance tool orchestration
- [ ] Add more tools to the agent

