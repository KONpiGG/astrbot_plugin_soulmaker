import asyncio
import json
import os
import sys
import types
from dataclasses import asdict
from pathlib import Path
import httpx

# ---------------------------------------------------------------------------
# Stub minimal astrbot modules so BehaviorTracker can be imported standalone
astrbot = types.ModuleType("astrbot")
api = types.ModuleType("astrbot.api")
star = types.ModuleType("astrbot.api.star")

provider = None  # will be set after provider class definition

class Context:  # minimal stand-in for AstrBot's Context
    def get_using_provider(self):
        return provider

star.Context = Context
api.star = star
astrbot.api = api
sys.modules["astrbot"] = astrbot
sys.modules["astrbot.api"] = api
sys.modules["astrbot.api.star"] = star

from soulmaker.behavior_tracker import (
    BehaviorTracker,
    BehaviorState,
    HistoryEntry,
    Memory,
)

# ---------------------------------------------------------------------------
# Simple provider performing direct OpenAI-compatible API calls
# DeepSeek R1 配置
API_KEY = os.environ.get("API_KEY", "sk-48e606513d554bc9bbca0bb6dfa650d7")
API_BASE_URL = os.environ.get(
    "API_BASE_URL", "https://api.deepseek.com/v1/chat/completions"
)
MODEL_NAME = os.environ.get("MODEL_NAME", "deepseek-reasoner")


class DirectAPIProvider:
    def __init__(self, api_key: str, base_url: str, model: str) -> None:
        self.api_key = api_key
        self.base_url = base_url
        self.model = model

    async def text_chat(self, prompt, contexts, image_urls, func_tool):
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
        }
        async with httpx.AsyncClient() as client:
            resp = await client.post(self.base_url, headers=headers, json=payload, timeout=60)
            resp.raise_for_status()
            data = resp.json()
            text = data["choices"][0]["message"]["content"]
        class Resp:
            def __init__(self, text: str) -> None:
                self.completion_text = text
        return Resp(text)


provider = DirectAPIProvider(API_KEY, API_BASE_URL, MODEL_NAME)
context = Context()
tracker = BehaviorTracker(context, data_dir=Path("data"))

# ---------------------------------------------------------------------------
# Test inputs that can be extended for different scenarios
TEST_CASES = [
    {
        "current_time": "14:30",
        "history": [
            {
                "start": "13:00",
                "end": "14:30",
                "activity": "睡午觉，梦到自己在吃烤肉",
            }
        ],
        "memory": {"last_query": None, "last_api_results": {}},
    },
    {
        "current_time": "20:00",
        "history": [
            {
                "start": "18:00",
                "end": "19:00",
                "activity": "在B站看番并吐槽",
            }
        ],
        "memory": {"last_query": "上海天气", "last_api_results": {}},
    },
]


async def run_case(case: dict) -> None:
    history = [HistoryEntry(**h) for h in case["history"]]
    
    # 确保 memory 是字典类型
    memory_data = case["memory"] if isinstance(case["memory"], dict) else {}
    memory = Memory(
        last_query=memory_data.get("last_query") or "",
        last_api_results=memory_data.get("last_api_results", {}),
    )
    state = BehaviorState(
        current_time=case["current_time"], history=history, memory=memory
    )
    output = await tracker.generate_thought(state)
    print(json.dumps({"thought": output.thought, "next_action": asdict(output.next_action)}, ensure_ascii=False, indent=2))
    await tracker.parse_next_action(output, state)


async def main() -> None:
    for idx, case in enumerate(TEST_CASES, 1):
        print(f"\n=== Test Case {idx} ===")
        try:
            await run_case(case)
        except Exception as exc:
            print(f"Error: {exc}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())