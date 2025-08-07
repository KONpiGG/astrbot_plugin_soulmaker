# Soulmaker Behavior Tracker

AstrBot 插件：模拟虚拟角色 **八奈见杏菜** 的行为轨迹。

该插件实现 `Thought-Query-Decision` 循环，通过多轮思考与外部信息
查询生成结构化的行为记录，供其它模块如日志生成器使用。

## 指令

- `/track <json>` 运行一次推演循环。指令参数为行为状态 JSON，格式
  参考 `soulmaker.behavior_tracker.BehaviorState`。
- `/bili_rank [rid]` 查看 B 站排行榜（可选分区 `rid`）。
- `/bili_random` 随机推荐一个热门视频。
- `/bili_search <关键词>` 搜索指定视频。
- `/bili_partition <rid>` 查看指定分区的最新视频。

## 依赖

- `httpx` 用于访问外部 API。

## 参考

更多 AstrBot 插件开发信息请查阅 [文档](https://astrbot.app)。
