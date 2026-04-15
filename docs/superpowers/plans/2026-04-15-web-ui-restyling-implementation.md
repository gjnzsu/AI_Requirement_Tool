# Web UI Restyling Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restyle the current Flask `index` and `login` pages to match the approved balanced monochrome design system while preserving all existing behavior.

**Architecture:** Keep the Flask templates and JavaScript hooks intact, then move visual rules into a shared token-driven stylesheet. Use light markup changes only where they improve grouping, empty states, and reusable UI patterns without changing runtime behavior.

**Tech Stack:** Flask templates, HTML, CSS, existing vanilla JavaScript hooks

---

### Task 1: Establish Shared UI Tokens And Reusable Patterns

**Files:**
- Modify: `web/static/css/style.css`

- [ ] **Step 1: Refactor the stylesheet around reusable tokens and shared patterns**

Add a root token layer and base interaction rules near the top of `web/static/css/style.css`, including variables for monochrome chrome, atmospheric gradients, spacing, radius, shadows, and dashed focus.

```css
:root {
    --color-black: #000000;
    --color-white: #ffffff;
    --color-ink-strong: #111111;
    --color-ink: #1f1f1f;
    --color-ink-soft: #5c5c5c;
    --color-line: rgba(0, 0, 0, 0.12);
    --color-line-strong: rgba(0, 0, 0, 0.22);
    --color-surface: #ffffff;
    --color-surface-muted: #f6f6f4;
    --color-surface-soft: rgba(255, 255, 255, 0.76);
    --color-overlay-dark: rgba(0, 0, 0, 0.08);
    --color-overlay-light: rgba(255, 255, 255, 0.18);
    --color-danger: #b42318;
    --gradient-atmosphere: linear-gradient(135deg, #d7ff64 0%, #9cff66 18%, #ffe66d 38%, #8b5cf6 68%, #ff4db8 100%);
    --gradient-atmosphere-soft: radial-gradient(circle at top left, rgba(215, 255, 100, 0.36), transparent 34%),
        radial-gradient(circle at 85% 18%, rgba(255, 77, 184, 0.22), transparent 30%),
        radial-gradient(circle at 60% 78%, rgba(139, 92, 246, 0.22), transparent 28%);
    --shadow-soft: 0 10px 30px rgba(0, 0, 0, 0.08);
    --shadow-card: 0 18px 50px rgba(0, 0, 0, 0.12);
    --shadow-float: 0 24px 70px rgba(0, 0, 0, 0.16);
    --radius-sm: 8px;
    --radius-md: 16px;
    --radius-pill: 999px;
    --space-1: 4px;
    --space-2: 8px;
    --space-3: 12px;
    --space-4: 16px;
    --space-5: 20px;
    --space-6: 24px;
    --space-8: 32px;
    --space-10: 40px;
    --transition-standard: 180ms ease;
}

*:focus-visible {
    outline: 2px dashed var(--color-black);
    outline-offset: 3px;
}
```

- [ ] **Step 2: Add reusable component classes for panels, pills, fields, and empty states**

Define reusable classes that both templates can share, including `panel`, `panel-section`, `section-label`, `pill-button`, `icon-button`, `field`, `field-input`, `field-select`, `empty-state`, and `user-badge`.

Run: `rg -n ":root|pill-button|empty-state|field-input" web/static/css/style.css`
Expected: Matching lines for the new token and component definitions.

- [ ] **Step 3: Commit the shared style foundation**

Run:

```powershell
git add web/static/css/style.css
git commit -m "refactor: add reusable web UI design tokens"
```

Expected: A commit containing the stylesheet foundation only.

### Task 2: Restyle The Main Chat Shell

**Files:**
- Modify: `web/templates/index.html`
- Modify: `web/static/css/style.css`

- [ ] **Step 1: Update the index markup with light structural polish**

Keep all existing IDs used by JavaScript, but introduce clearer structural wrappers for the workspace title, control groups, welcome state, and utility rail. Preserve elements like `modelSelect`, `agentModeSelect`, `newChatBtn`, `searchInput`, `conversationsList`, `logoutBtn`, `chatMessages`, `chatInput`, and `sendBtn`.

