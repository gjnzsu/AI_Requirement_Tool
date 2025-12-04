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

1. **Set Environment Variables** (recommended):
   ```bash
   export JIRA_URL="https://yourcompany.atlassian.net"
   export JIRA_EMAIL="your-email@example.com"
   export JIRA_API_TOKEN="your-jira-api-token"
   export JIRA_PROJECT_KEY="PROJ"
   export OPENAI_API_KEY="your-openai-api-key"
   export OPENAI_MODEL="gpt-3.5-turbo"  # Optional: defaults to gpt-3.5-turbo
   export MAX_BACKLOG_ITEMS="50"
   ```

   **Note:** The default model is `gpt-3.5-turbo` which is more accessible. If you have access to GPT-4, you can set `OPENAI_MODEL="gpt-4"` for potentially better results.

   Or on Windows PowerShell:
   ```powershell
   $env:JIRA_URL="https://yourcompany.atlassian.net"
   $env:JIRA_EMAIL="your-email@example.com"
   $env:JIRA_API_TOKEN="your-jira-api-token"
   $env:JIRA_PROJECT_KEY="PROJ"
   $env:OPENAI_API_KEY="your-openai-api-key"
   $env:OPENAI_MODEL="gpt-3.5-turbo"  # Optional: defaults to gpt-3.5-turbo
   ```

2. **Or Update config/config.py** directly with your credentials

3. **Or create a `.env` file** in the project root (automatically loaded):
   ```
   JIRA_URL=https://yourcompany.atlassian.net
   JIRA_EMAIL=your-email@example.com
   JIRA_API_TOKEN=your-jira-api-token
   JIRA_PROJECT_KEY=PROJ
   OPENAI_API_KEY=your-openai-api-key
   OPENAI_MODEL=gpt-3.5-turbo
   ```

### Getting API Credentials

#### Jira API Token
1. Go to https://id.atlassian.com/manage-profile/security/api-tokens
2. Click "Create API token"
3. Copy the generated token

#### OpenAI API Key
1. Go to https://platform.openai.com/api-keys
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

## Functionality

The chatbot is designed to provide engaging conversations and can be extended with additional features and improvements.