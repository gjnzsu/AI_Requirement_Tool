# LangGraph Agent Framework Integration

## Overview

The chatbot now uses **LangGraph** for intelligent tool orchestration and workflow management. LangGraph provides a state-based agent framework that routes user requests to appropriate tools (Jira, RAG, General Chat) based on detected intent.

## Architecture

### Graph Structure

```
Entry Point: intent_detection
    ↓
    ├─→ jira_creation → evaluation → [confluence_creation] → END
    ├─→ rag_query → END
    └─→ general_chat → END
```

### Nodes

1. **intent_detection**: Detects user intent using keyword matching
2. **jira_creation**: Creates Jira issues with LLM-generated backlog details
3. **evaluation**: Evaluates Jira issue maturity
4. **confluence_creation**: Creates Confluence pages (optional)
5. **rag_query**: Retrieves relevant context using RAG
6. **general_chat**: Handles general conversations

### State Management

The agent uses `AgentState` to track:
- Messages (conversation history)
- User input
- Detected intent
- Tool execution results (Jira, RAG, Confluence)
- Next action

## Intent Detection

### Keyword-Based Detection

Intent detection is **keyword-based** (no LLM calls) for speed and reliability:

**Jira Creation Keywords:**
- `create jira`, `create issue`, `create ticket`
- `new jira`, `new issue`, `new ticket`
- `add jira`, `add issue`
- `make jira`, `make issue`, `make ticket`

**RAG Query Keywords:**
- `what is`, `what are`, `how to`, `how do`
- `explain`, `tell me about`
- `document`, `documentation`, `guide`
- `help with`, `information about`
- `describe`, `definition`, `meaning`, `example`

**General Chat Keywords:**
- `hello`, `hi`, `hey`
- `who are you`, `what are you`
- `how are you`, `thanks`, `thank you`
- `bye`, `goodbye`, `help`, `assist`

### Default Behavior

If no keywords match, defaults to `general_chat`.

## Verification

### Startup Verification

When the chatbot starts, you should see:
```
✓ Initialized LangGraph Agent
```

### Runtime Verification

When processing a message, you'll see logs like:

```
🔄 LangGraph: Processing input through agent graph...
🔍 LangGraph: Detecting intent for input: 'your message...'
  → Intent: general_chat (keyword match)
✓ LangGraph: Intent detected = 'general_chat'
  → Executed nodes: intent_detection → general_chat
✓ LangGraph: Response generated successfully
```

### Test Cases

**General Chat:**
```
Input: "Hello"
Expected: intent_detection → general_chat
```

**Jira Creation:**
```
Input: "Create a Jira issue for user authentication"
Expected: intent_detection → jira_creation → evaluation
```

**RAG Query:**
```
Input: "What is authentication?"
Expected: intent_detection → rag_query
```

## Configuration

### Enable/Disable LangGraph

In `src/chatbot.py`, the agent is initialized with:
```python
self.agent = ChatbotAgent(
    use_agent=True,  # Enable LangGraph
    ...
)
```

### Customize Intent Detection

Edit `src/agent/agent_graph.py`:
- Add keywords to `jira_creation_keywords`
- Add keywords to `rag_keywords`
- Add keywords to `general_chat_keywords`

## Benefits

✅ **Fast**: Keyword-based intent detection (no API calls)  
✅ **Reliable**: No timeout issues  
✅ **Extensible**: Easy to add new tools and workflows  
✅ **Observable**: Clear logging shows execution flow  
✅ **Maintainable**: State-based architecture is easy to understand  

## Troubleshooting

### LangGraph Not Working

**Check:**
1. Startup logs show: `✓ Initialized LangGraph Agent`
2. Runtime logs show: `🔄 LangGraph: Processing input...`
3. `use_agent=True` in chatbot initialization

**If not working:**
- Check for errors in startup logs
- Verify LangGraph dependencies installed: `pip install langgraph langchain`
- Check if fallback to keyword-based routing is being used

### Intent Not Detected Correctly

**Solution:**
- Add more keywords to the keyword lists
- Check if keywords match user input (case-insensitive)
- Default behavior is `general_chat` if no match

## Future Enhancements

- [ ] Add LLM-based intent detection as fallback (with timeout)
- [ ] Add more tools (Confluence, Slack, etc.)
- [ ] Add multi-step workflows
- [ ] Add tool result validation
- [ ] Add retry logic for failed tool calls

