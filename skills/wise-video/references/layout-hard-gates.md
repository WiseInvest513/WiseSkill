# 版式硬门禁（可失败）

把 [同屏布局与元素退场](layout-and-lifecycle.md)、[文字角色与稳定版式](typography-layout.md)、[概念盘点](concept-inventory.md) 里已有的散文规矩，收成**必须失败**的检查项。语义校验通过也不能替代本文件；新语义重建在 encode 前必须跑通。

检查入口：`scripts/audit_layout_hard_gates.py`（可配合 `scripts/measure_layout_dom.cjs` 量实际 DOM）。

## 0. 何时 FAIL

下列任一项成立 → 整次审计 `status=fail`，**禁止 encode / 禁止宣称版式通过**。软提醒、人工“看着还行”、仅有 `validate_plan` 退出 0，一律不算过关。

## 1. 内容安全框与全画幅居中（对确认地球背景）

**事实依据**

- 确认地球在 composition 中是装饰背景（圆心约 `cx=1640`，`R≈414`），**只是背景，不占前景栏位，更不能预留右侧栏**。
- `assets/layout/wise-layout-tokens.json` 内容区默认 `x=144`（7.5%）…`x+width=1776`（92.5%）。安全框左右应对称到约 **8%–92%**，禁止把右缘收到 70% 给地球让位。
- 账户对照板、官方对比图 + 结果条等主内容组，必须在扣除系列顶栏 / 署名 / 字幕后的 **整幅 1920×1080 画布**上居中，不能左对齐把地球当成右栏。

**默认阈值（1080p / 1920 宽）——合同可以收紧，不得放宽**

| 项 | 规则 | FAIL 条件 / 代码 |
| --- | --- | --- |
| 安全框 | 主内容落在约 **8%–92%**；`layout_contract.safe_frame_x_ratio` 右缘必须 ≥ **0.88** | 合同右缘 < 0.88 → `contract_reserves_earth_column` |
| 视觉中心 | 默认 `layout_mode=center`：主内容并集（及账户板 / 图+结果条等主组）`center_x / canvas_w` ∈ **[0.46, 0.54]** | 中心不在该带 → `content_center_outside_band`；`< 0.45` → `left_bias_against_earth_bg`；合同带宽宽于该地板 → `contract_loosens_center_band` |
| 地球不得占栏 | 地球是背景。主组 `center_x < 0.48` 且 `right_ratio ≤ 0.74`（内容停在地球前，像给右栏让位） | `earth_reserved_column`。已知坏例：preview-60s-v1 约 0:42 双账户板、约 1:04 官方图+结果条 |
| 左栏禁令 | 对确认地球背景，**左栏/左贴轨布局默认 FAIL** | 即便合同写 `layout_mode=left_rail` 仍记 `earth_bg_left_rail` |

品牌 Logo、系列芯片、字幕条不计入主内容并集。无 `--url` / DOM 测量时，静态 HTML 的 `left`/`width` 也必须能打出上述失败，不能只靠隐喻扫描放过左偏构图。

## 2. 非预期叠层（堆叠）

- 不同 `group_id`（或不同根节点：`.prop` / `.claim` / `.step` / `.hold` / `.chip` / `.challenge` / `.gauge-wrap`）的可见外包矩形，边距必须 **≥ 16px**（推荐 24px）。
- 仅当 `layout_contract.allowed_overlaps` 或计划 `sentence_states` 显式登记「对象对 + 理由 + 时间窗」时允许相交（如表盘指针、组内标签贴图）。
- **图文共展不得叠别人家**：文字只能落在本组成员槽；主张芯片、持有标签、图标、指标卡不得互相压边。
- 典型 FAIL：`持有` 贴住步骤条；`+25bp` 卡盖住标尺图标。

## 2.1 路径不得压字

关系线、箭头、分叉路径不得穿过或压住文字（对象短标签、步骤板、主张卡、说明条）。

- 审计对 SVG `path`/`line` 采样，与文字外包框（含 `.prop` 下方 `.label`）相交或间距 < 6px → FAIL `path_covers_text`。
- 已知坏例：preview-60s-v1 约 0:04，hook 分叉线从「纳指100」标签上穿过。
- 路径应从徽章/图标主体外侧绕开标签，终点停在步骤板外沿，不得进入板内文字区。

## 3. 同级等大

- 同级卡片/步骤板（同一 `sibling_set`，或同场景同角色且并列比较/列举）**同宽同高**，容差 **±8%**（且绝对差 ≤ 24px 优先满足百分差）。
- 不得靠一边放大暗示优劣，除非计划写明主辅关系（那就不是同级，不应标进 `sibling_set`）。
- 典型 FAIL：结果两框一大一小。

## 4. 隐喻替换门禁（概念 → 素材）

分配 `concept_asset` 前必须做替换检查（见 concept-inventory）：换标签后图是否仍像原意。

**直接 FAIL 例（写死）**

| 概念/标签 | 禁止素材 | 原因 | 允许方向 |
| --- | --- | --- | --- |
| 卖出 / 降息卖出 | `wallet.png` 及钱包隐喻 | 钱包更像持有/账户资金，不是卖出动作 | 资金转出/箭头离场/订单簿成交/exit 母题；库无合适图则 **文字+关系板**，禁止硬塞错图 |
| 途中回撤 / 腰斩 | `wallet.png` | 同上；回撤是净值路径，不是钱包物件 | 下跌曲线/高点→半截数值板/`data_chart`；无图用主张字+状态 |

审计对 HTML/计划做静态扫描：`wallet` 与 `卖出|回撤|腰斩` 同节点或同 label/alt → FAIL `metaphor_mismatch`。

## 5. 生命周期清场

- 新主主张进入时，已完成解释的载体必须退场，除非该句 `retain[{object_id, reason}]` 写明当前任务。
- **一句一主焦点**：例如 `+25bp` / 利率条成为主焦点后，政策锚讲台、标尺报告等已完成定义的解释层应退出，不得继续占屏造成堆叠。
- 退出必须连标签/连线一起走；只淡字留大图仍 FAIL。
- DOM 审计：新主焦点元素 `opacity≥0.5` 时，列入 `should_retire` 的旧层仍 `opacity≥0.2` → FAIL `lifecycle_stale`。

## 6. 合同与产物

新语义重建至少产出并引用：

1. `layout_contract.json`（样式 token 哈希、`layout_mode`、安全框、`sibling_sets`、`allowed_overlaps`、审查时间点）
2. 本硬门禁审计报告（JSON）：`status` 必须为 `pass` 才允许 encode

旧散文规则继续有效；**本文件优先级更高**：散文写“宜/应”，这里写“必须/FAIL”。

## 7. 不替代句子展示点 / 收尾对标

本文件保证安全框、并集居中、堆叠、同级、隐喻、生命周期。它**不能**证明：

- 名词/动词已有素材落点（见 [句子展示点](sentence-display-points.md)）；
- 收尾使用了 `wise-outro-approved-v1`（见 [收尾对标](outro-parity.md)）。

两者与本审计一并 `pass` 才允许 encode。

