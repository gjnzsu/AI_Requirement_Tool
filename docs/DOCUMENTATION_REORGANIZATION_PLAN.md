# Documentation Reorganization Plan

## Current State
- **48 markdown files** in the root directory
- Documentation scattered across root folder
- Hard to find specific documentation
- No clear organization structure

## Proposed Structure

```
docs/
├── README.md                          # Documentation index (already created)
├── getting-started/
│   ├── QUICK_START.md
│   ├── SETUP_ENV.md
│   └── GITHUB_SETUP.md
├── features/
│   ├── agent/
│   │   ├── AGENT_FRAMEWORK.md
│   │   ├── LANGGRAPH_INTEGRATION.md
│   │   ├── README_LANGGRAPH.md
│   │   ├── INSTALL_AGENT.md
│   │   └── TEST_AGENT.md
│   ├── mcp/
│   │   ├── mcp_integration_guide.md (already here)
│   │   ├── mcp_integration_checklist.md (already here)
│   │   ├── MCP_INTEGRATION_SUMMARY.md
│   │   ├── MCP_TOOLING_ARCHITECTURE.md
│   │   ├── JIRA_MCP_INTEGRATION.md
│   │   ├── CUSTOM_JIRA_MCP_SERVER.md
│   │   ├── MCP_SETUP.md
│   │   ├── MCP_SERVER_SETUP.md
│   │   ├── MCP_SERVER_CONFIG.md
│   │   ├── QUICK_START_MCP.md
│   │   └── START_JIRA_MCP_SERVER.md
│   ├── rag/
│   │   ├── RAG_GUIDE.md
│   │   ├── RAG_QUICKSTART.md
│   │   ├── RAG_CACHE.md
│   │   └── HOW_TO_INGEST_PDF.md
│   ├── memory/
│   │   ├── MEMORY_SYSTEM.md
│   │   └── VERIFY_MEMORY.md
│   └── web-ui/
│       ├── WEB_UI_README.md
│       └── CHATBOT_USAGE.md
├── setup/
│   ├── providers/
│   │   ├── OPENAI_MODELS.md
│   │   ├── SWITCH_TO_OPENAI.md
│   │   ├── GEMINI_SETUP.md
│   │   └── GEMINI_PROXY_GUIDE.md
│   ├── integrations/
│   │   └── CONFLUENCE_SETUP.md
│   └── deployment/
│       ├── START_SERVER.md
│       ├── QUICK_START_SERVER.md
│       └── RESTART_APP.md
├── architecture/
│   ├── FUTURE_ARCHITECTURE.md
│   └── diagrams/
│       ├── architecture-diagram.drawio
│       └── architecture-diagram-future.drawio
├── troubleshooting/
│   ├── MCP_LOGGING_GUIDE.md
│   ├── WHY_ERROR_WASNT_CAUGHT.md
│   ├── TROUBLESHOOT_CONFLUENCE.md
│   └── fixes/
│       ├── MCP_FIX.md
│       ├── MCP_STABILITY_FIX.md
│       ├── MCP_TIMEOUT_FIX.md
│       ├── MCP_WINDOWS_FIX.md
│       └── INTENT_DETECTION_FIX.md
└── technical/
    ├── LAZY_TOOLS.md
    ├── MCP_VERIFICATION_RESULTS.md
    └── NODEJS_SETUP_COMPLETE.md
```

## Root Directory (Keep These)
- `README.md` - Main project README (stays in root)
- `CHANGELOG.md` - Project changelog (stays in root)

## Migration Strategy

### Phase 1: Create Structure (Non-breaking)
1. Create new directory structure
2. Create symlinks or update references
3. Update main README.md with new paths

### Phase 2: Move Files (Breaking Changes)
1. Move files to new locations
2. Update all internal references
3. Update README.md documentation links
4. Test all links

### Phase 3: Cleanup
1. Remove old files from root
2. Update CI/CD scripts if they reference docs
3. Update any external documentation references

## Benefits

### Organization
- ✅ Clear categorization by topic
- ✅ Easy to find specific documentation
- ✅ Logical grouping of related docs

### Maintainability
- ✅ Easier to maintain related documentation together
- ✅ Clear structure for new contributors
- ✅ Better version control (easier to see changes by category)

### User Experience
- ✅ Clear navigation path
- ✅ Better discoverability
- ✅ Professional project structure

## Considerations

### Breaking Changes
- ⚠️ External links to specific docs may break
- ⚠️ Internal references in code/comments need updating
- ⚠️ Bookmarks and saved links will break

### Mitigation
- ✅ Create redirects or symlinks initially
- ✅ Update main README.md with new structure
- ✅ Add migration notice in old locations
- ✅ Update all internal references

## Implementation Steps

1. **Create directory structure** ✅ (can be done now)
2. **Create documentation index** ✅ (already done)
3. **Move files gradually** (requires careful testing)
4. **Update references** (search and replace)
5. **Test all links** (verify everything works)
6. **Update README.md** (update documentation section)

## Alternative: Keep Files in Root, Organize via Index

If breaking changes are a concern, we can:
- Keep all files in root directory
- Create comprehensive index in `docs/README.md` ✅ (done)
- Add clear categorization in main README.md
- Use consistent naming conventions

This approach:
- ✅ No breaking changes
- ✅ Easy to implement
- ✅ Still improves discoverability
- ⚠️ Root directory remains cluttered

## Recommendation

**Option 1: Gradual Migration** (Recommended)
- Start with creating structure and index ✅
- Move files in phases, updating references as we go
- Test thoroughly before removing old files

**Option 2: Index Only** (Safer)
- Keep files in root
- Use comprehensive index for organization
- Add clear sections in main README

Which approach would you prefer?

