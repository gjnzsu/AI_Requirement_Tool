# requirement-quality-gate Specification

## Purpose
TBD - created by archiving change add-pre-jira-quality-gate. Update Purpose after archive.
## Requirements
### Requirement: Pre-Jira deterministic gate
The system SHALL evaluate approved requirement draft data with deterministic readiness checks before creating a Jira issue.

#### Scenario: Missing acceptance criteria blocks Jira creation
- **WHEN** an approved requirement draft has no non-empty acceptance criteria and the deterministic gate is enabled
- **THEN** the system MUST NOT create a Jira issue and MUST return a blocked workflow result explaining that acceptance criteria are missing

#### Scenario: Acceptance criteria allow Jira creation
- **WHEN** an approved requirement draft has at least one non-empty acceptance criterion and the deterministic gate is enabled
- **THEN** the system SHALL continue to Jira issue creation

#### Scenario: Disabled deterministic gate does not block creation
- **WHEN** the deterministic gate is disabled
- **THEN** the system SHALL preserve the existing Jira creation behavior even if deterministic readiness checks would otherwise fail

### Requirement: Pre-Jira LLM judge review
The system SHALL support an LLM-as-a-Judge review of approved requirement draft data before Jira issue creation.

#### Scenario: Judge review produces structured feedback
- **WHEN** judge review is enabled for an approved requirement draft
- **THEN** the system SHALL request a structured review containing an overall score, criterion-level scores, findings, and suggested improvements

#### Scenario: Judge review is advisory by default
- **WHEN** judge review returns a low score or quality findings and the deterministic gate passes
- **THEN** the system SHALL continue to Jira issue creation by default and surface the judge feedback as advisory guidance

#### Scenario: Judge failure does not block deterministic pass
- **WHEN** judge review fails due to timeout, provider error, or invalid output and the deterministic gate passes
- **THEN** the system SHALL continue to Jira issue creation and include a non-blocking warning in the workflow response or progress detail

### Requirement: Distinct evaluation phases
The system SHALL distinguish pre-Jira draft quality review from post-Jira maturity evaluation.

#### Scenario: Existing maturity evaluation remains post-Jira
- **WHEN** a Jira issue is successfully created and post-Jira evaluation is enabled
- **THEN** the system SHALL run the existing Jira maturity evaluation after Jira creation and preserve the existing maturity evaluation result shape

#### Scenario: Pre-Jira review does not replace maturity evaluation
- **WHEN** both pre-Jira judge review and post-Jira maturity evaluation are enabled
- **THEN** the system SHALL expose pre-Jira judge findings separately from post-Jira maturity evaluation results

### Requirement: Configurable quality behavior
The system SHALL allow deterministic gate behavior, LLM judge review, and post-Jira maturity evaluation to be configured independently.

#### Scenario: Evaluation settings are resolved from configuration
- **WHEN** the workflow service is created
- **THEN** the system SHALL resolve settings that control deterministic gate behavior, pre-Jira judge review, and post-Jira maturity evaluation

#### Scenario: Disabled judge review skips LLM judge call
- **WHEN** pre-Jira judge review is disabled
- **THEN** the system SHALL NOT call the LLM judge service before Jira creation

#### Scenario: Disabled post-Jira evaluation skips maturity evaluation
- **WHEN** post-Jira maturity evaluation is disabled
- **THEN** the system SHALL skip the existing Jira maturity evaluator while preserving Jira creation behavior

### Requirement: Workflow progress visibility
The system SHALL surface quality gate and judge review outcomes through the workflow result.

#### Scenario: Blocked gate is visible in progress
- **WHEN** the deterministic gate blocks Jira creation
- **THEN** the workflow progress SHALL mark the quality review or evaluation step as blocked and keep downstream durable steps skipped

#### Scenario: Advisory judge feedback is visible
- **WHEN** judge review completes and Jira creation continues
- **THEN** the workflow response or progress detail SHALL include a concise summary of the advisory judge findings
