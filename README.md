# Generative AI Chatbot

This project is a simple generative AI chatbot that interacts with users and generates responses based on their input. It also includes a Jira Requirement Maturity Evaluation Service that uses LLM models to assess the maturity of requirements in Jira backlogs.

## Project Structure

```
generative-ai-chatbot
├── src
│   ├── chatbot.py          # Enhanced LLM-powered chatbot with conversation memory
│   ├── llm/                # Multi-provider LLM infrastructure
│   │   ├── base_provider.py
│   │   ├── openai_provider.py
│   │   ├── gemini_provider.py
│   │   ├── deepseek_provider.py
│   │   └── router.py
│   ├── services
│   │   └── jira_maturity_evaluator.py  # Jira requirement maturity evaluation service
│   ├── utils
│   │   └── helpers.py      # Utility functions for input validation and response formatting
│   └── models
│       └── model.py        # Defines the structure of the generative AI model
├── web/                    # Web UI frontend
│   ├── templates/
│   │   └── index.html      # Main HTML template
│   └── static/
│       ├── css/
│       │   └── style.css   # Stylesheet
│       └── js/
│           └── app.js      # JavaScript for interactions
├── config
│   └── config.py           # Configuration for Jira and LLM settings
├── app.py                  # Flask web server for chatbot UI
├── evaluate_jira_maturity.py  # Main script to run maturity evaluation
├── requirements.txt         # Lists dependencies required for the project
├── .gitignore               # Specifies files and directories to be ignored by Git
└── README.md                # Documentation for the project
```

## Setup Instructions

1. Clone the repository:
   ```
   git clone <repository-url>
   cd generative-ai-chatbot
   ```

2. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Run the chatbot:
   ```
   python src/chatbot.py
   ```

## Chatbot Web UI

### Overview

The project includes a modern, beautiful web-based chatbot interface that provides an intuitive way to interact with the AI chatbot. The UI features a clean design with a sidebar for conversation management and a main chat area for messaging.

### UI Design

The web interface features:

- **Left Sidebar**:
  - Brand logo "CHAT A.I+"
  - "New chat" button for creating new conversations
  - Search functionality to find conversations
  - Conversation history list with titles
  - Settings button
  - User profile section (default: Raymond Gao)

- **Main Chat Area**:
  - Welcome message on first load
  - Chat messages with user and assistant avatars
  - Message actions (copy, regenerate)
  - Input field with send button
  - Smooth scrolling and animations

- **Right Sidebar**:
  - Upgrade to Pro prompt

### Features

✅ **Conversation Management**
- Create new conversations
- View conversation history
- Search conversations by title
- Edit conversation titles
- Delete individual conversations
- Clear all conversations

✅ **Chat Features**
- Real-time messaging with AI
- Conversation context maintained across messages
- Copy message functionality
- Regenerate responses
- Loading indicators during AI processing
- Smooth animations and transitions

✅ **Multi-Provider Support**
- Works with OpenAI (GPT-3.5, GPT-4, GPT-4o, GPT-4.1)
- Supports Google Gemini
- Supports DeepSeek
- Automatic fallback to backup providers

