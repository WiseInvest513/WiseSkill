# 外部方法与实测依据

本Skill统一维护本项目的视频流程。以下是参考方法，不是新的调用入口，也不把外部默认风格、权限或审批要求带入本项目。

- [HyperFrames Beat Direction](https://github.com/heygen-com/hyperframes/blob/main/skills/hyperframes-creative/references/beat-direction.md)：先明确观众要理解的变化，再让对象承担动作。
- [HyperFrames Video Composition](https://github.com/heygen-com/hyperframes/blob/main/skills/hyperframes-creative/references/video-composition.md) 与 [Remotion Video Layout](https://github.com/remotion-dev/skills/blob/main/skills/remotion-best-practices/remotion-create/video-layout.md)：建立观看主次，按可见主体而非盒子决定尺度。保留原有引擎。
- [SVG Icon Enrichment](https://github.com/heygen-com/hyperframes/blob/main/skills/hyperframes-animation/rules/svg-icon-enrichment.md) / [Control–Target Sync](https://github.com/heygen-com/hyperframes/blob/main/skills/hyperframes-animation/rules/control-target-sync.md)：有意义的部件运动，以及控制提示与目标同步。
- [Remotion Captions](https://github.com/remotion-dev/skills/blob/main/skills/remotion-best-practices/remotion-captions/REFERENCE.md)：保留时间化文本，字幕精度不能超过源数据。
- [用户参考教程](https://invest-nav.com/tutorials/ai-tutorials/text/codex-ai-video-editing-workflow/)：连续图解保留位置和关系，调整文字后重排。无需照搬其每一步手动确认或特定配色。

## 2026-10-11 的三轮本地回归

以下为作者本地历史实测摘要。历史工程、原声、成片和审阅证据不随包分发；这些记录说明方法来源，不能当作新安装已运行或可用输入。

三轮使用同一63条原字幕、121.2秒原声、冻结背景与已选开场：

- V1：当前方法，实际发现主体空档、图示太小、原计划验收数值漂移。
- V2：主体和承载面调整、股票支持关系拆开呈现。复查发现支持箭头可能误读为兑换，聚焦美股后分支不明确，整组淡化让承载面也失效。
- V3：保持父节点、逐个展开相连选择；支持关系明确；否定与股价参照显现；导航游标联动。独立复查发现“苹果、特斯拉”被概括，已恢复具体名称；运动中间态接触另行修复。

复用上述判断方法，不复用币安特定结论和坐标。每条字幕有对象不等于所有语义细节都保留；库存Logo不负责解释权利性质；短标签能消除歧义，无需追求彻底无文字。

历史证据分别记录于该项目各版本的 QA、比较报告、工具验证和前向演练中，未包含在本分发包。语义、几何、技术、音频内容核对分开记录；本次原声一致性可验证，未独立整片听审。旧题材测试和短新题材计划演练不能证明所有5–10分钟新片都无须检查。


前向演练还发现“仅24秒正文请求5分钟”被接入工具扩展到300秒的问题，已修复并加反例测试。whole-cues按已提供内容截止，exact超源保持pending；接线检查从原文独立重算源末尾，不能用自填ready绕过。新题材只验证规划，不伪造5分钟正文。
