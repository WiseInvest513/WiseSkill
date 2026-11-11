# 句子展示点硬门禁（可失败）

把「每句名词/动词都有素材落点、禁止无价值方框带过整句」收成必须失败的检查。
与 [版式硬门禁](layout-hard-gates.md) 并列：版式过关也不能代替本文件。

检查入口：Skill 安装目录下的 `scripts/audit_sentence_display_points.py`。
片尾另见 [收尾对标](outro-parity.md)。

设计方法直接读随包 [素材展示](asset-display-methods.md) 与 [动作方法](motion-methods.md)；来源归因见 [可选外部参考](external-methods.md)。不依赖外部笔记或作者历史工程。

## 0. 何时 FAIL

下列任一项成立 → 验收失败，**禁止宣称画面表达通过 / 禁止在未修前 encode 代表样片当合格**。脚本能识别的项输出 `status=fail`；实际帧发现的其他问题也须记录为失败并修复。
`validate_plan` / `audit_layout_hard_gates` 退出 0 一律不算过关。

自动扫描主要使用 HTML、计划和 cue 的启发式证据，不能证明图像内容正确、路径真的传意、最终可读性或完整的运动质量。新增语义必须有完整 `sentence_states`、概念清单及实际播放检查；不能省略输入或只增加 class/ID 取得绿色报告。对象构图中心等尚未自动覆盖的项按下文人工/DOM 复核，脚本通过只是必要条件。

## 1. sentence_display_points

对每个 `sentence_states[]`（或等价完整语义句）：

1. 从口播/`text`/`meaning_delta` 识别**信息性名词**与**动词/状态变化**（买入、卖出、传导、回撤、加息、比较、汇聚…）。连接语、纯语气词可忽略。
2. 每个信息性名词必须绑定至少一种展示点：
   - `exact_identity` / `concept_asset` → 已核对的实际 `<img>`、可辨识道具或代码图形；若本期有相容素材库可复用
   - `data_chart` → 可见数值/条/曲线主体（不能只有写在方框里的数字）
   - `relationship` → 路径/箭头/归属线等可观察关系
   - `text` 仅当盘点写明文字足够且依附某已有主体
3. 每个动词/状态变化必须有**可见动作或状态差**（位置/成员/方向/数量/路径），不能只有同名字卡淡入。
4. **整句被单一文本方框/卡片覆盖**（该句可见主体只有 `.claim`/`.card`/文本 pill，无 prop/img/chart/path）→ FAIL `sentence_covered_by_lone_box`。
5. **整句只剩上一句留下的身份徽章**（例如单独一枚「纳指100」，没有为本句提供名词+动词场景）→ FAIL `sentence_covered_by_stale_identity`。按实际口播区间检查：脚本可读 cue 在 caption 中点的 opacity，人工还需看变化前后和正速播放，不能只看 `focus_object_ids` 是否存在于 HTML。例：从“买前纠结进场”转到“赚钱后纠结卖出”，只保留同一枚身份徽章没有表达新的问题。
6. 口播正在说卖出 / 等跌 10% / 买回等动作时，画面上的关系路径若没有邻近标签、也不能让人读出该动作 → FAIL `unlabeled_stroke`。大账户板标题不算路径标签；无标签的残留曲线不能覆盖多个不同动词。

新计划在 `sentence_states[]` 显式连接展示点；以下片段嵌入本期真实句子，ID 要与实现一致：

```json
"display_points": [
  {"token": "纳指", "role": "noun", "kind": "exact_identity", "object_id": "nasdaqProp"},
  {"token": "卖出", "role": "verb", "kind": "relationship", "object_id": "exitPath"}
]
```

旧工程无该字段时，审计器从 `focus_object_ids` + HTML 类名/`<img>` 做启发式推断，部分证据不足会 FAIL `display_points_unproven`（新制作默认严格）。有字段并不证明对象在本句可见，`kind=relationship` 也不证明动作已执行；仍需检查真实状态。完整契约见 [计划校验](validation-contract.md)。

## 2. no_decorative_boxes

可见的 framed 面板（`.claim` / `.card` / `.board` / `.chip` 等）若同时满足：

- 无 `<img>` / `.prop` 子资产 / SVG 关系路径 / 数据主体；
- 文案极短（如 ≤ 8 个汉字或纯装饰标题）；
- 未登记为章节牌/必要导航；

