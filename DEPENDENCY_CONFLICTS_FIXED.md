# Dependency Conflicts - Fixed

## Issues Identified

### 1. Protobuf Version Conflict

**Problem:**
- `mem0ai>=1.0.0` requires `protobuf>=5.29.0,<6.0.0`
- Google packages (`googleapis-common-protos`, `google-api-core`, `proto-plus`) require `protobuf<5.0.0`
- These requirements are incompatible

**Solution:**
- Made `mem0ai` optional (commented out in requirements.txt)
- Pinned `protobuf>=3.19.5,<5.0.0` to satisfy Google packages
- mem0ai can be installed separately if needed (with `--no-deps` flag)

### 2. google-ai-generativelanguage Version Conflict

**Problem:**
- `langchain-google-genai 3.2.0` requires `google-ai-generativelanguage>=0.9.0,<1.0.0`
- But version `0.6.15` was installed

**Solution:**
- Added explicit requirement: `google-ai-generativelanguage>=0.9.0,<1.0.0`
- Updated `langchain-google-genai` constraint to `>=1.0.0,<3.0.0` to allow newer versions
- Install protobuf BEFORE Google packages to ensure compatibility

## Changes Made

### requirements.txt

1. **Added protobuf constraint:**
   ```txt
   protobuf>=3.19.5,<5.0.0
   ```

2. **Added google-ai-generativelanguage:**
   ```txt
   google-ai-generativelanguage>=0.9.0,<1.0.0
   ```

3. **Updated langchain-google-genai:**
   ```txt
   langchain-google-genai>=1.0.0,<3.0.0
   ```

4. **Commented out mem0ai:**
   ```txt
   # mem0ai>=1.0.0,<2.0.0  # Commented out due to protobuf conflicts
   ```

### Installation Scripts

Updated `install_requirements.ps1` and `install_requirements.sh` to:
1. Install protobuf BEFORE Google packages
2. Install Google packages in correct order
3. Skip mem0ai installation (with note)

## Installation Order (Critical)

The installation order matters! Follow this sequence:

1. **protobuf** (must be first)
2. **Google packages** (google-generativeai, google-ai-generativelanguage)
3. **LangChain packages** (langchain-google-genai)
4. **Other dependencies**

## Installing mem0ai (Optional)

If you need mem0ai despite the conflicts:

```bash
# Option 1: Install without dependencies (you'll need to resolve conflicts manually)
pip install mem0ai --no-deps

# Option 2: Use a separate environment for mem0ai features
# (Not recommended for production)
```

**Note:** mem0ai is optional - the chatbot works fine without it using the built-in MemoryManager.

## Verification

After installation, verify no conflicts:

```bash
pip check
```

You should see no dependency conflicts (or only mem0ai-related ones if you installed it separately).

## Quick Fix Command

If you've already installed packages with conflicts:

```powershell
# Fix protobuf version
pip install "protobuf>=3.19.5,<5.0.0" --force-reinstall

# Fix google-ai-generativelanguage
pip install "google-ai-generativelanguage>=0.9.0,<1.0.0" --upgrade

# Reinstall langchain-google-genai
pip install "langchain-google-genai>=1.0.0,<3.0.0" --force-reinstall
```

## Testing

Run the installation script:

```powershell
.\install_requirements.ps1
```

Then verify:

```bash
pip check
python test_startup_simple.py
```

All dependency conflicts should be resolved!
