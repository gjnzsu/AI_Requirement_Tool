# GitHub Authentication Setup Guide

## Step 1: Create a Personal Access Token

GitHub no longer accepts passwords for Git operations. You need to create a Personal Access Token.

1. **Go to GitHub Token Settings:**
   - Open: https://github.com/settings/tokens
   - Or: GitHub → Your Profile Picture → Settings → Developer settings → Personal access tokens → Tokens (classic)

2. **Generate New Token:**
   - Click "Generate new token" → "Generate new token (classic)"
   - Give it a name: `AI_Requirement_Tool_Access`
   - Set expiration: Choose your preference (90 days, 1 year, or no expiration)
   - Select scopes: Check `repo` (Full control of private repositories)
   - Click "Generate token" at the bottom

3. **Copy the Token:**
   - ⚠️ **IMPORTANT:** Copy the token immediately - you won't be able to see it again!
   - It will look like: `ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`

## Step 2: Push Your Code

After creating the token, run:

```powershell
cd c:\SourceCode\GenAIChatbot\generative-ai-chatbot
git push -u origin main
```

When prompted:
- **Username:** `30156758@qq.com` (or your GitHub username)
- **Password:** Paste your Personal Access Token (NOT your GitHub password)

## Alternative: Store Credentials Securely

To avoid entering credentials every time, you can store them:

```powershell
# This will prompt you once and save credentials
git config --global credential.helper wincred
git push -u origin main
```

Windows Credential Manager will store your token securely.

## Troubleshooting

If you get authentication errors:
1. Make sure you're using the token, not your password
2. Check that the token has `repo` scope
3. Verify your GitHub username (it might not be your email)