→ FAIL `decorative_box`。

允许：章牌、等宽步骤板且板上有编号+主张并有配套 prop、数据卡且数字本身是 `data_chart` 主体。

## 3. object_composition_center

在确认地球背景下：

- 计算**对象构图中心**：仅对 `.prop` / 主图 / chart / relationship 端点（排除纯文本 claim 栈）取并集中心。
- 若存在 ≥1 个 prop/img 主体，则对象构图 `center_x/canvas_w` 须 ∈ **[0.46, 0.54]**（与版式硬门禁地板一致）；纯文本栈把并集“抬”到中线但对象全在左侧 → FAIL `object_composition_left_bias`。
- 若句内本应有 concept_asset 却零 prop，先按 §1 FAIL，不再用文本栈中心冒充居中。

DOM 测量可复用 Skill 的 `scripts/measure_layout_dom.cjs`，再按主体 ID 分组计算；无 DOM 时按 HTML 内联 `left`/`transform` 做静态近似并用实际帧复核。本节是验收标准，当前句子展示点扫描器不计算对象中心，不能把它的 `pass` 当成中心已检查。

## 4. 与版式硬门禁的关系

- 堆叠、同级等大、隐喻、生命周期：**仍以** `audit_layout_hard_gates.py` 为准。
- 本文件检查「有结构却无素材落点 / 方框带过 / 假居中 / 只剩身份徽章 / 未标注动作路径 / 收尾不对标」；其中对象中心仍需另行测量，脚本覆盖以报告与覆盖说明为准。
- encode 前两者都要 `status=pass`（新语义重建 / 用户已点名的画质重修）；实际画面发现的失败也须修复。系列顶栏和片尾另按对应指南检查。

## 5. 命令

先按 [运行依赖与路径](runtime-and-paths.md) 设置 `SKILL_DIR`（Skill 安装目录）和 `EP`（本期工作目录）。下面是本期文件的示例位置，按真实产物调整；脚本不要求从项目根目录运行。

```sh
mkdir -p "$EP/qa"
python3 "$SKILL_DIR/scripts/audit_sentence_display_points.py" \
  --html "$EP/composition/index.html" \
  --plan "$EP/plan/semantic_plan.json" \
  --inventory "$EP/planning/concept-inventory.json" \
  --cues "$EP/composition/cue_sheet.json" \
  --captions "$EP/intake/captions.local.json" \
  --out "$EP/qa/sentence-display-points.json"
```

`--cues` 和 `--captions` 指向本期真实时间数据；引擎使用其他形式时先提供等价导出或实际逐句取帧证据，不能把无法检查的时间覆盖记成通过。

有片尾的完整片先按 [收尾对标](outro-parity.md) 取得浏览器实际 DOM 证据，再加 `--check-outro --dom-evidence "$EP/qa/dom.json" --outro-times "片尾取样秒数"`；原文含电报/交流群引导时再加 `--require-tg`。系列同时按 [系列顶栏](series-chrome.md) 加 `--check-series --episode 实际期数 --topic "本期主题"`。各时间点来自本片原声，不能沿用历史示例秒数。没有所需 DOM 证据会保留未检查状态，不算通过。局部样片不包含片尾时不为通过审计擅加片尾。

正常执行退出 0 = 脚本 pass；1 = fail 或所需证据未检查；2 = 工具/输入错误，结合报告状态阅读。验收不使用 `--legacy-soft` 或 `--expect-fail` 改写通过条件；后者只用于隔离回归证明坏例被检出。新引擎若不适配 HTML 扫描，应记录工具未适配及等价人工证据，不能冒称原脚本已通过。自动覆盖范围和局限见 [自动检查覆盖](automation-coverage.md)。

## 6. 多层多主体的使用边界

一句需要多个参与者时，让各主体配合路径或状态变化。说明板可展示细节，共同机制可跨句持续；不强制增加对象数量，也不以高亮替代原文要求的实际动作。读 [素材展示](asset-display-methods.md) 获取完整执行方法。

次级形式参考来自用户指定的轩辕频道，归因在 [外部方法](external-methods.md)。使用 Wise 模板时继续米白/蓝金，不复制第三方角色、暗色科技网格或未授权素材。
