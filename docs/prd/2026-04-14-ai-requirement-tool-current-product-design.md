# AI Requirement Tool Current Product Design

## Document Metadata

- **Version:** Draft v1
- **Date:** April 14, 2026
- **Audience:** Internal product, engineering, and delivery stakeholders
- **Document Type:** Current product design document
- **Primary Framing:** Guided delivery workflow assistant

## 1. Executive Summary

AI Requirement Tool is an internal AI-assisted delivery workflow product for software delivery teams. Its current primary value is helping product managers, business analysts, and delivery leads move from a rough request to a structured, reviewable requirement draft and associated Jira and Confluence workflow outputs in one guided flow.

The product already contains meaningful capability depth: conversational AI, internal knowledge grounding through RAG, Jira and Confluence workflow execution, multi-provider LLM routing, and operational fallback behavior. The current design priority is not to broaden the product into a general AI platform. The priority is to make the existing requirement-to-workflow journey clearer, more trusted, and more dependable for repeated team use.

This document defines the current product, who it is for, what problem it should solve now, what success looks like, what belongs in the current MVP/current phase, and what should wait for later platform evolution.

## 2. Product Definition And Positioning

### 2.1 What The Product Is

AI Requirement Tool is an internal AI-assisted workflow product that helps teams:

- turn rough ideas into structured requirement drafts
- review and refine requirement outputs before execution
- create Jira issues and related Confluence outputs faster
- use internal context and documents during requirement and delivery work
- reduce context switching between chat, documentation, and work-management tools

### 2.2 Current Product Positioning

The product should currently be positioned as:

- a guided internal delivery workflow assistant
- optimized first for PMs and BAs
- useful to engineering and delivery leads as collaborators and reviewers

It should not currently be positioned as:

- a fully autonomous agent product
- a broad internal AI platform as the primary story
- a generic enterprise chatbot with many loosely related features

### 2.3 Product Promise

When a user starts with a rough request or incomplete requirement, the product should help them move through a clear guided path to produce a useful, reviewable output and, when appropriate, execute the next workflow steps in Jira and Confluence.

## 3. Problem Framing Canvas Summary

### 3.1 Initial Problem

The current product needs to solve a combined workflow problem rather than a single drafting problem:

- users begin with rough, fragmented requests
- they need to convert those requests into structured requirement artifacts
- they then need to move those artifacts into delivery systems such as Jira and Confluence
- current work is spread across chat, documents, tickets, and team memory

### 3.2 Why This Has Not Been Fully Solved Yet

The current product already has significant capability, but the experience has not fully solved the user problem because:

- the workflow is still too chat-first and not guided enough
- users may need to infer the right path from a general-purpose UI
- the product experience does not yet consistently communicate what to do next

### 3.3 How We Are Part Of The Problem

The main assumption to challenge is:

- we assumed users would figure out the right workflow from a general chat UI

That assumption creates friction for PM and BA users who need guided structure more than conversational flexibility.

### 3.4 Who Experiences The Problem

Primary users experience the problem:

- at the start of a new requirement or delivery request
- when they only have a rough prompt, stakeholder note, or partial idea
- when they need to transform that input into a usable draft and then into delivery artifacts

Consequences when the product does not work well:

- time lost rewriting vague ideas into structured requirements
- inconsistent quality across requirement outputs
- reduced confidence in generated workflow artifacts
- repeated switching between tools and manual cleanup

### 3.5 Reframed Problem Statement

PMs, BAs, and delivery leads need a clearer way to turn rough requests into trusted, reviewable requirement and workflow outputs because current work is fragmented across tools and generic AI experiences do not reliably guide the full requirement-to-delivery flow.

### 3.6 How Might We

How might we help PMs and delivery teams turn rough requests into trusted, reviewable requirement and workflow outputs through one guided flow?

## 4. Target Users And Personas

### 4.1 Primary Persona: Product Manager / Business Analyst

#### Profile

- owns or shapes requirement definition
- receives requests from stakeholders, leadership, customers, or delivery teams
- needs to convert incomplete inputs into structured requirement artifacts

#### Goals

- go from rough request to structured draft faster
- improve quality and consistency of requirement outputs
- reduce manual rewriting across tools
- keep control over review and approval before workflow execution

#### Pain Points

