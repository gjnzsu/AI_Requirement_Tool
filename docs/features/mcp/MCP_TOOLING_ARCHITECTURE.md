# MCP Tooling Architecture

## Overview

The MCP (Model Context Protocol) tooling architecture allows the chatbot to execute external tools and services based on user intent. This follows a plugin-based pattern where tools can be easily added and integrated.

## Architecture Components

### 1. Base Tool Interface

**File:** `src/tools/base_tool.py`

**Class:** `BaseTool`

This is the abstract base class that defines the interface for all tools.

```python
class BaseTool(ABC):
    @abstractmethod
    def get_name(self) -> str:
        """Get the name of the tool."""
        
    @abstractmethod
    def get_description(self) -> str:
        """Get the description of what the tool does."""
        
    @abstractmethod
    def execute(self, **kwargs) -> Dict[str, Any]:
        """Execute the tool with provided arguments."""
```

**Purpose:**
- Defines the contract that all tools must implement
- Ensures consistent interface across all tools
- Enables polymorphism and tool discovery

---

### 2. Concrete Tool Implementations

#### JiraTool

**File:** `src/tools/jira_tool.py`

**Class:** `JiraTool(BaseTool)`

**Purpose:** Creates and manages Jira issues

**Methods:**
- `get_name()` → Returns `"jira_tool"`
- `get_description()` → Returns description of Jira operations
- `execute(action, **kwargs)` → Routes to specific Jira operations
- `create_issue(summary, description, priority)` → Creates a new Jira issue

**Usage:**
```python
jira_tool = JiraTool()
result = jira_tool.create_issue(
    summary="Feature X",
    description="...",
    priority="Medium"
)
```

---

#### ConfluenceTool

**File:** `src/tools/confluence_tool.py`

**Class:** `ConfluenceTool(BaseTool)`

**Purpose:** Creates and manages Confluence pages

**Methods:**
- `get_name()` → Returns `"confluence_tool"`
- `get_description()` → Returns description of Confluence operations
- `execute(action, **kwargs)` → Routes to specific Confluence operations
- `create_page(title, content, parent_id)` → Creates a new Confluence page
- `_html_to_confluence_storage(html_content)` → Converts HTML to Confluence format

**Usage:**
```python
confluence_tool = ConfluenceTool()
result = confluence_tool.create_page(
    title="Page Title",
    content="<h1>Content</h1>"
)
```

---

### 3. Tool Integration in Chatbot

**File:** `src/chatbot.py`

**Class:** `Chatbot`

**Tool Management:**

The `Chatbot` class manages tools as instance variables:

```python
class Chatbot:
    def __init__(self, ...):
        # Initialize Tools
        self.jira_tool = None
        self.confluence_tool = None
        self.jira_evaluator = None
        
        # Initialize tools during chatbot creation
        try:
            self.jira_tool = JiraTool()
            self.confluence_tool = ConfluenceTool()
        except Exception as e:
            # Handle initialization errors
```

**Tool Execution Flow:**

1. **Intent Detection** (`get_response()` method):
   ```python
   # Check for Jira creation intent
   jira_keywords = ["create the jira", "create jira", ...]
   if any(keyword in user_input_lower for keyword in jira_keywords):
       return self._handle_jira_creation(user_input)
   ```

2. **Workflow Execution** (`_handle_jira_creation()` method):
   - Step 1: Generate backlog details using LLM
   - Step 2: Create Jira issue using `JiraTool`
   - Step 3: Evaluate maturity using `JiraMaturityEvaluator`
   - Step 4: Create Confluence page using `ConfluenceTool`

---

## Architecture Diagram

