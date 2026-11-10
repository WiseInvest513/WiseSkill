# 版式硬门禁摘要（给代理 / 给用户）

语义校验过了也不算版式过关。新语义重建 **encode 前** 必须：

1. 写/更新 `layout_contract.json`（`layout_mode`、安全框、`sibling_sets`、`allowed_overlaps`、生命周期清退表、审查时间点）
2. 跑 `python3 .agents/skills/wise-video/scripts/audit_layout_hard_gates.py ...`
3. 报告 `status=pass` 且 `encode_allowed=true` 才能出片

## 六条硬 FAIL

| 门禁 | FAIL 条件 |
| --- | --- |
| 安全框居中 | 确认地球是背景，不占栏、不预留右栏；主内容并集及账户板/图+结果条 `center_x` 须在 **46%–54%**；`<45%` 或 `center_x<0.48` 且右缘停在地球前 → FAIL `earth_reserved_column` / `left_bias_against_earth_bg`。合同不得把安全框右缘收到 0.88 以下，也不得放宽居中带。路径压字 → FAIL `path_covers_text` |
| 非预期叠层 | 不同组可见框间距 **&lt;16px**（相交更深）且未登记允许对 → FAIL（如「持有」贴步骤条） |
| 同级等大 | 同级卡/步骤板宽高差 **&gt;8%** → FAIL |
| 隐喻替换 | **卖出→钱包**、**回撤/腰斩→钱包** → FAIL；无合适图用文字+关系板，禁止硬塞 |
| 生命周期清场 | 新主主张（如 +25bp 利率条）上场后，已完成的政策锚/标尺层仍可见 → FAIL |
| 图文共展 | 文字只落在本集团槽，不得压别组外包 |

细则：`.agents/skills/wise-video/references/layout-hard-gates.md`

## 基线证明（semantic-v2，已知坏片）

对 `preview-60s-semantic-v2` 的 composition 抽检 `t=4.8 / 26.5 / 35.5 / 54.5`：

- 报告：`projects/2026-11-09-grokbot-aview-parity-test/qa/layout-hard-gates-baseline-fail.json`
- 结果：`status=fail`，`encode_allowed=false`
- 已打中：`left_bias_against_earth_bg`、`unintended_overlap`（持有贴步骤）、`sibling_size_mismatch`、`metaphor_mismatch`（卖出/回撤→wallet）、`lifecycle_stale`（25bp 未清退标尺/政策锚）

**下一步（重渲前）**：按硬门禁改 composition / 隐喻 / 生命周期 → 再跑同一审计必须 `pass` → 才 encode。本任务不重渲。

Also run `audit_sentence_display_points.py --check-outro` (box/outro gaps layout gates miss).
