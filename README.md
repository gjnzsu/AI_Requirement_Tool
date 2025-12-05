# Generative AI Chatbot

This project is a simple generative AI chatbot that interacts with users and generates responses based on their input. It also includes a Jira Requirement Maturity Evaluation Service that uses LLM models to assess the maturity of requirements in Jira backlogs.

## Project Structure

```
generative-ai-chatbot
├── src
│   ├── chatbot.py          # Main entry point for the chatbot application
│   ├── services
│   │   └── jira_maturity_evaluator.py  # Jira requirement maturity evaluation service
│   ├── utils
│   │   └── helpers.py      # Utility functions for input validation and response formatting
│   └── models
│       └── model.py        # Defines the structure of the generative AI model
├── config
│   └── config.py           # Configuration for Jira and LLM settings
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
- **OpenAI**: GPT-3.5-turbo, GPT-4, GPT-4-turbo-preview
- **Google Gemini**: gemini-pro, gemini-1.5-pro, gemini-1.5-flash
- **DeepSeek**: deepseek-chat, deepseek-coder

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

## Usage

Once the chatbot is running, you can interact with it by typing your messages. The chatbot will generate responses based on its underlying AI model.

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

## Functionality

The chatbot is designed to provide engaging conversations and can be extended with additional features and improvements.