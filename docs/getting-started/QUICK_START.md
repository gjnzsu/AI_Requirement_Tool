# Quick Start Guide - Running the Evaluation Service

## Step 1: Verify Configuration

First, make sure everything is configured correctly:

```powershell
python check_setup.py
```

This will verify:
- ✅ All required packages are installed
- ✅ Configuration values are set
- ✅ Gemini API key and proxy are configured

## Step 2: Test Gemini Connection (Optional but Recommended)

Test if Gemini is working with your proxy:

```powershell
python test_gemini.py
```

This will:
- Verify API key is valid
- Test proxy connection
- Send a test request to Gemini

## Step 3: Run the Evaluation Service

Once everything is configured, run the main evaluation:

```powershell
python evaluate_jira_maturity.py
```

## What Happens During Evaluation

1. **Connects to Jira** - Fetches backlog items from your project
2. **Evaluates Each Item** - Uses Gemini Pro to analyze requirement maturity
3. **Displays Results** - Shows scores, strengths, weaknesses, and recommendations
4. **Saves Results** - Creates `maturity_evaluation_results.json` file

## Expected Output

```
Initializing LLM Provider: gemini (model: gemini-pro)...
Using proxy: http://proxy.example.com:8080
Initializing Jira Maturity Evaluator...
Fetching backlog items from project SCRUM...
Found 2 items. Evaluating maturity scores...
Evaluating 1/2: SCRUM-1
Evaluating 2/2: SCRUM-2

================================================================================
MATURITY EVALUATION RESULTS
================================================================================

Issue: SCRUM-1
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

## Troubleshooting

### If you get "Connection timeout"
- Verify proxy is set: `$env:GEMINI_PROXY`
- Test proxy connection: `python test_gemini.py`

### If you get "API key not valid"
- Check your API key: `$env:GEMINI_API_KEY`
- Verify key from: https://makersuite.google.com/app/apikey

### If you get "No backlog items found"
- Check JIRA_PROJECT_KEY is correct
- Verify project has items in "To Do" or "Backlog" status

## Viewing Results

Results are saved to: `maturity_evaluation_results.json`

You can view the JSON file or use it for further analysis.

