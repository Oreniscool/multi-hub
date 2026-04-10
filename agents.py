"""Agent orchestration for MultiHub prompt builder."""

import json
import re
from typing import Any, Dict, List, Literal, Optional, TypedDict, Tuple

import google.generativeai as genai
from langgraph.graph import END, START, StateGraph

from prompts import (
    critic_prompt,
    format_transcript,
    interviewer_prompt,
    planner_prompt,
    srs_generation_prompt,
)


class AgentState(TypedDict, total=False):
    mode: Literal["chat", "srs"]
    api_key: str
    transcript_text: str
    next_node: str
    planner_text: str
    planner_data: Dict[str, Any]
    critic_text: str
    critic_data: Dict[str, Any]
    interviewer_text: str
    srs_text: str


def _safe_parse_json(raw_text: str) -> Dict:
    if not raw_text:
        return {}

    text = raw_text.strip()
    try:
        return json.loads(text)
    except Exception:
        pass

    match = re.search(r"```(?:json)?\s*(\{.*\})\s*```", text, flags=re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except Exception:
            return {}

    return {}


class PromptBuilderAgents:
    def __init__(self, model_name: str):
        self.model_name = model_name
        self.graph = self._build_orchestrator()

    def _model(self, api_key: str):
        genai.configure(api_key=api_key)
        return genai.GenerativeModel(self.model_name)

    def _generate(self, api_key: str, prompt_text: str) -> str:
        model = self._model(api_key)
        resp = model.generate_content(prompt_text)
        return (resp.text or "").strip()

    def _orchestrator(self, state: AgentState) -> AgentState:
        mode = state.get("mode")
        if mode == "chat":
            if not state.get("planner_text"):
                return {"next_node": "planner"}
            if not state.get("critic_text"):
                return {"next_node": "critic"}
            if not state.get("interviewer_text"):
                return {"next_node": "interviewer"}
            return {"next_node": END}

        if mode == "srs":
            if not state.get("srs_text"):
                return {"next_node": "srs_writer"}
            return {"next_node": END}

        return {"next_node": END}

    def _planner_node(self, state: AgentState) -> AgentState:
        planner_text = self._generate(
            state["api_key"],
            planner_prompt(state["transcript_text"]),
        )
        return {
            "planner_text": planner_text,
            "planner_data": _safe_parse_json(planner_text),
        }

    def _critic_node(self, state: AgentState) -> AgentState:
        critic_text = self._generate(
            state["api_key"],
            critic_prompt(state["transcript_text"], state.get("planner_text", "")),
        )
        return {
            "critic_text": critic_text,
            "critic_data": _safe_parse_json(critic_text),
        }

    def _interviewer_node(self, state: AgentState) -> AgentState:
        interviewer_text = self._generate(
            state["api_key"],
            interviewer_prompt(
                state["transcript_text"],
                state.get("planner_text", ""),
                state.get("critic_text", ""),
            ),
        )
        return {"interviewer_text": interviewer_text}

    def _srs_node(self, state: AgentState) -> AgentState:
        srs_text = self._generate(
            state["api_key"],
            srs_generation_prompt(state["transcript_text"]),
        )
        return {"srs_text": srs_text}

    def _route(self, state: AgentState) -> str:
        return state.get("next_node", END)

    def _build_orchestrator(self):
        graph_builder = StateGraph(AgentState)
        graph_builder.add_node("orchestrator", self._orchestrator)
        graph_builder.add_node("planner", self._planner_node)
        graph_builder.add_node("critic", self._critic_node)
        graph_builder.add_node("interviewer", self._interviewer_node)
        graph_builder.add_node("srs_writer", self._srs_node)

        graph_builder.add_edge(START, "orchestrator")
        graph_builder.add_conditional_edges(
            "orchestrator",
            self._route,
            {
                "planner": "planner",
                "critic": "critic",
                "interviewer": "interviewer",
                "srs_writer": "srs_writer",
                END: END,
            },
        )
        graph_builder.add_edge("planner", "orchestrator")
        graph_builder.add_edge("critic", "orchestrator")
        graph_builder.add_edge("interviewer", "orchestrator")
        graph_builder.add_edge("srs_writer", "orchestrator")

        return graph_builder.compile()

    def chat_reply(
        self,
        user_msg: str,
        history: List[Dict[str, str]],
        api_key: str,
    ) -> Tuple[Optional[str], Optional[Dict], Optional[str]]:
        if not api_key:
            return None, None, "Provide a Gemini API key in the sidebar."

        transcript = list(history) + [{"role": "user", "content": user_msg}]
        transcript_text = format_transcript(transcript)

        try:
            result = self.graph.invoke(
                {
                    "mode": "chat",
                    "api_key": api_key,
                    "transcript_text": transcript_text,
                }
            )

            planner_data = result.get("planner_data", {})
            critic_data = result.get("critic_data", {})

            agent_trace = {
                "planner": {
                    "known_requirements": planner_data.get("known_requirements", []),
                    "missing_dimensions": planner_data.get("missing_dimensions", []),
                    "risk_flags": planner_data.get("risk_flags", []),
                },
                "critic": {
                    "improved_question": critic_data.get("improved_question", ""),
                    "why_best_next": critic_data.get("why_best_next", ""),
                    "micro_probes": critic_data.get("micro_probes", []),
                },
            }
            return result.get("interviewer_text", ""), agent_trace, None
        except Exception as exc:
            return None, None, f"Gemini error: {exc}"

    def generate_srs(
        self,
        chat: List[Dict[str, str]],
        api_key: str,
    ) -> Tuple[Optional[str], Optional[str]]:
        if not api_key:
            return None, "Provide a Gemini API key in the sidebar."

        try:
            transcript_text = format_transcript(chat)
            result = self.graph.invoke(
                {
                    "mode": "srs",
                    "api_key": api_key,
                    "transcript_text": transcript_text,
                }
            )
            return result.get("srs_text", ""), None
        except Exception as exc:
            return None, f"Gemini error: {exc}"
