"""soulmaker 插件的行为跟踪模块。

此模块实现了思考-查询-决策循环来模拟虚拟角色"八奈见杏菜"的行为。

工作流程大致如下：
1. 基于当前状态和记忆生成思考。
2. 从模型输出中解析下一个行动。
3. 可选地调用外部API来收集信息。
4. 为下一轮累积新的上下文。
5. 保存最终的行为记录供日志模块使用。

该类被编写为框架无关的，因此可以轻松进行单元测试。
网络请求使用 ``httpx``，这是AstrBot插件中推荐的异步HTTP客户端。
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
    """表示过去的行为条目。"""

    start: str
    end: str
    activity: str


@dataclass
class Memory:
    """循环之间的可变记忆。"""

    last_query: str = ""
    last_api_results: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BehaviorState:
    """行为跟踪器的输入状态。"""

    current_time: str
    history: List[HistoryEntry] = field(default_factory=list)
    memory: Memory = field(default_factory=Memory)


@dataclass
class BehaviorRecord:
    """最终行为决策。"""

    start: str
    end: str
    activity: str
    cause: str
    mood: str
    notes: str


@dataclass
class NextAction:
    """模型提出的下一个行动。"""

    type: Literal["query", "final_decision", "idle"]
    content: Optional[str] = None
    behavior: Optional[BehaviorRecord] = None


@dataclass
class ThoughtOutput:
    """单次推理循环的输出。"""

    thought: str
    next_action: NextAction


class BehaviorTracker:
    """实现思考-查询-决策循环。"""

    def __init__(self, context: Context, data_dir: Optional[Path] = None) -> None:
        self.context = context
        self.data_dir = data_dir or Path("data")
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.log_path = self.data_dir / "behavior_log.json"

    # ------------------------------------------------------------------
    async def generate_thought(self, state: BehaviorState) -> ThoughtOutput:
        """使用LLM生成思考和下一个行动。

        提示词将角色特征、历史和记忆注入到模型中。
        模型预期返回一个匹配 :class:`ThoughtOutput` 的JSON字符串。
        """

        provider = self.context.get_using_provider()
        if provider is None:
            raise RuntimeError("未配置LLM提供者")

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
        # provider.text_chat 返回带有 .completion_text 的响应对象
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
        """基于下一个行动更新记忆或历史。"""

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
        """基于内容关键词调用简单的外部API。"""

        result: Dict[str, Any] = {}
        try:
            if "天气" in content:
                # wttr.in 提供免费文本天气
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
        except Exception as exc:  # pragma: no cover - 网络故障
            result["error"] = str(exc)
        return result

    # ------------------------------------------------------------------
    def accumulate_context(self, state: BehaviorState, output: ThoughtOutput) -> None:
        """为后续循环持久化中间状态。"""

        state.memory.last_api_results = getattr(state.memory, "last_api_results", {})
        # 此方法可以扩展为更丰富的上下文管理。

    # ------------------------------------------------------------------
    async def save_behavior(self, behavior: BehaviorRecord) -> None:
        """将行为记录追加到JSON日志文件。"""

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
        """执行完整的推理循环。"""

        output = await self.generate_thought(state)
        new_state = await self.parse_next_action(output, state)
        self.accumulate_context(new_state, output)
        return new_state
