# Switching to OpenAI ChatGPT

## Quick Setup

### Option 1: Update .env file (Recommended)

Edit your `.env` file in the project root and set:

```env
# Set provider to OpenAI
LLM_PROVIDER=openai

# Set your OpenAI API key
OPENAI_API_KEY=your-openai-api-key-here

# Optional: defaults to gpt-5.5 when omitted
OPENAI_MODEL=gpt-5.5
```

### Recommended OpenAI Models

- `gpt-5.5` - Current OpenAI target for this project; best for complex reasoning, coding, and agentic work
- `gpt-4o-mini` - Lower-cost fallback if your API key cannot access `gpt-5.5`
- `gpt-4o` - Older high-capability fallback for general chat and tool workflows

See `OPENAI_MODELS.md` for details and availability notes.

### Option 2: Set Environment Variables (Windows PowerShell)

```powershell
$env:LLM_PROVIDER="openai"
$env:OPENAI_API_KEY="your-openai-api-key-here"
$env:OPENAI_MODEL="gpt-5.5"
```

### Option 3: Set Environment Variables (Windows CMD)

```cmd
set LLM_PROVIDER=openai
set OPENAI_API_KEY=your-openai-api-key-here
set OPENAI_MODEL=gpt-5.5
```

## Getting Your OpenAI API Key

1. Go to https://platform.openai.com/api-keys
2. Sign in or create an account
3. Click "Create new secret key"
4. Copy the key
5. Paste it into your `.env` file or environment variable

## Verify Configuration

After setting up, run the chatbot:

```bash
python src/chatbot.py
```

You should see:

```text
Initialized LLM provider: openai (gpt-5.5)
```

## Example .env File

```env
# LLM Provider Configuration
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-your-actual-api-key-here
OPENAI_MODEL=gpt-5.5

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
- Try a fallback model such as `gpt-4o-mini` if `gpt-5.5` is unavailable for your key

### Model Not Found

- Make sure your API key has access to `gpt-5.5`
- Try `gpt-4o-mini` as the lower-cost compatibility fallback
- Check OpenAI's model availability page
