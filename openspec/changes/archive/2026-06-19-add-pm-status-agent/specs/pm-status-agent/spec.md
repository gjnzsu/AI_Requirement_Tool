## ADDED Requirements

### Requirement: PM Status Agent Mode
The system SHALL provide a PM Status Agent mode that can be selected explicitly from the web UI and API request payload.

#### Scenario: User selects PM Status Agent mode
- **WHEN** a chat request includes `agent_mode` set to `pm_status_agent`
- **THEN** the system routes the request to the PM Status Agent workflow

#### Scenario: UI exposes PM Status Agent mode
- **WHEN** the user opens the agent mode selector
- **THEN** the selector includes an option for PM Status Agent

### Requirement: PM Status Signal Collection
The system SHALL collect project delivery signals from Jira, Confluence, and optional meeting-note input before generating a PM status report.

#### Scenario: Jira project status requested
- **WHEN** the user asks for status for a project key, sprint, milestone, or JQL scope
- **THEN** the system retrieves matching Jira issues through a read-side Jira capability

#### Scenario: Confluence context requested
- **WHEN** the user provides Confluence page identifiers, page titles, or a project documentation scope
- **THEN** the system retrieves relevant Confluence content through a read-side Confluence capability

#### Scenario: Meeting notes included
- **WHEN** the user includes meeting notes in the request
- **THEN** the system extracts action items, risks, decisions, and owner references from those notes

### Requirement: Structured Project Status Report
The system SHALL generate a structured PM status report with health color, rationale, risks, blockers, decisions, owner gaps, next actions, suggested Jira updates, suggested Confluence content, and stakeholder-ready communication.

#### Scenario: PM report generated
- **WHEN** Jira, Confluence, or meeting-note signals are available
- **THEN** the response includes a project health color, executive summary, progress, risks/issues/blockers, decisions needed, next actions, and PM judgment rationale

#### Scenario: Missing source data
- **WHEN** Jira or Confluence retrieval fails or returns no relevant data
- **THEN** the response states which source was unavailable and continues using the remaining available inputs

### Requirement: Human Approval Before Write Back
The system SHALL require explicit user approval before creating or updating Jira or Confluence artifacts from a PM status report.

#### Scenario: Write-back suggestion generated
- **WHEN** the PM Status Agent identifies useful Jira updates or Confluence status-page content
- **THEN** the system presents them as suggestions rather than immediately writing them

#### Scenario: User approves write back
- **WHEN** the user approves a pending PM status write-back action
- **THEN** the system performs only the approved action and reports the created or updated artifact link

#### Scenario: User cancels write back
- **WHEN** the user cancels a pending PM status write-back action
- **THEN** the system performs no Jira or Confluence write operation

### Requirement: Source Traceability
The system SHALL preserve source references used to generate the PM status report.

#### Scenario: Report includes source references
- **WHEN** a PM status report is generated from Jira or Confluence data
- **THEN** the report includes issue keys, page titles, page ids, or links for the source signals when available

### Requirement: Existing Requirement Workflows Remain Unchanged
The system SHALL preserve existing Requirement SDLC Agent behavior when PM Status Agent mode is not selected.

#### Scenario: Requirement SDLC Agent selected
- **WHEN** a chat request includes `agent_mode` set to `requirement_sdlc_agent`
- **THEN** the system continues to use the existing Requirement SDLC Agent workflow

#### Scenario: Auto mode receives non-PM requirement request
- **WHEN** the user sends an existing requirement lifecycle request in Auto mode
- **THEN** the system continues to route it according to existing requirement workflow behavior