- rough requests arrive incomplete or ambiguous
- requirement writing quality varies depending on time and context
- manual transfer into Jira and Confluence is repetitive
- generic AI output often needs heavy cleanup before it is useful

#### What Success Looks Like

- the user can provide a rough prompt and quickly receive a structured requirement draft
- the product asks useful clarifying questions when needed
- the output is trustworthy enough to use as a serious working draft
- downstream workflow actions are visible, controllable, and understandable

### 4.2 Secondary Persona: Engineering Lead / Delivery Lead

#### Profile

- reviews scope, clarity, and feasibility
- collaborates on delivery planning and backlog shaping
- may consume or refine Jira and Confluence outputs

#### Goals

- align quickly on scope and intent
- reduce ambiguity before execution
- improve consistency of delivery artifacts
- avoid repeated context gathering across meetings and tools

#### Pain Points

- requirements are often incomplete or inconsistent
- workflow outputs may be difficult to trust if the generation path is unclear
- important context may be hidden in chats or documents rather than in the artifact itself

### 4.3 Secondary Stakeholders

- platform and enablement teams that support adoption and reliability
- tooling owners or operations stakeholders who care about observability, provider behavior, and integration health

## 5. Product Strategy For The Current Phase

### 5.1 Strategic Focus

The product should currently focus on one strong journey:

1. user starts with a rough request
2. product clarifies and structures the request
3. product presents a reviewable draft
4. user approves or revises
5. product executes selected workflow steps
6. product shows clear outcomes and next actions

### 5.2 Strategic Choice

The recommended current-product strategy is:

- position the product as a guided delivery workflow assistant
- optimize first for PM and BA success
- support delivery leads as key collaborators
- keep future platform evolution visible, but secondary

### 5.3 Why This Strategy

This strategy best matches the product’s current strengths:

- workflow depth already exists
- requirement drafting plus Jira and Confluence execution is a meaningful wedge
- trust and clarity are now higher priorities than adding more breadth

### 5.4 What We Are Not Optimizing For Yet

- broad autonomous behavior without review
- generalized workflow support for every department or use case
- platform abstraction as the headline product story for the current phase

## 6. Current Product Scope

### 6.1 In-Scope Capabilities

The current product includes:

- conversational interaction for requirement and delivery support
- guided requirement drafting and review flow
- requirement lifecycle support through staged analysis, preview, confirmation, and execution
- Jira issue creation
- Confluence content generation
- requirement quality or maturity evaluation
- RAG-backed retrieval using internal documents and project context
- multi-provider LLM support with fallback behavior
- web-based UI with authentication, conversation handling, and operational observability

### 6.2 Core User Outcome

The main outcome for the current phase is:

- a PM or BA can move from rough request to a reviewable draft and associated workflow outputs through one clear guided flow

### 6.3 Product Boundaries

The current product is not required to:

- operate as a fully autonomous agent
- support every enterprise workflow domain
- provide a complete no-code workflow builder
- deliver a broad platform model to end users as the main value proposition

## 7. MVP And User Story Map

### 7.1 Segment

- internal software delivery teams

### 7.2 Primary Persona

- Product Manager / Business Analyst

### 7.3 Narrative

- Turn a rough requirement request into a trusted, reviewable delivery draft and workflow output without repeatedly rewriting the same context across tools.

### 7.4 Backbone Activities

1. Start a requirement request
2. Clarify and structure the requirement
3. Review and refine the draft
4. Execute workflow outputs
5. Confirm results and next steps

### 7.5 Steps And Tasks

#### Activity 1: Start A Requirement Request

Steps:

- enter a rough request or prompt
- understand available workflow support
- select or enter the intended path

Tasks:

- input requirement idea, stakeholder note, or partial request
- identify whether this is requirement drafting, workflow creation, or knowledge support
- understand what integrations and actions are available

#### Activity 2: Clarify And Structure The Requirement

Steps:

- gather missing context
- shape the requirement draft
- apply internal context where useful

Tasks:

- ask focused follow-up questions
- infer missing structure where safe
- use RAG or prior context when helpful
- draft summary, business goal, scope notes, assumptions, and acceptance criteria

#### Activity 3: Review And Refine The Draft

Steps:

- inspect generated output
- revise unclear or weak sections
- confirm readiness for execution

Tasks:

