# LangGraph Agent Framework

## Overview

The chatbot now uses **LangGraph** for intelligent agent-based orchestration. Instead of keyword-based routing, the agent uses LLM-powered intent detection to intelligently route requests and orchestrate tools.

## What Changed

### Before (Keyword-Based)
- Simple keyword matching: "create jira" → triggers Jira creation
- Manual intent detection
- Fixed workflow execution

### After (LangGraph Agent)
- **LLM-powered intent detection**: Understands user intent from natural language
- **Intelligent routing**: Automatically decides which tools to use
- **State management**: Maintains conversation context across multi-step workflows
- **Flexible workflows**: Can handle complex, conditional workflows

## Architecture

### Agent Graph Structure

```
User Input
    ↓
Intent Detection (LLM-powered)
    ↓
    ├─→ Jira Creation → Evaluation → Confluence Creation
    ├─→ RAG Query → Document Retrieval → Answer Generation
    └─→ General Chat → Direct Response
```

### State Management

The agent maintains state across the workflow:
- **Messages**: Conversation history
- **Intent**: Detected user intent
- **Tool Results**: Jira, evaluation, Confluence results
- **RAG Context**: Retrieved document chunks
- **Conversation History**: Full conversation context

## Features

### 1. Intelligent Intent Detection

The agent uses LLM to detect user intent:
- **jira_creation**: User wants to create a Jira issue
- **rag_query**: User asks questions that benefit from document retrieval
- **general_chat**: Normal conversation

### 2. Multi-Step Workflows

**Jira Creation Workflow:**
1. Detect intent → "jira_creation"
2. Generate backlog details using LLM
3. Run pre-Jira quality review when enabled
4. Create Jira issue
5. Evaluate maturity
6. Create Confluence page (if configured)

### Requirement Quality Review vs Maturity Evaluation

The requirement lifecycle has two distinct quality phases:

- **Pre-Jira Quality Review** runs before Jira creation. It can apply deterministic checks such as missing acceptance criteria, and it can run an LLM-as-a-Judge review for advisory feedback on clarity, testability, scope, ambiguity, and business value.
- **Post-Jira Maturity Evaluation** runs after Jira creation. It evaluates the created Jira issue and preserves the existing maturity output shape with `overall_maturity_score`, `detailed_scores`, `strengths`, `weaknesses`, and `recommendations`.

The pre-Jira judge is advisory by default. Deterministic gate failures may block Jira creation when enabled, but low judge scores alone do not block creation in the initial implementation.

### 3. RAG Integration

When intent is "rag_query":
- Retrieves relevant document chunks
- Uses context to generate accurate answers
- Falls back to general chat if no relevant context

### 4. Tool Orchestration

The agent intelligently:
- Decides when to use tools
- Handles tool failures gracefully
- Routes based on tool availability

## Usage

### Basic Usage

The agent is enabled by default. Just use the chatbot normally:

```python
from src.chatbot import Chatbot

chatbot = Chatbot(
    provider_name="openai",
    use_agent=True  # Enabled by default
)

response = chatbot.get_response("I need to create a Jira ticket for user authentication")
```

### Disable Agent (Fallback to Keyword-Based)

```python
chatbot = Chatbot(
    use_agent=False  # Falls back to keyword-based routing
)
```

## Configuration

### LLM Provider

The agent supports:
- **OpenAI**: GPT-5.5, GPT-4o, GPT-4o-mini
- **Gemini**: gemini-pro, gemini-1.5-pro
- **DeepSeek**: deepseek-v4-flash

Set in `.env`:
```bash
LLM_PROVIDER=openai
OPENAI_API_KEY=your-key
OPENAI_MODEL=gpt-5.4
```

### Tools Configuration

Enable/disable tools:
```python
chatbot = Chatbot(
    enable_mcp_tools=True,  # Enable Jira/Confluence tools
    use_agent=True
)
```

## Agent Nodes

### 1. `intent_detection`
- Analyzes user input
- Determines intent using LLM
- Routes to appropriate workflow

### 2. `jira_creation`
- Generates backlog details from conversation
- Creates Jira issue
- Returns issue key and link

### 3. `evaluation`
- Fetches created issue
- Evaluates maturity score
- Provides recommendations

### 4. `confluence_creation`
- Formats evaluation results
- Creates Confluence page
- Links to Jira issue

### 5. `rag_query`
- Retrieves relevant documents
- Generates answer with context
- Falls back if no context found

### 6. `general_chat`
- Handles normal conversation
- Uses conversation history
- Generates contextual responses

## Benefits

✅ **Intelligent**: LLM-powered intent detection  
✅ **Flexible**: Handles natural language variations  
✅ **Robust**: Graceful error handling  
✅ **Extensible**: Easy to add new nodes/workflows  
✅ **Stateful**: Maintains context across steps  
✅ **Integrated**: Works with existing tools and RAG  

## Migration from Keyword-Based

The agent is backward compatible:
- If agent fails, falls back to keyword-based routing
- Existing workflows still work
- No breaking changes

## Troubleshooting

### Agent Not Initializing

Check:
1. LangGraph dependencies installed: `pip install -r requirements.txt`
2. LLM provider configured correctly
3. API keys are set in `.env`

### Tools Not Working

Ensure:
1. Jira/Confluence credentials configured
2. `enable_mcp_tools=True`
3. Tools initialized successfully (check startup logs)

### Intent Detection Issues

If intent detection is inaccurate:
- Use more specific prompts
- Check LLM model quality
- Consider fine-tuning intent detection prompt

## Next Steps

- Add more agent nodes (e.g., GitHub integration)
- Implement custom workflows
- Add tool calling for dynamic tool selection
- Enhance RAG integration

## See Also

- `MCP_TOOLING_ARCHITECTURE.md` - Tool architecture
- `RAG_GUIDE.md` - RAG documentation
- `README.md` - General project documentation

