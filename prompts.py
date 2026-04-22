"""Prompt templates and prompt builders for MultiHub agents."""

from typing import List, Dict


def format_transcript(chat: List[Dict[str, str]]) -> str:
    lines = []
    for msg in chat:
        role = "User" if msg.get("role") == "user" else "Assistant"
        lines.append(f"{role}: {msg.get('content', '')}")
    return "\n".join(lines)


def planner_prompt(transcript_text: str) -> str:
    return f"""
You are Agent Planner in a collaborative multi-agent system.
Extract requirement signals and identify information gaps from the conversation.

Return strict JSON with this schema:
{{
  "known_requirements": ["..."],
  "missing_dimensions": ["..."],
  "risk_flags": ["..."],
  "priority_question": "one high-value question",
  "question_goal": "what this question unlocks"
}}

Conversation:
{transcript_text}
"""


def critic_prompt(transcript_text: str, planner_json_text: str) -> str:
    return f"""
You are Agent Critic in a collaborative multi-agent system.
Review the Planner output and improve the next question quality.
Make sure the next question is specific, practical, and non-redundant.

Return strict JSON with this schema:
{{
  "improved_question": "one precise question",
  "why_best_next": "brief reason",
  "micro_probes": ["optional short probe", "optional short probe"]
}}

Planner JSON:
{planner_json_text}

Conversation:
{transcript_text}
"""


def interviewer_prompt(transcript_text: str, planner_json_text: str, critic_json_text: str) -> str:
    return f"""
You are Agent Interviewer in a collaborative multi-agent system.
Use the planner and critic outputs to produce the user-facing response.

Response rules:
- Keep to 2-4 concise sentences.
- Start with a one-sentence understanding summary.
- Ask exactly one primary question.
- Optionally add one short line with 1-2 concrete examples to help the user answer.
- Do not generate the final SRS yet.

Planner JSON:
{planner_json_text}

Critic JSON:
{critic_json_text}

Conversation:
{transcript_text}
"""


SRS_SHARED_CONSTRAINTS = """
Global constraints to preserve:
- Exactly 8 files total: app.py, agents.py, tools.py, prompts.py, models.py, databases.py, vector_embeddings.py, requirements.txt.
- Groq is the only supported LLM provider/model family.
- Database backend is Supabase only.
- Vector storage/search is pgvector only.
- Agents collaborate in a Planner -> Critic -> Interviewer loop for requirement collection.
- app.py handles entrypoint/runtime wiring only; keep business logic in modules.
""".strip()


def srs_prompt_step_one(transcript_text: str) -> str:
    return f"""
You are generating Prompt 1 of 3 in a sequential prompt pack.

Task:
Create a user-pasteable prompt that asks another coding model to produce only the product definition and requirements baseline.

Prompt 1 must ask for these sections only:
1) Product Summary
2) Primary Users & Roles
3) Core Use Cases
4) Functional Requirements
5) Non-Functional Requirements

Include these constraints in Prompt 1:
{SRS_SHARED_CONSTRAINTS}

Output rules:
- Return ONLY Prompt 1 text (no commentary, no markdown fences).
- Keep Prompt 1 concise and actionable.
- Prompt 1 must tell the downstream model to avoid writing code.

Conversation:
{transcript_text}
"""


def srs_prompt_step_two(transcript_text: str, step_one_prompt_text: str) -> str:
    return f"""
You are generating Prompt 2 of 3 in a sequential prompt pack.

Task:
Create a user-pasteable follow-up prompt that should be run after Prompt 1 output exists.
Prompt 2 should focus on architecture and implementation planning, using Prompt 1 context.

Prompt 2 must ask for these sections only:
6) Agent Architecture (roles, collaboration, loop flow)
7) Tooling Architecture (helpers and integrations)
8) API/UI Design (interaction contracts)
9) Prompt Library Specification
10) Project File Plan (exactly 8 files with responsibilities)

Include these constraints in Prompt 2:
{SRS_SHARED_CONSTRAINTS}

Additional requirements for Prompt 2:
- Explicitly require a Planner -> Critic -> Interviewer loop definition.
- Require concise interface contracts between app.py, agents.py, and tools.py.

Reference Prompt 1 draft:
{step_one_prompt_text}

Conversation:
{transcript_text}

Output rules:
- Return ONLY Prompt 2 text (no commentary, no markdown fences).
- Keep Prompt 2 concise and directly executable.
"""


