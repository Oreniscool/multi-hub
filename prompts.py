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


def srs_generation_prompt(transcript_text: str) -> str:
    return f"""
IMPORTANT - MANDATORY GENERATION REQUIREMENTS:
Use the conversation to generate an implementation-ready SRS/build prompt that strictly enforces ALL constraints below:

1) File Count Constraint
- Exactly 5 files total must be generated.
- Mandatory files: app.py, agents.py, tools.py, prompts.py, requirements.txt.

2) app.py Constraint
- app.py must contain the full application entrypoint and runtime wiring.
- Must orchestrate UI and route calls to agents and tools modules.

3) agents.py Constraint
- agents.py must contain minimalistic agent code built with model-driven prompting.
- Include explicit prompt instructions for each agent role.
- Gemini must be configured as the primary reasoning LLM.
- Agents must collaborate in a Planner -> Critic -> Interviewer loop.

4) tools.py Constraint
- tools.py must contain helper utilities for OAuth, persistence, and runtime integrations.
- Keep UI rendering logic thin in app.py.

5) prompts.py Constraint
- prompts.py must be a reusable prompt library where all prompt templates are defined.

6) Conversation Intelligence Constraint
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
10) Project File Plan (exactly 5 files with responsibilities)
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
