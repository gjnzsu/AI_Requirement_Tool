# LangGraph Agent Framework - Quick Reference

## What is LangGraph?

LangGraph is a framework for building stateful, multi-actor applications with LLMs. In this chatbot, it orchestrates:
- Intent detection
- Tool selection (Jira, RAG, General Chat)
- Workflow execution
- State management

## How It Works

1. **User sends message** → Agent receives input
2. **Intent detection** → Keyword matching determines intent
3. **Routing** → LangGraph routes to appropriate node
4. **Tool execution** → Selected tool processes the request
5. **Response** → Agent returns formatted response

## Current Workflow

```
User Input
    ↓
Intent Detection (keywords)
    ↓
    ├─ Jira Creation? → Create Issue → Evaluate → [Confluence] → Response
    ├─ RAG Query? → Retrieve Context → Generate Answer → Response
    └─ General Chat? → LLM Response → Response
```

## Verification

**Startup:**
```
✓ Initialized LangGraph Agent
```

**Runtime (for each message):**
```
🔄 LangGraph: Processing input through agent graph...
🔍 LangGraph: Detecting intent...
  → Intent: [detected_intent]
✓ LangGraph: Intent detected = '[intent]'
  → Executed nodes: [node_path]
✓ LangGraph: Response generated successfully
```

## Key Files

- `src/agent/agent_graph.py` - Main LangGraph implementation
- `src/chatbot.py` - Chatbot integration
- `LANGGRAPH_INTEGRATION.md` - Detailed documentation

## Status

✅ **Working**: LangGraph is operational and handling all requests  
✅ **Verified**: Logs confirm proper execution  
✅ **Stable**: No timeout or error issues  

