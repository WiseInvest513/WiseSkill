# 收尾对标（可失败）

片尾必须对标已确认模板与已发布成片，不得另起一套「告别方框栈」。

## 权威来源

1. `assets/templates/wise-outro-approved-v1`（README / manifest / index.html）
2. 已导出系列成片末段（如 `exports/纳斯达克投资系列/第09期…`、`第10期…`）
3. 学习简报：`.agents/skills/_external/skill-asset-display-learning.md`

## 强制配方

**若口播含电报/交流群引导**：完整走 community → signature（模板默认 ~35s 时序，按本期音频对齐）。

**若口播只有关注订阅/下期再见**：仍必须使用 signature 段的核心物件，并优先对标已发布系列成片（第 10 期是完整样本），不要只做到「有肖像、有红按钮」就视为通过：

- 真实头像 `portrait.png`（标签/兴趣块不得压在头像上）
- WiseInvest 品牌字
- 话题行纯文字：`美股 · 宏观 · 科技 · AI`（不要用一排兴趣胶囊贴在头像周围）
- 口号：`用大白话，讲清楚市场`（口播讲到讲清楚市场时出现）
- **大红色**「关注 · 订阅」按钮，带播放三角形
- 按钮右侧金色书签「收藏」（第 10 期用收藏，不是模板默认铃铛；口播没有铃铛/电报就不要改成铃铛或电报段）
- 支持句：`你的支持，是持续更新的动力`
- 「我们下期再见」落在品牌构图上
- 系列顶栏在收尾仍然可见，见 [系列顶栏](series-chrome.md)

`wise-outro-approved-v1` 里的电报群、兴趣胶囊、定投三连、铃铛、十年前→现在，只在口播真正讲到时使用，不能拿模板默认时间轴覆盖第 10 期这类「关注/收藏/下期再见」口播。

**下期预告**：用具体素材表达下期主题。第 10 期样本是红色播放图标 + 具体标题（如 `下一期 · 同样投资纳指，汇率怎样影响收益?`）+ Nasdaq 标识 + `纳指100`。禁止仅一张下一期文字卡。

## FAIL

| code | 条件 |
| --- | --- |
| `outro_template_missing` | 成片收尾 HTML/合成未引用或未复用 `wise-outro-approved-v1` 的关键节点（portrait / subscribe / bye），却用自制 claim 栈冒充 |
| `outro_missing_red_subscribe` | 口播要求关注/订阅，但画面无红色订阅主按钮 |
| `outro_missing_portrait` | signature 段无真实头像 |
| `outro_box_stack_farewell` | 收尾仅有多层文本方框（我是…/欢迎关注…/下期再见）而无模板物件 |
| `next_ep_text_only` | 下期预告句只有文字卡，无主题道具 |
| `outro_missing_topics_line` | 第 10 期这类收尾缺少「美股 · 宏观 · 科技 · AI」文字行 |
| `outro_bell_instead_of_bookmark` | 口播是收藏/订阅路线，画面却只用模板铃铛、没有「收藏」 |
| `outro_interest_chips_on_portrait` | 兴趣胶囊压在肖像上 |

`audit_sentence_display_points.py --check-outro` 扫描上述模式。有系列栏目时同时按 [系列顶栏](series-chrome.md) 检查左上红色期数卡和右上署名。
