"""AstrBot plugin for generating behaviour traces of 八奈见杏菜."""

from __future__ import annotations

import json
from typing import List

from astrbot.api.event import AstrMessageEvent, filter
from astrbot.api.star import Context, Star, register

from soulmaker.behavior_tracker import (
    BehaviorTracker,
    BehaviorState,
    HistoryEntry,
    Memory,
)


@register("soulmaker", "YourName", "行为轨迹生成插件", "0.1.0")
class SoulmakerPlugin(Star):
    """Entry point for the behaviour tracking plugin."""

    def __init__(self, context: Context):
        super().__init__(context)
        self.tracker = BehaviorTracker(context)

    @filter.command("track")
    async def track(self, event: AstrMessageEvent, state_json: str):
        """Run one reasoning cycle with provided JSON state."""

        payload = json.loads(state_json)
        history: List[HistoryEntry] = [HistoryEntry(**h) for h in payload.get("history", [])]
        memory = Memory(**payload.get("memory", {}))
        state = BehaviorState(current_time=payload["current_time"], history=history, memory=memory)
        new_state = await self.tracker.run_cycle(state)
        result = {
            "thought_state": {
                "current_time": new_state.current_time,
                "history": [h.__dict__ for h in new_state.history],
                "memory": {
                    "last_query": new_state.memory.last_query,
                    "last_api_results": new_state.memory.last_api_results,
                },
            }
        }
        yield event.plain_result(json.dumps(result, ensure_ascii=False))
