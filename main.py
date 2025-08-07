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
from soulmaker.bilibili_api import (
    get_ranking,
    get_random_video,
    search_videos,
    search_partition,
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

    @filter.command("bili_rank")
    async def bili_rank(self, event: AstrMessageEvent, rid: str = "0"):
        """View bilibili ranking for a partition."""

        videos = await get_ranking(int(rid))
        lines = [
            f"{idx + 1}. {v.get('title')} https://www.bilibili.com/video/{v.get('bvid')}"
            for idx, v in enumerate(videos[:10])
        ]
        yield event.plain_result("\n".join(lines))

    @filter.command("bili_random")
    async def bili_random(self, event: AstrMessageEvent):
        """Get a random popular video from bilibili."""

        video = await get_random_video()
        if not video:
            yield event.plain_result("未获取到视频")
            return
        yield event.plain_result(
            f"{video.get('title')} https://www.bilibili.com/video/{video.get('bvid')}"
        )

    @filter.command("bili_search")
    async def bili_search(self, event: AstrMessageEvent, keyword: str):
        """Search bilibili videos by keyword."""

        videos = await search_videos(keyword)
        lines = [
            f"{v.get('title')} https://www.bilibili.com/video/{v.get('bvid', v.get('id'))}"
            for v in videos[:5]
        ]
        yield event.plain_result("\n".join(lines) or "无结果")

    @filter.command("bili_partition")
    async def bili_partition(self, event: AstrMessageEvent, rid: str):
        """Search videos from a specific partition."""

        videos = await search_partition(int(rid))
        lines = [
            f"{v.get('title')} https://www.bilibili.com/video/{v.get('bvid')}"
            for v in videos[:5]
        ]
        yield event.plain_result("\n".join(lines) or "无结果")