```
┌─────────────────────────────────────────┐
│           Chatbot Class                 │
│  (Intent Detection & Orchestration)     │
└──────────────┬──────────────────────────┘
               │
               │ manages
               │
    ┌──────────┴──────────┐
    │                     │
    ▼                     ▼
┌──────────┐        ┌──────────────┐
│ JiraTool │        │ConfluenceTool│
└────┬─────┘        └──────┬───────┘
     │                     │
     │ inherits from       │ inherits from
     │                     │
     └──────────┬──────────┘
                │
                ▼
         ┌─────────────┐
         │  BaseTool   │
         │  (Abstract) │
         └─────────────┘
```

---

## Tool Registration

**File:** `src/tools/__init__.py`

All tools are exported from the tools package:

```python
from .base_tool import BaseTool
from .jira_tool import JiraTool
from .confluence_tool import ConfluenceTool

__all__ = ['BaseTool', 'JiraTool', 'ConfluenceTool']
```

---

## Adding New Tools

To add a new tool:

1. **Create Tool Class** (`src/tools/your_tool.py`):
   ```python
   from .base_tool import BaseTool
   
   class YourTool(BaseTool):
       def get_name(self) -> str:
           return "your_tool"
       
       def get_description(self) -> str:
           return "Description of what your tool does"
       
       def execute(self, **kwargs) -> Dict[str, Any]:
           # Implement your tool logic
           pass
   ```

2. **Register in `__init__.py`**:
   ```python
   from .your_tool import YourTool
   __all__ = [..., 'YourTool']
   ```

3. **Integrate in Chatbot**:
   ```python
   # In Chatbot.__init__()
   self.your_tool = YourTool()
   
   # In intent detection
   if "your keyword" in user_input:
       return self._handle_your_tool(user_input)
   ```

---

## Current Tool Workflow

### Jira Creation Workflow

```
User Input: "create the jira"
    ↓
Chatbot.get_response()
    ↓
Intent Detection (keyword matching)
    ↓
_handle_jira_creation()
    ↓
┌─────────────────────────────────────┐
│ Step 1: LLM generates backlog data │
└──────────────┬──────────────────────┘
               ↓
┌─────────────────────────────────────┐
│ Step 2: JiraTool.create_issue()    │
└──────────────┬──────────────────────┘
               ↓
┌─────────────────────────────────────┐
│ Step 3: JiraMaturityEvaluator      │
│         .evaluate_maturity()        │
└──────────────┬──────────────────────┘
               ↓
┌─────────────────────────────────────┐
│ Step 4: ConfluenceTool.create_page()│
└──────────────┬──────────────────────┘
               ↓
Return formatted response to user
```

---

## Key Classes Summary

| Class | File | Purpose |
|-------|------|---------|
| `BaseTool` | `src/tools/base_tool.py` | Abstract base class for all tools |
| `JiraTool` | `src/tools/jira_tool.py` | Jira issue creation and management |
| `ConfluenceTool` | `src/tools/confluence_tool.py` | Confluence page creation |
| `Chatbot` | `src/chatbot.py` | Orchestrates tool execution based on user intent |

---

## Design Patterns Used

1. **Abstract Base Class Pattern**: `BaseTool` defines the interface
2. **Strategy Pattern**: Different tools implement the same interface
3. **Factory Pattern**: Tools are instantiated and managed by `Chatbot`
4. **Template Method Pattern**: Workflow steps are defined in `_handle_jira_creation()`

---

## Configuration

Tools use configuration from `config/config.py`:

- `JiraTool` → Uses `Config.JIRA_URL`, `Config.JIRA_EMAIL`, `Config.JIRA_API_TOKEN`, `Config.JIRA_PROJECT_KEY`
- `ConfluenceTool` → Uses `Config.CONFLUENCE_URL`, `Config.CONFLUENCE_SPACE_KEY`, `Config.JIRA_EMAIL`, `Config.JIRA_API_TOKEN`

---

## Error Handling

Tools implement error handling:

- **Initialization Errors**: Caught during `Chatbot.__init__()`, tools set to `None` if initialization fails
- **Execution Errors**: Returned in result dictionary with `success: False` and `error` message
- **User Feedback**: Errors are formatted and returned to user with helpful configuration hints

