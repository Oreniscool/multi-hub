"""Agent orchestration for MultiHub prompt builder."""

import json
import os
import re
from typing import Any, Callable, Dict, List, Literal, Optional, TypedDict, Tuple

from groq import Groq
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
        self.groq_api_key = os.getenv("GROQ_API_KEY", "").strip()
        self.client = Groq(api_key=self.groq_api_key) if self.groq_api_key else None
        self.graph = self._build_orchestrator()

    def _generate(self, prompt_text: str) -> str:
        if not self.client:
            raise ValueError("AI backend is not configured on the server.")

        resp = self.client.chat.completions.create(
            model=self.model_name,
            messages=[{"role": "user", "content": prompt_text}],
            temperature=0.2,
        )
        return ((resp.choices[0].message.content or "") if resp.choices else "").strip()

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
            planner_prompt(state["transcript_text"]),
        )
        return {
            "planner_text": planner_text,
            "planner_data": _safe_parse_json(planner_text),
        }

    def _critic_node(self, state: AgentState) -> AgentState:
        critic_text = self._generate(
            critic_prompt(state["transcript_text"], state.get("planner_text", "")),
        )
        return {
            "critic_text": critic_text,
            "critic_data": _safe_parse_json(critic_text),
        }

    def _interviewer_node(self, state: AgentState) -> AgentState:
        interviewer_text = self._generate(
            interviewer_prompt(
                state["transcript_text"],
                state.get("planner_text", ""),
                state.get("critic_text", ""),
            ),
        )
        return {"interviewer_text": interviewer_text}

    def _srs_node(self, state: AgentState) -> AgentState:
        srs_text = self._generate(
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
        status_callback: Optional[Callable] = None,
    ) -> Tuple[Optional[str], Optional[Dict], Optional[str]]:
        if not self.client:
            return None, None, "AI backend is not configured on the server."

        transcript = list(history) + [{"role": "user", "content": user_msg}]
        transcript_text = format_transcript(transcript)

        try:
            final_state = {
                "mode": "chat",
                "transcript_text": transcript_text,
            }
            for event in self.graph.stream(final_state):
                for node_name, state_update in event.items():
                    if status_callback:
                        status_callback(node_name)
                    final_state.update(state_update)

            planner_data = final_state.get("planner_data", {})
            critic_data = final_state.get("critic_data", {})

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
            return final_state.get("interviewer_text", ""), agent_trace, None
        except Exception as exc:
            return None, None, f"Groq error: {exc}"

    def generate_srs(
        self,
        chat: List[Dict[str, str]],
    ) -> Tuple[Optional[str], Optional[str]]:
        if not self.client:
            return None, "AI backend is not configured on the server."

        try:
            transcript_text = format_transcript(chat)
            result = self.graph.invoke(
                {
                    "mode": "srs",
                    "transcript_text": transcript_text,
                }
            )
            return result.get("srs_text", ""), None
        except Exception as exc:
            return None, f"Groq error: {exc}"
