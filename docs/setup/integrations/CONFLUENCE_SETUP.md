# Confluence Configuration Guide

## Overview

The chatbot can automatically create Confluence pages for Jira requirements after evaluation. This requires Confluence configuration in addition to Jira settings.

## Configuration

### Step 1: Add to .env File

Add the following to your `.env` file:

```env
# Confluence Configuration
CONFLUENCE_URL=https://yourcompany.atlassian.net/wiki
CONFLUENCE_SPACE_KEY=YOUR_SPACE_KEY
```

**Note:** Confluence uses the same credentials as Jira (same Atlassian instance):
- `JIRA_EMAIL` (same email for Confluence)
- `JIRA_API_TOKEN` (same API token for Confluence)

### Step 2: Find Your Confluence Space Key

1. Go to your Confluence instance
2. Navigate to the space where you want pages created
3. Look at the URL: `https://yourcompany.atlassian.net/wiki/spaces/SPACE_KEY/...`
4. The `SPACE_KEY` is the part after `/spaces/`

**Example:**
- URL: `https://company.atlassian.net/wiki/spaces/DEV/overview`
- Space Key: `DEV`

### Step 3: Verify Configuration

After setting the environment variables, restart the chatbot server:

```bash
python app.py
```

You should see:
```
✓ Initialized Confluence Tool
```

If you see a warning, check that:
- `CONFLUENCE_URL` is set correctly (usually ends with `/wiki`)
- `CONFLUENCE_SPACE_KEY` matches an existing space in your Confluence instance
- Your API token has permissions to create pages in that space

## Workflow

When you create a Jira issue using "create the jira", the system will:

1. ✅ Create Jira issue
2. ✅ Evaluate maturity
3. ✅ Create Confluence page (if configured)

## Troubleshooting

### "CONFLUENCE_URL is not configured"

**Solution:** Add `CONFLUENCE_URL` to your `.env` file:
```env
CONFLUENCE_URL=https://yourcompany.atlassian.net/wiki
```

### "CONFLUENCE_SPACE_KEY is not configured"

**Solution:** Add `CONFLUENCE_SPACE_KEY` to your `.env` file:
```env
CONFLUENCE_SPACE_KEY=YOUR_SPACE_KEY
```

### "HTTP 403: Forbidden"

**Possible causes:**
- API token doesn't have permission to create pages
- Space key is incorrect
- User doesn't have access to the space

**Solution:**
1. Verify the space key is correct
2. Check API token permissions
3. Ensure your user has "Create" permission in the Confluence space

### "HTTP 404: Not Found"

**Possible causes:**
- Confluence URL is incorrect
- Space doesn't exist

**Solution:**
1. Verify `CONFLUENCE_URL` ends with `/wiki`
2. Check that the space key exists in your Confluence instance

### Confluence Page Not Created (No Error)

If Jira is created but Confluence page is not, check:
1. Is Confluence Tool initialized? (Look for "✓ Initialized Confluence Tool" in startup)
2. Check the chatbot response for any warnings about Confluence
3. Review server logs for error messages

## Example .env File

```env
# Jira Configuration
JIRA_URL=https://yourcompany.atlassian.net
JIRA_EMAIL=your-email@example.com
JIRA_API_TOKEN=your-api-token
JIRA_PROJECT_KEY=PROJ

# Confluence Configuration
CONFLUENCE_URL=https://yourcompany.atlassian.net/wiki
CONFLUENCE_SPACE_KEY=DEV

# LLM Configuration
LLM_PROVIDER=openai
OPENAI_API_KEY=your-openai-api-key
OPENAI_MODEL=gpt-4.1
```

## API Token Permissions

Your Atlassian API token needs:
- ✅ Read access to Jira
- ✅ Create access to Jira issues
- ✅ Read access to Confluence
- ✅ Create access to Confluence pages in the specified space

## Getting API Token

1. Go to https://id.atlassian.com/manage-profile/security/api-tokens
2. Click "Create API token"
3. Copy the token
4. Use the same token for both Jira and Confluence (same Atlassian instance)