- show requirement preview before creation
- allow revision requests
- highlight open questions or assumptions
- require explicit user approval before durable actions

#### Activity 4: Execute Workflow Outputs

Steps:

- create Jira output
- create Confluence output when applicable
- evaluate requirement quality

Tasks:

- create Jira issue from approved draft
- generate related Confluence content
- run requirement maturity or quality checks
- preserve partial success if one downstream step fails

#### Activity 5: Confirm Results And Next Steps

Steps:

- show completed outputs
- explain failures or partial results
- guide the next action

Tasks:

- return links, keys, and status
- present workflow progress clearly
- show what succeeded, failed, or was skipped
- suggest follow-up edits or next delivery actions

### 7.6 MVP Release Slice

The current MVP/current-phase experience should include:

- rough request intake
- guided clarification where needed
- structured requirement draft generation
- preview and explicit confirmation
- Jira creation
- optional Confluence creation
- visible workflow progress and outcome reporting

### 7.7 Later Phase Slice

The later phase can expand to:

- stronger onboarding and workflow guidance in the UI
- clearer integration health and readiness visibility
- richer draft-editing and artifact review tools
- broader workflow packs or reusable platform capabilities

## 8. Future Phases And Platform Evolution

### 8.1 Near-Future Direction

The product can evolve toward a reusable internal AI workflow platform, but that should remain a future-oriented direction rather than the current headline.

### 8.2 Conditions For Platform Expansion

Platform-oriented evolution makes sense after the product demonstrates:

- a strong and repeatable core workflow
- trust in requirement outputs
- reliable execution outcomes
- clearer onboarding and product understanding

### 8.3 Future Expansion Areas

Potential later areas include:

- reusable workflow modules
- broader enterprise integration support
- stronger admin and governance controls
- clearer self-service configuration and operational visibility

## 9. Success Metrics

### 9.1 Primary Success Metrics

- percentage of rough requests that reach a reviewable structured draft
- percentage of approved drafts that successfully produce Jira outputs
- percentage of workflow runs that complete with clear, understandable result states

### 9.2 Secondary Success Metrics

- reduction in manual rewriting effort for PM and BA users
- improvement in user trust for generated requirement outputs
- improved clarity of workflow results and downstream actions
- repeat usage by target users for requirement and delivery work

### 9.3 Qualitative Success Signals

- users describe the product as a practical working assistant rather than a general chatbot
- PM and BA users use the generated draft as a serious starting point
- engineering and delivery stakeholders report less ambiguity in generated workflow artifacts

## 10. Non-Goals

The following are explicitly out of scope for the current product design:

- fully autonomous agents that act without user review
- broad platform abstractions as the main story for the current phase
- support for every enterprise workflow domain
- optimizing for a generic chat experience over the requirement-to-workflow journey

## 11. Risks And Open Questions

### 11.1 Risks

- users may still interpret the product as a general chat tool rather than a guided workflow product
- workflow trust may remain uneven if preview and result visibility are not strong enough
- technical capability breadth may continue to distract from core user-journey clarity
- integration reliability can undermine product trust even when drafting quality is strong

### 11.2 Open Questions

- how strongly should the UI emphasize guided workflow over free-form chat in the next release?
- what level of draft editing should be supported before execution?
- how should integration readiness and unavailable capabilities be surfaced to users?
- which user-facing metrics best capture trust and workflow usefulness for PM and BA users?

## 12. Stakeholder Review Workshop Plan

### 12.1 Workshop Goal

Align product, engineering, and delivery stakeholders on the current product definition, primary persona, MVP scope, and future-phase boundaries.

### 12.2 Participants

- product manager or business analyst lead
- engineering lead
- delivery lead
- optional platform or enablement stakeholder

### 12.3 Recommended Agenda

1. Review product framing and problem statement
2. Confirm primary and secondary personas
3. Review the core user journey and story map
4. Confirm MVP/current-phase scope
5. Confirm non-goals and future-phase boundaries
6. Capture open questions and owners

### 12.4 Decisions Required

- approve the product’s current positioning
- approve the primary persona and user journey
- approve MVP/current-phase boundaries
- agree on what should wait for future platform evolution

## 13. Recommended Next Artifact

The next document after approval of this product design should be a release-focused PRD that translates this framing into a concrete roadmap, workflow improvements, and implementation priorities for the next product phase.
