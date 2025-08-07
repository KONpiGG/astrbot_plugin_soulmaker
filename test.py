import asyncio
import json
from pathlib import Path
import tempfile
import types
import sys

# Stub astrbot modules so BehaviorTracker can be imported without the real package
astrbot = types.ModuleType("astrbot")
api = types.ModuleType("astrbot.api")
star = types.ModuleType("astrbot.api.star")

class Context:  # minimal stand-in for AstrBot's Context
    pass

star.Context = Context
api.star = star
astrbot.api = api
sys.modules["astrbot"] = astrbot
sys.modules["astrbot.api"] = api
sys.modules["astrbot.api.star"] = star

from soulmaker.behavior_tracker import BehaviorTracker, BehaviorState, HistoryEntry, Memory


class DummyProvider:
    """Mock LLM provider returning a canned response."""

    async def text_chat(self, prompt, contexts, image_urls, func_tool):
        class Resp:
            def __init__(self, text: str) -> None:
                self.completion_text = text

        result = {
            "thought": "计划一下接下来的行动",
            "next_action": {
                "type": "final_decision",
                "behavior": {
                    "start": "10:00",
                    "end": "11:00",
                    "activity": "coding",
                    "cause": "实现新功能",
                    "mood": "focused",
                    "notes": "none",
                },
            },
        }
        return Resp(json.dumps(result, ensure_ascii=False))


class DummyContext:
    """Minimal context supplying the mock provider."""

    def get_using_provider(self):
        return DummyProvider()


async def main() -> None:
    context = DummyContext()
    with tempfile.TemporaryDirectory() as tmpdir:
        tracker = BehaviorTracker(context, data_dir=Path(tmpdir))
        history = [HistoryEntry(start="09:00", end="09:30", activity="reading")]
        memory = Memory(last_query="天气", last_api_results={"weather": "25°C"})
        state = BehaviorState(current_time="2024-05-04 10:00", history=history, memory=memory)
        new_state = await tracker.run_cycle(state)
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
        print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(main())