✅ **Modern Design**
- Clean, professional interface
- Purple theme (#8b5cf6)
- Responsive layout
- Smooth animations
- User-friendly interactions

### Running the Web UI

1. **Start the Flask server**:
   ```bash
   python app.py
   ```

2. **Open your browser** and navigate to:
   ```
   http://localhost:5000
   ```

3. **Start chatting**:
   - Click "+ New chat" to create a conversation
   - Type your message and press Enter or click send
   - View conversation history in the sidebar
   - Use search to find specific conversations

### Web UI API Endpoints

The Flask backend provides REST API endpoints:

- `POST /api/chat` - Send a message and get AI response
- `GET /api/conversations` - Get list of all conversations
- `GET /api/conversations/<id>` - Get a specific conversation
- `DELETE /api/conversations/<id>` - Delete a conversation
- `DELETE /api/conversations` - Clear all conversations
- `POST /api/new-chat` - Create a new chat
- `PUT /api/conversations/<id>/title` - Update conversation title

For detailed API documentation, see `WEB_UI_README.md`.

### Command Line vs Web UI

**Command Line Interface** (`python src/chatbot.py`):
- Simple, text-based interface
- Quick interactions
- Good for scripts and automation
- Supports `/clear` and `/history` commands

**Web UI** (`python app.py`):
- Modern, visual interface
- Conversation management
- Better for extended conversations
- Search and organize conversations
- User-friendly experience

## Jira Requirement Maturity Evaluation Service

### Overview

The Jira Requirement Maturity Evaluation Service uses LLM models (OpenAI GPT-4) to evaluate the maturity of requirements in your Jira backlog. It assesses requirements based on multiple criteria and provides detailed scores, strengths, weaknesses, and recommendations.

### Features

- **Automated Backlog Analysis**: Fetches backlog items from Jira automatically
- **Multi-Criteria Evaluation**: Evaluates requirements based on 8 key criteria:
  - Description completeness
  - Acceptance criteria
  - Dependencies identification
  - Business value articulation
  - Technical feasibility assessment
  - User story structure
  - Estimation readiness
  - Priority clarity
- **Detailed Scoring**: Provides overall maturity score (0-100) and individual criterion scores
- **Actionable Insights**: Generates strengths, weaknesses, and recommendations for each requirement
- **Jira Integration**: Optionally updates Jira issues with maturity scores

### Configuration

#### Multi-Provider LLM Support

The service supports multiple LLM providers through a flexible router pattern:
- **OpenAI**: GPT-3.5-turbo, GPT-4, GPT-4-turbo, GPT-4o, GPT-4o-mini, GPT-4.1
- **Google Gemini**: gemini-pro, gemini-1.5-pro, gemini-1.5-flash
- **DeepSeek**: deepseek-chat, deepseek-coder

See `OPENAI_MODELS.md` for a complete list of available OpenAI models.

#### Environment Variables

1. **Set Environment Variables** (recommended):
   ```bash
   # Jira Configuration
   export JIRA_URL="https://yourcompany.atlassian.net"
   export JIRA_EMAIL="your-email@example.com"
   export JIRA_API_TOKEN="your-jira-api-token"
   export JIRA_PROJECT_KEY="PROJ"
   
   # LLM Provider Selection
   export LLM_PROVIDER="openai"  # Options: 'openai', 'gemini', 'deepseek'
   
   # Provider-specific API Keys (set the one for your chosen provider)
   export OPENAI_API_KEY="your-openai-api-key"
   export GEMINI_API_KEY="your-gemini-api-key"
   export DEEPSEEK_API_KEY="your-deepseek-api-key"
   
   # Provider-specific Models (optional, defaults shown)
   export OPENAI_MODEL="gpt-3.5-turbo"
   export GEMINI_MODEL="gemini-pro"
   export DEEPSEEK_MODEL="deepseek-chat"
   
   export MAX_BACKLOG_ITEMS="50"
   ```

   Or on Windows PowerShell:
   ```powershell
   $env:LLM_PROVIDER="openai"
   $env:OPENAI_API_KEY="your-openai-api-key"
   $env:OPENAI_MODEL="gpt-3.5-turbo"
   # ... other variables
   ```

2. **Or Update config/config.py** directly with your credentials

3. **Or create a `.env` file** in the project root (automatically loaded):
   ```
   LLM_PROVIDER=openai
   OPENAI_API_KEY=your-openai-api-key
   OPENAI_MODEL=gpt-3.5-turbo
   # ... other variables
   ```

### Getting API Credentials

#### Jira API Token
1. Go to https://id.atlassian.com/manage-profile/security/api-tokens
2. Click "Create API token"
3. Copy the generated token

#### LLM Provider API Keys

**OpenAI:**
1. Go to https://platform.openai.com/api-keys
2. Create a new API key
3. Copy the key (keep it secure!)

**Google Gemini:**
1. Go to https://makersuite.google.com/app/apikey
2. Create a new API key
3. Copy the key (keep it secure!)

**DeepSeek:**
1. Go to https://platform.deepseek.com/api_keys
2. Create a new API key
3. Copy the key (keep it secure!)

### Usage

Run the maturity evaluation service:
```bash
python evaluate_jira_maturity.py
```

The service will:
1. Connect to your Jira instance
2. Fetch backlog items from the specified project
3. Evaluate each item using the LLM model
4. Display results in the console
5. Save results to `maturity_evaluation_results.json`

### Output Format

The service generates a JSON file with evaluation results:
```json
{
  "issue_key": "PROJ-123",
  "overall_maturity_score": 75.5,
  "detailed_scores": {
    "description_completeness": 80,
    "acceptance_criteria": 70,
    ...
  },
  "strengths": ["Clear business value", "Well-defined acceptance criteria"],
  "weaknesses": ["Missing dependencies", "Incomplete user story format"],
  "recommendations": ["Add dependency mapping", "Refine user story structure"]
}
```

### Optional: Update Jira with Scores

To automatically update Jira issues with maturity scores, you need to:
1. Create a custom number field in Jira for storing maturity scores
2. Get the custom field ID (e.g., `customfield_12345`)
3. Set the environment variable: `JIRA_MATURITY_SCORE_FIELD=customfield_12345`

### Example Output

```
MATURITY EVALUATION RESULTS
================================================================================

Issue: PROJ-123
Overall Maturity Score: 75.5/100

Detailed Scores:
  - Description Completeness: 80/100
  - Acceptance Criteria: 70/100
  ...

Strengths:
  + Clear business value articulation
  + Well-structured user story

Weaknesses:
  - Missing dependency information
  - Incomplete acceptance criteria

Recommendations:
  → Add explicit dependency mapping
  → Refine acceptance criteria with measurable outcomes
```

## Chatbot Usage

### Command Line Interface

Run the chatbot in command line mode:
```bash
python src/chatbot.py
```

**Features:**
- Interactive conversation
- Conversation history (last 10 turns)
- Commands: `/clear`, `/history`
- Multi-provider LLM support
- Automatic fallback to backup providers

**Example Session:**
```
You: What is Python?
Chatbot: Python is a high-level programming language...

You: /history
Chatbot: Conversation has 1 turn(s) in history.

You: bye
Chatbot: Goodbye! It was great chatting with you.
```

### Web Interface

Run the web UI:
```bash
python app.py
```

Then open `http://localhost:5000` in your browser.

**Features:**
- Modern web interface
- Conversation management
- Search functionality
- Message copy/regenerate
- Visual conversation history

See `CHATBOT_USAGE.md` for detailed usage instructions.

## Multi-Provider LLM Architecture

The service uses a flexible router pattern to support multiple LLM providers:

### Architecture Overview

```
┌─────────────────────┐
│ Jira Evaluator      │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│   LLM Router        │
└──────────┬──────────┘
           │
    ┌──────┴──────┬──────────┐
    ▼             ▼           ▼
┌─────────┐  ┌─────────┐  ┌─────────┐
│ OpenAI  │  │ Gemini  │  │DeepSeek │
└─────────┘  └─────────┘  └─────────┘
```

### Adding New Providers

To add a new LLM provider:

1. Create a new provider class inheriting from `LLMProvider`:
   ```python
   from src.llm.base_provider import LLMProvider
   
   class MyProvider(LLMProvider):
       def generate_response(self, system_prompt, user_prompt, 
                            temperature=0.3, json_mode=False):
           # Implement your provider's API call
           pass
       
       def supports_json_mode(self):
           return True  # or False
       
       def get_provider_name(self):
           return "myprovider"
   ```

2. Register it with the router:
   ```python
   from src.llm import LLMRouter
   LLMRouter.register_provider("myprovider", MyProvider)
   ```

3. Update configuration to support the new provider's API key.

See `examples/multi_provider_example.py` for usage examples.

## Documentation

- **CHATBOT_USAGE.md** - Detailed guide for using the chatbot
- **WEB_UI_README.md** - Web UI setup and API documentation
- **OPENAI_MODELS.md** - Complete list of OpenAI models and recommendations
- **SWITCH_TO_OPENAI.md** - Guide for switching to OpenAI provider

## Summary

This project provides:

1. **Enhanced LLM Chatbot** - Multi-provider support with conversation memory
2. **Modern Web UI** - Beautiful, user-friendly interface for chat interactions
3. **Jira Integration** - Requirement maturity evaluation service
4. **Flexible Architecture** - Easy to add new LLM providers
5. **Comprehensive Documentation** - Guides for all features

The chatbot can be used via command line or web interface, supporting multiple LLM providers (OpenAI, Gemini, DeepSeek) with automatic fallback capabilities. The web UI provides an intuitive way to manage conversations and interact with the AI, while the command line interface offers quick access for scripts and automation.