# Web UI Restyling Design

## Summary

Restyle the current Flask `index` and `login` pages to align with the root [`DESIGN.md`](../../../DESIGN.md) direction while preserving all existing application behavior. The redesign should make the product feel calmer, sharper, and more intentional through monochrome chrome, selective atmospheric color, pill and circular controls, tighter typography, dashed focus treatments, and cleaner spacing.

This pass also establishes a small set of reusable UI elements so future pages and enhancements can follow the same system instead of reintroducing one-off styling.

## Goals

- Align the current web UI with the design principles defined in `DESIGN.md`
- Improve first impression and perceived product quality on `login` and empty chat states
- Improve information hierarchy and scanability without changing workflows
- Consolidate visual language across pages into one shared stylesheet system
- Introduce reusable UI building blocks for future use

## Non-Goals

- No authentication logic changes
- No chat workflow or API behavior changes
- No backend route changes
- No new product features beyond presentational and structural polish

## Scope

### In Scope

- Restyle `web/templates/index.html`
- Restyle `web/templates/login.html`
- Refactor `web/static/css/style.css` into a more reusable token and component-oriented stylesheet
- Apply light structural markup improvements where needed to support hierarchy and consistency
- Define reusable UI element patterns that can support future pages

### Out of Scope

- Rebuilding the application in a new frontend framework
- Reworking chat interactions or conversation behavior
- Adding settings, billing, or new dashboard functionality

## Visual Direction

The UI will follow a balanced interpretation of the Figma-inspired design system from `DESIGN.md`.

### Core Principles

- Interface chrome stays mostly black and white
- Color is used sparingly as atmospheric content, not as general-purpose chrome
- Buttons, icon controls, and chips use pill or circular geometry
- Focus styling uses dashed outlines instead of generic glow-heavy states
- Typography is tighter and more deliberate, with stronger hierarchy and less generic spacing

### Page-Specific Expression

#### Login

- The login page carries the strongest visual expression
- A vivid gradient stage sits behind a monochrome auth card
- The auth card itself remains restrained and highly legible
- Shared field, button, and feedback styles are used instead of page-local visual rules

#### Index

- The application shell remains mostly monochrome and productivity-oriented
- The welcome state may include a stronger branded visual moment
- Chat, sidebar, and controls stay restrained so conversation remains the focus
- Decorative color is limited and should not compete with functional content

## Structural Changes

### Index Page

Keep all existing behavior and JS hooks, but improve structure and grouping:

- Reframe the left sidebar as a more intentional workspace rail
- Group workspace title, model controls, search, conversation list, and user actions more clearly
- Improve the welcome state so it feels like a designed landing surface rather than empty space
- Refine the chat stage to feel like a cleaner reading canvas
- Soften or visually integrate the right-side upgrade strip so it no longer feels disconnected

### Login Page

- Replace inline page-specific styles with shared system styles
- Keep the page centered around a single auth card
- Improve heading, helper text, input rhythm, error treatment, and button presentation
- Preserve existing form IDs and JS behavior

## Reusable UI Elements

This redesign should create a small, reusable component vocabulary in HTML/CSS terms. These are not framework components, but stable styling patterns and markup conventions we can reuse later.

### Planned Reusable Elements

- `app-shell` layout pattern for full-page application screens
- `panel` and `panel-section` containers for sidebar and card groupings
- `pill-button` variants for primary, secondary, and destructive actions
- `icon-button` pattern for compact circular actions
- `field` pattern for labels, inputs, selects, and validation states
- `section-label` pattern for small uppercase technical labels
- `message-card` treatment for assistant and user message blocks
- `empty-state` pattern for welcome and no-content surfaces
- `user-badge` or avatar/profile summary pattern

### Why Reusability Matters

- Future UI work can move faster with less design drift
- Shared patterns reduce duplicated CSS and page-specific overrides
- New screens can inherit a consistent product identity
- It becomes easier to document, test, and evolve the UI intentionally

## Styling System

### Tokens

Introduce a consistent token layer in `style.css` for:

- Core colors
- Atmospheric gradient surfaces
- Border and divider colors
- Spacing rhythm
- Radius scale
- Shadow levels
- Transition timing

### Color Strategy

- Primary chrome colors are pure black and pure white
- Neutrals and translucent overlays support contrast and depth
- Gradient color appears in hero-like or atmospheric surfaces only
- Error styling remains clear but should harmonize with the monochrome system

### Typography Strategy

- Use a tighter, more refined typographic rhythm than the current UI
- Emphasize large headings, restrained body styles, and compact utility labels
- Prefer a clear distinction between display text, body copy, and small technical labels
- Apply tighter letter spacing where appropriate to echo `DESIGN.md`

### Interaction Strategy

- Primary actions use pill shapes
- Secondary compact actions use circular or soft-pill forms
- Inputs and selects receive more intentional focus styling
- Dashed outlines become the shared accessibility signature
- Hover and active states should feel deliberate, not glossy or over-animated

## Responsive Behavior

The redesign must preserve support for desktop and smaller screens while improving layout resilience.

- Desktop remains the primary experience
- Sidebar width may compress at smaller breakpoints
- The upgrade rail may collapse or disappear on smaller screens
- Welcome state and auth layout must remain readable on mobile widths
- Inputs and action controls must remain easy to tap

## Implementation Notes

- Preserve existing element IDs used by JavaScript
- Preserve route structure and current app behavior
- Keep markup changes limited to what supports clearer hierarchy and reusable styling
- Remove page-local inline styling from `login.html` in favor of shared CSS
- Organize CSS so reusable primitives are defined before page-specific overrides

## Testing Considerations

### Functional Safety

- Login form still submits correctly
- Existing auth redirect behavior still works
- Chat input, send button, new chat, search, clear all, and logout still work
- Existing dynamic conversation rendering still attaches to expected elements

### Visual Checks

- Login page renders correctly on desktop and mobile widths
- Index layout remains usable at current breakpoints
- Focus states are visible on keyboard navigation
- Message content remains readable for markdown, code blocks, and longer text

## Value of the Change

This restyling delivers product value beyond aesthetics.

- It improves trust and perceived quality by replacing a generic look with a more intentional system
- It improves usability by clarifying hierarchy, grouping, and interaction emphasis
- It gives the product a more coherent first impression across login and main app surfaces
- It reduces future design drift through reusable UI patterns and shared tokens
- It creates a stronger base for future enhancements without forcing a frontend rewrite

## Risks and Mitigations

### Risk

Markup changes could accidentally break JavaScript hooks.

### Mitigation

Keep existing IDs and key structure intact, and verify behaviors after implementation.

### Risk

The monochrome system could feel too stark for a conversational product.

### Mitigation

Use a balanced approach: restrained shell, stronger visual treatment in welcome and login surfaces only.

### Risk

Shared CSS refactoring could introduce regressions across pages.

### Mitigation

Build reusable primitives carefully, then validate both `login` and `index` in the browser after implementation.
