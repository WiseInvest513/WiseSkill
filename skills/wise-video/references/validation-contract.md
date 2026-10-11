# 计划校验契约 v1

`validate_plan.py` 是结构与遗漏检查，不是自然语言理解器，不证明计划正确或动画已经实现。

顶层：version=1、scope_caption_ids（本次全部原字幕ID）、entities、beats、coverage。

entities每项：id、name、identity_required(bool)、representation(icon/text/omit)、asset_status(ready/missing/review)、asset_id（ready/icon时）、fallback_approved(bool)、fallback_evidence（文字替代确认原话，仅已发生时填写）、reason（不配图/替代的内容理由）。非关键名词不强制配图。

beats每项：id、source_caption_ids、text（原条目文本顺序拼接）、entity_ids、meaning、kind(identity/relation_change/quantity_change/transfer/comparison/hold)、before、after、action、changes（变化属性列表）、acceptance（可观察验收描述）。变化属性允许：opacity、scale、position、distance、membership、count、direction、unit、grouping、focus、labels。关系/数量/转移/比较重点不能只有 opacity 或 scale。before/after不得相同，除非hold且有理由。计划只约束意图，实际渲染必须再观察。

coverage每项：caption_id、beat_ids、hold_reason。覆盖本范围每一条字幕，按语义指向beat或说明停留；不等于每条新建场景。正文范围变化后必须用新的scope，不能把没规划的新段排除来“通过”。

命令：`python3 scripts/validate_plan.py PLAN.json --captions captions.parsed.json`
原字幕数组项用 caption_id/start_ms/end_ms/text。本工具读取文件，无修改。退出0表示可进入实现；退出1列出计划缺口。带未知/未审核身份素材时不通过。缺口清单仍可先交用户，不必强行把计划改成通过。

## 状态与实现的接线

- 实现适配器必须读已检查的计划文件；输出中记录该文件SHA256与输入哈希。资产ID查索引，不能默认随手找图。
- 本Skill的 `scripts/render_plan.py` 可编译已编写的 `render_spec`，接口见 [渲染适配器](render-adapter.md)；它不会从语义描述自动推导动画。扩展适配器应读取同一计划，而不重写独立动作表；验收测试要修改一个计划动作并确认输出相应改变。
- 首先自动检查索引和几何/时间数据，再逐beat定位before/middle/after。距离检查可测对象中心间距，增多可测可见成员数，身份锚点可检查资产引用。不能仅凭验收文字存在就报告已验收。
- 产出semantic_qc.md：每beat计划的变化、实际快照/时间点、通过/失败/未验证及理由。带声音的审阅另记，静态截图不替代。


## 视觉承接与布局补充（制作时审阅）

在同一计划中补充逐句可见主体及其复用/聚焦/变换、对象进入与退出、归位后的占用区域、预期有意叠放和验收时间点。可引用已有对象ID和beat，避免复制动作表。具体字段适配本期实现；当前结构校验器不验证这些补充的几何/视觉正确性，不得将其退出0当作防堆叠证明。运行期观察方法见 [同屏布局与元素退场](layout-and-lifecycle.md)。
