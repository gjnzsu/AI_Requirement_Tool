# Switching to OpenAI ChatGPT

## Quick Setup

### Option 1: Update .env file (Recommended)

Edit your `.env` file in the project root and set:

```env
# Set provider to OpenAI
LLM_PROVIDER=openai

# Set your OpenAI API key
OPENAI_API_KEY=your-openai-api-key-here

# Choose your model (optional, defaults to gpt-3.5-turbo)
OPENAI_MODEL=gpt-3.5-turbo
```

### Available OpenAI Models (Latest)

**Recommended:**
- `gpt-4o` - Latest optimized GPT-4, fastest and most capable (⭐ Recommended)
- `gpt-4.1` - Enhanced GPT-4 with improved coding capabilities (⭐ Great for coding)
- `gpt-4o-mini` - Cost-effective version of GPT-4o
- `gpt-3.5-turbo` - Fast and cost-effective (good for high volume)

**Other Options:**
- `gpt-4-turbo` - Enhanced GPT-4 with 128k context window
- `gpt-4` - Original GPT-4 (may be deprecated)

See `OPENAI_MODELS.md` for complete list and details.

### Option 2: Set Environment Variables (Windows PowerShell)

```powershell
$env:LLM_PROVIDER="openai"
$env:OPENAI_API_KEY="your-openai-api-key-here"
$env:OPENAI_MODEL="gpt-3.5-turbo"
```

### Option 3: Set Environment Variables (Windows CMD)

```cmd
set LLM_PROVIDER=openai
set OPENAI_API_KEY=your-openai-api-key-here
set OPENAI_MODEL=gpt-3.5-turbo
```

## Getting Your OpenAI API Key

1. Go to https://platform.openai.com/api-keys
2. Sign in or create an account
3. Click "Create new secret key"
4. Copy the key (you won't be able to see it again!)
5. Paste it into your `.env` file or environment variable

## Verify Configuration

After setting up, run the chatbot:

```bash
python src/chatbot.py
```

You should see:
```
✓ Initialized LLM provider: openai (gpt-3.5-turbo)
```

## Example .env File

Here's a complete example `.env` file for OpenAI:

```env
# LLM Provider Configuration
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-your-actual-api-key-here
OPENAI_MODEL=gpt-3.5-turbo

# Optional: Keep other provider keys if you want fallback
# GEMINI_API_KEY=your-gemini-key
# DEEPSEEK_API_KEY=your-deepseek-key
```

## Troubleshooting

### "No API key found for provider 'openai'"
- Make sure `OPENAI_API_KEY` is set in your `.env` file
- Check that the `.env` file is in the project root directory
- Verify the API key doesn't have extra spaces or quotes

### "Failed to initialize LLM provider"
- Verify your API key is valid
- Check your internet connection
- Ensure you have credits/quota in your OpenAI account
- Try a different model name if the current one isn't available

### Model Not Found
- Make sure you have access to the model (some models require API access)
- Try `gpt-3.5-turbo` first as it's widely available
- Check OpenAI's model availability page

