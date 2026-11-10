# 句子展示点硬门禁（可失败）

把「每句名词/动词都有素材落点、禁止无价值方框带过整句」收成必须失败的检查。
与 [版式硬门禁](layout-hard-gates.md) 并列：版式过关也不能代替本文件。

检查入口：`scripts/audit_sentence_display_points.py`。
片尾另见 [收尾对标](outro-parity.md)。

方法来源（结构，不抄画风）：`_external/skill-asset-display-learning.md` 所记
remotion-code-motion-explainer（clause→actors）、OpenMontage scene/asset directors
（required_assets）、clueso beat-type / end-card。

## 0. 何时 FAIL

下列任一项成立 → 审计 `status=fail`，**禁止宣称画面表达通过 / 禁止在未修前 encode 代表样片当合格**。
`validate_plan` / `audit_layout_hard_gates` 退出 0 一律不算过关。

## 1. sentence_display_points

对每个 `sentence_states[]`（或等价完整语义句）：

1. 从口播/`text`/`meaning_delta` 识别**信息性名词**与**动词/状态变化**（买入、卖出、传导、回撤、加息、比较、汇聚…）。连接语、纯语气词可忽略。
2. 每个信息性名词必须绑定至少一种展示点：
   - `exact_identity` / `concept_asset` → 实际 `<img>` 或 wise-3d prop / 已备素材图
   - `data_chart` → 可见数值/条/曲线主体（不能只有写在方框里的数字）
   - `relationship` → 路径/箭头/归属线等可观察关系
   - `text` 仅当盘点写明文字足够且依附某已有主体
3. 每个动词/状态变化必须有**可见动作或状态差**（位置/成员/方向/数量/路径），不能只有同名字卡淡入。
4. **整句被单一文本方框/卡片覆盖**（该句可见主体只有 `.claim`/`.card`/文本 pill，无 prop/img/chart/path）→ FAIL `sentence_covered_by_lone_box`。
5. **整句只剩上一句留下的身份徽章**（例如单独一枚「纳指100」，没有为本句提供名词+动词场景）→ FAIL `sentence_covered_by_stale_identity`。必须按口播句的实际可见时间检查（读 cue 在该 caption 中点的 opacity），不能只看计划 `focus_object_ids` 是否在 HTML 里存在。已知坏例：preview-60s-v1 约 0:21「买之前我们纠结什么时候进场 / 买完开始赚钱又会纠结另一个问题」。
6. 口播正在说卖出 / 等跌 10% / 买回等动作时，画面上的关系路径若没有邻近标签、也不能让人读出该动作 → FAIL `unlabeled_stroke`。大账户板标题不算路径标签。已知坏例：preview-60s-v1 约 0:47 账户板下方未标注的卖出/等跌/买回曲线。

计划侧最低接线：鼓励在 `sentence_states[]` 增加：

```json
"display_points": [
  {"token": "纳指", "role": "noun", "kind": "exact_identity", "object_id": "nasdaqProp"},
  {"token": "卖出", "role": "verb", "kind": "relationship", "object_id": "exitPath"}
]
```

无该字段时，审计器从 `focus_object_ids` + HTML 类名/`<img>` 做启发式推断，并在证据不足时 FAIL `display_points_unproven`（新制作默认严格）。

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

DOM 测量可复用 `measure_layout_dom.cjs`；无 DOM 时对 HTML 内联 `left`/`transform` 做静态近似。

## 4. 与版式硬门禁的关系

- 堆叠、同级等大、隐喻、生命周期：**仍以** `audit_layout_hard_gates.py` 为准。
- 本审计专抓「有结构却无素材落点 / 方框带过 / 假居中 / 只剩身份徽章 / 未标注动作路径 / 收尾不对标」。
- encode 前两者都要 `status=pass`（新语义重建 / 用户已点名的画质重修）。

## 5. 命令

```sh
python3 scripts/audit_sentence_display_points.py \
  --html composition/full-v1/index.html \
  --plan plan/semantic_plan.full-v1.json \
  --inventory planning/concept-inventory.json \
  --out qa/sentence-display-points.json
```

退出 0 = pass；1 = fail；2 = 工具/输入错误。

## 6. 次级对标：多层多主体（@xuanyuancoding 方法，不抄画风）

用户指定 https://www.youtube.com/@xuanyuancoding 为表现形式参考。吸收：

- 一句口播尽量拆成多个主体 + 关系路径，而不是一张总卡；
- 名词落道具/模块，动词落箭头/状态/高亮；
- 允许前景说明板 + 中景系统图的分层，但说明板不能替代主体道具；
- 同一机制世界跨句持续变形，禁止每句整屏换成无关方框。

仍使用 Wise 米白/蓝金与 wise-3d；禁止暗色科技网格与第三方角色。
详见 `_external/skill-asset-display-learning.md` 中 xuanyuan 节。
