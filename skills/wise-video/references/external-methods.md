# 外部方法与实测依据

> 历史验证说明：文中的旧测试项目仅是当时的验证记录；原工作区已按用户要求精简归档，这些工程不随包提供，也不是运行依赖。新内容在本期工作区重新验证。

本Skill统一维护视频流程。执行所需方法已随包提供：[素材展示](asset-display-methods.md)、[动作方法](motion-methods.md)、[设计到动效](design-to-motion.md)。无需克隆外部仓库或安装额外 Skill；以下链接只说明历史学习来源，外链不可用不阻断制作。外部默认风格、权限或审批要求不带入本流程。

本文及上述指南是针对 Wise 制作任务重新编写的决策方法，不随包复制上游完整文档、代码、视频或素材。引用不等于取得第三方素材使用许可；如需使用具体代码或资产，另核实其来源、许可和本次授权。

- [HyperFrames Beat Direction](https://github.com/heygen-com/hyperframes/blob/main/skills/hyperframes-creative/references/beat-direction.md)：先明确观众要理解的变化，再让对象承担动作。
- [HyperFrames Video Composition](https://github.com/heygen-com/hyperframes/blob/main/skills/hyperframes-creative/references/video-composition.md) 与 [Remotion Video Layout](https://github.com/remotion-dev/skills/blob/main/skills/remotion-best-practices/remotion-create/video-layout.md)：建立观看主次，按可见主体而非盒子决定尺度。保留原有引擎。
- [SVG Icon Enrichment](https://github.com/heygen-com/hyperframes/blob/main/skills/hyperframes-animation/rules/svg-icon-enrichment.md) / [Control–Target Sync](https://github.com/heygen-com/hyperframes/blob/main/skills/hyperframes-animation/rules/control-target-sync.md)：有意义的部件运动，以及控制提示与目标同步。
- [Remotion Captions](https://github.com/remotion-dev/skills/blob/main/skills/remotion-best-practices/remotion-captions/REFERENCE.md)：保留时间化文本，字幕精度不能超过源数据。
- [用户参考教程](https://invest-nav.com/tutorials/ai-tutorials/text/codex-ai-video-editing-workflow/)：先用实际分镜图验证表达，保留独立素材与可编辑文字；再针对已发现的问题局部修订，设计稳定后处理动画。2026-10-12 实际阅读教程并查看第一版、第一轮和第二轮改版示例，未观看示例视频；不同镜头的示例不能冒称严格同镜前后对比。迁移方法已落实到 [视觉设计与迭代](visual-direction.md)，不照搬纸张、字体、人物、默认加框或多入口架构。

## 2026-10-11 的三轮本地回归

以下为作者本地历史实测摘要。历史工程、原声、成片和审阅证据不随包分发；这些记录说明方法来源，不能当作新安装已运行或可用输入。

三轮使用同一63条原字幕、121.2秒原声、冻结背景与已选开场：

- V1：当前方法，实际发现主体空档、图示太小、原计划验收数值漂移。
- V2：主体和承载面调整、股票支持关系拆开呈现。复查发现支持箭头可能误读为兑换，聚焦美股后分支不明确，整组淡化让承载面也失效。
- V3：保持父节点、逐个展开相连选择；支持关系明确；否定与股价参照显现；导航游标联动。独立复查发现“苹果、特斯拉”被概括，已恢复具体名称；运动中间态接触另行修复。

复用上述判断方法，不复用币安特定结论和坐标。每条字幕有对象不等于所有语义细节都保留；库存Logo不负责解释权利性质；短标签能消除歧义，无需追求彻底无文字。

历史证据分别记录于该项目各版本的 QA、比较报告、工具验证和前向演练中，未包含在本分发包。语义、几何、技术、音频内容核对分开记录；本次原声一致性可验证，未独立整片听审。旧题材测试和短新题材计划演练不能证明所有5–10分钟新片都无须检查。


前向演练还发现“仅24秒正文请求5分钟”被接入工具扩展到300秒的问题，已修复并加反例测试。whole-cues按已提供内容截止，exact超源保持pending；接线检查从原文独立重算源末尾，不能用自填ready绕过。新题材只验证规划，不伪造5分钟正文。

## 2026-10-12 实际失败带来的修订

BBAE 第一阶段技术检查通过后被用户否定审美和表达。可复用失误：用整场对象绑定制造覆盖率、批量复制通用语义字段、同一入场动作充当多数编排、制作备注形成第二字幕、库存建筑替代地理位置、同组主图完成度不一致。

本次不靠增加“丰富/优雅”等形容词解决：先运行设计退化候选扫描，再从新文稿选择代表镜头、制作真实样张、按已接受素材检查、定点修正；将内部审阅与上屏文案分开。结构检查、视觉审阅、运动实测各有结论，不能互相代替。具体品牌、坐标和费用关系留项目，不写成通用镜头模板。


## 2026-11 的方法整理与可选来源

下面是当时参考资料中的方法方向，不声称链接仍对应当前最新版。上方具体文档路径也属于历史归因；目录变化时可从项目首页查找，执行本 Skill 不需要打开它们。

| 可选来源 | 吸收的判断方法 | 随包执行入口 |
| --- | --- | --- |
| [HyperFrames](https://github.com/heygen-com/hyperframes) 的 motion / review 方法 | 转场有场内依据，按角色选缓动，拒绝以漂浮代替语义变化，检查实际前中后态 | [动作方法](motion-methods.md) |
| [mhuot/explainer-video-skill](https://github.com/mhuot/explainer-video-skill) | 路径表达流向；稿件、声音和画面使用同一时间依据 | [设计到动效](design-to-motion.md) |
| [remotion-code-motion-explainer](https://github.com/vibe-motion/remotion-code-motion-explainer) | 语句中的对象、动作、数量和关系分别承担可见任务，保留对象身份 | [素材展示](asset-display-methods.md) |
| [OpenMontage](https://github.com/OpenMontageInc/OpenMontage) 的 scene / asset director 方法 | 在制作前列具体素材需要，检查文字到画面的缺口 | [概念盘点](concept-inventory.md)、[素材展示](asset-display-methods.md) |
| [Clueso Skills](https://github.com/clueso-ai/skills) 的 explain-it-simply / end-card 方法 | 按比较、过程、数据等内容选择处理方式，片尾围绕清楚的行动 | [素材展示](asset-display-methods.md)、[收尾对标](outro-parity.md) |
| [轩辕的编程宇宙](https://www.youtube.com/@xuanyuancoding/videos)，用户指定的次级形式参考 | 同句多个对象按需配合、关系路径、分层说明、跨句保留同一机制 | [素材展示](asset-display-methods.md)、[句子展示点](sentence-display-points.md) |

借鉴结构，不迁移第三方调色、角色、材质或预设。使用 Wise 模板时保持其米白、深蓝、金色与已确认素材；已有其他风格时延续该项目决定。任何来源都不能覆盖用户最新范围、原声完整性和本期事实边界。
