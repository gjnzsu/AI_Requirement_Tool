# OpenAI ChatGPT Models - Complete List

## Latest Models (2024-2025)

### GPT-4 Family (Most Capable)

#### GPT-4o (Recommended - Latest)
- **Model Name**: `gpt-4o`
- **Description**: Optimized GPT-4 model, faster and more capable than GPT-4 Turbo
- **Features**: Multimodal (text, images), faster responses, better reasoning
- **Best for**: General use, complex reasoning, multimodal tasks
- **Availability**: Requires API access

#### GPT-4o-mini
- **Model Name**: `gpt-4o-mini`
- **Description**: Smaller, faster, and more cost-effective version of GPT-4o
- **Best for**: Cost-effective general use with GPT-4o capabilities
- **Availability**: Requires API access

#### GPT-4.1
- **Model Name**: `gpt-4.1`
- **Description**: Enhanced GPT-4 model with improved coding capabilities and instruction following
- **Features**: Better web development capabilities, precise instruction following
- **Best for**: Coding tasks, technical development work
- **Availability**: Requires API access

#### GPT-4 Turbo
- **Model Name**: `gpt-4-turbo` or `gpt-4-0125-preview`
- **Description**: Enhanced GPT-4 with improved performance and larger context window
- **Features**: 128k context window, improved instruction following
- **Best for**: Complex tasks requiring long context
- **Availability**: Requires API access

#### GPT-4
- **Model Name**: `gpt-4`
- **Description**: Original GPT-4 model
- **Best for**: Complex reasoning, advanced tasks
- **Availability**: Requires API access (may be deprecated in favor of GPT-4 Turbo)

### GPT-3.5 Family (Cost-Effective)

#### GPT-3.5 Turbo (Recommended for Budget)
- **Model Name**: `gpt-3.5-turbo`
- **Description**: Fast, cost-effective model
- **Features**: Good performance at lower cost
- **Best for**: General conversations, simple tasks, high-volume usage
- **Availability**: Widely available

#### GPT-3.5 Turbo (Latest)
- **Model Name**: `gpt-3.5-turbo-0125` (or latest version)
- **Description**: Latest iteration of GPT-3.5 Turbo
- **Best for**: Same as gpt-3.5-turbo but with latest improvements

### Legacy Models

#### GPT-3.5 Turbo (Older Versions)
- `gpt-3.5-turbo-1106`
- `gpt-3.5-turbo-16k` (larger context window)

#### GPT-4 (Older Versions)
- `gpt-4-0613`
- `gpt-4-32k` (larger context window)

## Model Comparison

| Model | Speed | Capability | Cost | Context Window | Best Use Case |
|-------|-------|------------|------|----------------|---------------|
| `gpt-4o` | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | $$$ | 128k | Best overall performance |
| `gpt-4o-mini` | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | $$ | 128k | Cost-effective GPT-4o |
| `gpt-4.1` | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | $$$$ | 128k | Coding, technical tasks |
| `gpt-4-turbo` | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | $$$$ | 128k | Complex, long-context tasks |
| `gpt-4` | ⭐⭐ | ⭐⭐⭐⭐⭐ | $$$$ | 8k | Complex reasoning |
| `gpt-3.5-turbo` | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | $ | 16k | General use, high volume |

## Recommended Models by Use Case

### For General Chatbot Use
- **Best**: `gpt-4o` or `gpt-4o-mini`
- **Budget**: `gpt-3.5-turbo`

### For Complex Reasoning
- **Best**: `gpt-4o` or `gpt-4-turbo`
- **Budget**: `gpt-3.5-turbo`

### For Coding/Technical Tasks
- **Best**: `gpt-4.1` or `gpt-4o`
- **Budget**: `gpt-3.5-turbo`

### For High-Volume Applications
- **Best**: `gpt-3.5-turbo` or `gpt-4o-mini`

### For Long Context (Large Documents)
- **Best**: `gpt-4-turbo` or `gpt-4o` (128k context)

## How to Use in This Project

### Update .env file:
```env
LLM_PROVIDER=openai
OPENAI_API_KEY=your-api-key-here
OPENAI_MODEL=gpt-4o
```

### Or set environment variable:
```powershell
$env:OPENAI_MODEL="gpt-4o"
```

### Or specify in code:
```python
chatbot = Chatbot(
    provider_name='openai',
    # Model will be read from Config.OPENAI_MODEL
)
```

## Model Availability Notes

⚠️ **Important**: 
- Model availability depends on your OpenAI API access level
- Some models require specific API access or subscription tiers
- Model names may change - always check OpenAI's documentation for the latest
- Newer models may have different pricing

## Checking Available Models

You can check which models are available to your API key by visiting:
- OpenAI API Documentation: https://platform.openai.com/docs/models
- OpenAI Models Page: https://platform.openai.com/docs/models/overview

## Getting the Latest Model Names

To get the most up-to-date model list, you can:

1. **Check OpenAI Documentation**: https://platform.openai.com/docs/models
2. **Use OpenAI API**: List models endpoint
3. **Check OpenAI Status Page**: For model availability

## Example: Listing Available Models via API

```python
from openai import OpenAI

client = OpenAI(api_key="your-api-key")
models = client.models.list()

for model in models.data:
    if model.id.startswith('gpt'):
        print(model.id)
```

## Notes

- Model names are case-sensitive
- Always use the exact model name as shown in OpenAI's documentation
- Some models may be deprecated over time
- New models are added regularly - check OpenAI's announcements

