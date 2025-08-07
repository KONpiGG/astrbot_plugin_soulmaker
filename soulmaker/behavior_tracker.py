"""Behavior tracking module for soulmaker plugin.

This module implements a Thought-Query-Decision loop to simulate the
behaviour of the virtual character "八奈见杏菜".

The workflow roughly follows:
1. Generate a thought based on current state and memory.
2. Parse the next action from model output.
3. Optionally call external APIs to gather information.
4. Accumulate new context for the next round.
5. Save final behaviour records for logging modules.

The class is written to be framework agnostic so it can be easily unit
tested.  Network requests use ``httpx`` which is the recommended async
HTTP client in AstrBot plugins.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Literal
import json
import httpx

from astrbot.api.star import Context


@dataclass
class HistoryEntry:
    """Represents a past behaviour entry."""

    start: str
    end: str
    activity: str


@dataclass
class Memory:
    """Mutable memory between cycles."""

    last_query: str = ""
    last_api_results: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BehaviorState:
    """Input state for the behaviour tracker."""

    current_time: str
    history: List[HistoryEntry] = field(default_factory=list)
    memory: Memory = field(default_factory=Memory)


@dataclass
class BehaviorRecord:
    """Final behaviour decision."""

    start: str
    end: str
    activity: str
    cause: str
    mood: str
    notes: str


@dataclass
class NextAction:
    """Next action proposed by the model."""

    type: Literal["query", "final_decision", "idle"]
    content: Optional[str] = None
    behavior: Optional[BehaviorRecord] = None


@dataclass
class ThoughtOutput:
    """Output of a single reasoning cycle."""

    thought: str
    next_action: NextAction


class BehaviorTracker:
    """Implements the Thought-Query-Decision loop."""

    def __init__(self, context: Context, data_dir: Optional[Path] = None) -> None:
        self.context = context
        self.data_dir = data_dir or Path("data")
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.log_path = self.data_dir / "behavior_log.json"

    # ------------------------------------------------------------------
    async def generate_thought(self, state: BehaviorState) -> ThoughtOutput:
        """Use the LLM to generate a thought and next action.

        The prompt injects character traits, history and memory into the
        model.  The model is expected to return a JSON string that matches
        :class:`ThoughtOutput`.
        """

        provider = self.context.get_using_provider()
        if provider is None:
            raise RuntimeError("No LLM provider configured")

        history_text = "\n".join(
            f"{h.start}-{h.end}: {h.activity}" for h in state.history
        )
        memory_text = json.dumps(state.memory.last_api_results, ensure_ascii=False)
        prompt = (
            "你是八奈见杏菜，懒散但细腻。"
            f"现在时间 {state.current_time}。今天的记录:\n{history_text}\n"
            f"上次查询: {state.memory.last_query}，结果: {memory_text}\n"
            "请输出一个 JSON，包含 thought 和 next_action。"
        )

        resp = await provider.text_chat(prompt=prompt, contexts=[], image_urls=[], func_tool=None)
        # provider.text_chat returns response object with .completion_text
        raw = resp.completion_text if hasattr(resp, "completion_text") else str(resp)
        data = json.loads(raw)
        next_action = data.get("next_action", {})
        behavior = (
            BehaviorRecord(**next_action["behavior"]) if next_action.get("type") == "final_decision" and next_action.get("behavior") else None
        )
        action = NextAction(
            type=next_action.get("type", "idle"),
            content=next_action.get("content"),
            behavior=behavior,
        )
        return ThoughtOutput(thought=data.get("thought", ""), next_action=action)

    # ------------------------------------------------------------------
    async def parse_next_action(self, output: ThoughtOutput, state: BehaviorState) -> BehaviorState:
        """Update memory or history based on the next action."""

        action = output.next_action
        if action.type == "query" and action.content:
            state.memory.last_query = action.content
            api_result = await self.call_external_api(action.content)
            state.memory.last_api_results = api_result
        elif action.type == "final_decision" and action.behavior:
            state.history.append(HistoryEntry(
                start=action.behavior.start,
                end=action.behavior.end,
                activity=action.behavior.activity,
            ))
            await self.save_behavior(action.behavior)
        return state

    # ------------------------------------------------------------------
    async def call_external_api(self, content: str) -> Dict[str, Any]:
        """Call a simple external API based on content keywords."""

        result: Dict[str, Any] = {}
        try:
            if "天气" in content:
                # wttr.in provides free text weather
                url = f"https://wttr.in/{content.replace('天气', '').strip()}?format=j1"
                async with httpx.AsyncClient() as client:
                    resp = await client.get(url, timeout=10)
                    data = resp.json()
                    result["weather"] = data["current_condition"][0]["temp_C"] + "°C"
            elif "B站" in content or "Bilibili" in content:
                url = "https://tenapi.cn/v2/bilibili"
                async with httpx.AsyncClient() as client:
                    resp = await client.get(url, timeout=10)
                    result["bilibili"] = resp.json()
            else:
                result["info"] = "no_api"
        except Exception as exc:  # pragma: no cover - network failure
            result["error"] = str(exc)
        return result

    # ------------------------------------------------------------------
    def accumulate_context(self, state: BehaviorState, output: ThoughtOutput) -> None:
        """Persist intermediate state for subsequent cycles."""

        state.memory.last_api_results = getattr(state.memory, "last_api_results", {})
        # This method can be expanded for richer context management.

    # ------------------------------------------------------------------
    async def save_behavior(self, behavior: BehaviorRecord) -> None:
        """Append the behaviour record to a JSON log file."""

        records: List[Dict[str, Any]] = []
        if self.log_path.exists():
            try:
                records = json.loads(self.log_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                records = []
        records.append(behavior.__dict__)
        self.log_path.write_text(
            json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    # ------------------------------------------------------------------
    async def run_cycle(self, state: BehaviorState) -> BehaviorState:
        """Execute a full reasoning cycle."""

        output = await self.generate_thought(state)
        new_state = await self.parse_next_action(output, state)
        self.accumulate_context(new_state, output)
        return new_state
