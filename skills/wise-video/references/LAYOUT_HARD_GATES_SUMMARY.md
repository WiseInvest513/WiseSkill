# 版式硬门禁摘要（给代理 / 给用户）

语义校验过了也不算版式过关。新语义重建 **encode 前** 必须：

1. 写/更新 `layout_contract.json`（`layout_mode`、安全框、`sibling_sets`、`allowed_overlaps`、生命周期清退表、审查时间点）。
2. 按 [运行路径](runtime-and-paths.md) 设置 `SKILL_DIR` 与 `EP`，调用 `python3 "$SKILL_DIR/scripts/audit_layout_hard_gates.py"`；输入参数指向本期实际 HTML、计划、合同和 cue，不依赖当前工作目录或作者路径。具体检查见 [版式硬门禁](layout-hard-gates.md)。
3. 报告 `status=pass` 且 `encode_allowed=true` 只表示此门禁满足；实际帧发现的问题仍须修复，不能当作语义、审美或声音同步通过。

## 六条硬 FAIL

| 门禁 | FAIL 条件 |
| --- | --- |
| 安全框居中 | 确认地球是背景，不占栏、不预留右栏；主内容并集及账户板/图+结果条 `center_x` 须在 **46%–54%**；`<45%` 或 `center_x<0.48` 且右缘停在地球前 → FAIL `earth_reserved_column` / `left_bias_against_earth_bg`。合同不得把安全框右缘收到 0.88 以下，也不得放宽居中带。路径压字 → FAIL `path_covers_text` |
| 非预期叠层 | 不同组可见框间距 **&lt;16px**（相交更深）且未登记允许对 → FAIL（如「持有」贴步骤条） |
| 同级等大 | 同级卡/步骤板宽高差 **&gt;8%** → FAIL |
| 隐喻替换 | **卖出→钱包**、**回撤/腰斩→钱包** → FAIL；无合适图用文字+关系板，禁止硬塞 |
| 生命周期清场 | 新主主张（如 +25bp 利率条）上场后，已完成的政策锚/标尺层仍可见 → FAIL |
| 图文共展 | 文字只落在本集团槽，不得压别组外包 |

新计划和画质重修同时按 [句子展示点](sentence-display-points.md) 检查名词/动词的实际落点。系列顶栏按 [系列顶栏](series-chrome.md) 检查；仅当本次范围包含片尾时，按 [收尾对标](outro-parity.md) 加片尾检查。局部样片不为审计擅加片尾。DOM 证据要求与未检查状态见 [自动检查覆盖](automation-coverage.md)。

## 历史失败说明

作者历史样片曾在语义结构通过后检出版式失败：左偏、非预期重叠、同级尺度不一致、卖出/回撤误用钱包、主张切换后旧层未退场。该记录说明这些门禁为何存在，不是新安装已执行的证明，也不要求取得历史工程。

对当前内容从本期 cue 选择稳定态、动作中途和转场时点，修复后检查受影响区间。不要照抄旧片秒数；没有执行的检查记录为未验证。