def srs_prompt_step_three(
    transcript_text: str,
    step_one_prompt_text: str,
    step_two_prompt_text: str,
) -> str:
    return f"""
You are generating Prompt 3 of 3 in a sequential prompt pack.

Task:
Create a user-pasteable final prompt that should be run after Prompt 1 and Prompt 2 outputs are available.
Prompt 3 should finalize quality and delivery criteria.

Prompt 3 must ask for these sections only:
11) Critical Q&A Collection Strategy
12) Acceptance Criteria

Prompt 3 must also require:
- A final coherence pass that checks alignment with Prompt 1 and Prompt 2 outputs.
- Clear completion gates for requirement completeness.
- A short risk register with mitigations.

Reference Prompt 1 draft:
{step_one_prompt_text}

Reference Prompt 2 draft:
{step_two_prompt_text}

Conversation:
{transcript_text}

Output rules:
- Return ONLY Prompt 3 text (no commentary, no markdown fences).
- Keep Prompt 3 concise and implementation-focused.
"""


def _sanitize_prompt_block(prompt_text: str) -> str:
    return (prompt_text or "").strip().replace("```", "'''")


def format_prompt_sequence(
    step_one_text: str,
    step_two_text: str,
    step_three_text: str,
) -> str:
    step_one = _sanitize_prompt_block(step_one_text)
    step_two = _sanitize_prompt_block(step_two_text)
    step_three = _sanitize_prompt_block(step_three_text)

    return f"""
# Sequential Prompt Pack (Run in Order)

Use these prompts one after another with your coding model.
Do not skip order.

## Prompt 1 - Product & Requirements Baseline
```
{step_one}
```

## Prompt 2 - Architecture & File Plan
```
{step_two}
```

## Prompt 3 - Quality Gates & Acceptance
```
{step_three}
```
""".strip()


def srs_generation_prompt(transcript_text: str) -> str:
    """Backward-compatible single-step template entry point."""
    return f"""
IMPORTANT - MANDATORY GENERATION REQUIREMENTS:
Use the conversation to generate an implementation-ready SRS/build prompt that strictly enforces ALL constraints below:

1) File Count Constraint
- Exactly 8 files total must be generated.
- Mandatory files: app.py, agents.py, tools.py, prompts.py, models.py, databases.py, vector_embeddings.py, requirements.txt.

2) app.py Constraint
- app.py must contain the full application entrypoint and runtime wiring.
- Must orchestrate UI and route calls to agents and tools modules.

3) agents.py Constraint
- agents.py must contain minimalistic agent code built with model-driven prompting.
- Include explicit prompt instructions for each agent role.
- Groq must be configured as the primary reasoning LLM.
- Agents must collaborate in a Planner -> Critic -> Interviewer loop.

4) tools.py Constraint
- tools.py must contain helper utilities for OAuth, persistence, and runtime integrations.
- Keep UI rendering logic thin in app.py.

5) models.py Constraint
- models.py must contain the AI model configurations the application can use.
- For now, Groq must be the only supported model provider/model family.
- Do not include Mistral, OpenAI, Anthropic, Gemini, or any non-Groq model options.

6) databases.py Constraint
- databases.py must contain database connectivity, CRUD helpers, and repository/data-access functions.
- Database backend must be limited to Supabase only.
- Vector data storage/retrieval must use pgvector only (through Postgres/Supabase).
- Keep direct database calls out of app.py and agent logic.

7) vector_embeddings.py Constraint
- vector_embeddings.py must contain embedding creation, vector index operations, and similarity search helpers.
- Keep all vector store integration logic isolated in this file.
- Restrict vector integration to pgvector-backed operations only.

8) prompts.py Constraint
- prompts.py must be a reusable prompt library where all prompt templates are defined.

9) Conversation Intelligence Constraint
- Chat agents must conduct a structured Q&A flow to collect complete user requirements before final answers.
- Agents must ask targeted follow-up questions for missing details.

Now produce a concise, implementable SRS with the exact sections below:
1) Product Summary
2) Primary Users & Roles
3) Core Use Cases
4) Functional Requirements
5) Non-Functional Requirements
6) Agent Architecture (roles, collaboration, loop flow)
7) Tooling Architecture (helpers and integrations)
8) API/UI Design (interaction contracts)
9) Prompt Library Specification
10) Project File Plan (exactly 8 files with responsibilities)
11) Critical Q&A Collection Strategy
12) Acceptance Criteria

In section 6 and section 11, explicitly define a multi-agent loop with at least these roles:
- Planner Agent: extracts known requirements and missing dimensions.
- Critic Agent: improves the next best question quality.
- Interviewer Agent: asks one high-value question to the user.

The loop must run iteratively across turns until requirement completeness is reached.

Conversation:
{transcript_text}
"""