Example target structure:

```html
<aside class="sidebar panel">
    <div class="sidebar-header panel-section">
        <p class="section-label">Workspace</p>
        <div class="brand-block">
            <h1 class="logo">CHAT A.I+</h1>
            <p class="brand-copy">Requirement conversations with a cleaner, quieter interface.</p>
        </div>
        <div class="control-stack">
            ...
        </div>
    </div>
</aside>
```

- [ ] **Step 2: Redesign the welcome state and shell styling**

Style the app shell as a restrained monochrome workspace, with the welcome state carrying the main atmospheric color moment. Ensure buttons and controls use shared pill/circle patterns and dashed focus. Keep the right rail subtle or visually integrated.

Run: `rg -n "welcome-message|chat-area|sidebar|upgrade-sidebar" web/templates/index.html web/static/css/style.css`
Expected: Updated markup and styling references for the redesigned shell.

- [ ] **Step 3: Verify there are no lost JavaScript hook IDs**

Run:

```powershell
rg -n "id=\"(modelSelect|agentModeSelect|newChatBtn|searchInput|conversationsList|logoutBtn|chatMessages|chatInput|sendBtn)\"" web/templates/index.html
```

Expected: One match for each existing hook ID.

- [ ] **Step 4: Commit the chat shell redesign**

Run:

```powershell
git add web/templates/index.html web/static/css/style.css
git commit -m "feat: restyle main chat interface"
```

Expected: A commit containing the updated shell structure and styles.

### Task 3: Restyle The Login Experience

**Files:**
- Modify: `web/templates/login.html`
- Modify: `web/static/css/style.css`

- [ ] **Step 1: Replace inline login-only styles with shared system markup**

Remove the `<style>` block from `web/templates/login.html` and move the page to shared classes such as `auth-page`, `auth-stage`, `auth-card`, `field`, and `pill-button`. Keep the existing IDs `loginForm`, `username`, `password`, `loginBtn`, `loginBtnText`, and `errorMessage`.

Example target structure:

```html
<body class="auth-page">
    <div class="auth-stage">
        <section class="auth-card panel">
            <p class="section-label">Secure Access</p>
            <div class="login-header">
                <h1>CHAT A.I+</h1>
                <p>Sign in to continue your requirement workflow.</p>
            </div>
            ...
        </section>
    </div>
</body>
```

- [ ] **Step 2: Add shared auth-page styles to the stylesheet**

Implement the gradient stage, monochrome card, shared field styling, loading spinner integration, and harmonized error treatment in `web/static/css/style.css`.

Run: `rg -n "auth-page|auth-stage|auth-card|error-message|loading-spinner" web/templates/login.html web/static/css/style.css`
Expected: Matching lines for the new shared auth structure and styles.

- [ ] **Step 3: Verify the login hook IDs remain intact**

Run:

```powershell
rg -n "id=\"(loginForm|username|password|loginBtn|loginBtnText|errorMessage)\"" web/templates/login.html
```

Expected: One match for each existing hook ID.

- [ ] **Step 4: Commit the login redesign**

Run:

```powershell
git add web/templates/login.html web/static/css/style.css
git commit -m "feat: restyle login experience"
```

Expected: A commit containing the shared auth redesign.

### Task 4: Verify Rendering And Behavior Safety

**Files:**
- Modify: `web/templates/index.html`
- Modify: `web/templates/login.html`
- Modify: `web/static/css/style.css`

- [ ] **Step 1: Run a focused syntax and template sanity check**

Run:

```powershell
python -m compileall app.py src
```

Expected: Python modules compile successfully with no syntax errors introduced by adjacent changes.

- [ ] **Step 2: Start the app and do a manual UI smoke check**

Run:

```powershell
python app.py
```

Expected: Flask app starts successfully so `login` and `index` can be checked in the browser for layout, visible focus states, and preserved interaction wiring.

- [ ] **Step 3: Inspect the final worktree before handoff**

Run:

```powershell
git status --short
git log --oneline -3
```

Expected: Only intended UI files are changed, and the recent commits reflect the stylesheet foundation plus page updates.
