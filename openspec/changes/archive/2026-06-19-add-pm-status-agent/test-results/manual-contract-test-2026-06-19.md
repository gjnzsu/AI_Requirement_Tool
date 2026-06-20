# PM Status Agent Manual Contract Test

Date: 2026-06-19

Scope: Validate PM Status Agent expected behavior using fixture data before implementation.

Deployment target: Local only. No GCP deployment is required for this test phase.

## Test Method

The fixtures in `openspec/changes/add-pm-status-agent/test-data/` were reviewed as contract-level test cases. Each case includes Jira issues, Confluence pages, meeting notes, and expected health classification.

The expected PM Agent behavior is:

1. Collect delivery signals from Jira, Confluence, and meeting notes.
2. Distinguish normal progress, delay without blocker, and delay with blocker.
3. Generate a structured PM report.
4. Suggest write-back actions without performing them.
5. Preserve source references such as Jira issue keys and Confluence page titles.

## Scenario 1: On Track

Fixture: `scenario-01-on-track.json`

Expected health: Green

### Expected PM Status Output

**Executive Summary**

Enterprise AI Platform MVP is Green. Model Gateway API is ready for SIT package handoff, Prompt Template UI is progressing, and logging schema alignment has been completed. No active blocker is visible in Jira, Confluence, or meeting notes.

**Progress**

- AIP-102 Model Gateway API is in review with only a minor naming comment remaining.
- AIP-118 Prompt Template Management UI has completed list and create-template flows.
- AIP-130 logging schema is done and documented with masking fields.
- Security confirmed logging masking fields are acceptable for SIT.

**Risks / Issues / Blockers**

- No active blocker.
- Monitor prompt approval UX complexity.
- Monitor SIT test data preparation.

**Decisions Needed**

- No urgent decision required from sponsor or IT Director.

**Next Actions**

- PM: prepare SIT entry checklist by 2026-06-21.
- Engineering: complete AIP-102 review and package SIT deployment.
- Product Owner: keep demo scope focused on Model Gateway request flow and prompt template creation.

**Suggested Write-Back**

- Suggested Confluence update: add a Green status note to the delivery plan.
- Suggested Jira update: none required beyond normal issue comments.
- Write-back must wait for user approval.

**Source References**

- Jira: AIP-102, AIP-118, AIP-130.
- Confluence: Enterprise AI Platform MVP - Delivery Plan; AI Platform RAID Log.

### Result

Pass. Fixture clearly supports Green status because work is progressing, owners and dates exist, and no active blocker appears.

## Scenario 2: Delayed Without Blocker

Fixture: `scenario-02-delayed-no-blocker.json`

Expected health: Amber

### Expected PM Status Output

**Executive Summary**

Enterprise AI Platform MVP is Amber. Prompt approval workflow slipped by two days, reducing schedule buffer, but the team has no active blocker and has a plausible recovery path.

**Progress**

- AIP-145 reviewer role mapping is Done.
- AIP-118 Prompt Template Management UI remains In Progress with a revised forecast of 2026-06-26.
- AIP-149 approval API contract update is In Progress and the endpoint shape is confirmed.

**Risks / Issues / Blockers**

- Delay: approval workflow slipped by two days.
- Risk: UAT buffer is compressed because the revised completion date is close to the UAT target.
- No active blocker: Security and Product finalized the role mapping.

**Decisions Needed**

- Product Owner must confirm whether edge-case approval scenarios can move after UAT entry.
- Delivery Review should confirm whether happy-path demo scope is sufficient.

**Next Actions**

- Engineering Lead: publish recovery plan by 2026-06-20.
- Product Owner: confirm post-UAT handling of approval edge cases.
- PM: track whether AIP-118 and AIP-149 remain aligned to the revised 2026-06-26 forecast.

**Suggested Write-Back**

- Suggested Jira comment on AIP-118: "Status Amber. Approval workflow slipped by two days; no active blocker; recovery plan due 2026-06-20."
- Suggested Confluence RAID update: record schedule compression risk and mitigation.
- Write-back must wait for user approval.

**Source References**

- Jira: AIP-118, AIP-145, AIP-149.
- Confluence: Enterprise AI Platform MVP - Delivery Plan; AI Platform RAID Log.

### Result

Pass. Fixture clearly supports Amber status because there is delivery delay and reduced buffer, but no unresolved blocker prevents progress.

## Scenario 3: Delayed With Blocker

Fixture: `scenario-03-delayed-with-blocker.json`

Expected health: Red

### Expected PM Status Output

**Executive Summary**

Enterprise AI Platform MVP is Red. UAT readiness is at risk because key rotation policy, UAT environment provisioning, and audit trail ownership are unresolved. Jira and meeting notes indicate active blockers and missing ownership.

**Progress**

- AIP-121 key rotation automation is not progressing because Security policy is not approved.
- AIP-134 UAT environment provisioning is blocked by Security and Network approvals.
- AIP-151 audit trail ownership is open and unassigned.

**Risks / Issues / Blockers**

- Blocker: AIP-121 cannot proceed until Security approves secret rotation policy.
- Blocker: AIP-134 cannot complete UAT environment provisioning until whitelist approval is resolved.
- Blocker / owner gap: no named owner for final Network approval.
- Governance issue: AIP-151 has no owner, blocking governance sign-off.
- UAT readiness is at risk for the 2026-06-28 target.

**Decisions Needed**

- IT Director / Security Manager: approve temporary manual key rotation for UAT or accept UAT delay.
- Security / Network: assign final approval owner for whitelist.
- AI Platform / Data Governance: assign AI usage audit trail owner.

**Next Actions**

- PM: escalate key rotation policy and owner decisions today.
- Security Manager: confirm whether manual key rotation is acceptable for UAT.
- Infra / Network: name approval owner and provide approval ETA.
- Sponsor: decide whether to preserve UAT date with a temporary control or reset UAT entry criteria.

**Suggested Write-Back**

- Suggested Confluence RAID update: record Red status, active blockers, escalation owner, and UAT risk.
- Suggested Jira comments on AIP-121 and AIP-134: note active blocker and required owner decision.
- Suggested Jira update for AIP-151: assign owner before governance sign-off.
- Write-back must wait for user approval.

**Source References**

- Jira: AIP-121, AIP-134, AIP-151.
- Confluence: Enterprise AI Platform MVP - Delivery Plan; AI Platform RAID Log.

### Result

Pass. Fixture clearly supports Red status because delivery is delayed and blocked by unresolved policy, environment, and ownership decisions.

## Overall Result

All three contract fixtures are suitable for PM Status Agent testing:

- Green: normal progress, no active blocker.
- Amber: delayed, no active blocker, recovery still plausible.
- Red: delayed, active blocker, owner/decision escalation required.

## GCP Deployment Decision

Do not deploy to GCP for this test phase.

Recommended test sequence:

1. Use these fixtures for local unit tests.
2. Implement PM Status Agent locally.
3. Run focused unit tests for PM service, read ports, routing, API validation, and UI mode selection.
4. Run local Flask API tests.
5. Only deploy to GCP after local behavior passes and write-back approval safety is verified.

