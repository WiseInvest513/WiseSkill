# 计划校验契约 v1

`validate_plan.py` 是结构与遗漏检查，不是自然语言理解器，不证明计划正确或动画已经实现。

顶层：version=1、scope_caption_ids（本次全部原字幕ID）、entities、beats、coverage。

entities每项：id、name、identity_required(bool)、representation(icon/text/omit)、asset_status(ready/missing/review)、asset_id（ready/icon时）、fallback_approved(bool)、fallback_evidence（文字替代确认原话，仅已发生时填写）、reason（不配图/替代的内容理由）。非关键名词不强制配图。

beats每项：id、source_caption_ids、text（原条目文本顺序拼接）、entity_ids、meaning、kind(identity/relation_change/quantity_change/transfer/comparison/hold)、before、after、action、changes（变化属性列表）、acceptance（可观察验收描述）。变化属性允许：opacity、scale、position、distance、membership、count、direction、unit、grouping、focus、labels。关系/数量/转移/比较重点不能只有 opacity 或 scale。before/after不得相同，除非hold且有理由。计划只约束意图，实际渲染必须再观察。

coverage每项：caption_id、beat_ids、hold_reason。覆盖本范围每一条字幕，按语义指向beat或说明停留；不等于每条新建场景。正文范围变化后必须用新的scope，不能把没规划的新段排除来“通过”。

命令：`python3 scripts/validate_plan.py PLAN.json --captions captions.parsed.json`
原字幕数组项用 caption_id/start_ms/end_ms/text。本工具读取文件，无修改。退出0只表示结构检查通过，可制作视觉小样，不是批量导出许可或设计合格证明；退出1列出计划缺口。带未知/未审核身份素材时不通过。缺口清单仍可先交用户，不必强行把计划改成通过。

随后运行 `python3 scripts/audit_visual_plan.py PLAN.json --out EP/qa/visual-plan-audit.json`，审阅重复占位语义、统一进场、常驻备注和主视觉降级候选。新制作计划再加 `--require-sentence-states`，检查下面的状态绑定。退出0表示扫描完成；必须读取 JSON 中的 `status` 和 `findings`，`review_required` 不能当作通过。该工具不评美，不改录音/字幕。按 [视觉设计](visual-direction.md) 看实际样张后，在项目 `design-review.md` 记录具体判断和证据。不是继续加字段就算完成。

## 状态与实现的接线

- 实现适配器必须读已检查的计划文件；输出中记录该文件SHA256与输入哈希。资产ID查索引，不能默认随手找图。
- 本Skill提供 `render_plan.py` 计划编译器，见 [接口](render-adapter.md)。它不会替你选择素材或构图。需要扩展时读取同一计划，不重写独立动作表；验收要确认一个计划动作修改能影响实际输出。
- 首先自动检查索引和几何/时间数据，再逐beat定位before/middle/after。距离检查可测对象中心间距，增多可测可见成员数，身份锚点可检查资产引用。不能仅凭验收文字存在就报告已验收。
- 产出semantic_qc.md：每beat计划的变化、实际快照/时间点、通过/失败/未验证及理由。带声音的审阅另记，静态截图不替代。


## 视觉承接与布局补充（制作时审阅）

新计划的句间决策写在同一计划的 `sentence_states` 中（按完整语义句/转折，不按每条半句字幕强拆）：`scene_id`、`caption_ids`、`meaning_delta`、`focus_object_ids`、`retain[{object_id,reason}]`、`retire_object_ids`、`handoff`、`end_state`。审阅帧另记 `target_caption_id`、绝对 `time_ms`；当前承接句列在 `caption_ids`，只作理解背景的上文列在 `context_caption_ids`，不能把上下文全部宣称为此帧已覆盖。

焦点引用本场真实对象；比较/关系可由多个对象共同承担，用 `focus_reason` 解释共同理解任务，不强制“一句只能一个主体”。retain 每项理由必须对应该 ID 当前承担的任务，不从另一个对象复制。退出对象可引用计划中前场对象。停留沿用既有对象和阅读理由，不复制动作表，也不强制每句换图。

`audit_visual_plan.py` 现在检查场景/对象引用、空焦点、无共同任务说明却几乎全选前景的候选，以及 retain 的未知/重复 ID 和空理由。严格选项另检查每场有状态、审阅字幕属于当前句、审阅时间存在。旧计划没有 states 时默认兼容；报告会明示未扫描该层。**脚本不判断理由语义是否对应、时间是否与原声同步，也不能验证实际焦点与对比度。** `validate_plan.py` 与编译器仍不执行 states；决策必须落实进 render_spec/actions，并在真实输出中核对。

先用它审阅新增意思是否独立体现、当前重点是否成立、旧载体是否该退场；图形存在/相关/表达完整是三个不同结论。字段填全不能得到语义通过，现有项目也不能仅回填这些文字就宣称修复。交付前将原字幕句、实际审阅帧及第一眼看到的重点对照记录；相符才记通过，不能抄计划的 focus 字段作为观察结果。

在同一计划中补充逐句可见主体及其复用/聚焦/变换、对象进入与退出、归位后的占用区域、预期有意叠放和验收时间点。可引用已有对象ID和beat，避免复制动作表。具体字段适配本期实现；当前结构校验器不验证这些补充的几何/视觉正确性，不得将其退出0当作防堆叠证明。运行期观察方法见 [同屏布局与元素退场](layout-and-lifecycle.md)。
