# OpenAI ChatGPT Models

This project currently targets `gpt-5.5` for the OpenAI provider. The production default provider can still be DeepSeek, but whenever users select OpenAI, `OPENAI_MODEL=gpt-5.5` is the documented default.

## Current Project Default

### GPT-5.5

- **Model Name**: `gpt-5.5`
- **Description**: OpenAI frontier model for complex reasoning, coding, professional work, and agentic tool use
- **Best for**: Requirement analysis, SDLC drafting, Jira/Confluence workflow reasoning, coding help, and complex chat turns
- **Pricing used by this app**: $5 / 1M input tokens and $30 / 1M output tokens
- **Availability**: Requires API access for the key in use

## Compatibility Fallbacks

Use these only if your OpenAI API key cannot call `gpt-5.5`.

### GPT-4o-mini

- **Model Name**: `gpt-4o-mini`
- **Description**: Lower-cost OpenAI fallback for general chat and simpler workflows
- **Best for**: Cost-sensitive testing and high-volume lightweight use

### GPT-4o

- **Model Name**: `gpt-4o`
- **Description**: Older high-capability OpenAI model
- **Best for**: General chat and tool workflows when `gpt-5.5` is not available

## Model Comparison

| Model | Relative Cost | Capability | Best Use Case |
|---|---:|---|---|
| `gpt-5.5` | Higher | Highest | Complex reasoning, coding, agentic workflows |
| `gpt-4o` | Medium | High | General-purpose fallback |
| `gpt-4o-mini` | Lower | Medium | Cost-sensitive fallback |

## How to Use in This Project

### Update .env file

```env
LLM_PROVIDER=openai
OPENAI_API_KEY=your-api-key-here
OPENAI_MODEL=gpt-5.5
```

### Or set environment variable

```powershell
$env:OPENAI_MODEL="gpt-5.5"
```

### Or specify in code

```python
chatbot = Chatbot(
    provider_name="openai",
    # Model will be read from Config.OPENAI_MODEL
)
```

## Model Availability Notes

- Model availability depends on your OpenAI API access level.
- If `gpt-5.5` is unavailable, use `gpt-4o-mini` as the compatibility fallback.
- Model names are case-sensitive.
- Provider pricing can change; update `src/llm/cost_tracker.py` when pricing changes.

## Checking Available Models

You can check current OpenAI model availability here:

- OpenAI API Documentation: https://platform.openai.com/docs/models
- OpenAI Models Page: https://platform.openai.com/docs/models/overview

## Example: Listing Available Models via API

```python
from openai import OpenAI

client = OpenAI(api_key="your-api-key")
models = client.models.list()

for model in models.data:
    if model.id.startswith("gpt"):
        print(model.id)
```
