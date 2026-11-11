# 自动门禁的证据边界

`pass` 必须附带检查范围。源文件标记、DOM 测量、实际成片审阅是不同证据，不能相互替代。

| 检查 | 自动证据 | 仍需实际画面/人工审阅 |
| --- | --- | --- |
| `audit_sentence_display_points.py` 原有检查 | HTML/计划/动作表启发式：独占文本框、缺少素材节点、遗留徽章、未标路径等 | 是否理解正确，动词是否真正表达，主体主次，动画与口播配合 |
| `audit_chrome_outro.py --check-series` | 浏览器实测位置、期数背景色、两行可见文案；t=0、指定开场及已采样时点的祖先透明度与裁剪；同时开启 `--check-outro` 才要求片尾采样 | 未采样时间、未请求的片尾范围、复杂遮罩与实际像素遮挡、源头像身份、整体审美 |
| `audit_chrome_outro.py --check-outro` | 指定 signature 时点集合中实际可见对象、解码成功头像、红订阅按钮、纯话题文字行、书签实际 SVG 路径与金色、兴趣块和头像的矩形重叠 | 下期预告语义、收藏图形的任意替代实现、字号/精确形状观感、口播时间对齐、最终编码帧 |
| `--check-outro --require-tg --community-times …` | 改走 community→signature 分支：community 时点中群标签与解码成功群图/Telegram链接同时可见，signature 时点中头像、品牌、红订阅按钮、再见；不强加 subscribe-only 话题行/口号/收藏 | 口播是否确实要求群引导、真实群身份和链接有效性、模板其他定投/时间线动作的语义与时序 |

DOM 审计输出 `scope=sampled_computed_dom_only`、`visual_review=not_checked`；`encode_allowed=true` 仅表示此门禁满足，不是所有制作验收通过。`audit_sentence_display_points.py` 同样明确其检查范围。缺必要证据输出 `status=not_checked`，退出码 **1**，禁止将其改写为视觉通过。已测出错误输出 `fail`；无请求检查/缺采样也不能成功退出。输入损坏退出 **2**。

## 可移动的运行方式

外部工具路径由调用者配置；无需历史项目或作者机器路径。`WISE_PUPPETEER` 指向已安装的 `puppeteer-core` 包目录，`WISE_CHROME` 指向可执行文件。HTML 必须提供可重复定位的 `window.renderAt(seconds)`；采样器会等待其完成、两个动画帧、字体和图片解码。

以下时间对应随包的 [signature 样例](../assets/signature-outro/index.html)，实际作品应按本期原声和完整时间轴重新选择，不能照抄样例秒数：

```bash
node "$SKILL_DIR/scripts/measure_layout_dom.cjs" \
  --url "$COMPOSITION_URL" --times '0,4,6,10,13.8' \
  --chrome "$WISE_CHROME" --puppeteer "$WISE_PUPPETEER" \
  --out "$EP/qa/dom.json"
python3 "$SKILL_DIR/scripts/audit_chrome_outro.py" \
  --dom-evidence "$EP/qa/dom.json" \
  --check-series --episode 10 --topic '加息买入，降息卖出？' \
  --check-outro --outro-times '6,10,13.8' \
  --out "$EP/qa/chrome-outro.json"
```

也可以在原命令 `audit_sentence_display_points.py --html … --plan … --check-outro` 后追加同样的 `--dom-evidence / --check-series / --episode / --topic / --outro-times`，自动合并报告。不开启系列或收尾检查时保留原句子检查流程。开启 `--check-outro` 却没有 DOM 证据时，只能得到源文件失败或 `not_checked`，不再把正则匹配当作已通过。

**局部样片**：例如45秒开场，只运行 `--check-series --episode 10 --topic '加息买入，降息卖出？'`，采样覆盖 `0,4,44.5` 等本次实际范围，不需要 `--outro-times`。报告 `requested_checks.outro=false`，不代表完整片尾已通过。**完整成片**仍须同时开启 `--check-series --check-outro` 并提供真实 `--outro-times`；缺少片尾时点依然返回 `not_checked`。

## 按实际口播声明可选文字

subscribe-only 默认完整对象集合仍为头像、品牌、话题行、口号、红订阅按钮、收藏、支持句、再见。只有本期原声确实省略对应句时，才通过 `--outro-policy "$EP/plan/outro-policy.json"` 显式免除 `slogan` 和/或 `support` 的必需检查。例如仅省略口号：

```json
{
  "schema_version": 1,
  "optional_objects": {
    "slogan": {"expected": false, "reason": "本期原声没有讲清楚市场的口号句，按录音省略"}
  }
}
```

省略支持句时，在同一 `optional_objects` 中增加 `"support":{"expected":false,"reason":"本期原声没有支持更新句"}`。未列出的对象沿用默认要求；`expected:false` 表示“不再要求出现”，不是“必须不可见”。禁止在此策略里写 portrait、brand、topics、subscribe、bookmark、bye 或任何未知字段；布尔值必须是真布尔，省略理由不能为空。默认没有策略时，缺口号/支持句仍然失败。策略不放宽采样、图片加载、颜色、书签、源 HTML 哈希或其他检查。

两个审计入口使用相同参数：

```bash
python3 "$SKILL_DIR/scripts/audit_chrome_outro.py" \
  --dom-evidence "$EP/qa/dom.json" --check-outro --outro-times '6,10,13.8' \
  --outro-policy "$EP/plan/outro-policy.json"
python3 "$SKILL_DIR/scripts/audit_sentence_display_points.py" \
  --html "$EP/composition/index.html" --plan "$EP/plan/semantic_plan.json" \
  --dom-evidence "$EP/qa/dom.json" --check-outro --outro-times '6,10,13.8' \
  --outro-policy "$EP/plan/outro-policy.json"
```

报告 `outro_object_policy` 保存生效的对象集合、免除理由以及策略文件路径/SHA256。理由是调用者对本期口播的声明，自动审计不证明原声确实省略该句，仍须对声复核。策略仅适用于 `--check-outro` 的 subscribe-only 分支；与 `--require-tg` 同用或未开启片尾检查是输入错误，社区分支保持自身规则。

模板的实际接口是 `configureSignature({sloganEnabled:false})`；随后重新采样才能验证真实缺省画面。当前没有 `supportEnabled`：需要省略支持句时，在本期工程的样式中令 `#support{display:none}`，并按原声用 `configureSignature({cues:{bye:[开始秒,进入时长]}})` 调整再见时序；不要改写包内批准模板，也不要留下原支持句的空等待。策略本身不改变 HTML 或时间轴。

## 社区片尾分支

原声确实包含电报群引导时使用 `--check-outro --require-tg --community-times '4,10' --outro-times '17,25.7,34.5'`；这是随包 `assets/outro/index.html` 的示例时点，按实际时间轴调整。先让采样器 `--times` 包含这两组时间，再执行审计。此分支保留原社区模板的兴趣/铃铛用法，不强制 EP10 subscribe-only 的话题行与收藏；是否应该出现群、铃铛、兴趣块仍由本期口播决定。

原社区 HTML 是宿主时间线模板，需显式提供 GSAP，并由宿主/工程适配器实现 `renderAt(seconds)`（定位 `window.__timelines['srt-video'].time(seconds,false)` 及 `.clip` 起止可见性）。新 signature 样例原生提供 `renderAt`。采用本地 HTTP 服务加载，避免 `file://` 的纹理同源限制；浏览器脚本异常进入报告并使审计未检查，不吞掉错误。社区浏览器回归另需设置 `WISE_GSAP` 指向实际 GSAP 文件，测试内显式提供上述宿主适配；没有配置时该项明确跳过。

## DOM 接口

`measure_layout_dom.cjs` 保留原 `frames[].nodes` 与 `union`，另增 `frames[].chrome_outro`：

顶层 `document_sha256` 保存浏览器取得的 HTML 原始响应哈希；合并到句子审计时必须与 `--html` 相同，缺失为未检查、不符为失败。该哈希不涵盖外链 CSS/脚本/图片，修改依赖后必须重新采样。

- `capture_version:1`、`source:"browser_computed_dom"`，及 `nodes` 列表；空列表表示确实采样但找不到节点。
- 每节点含 `role/id/text/rect/visible/opacity/visible_area_ratio/background_color/color`，以及 `image_loaded`、实际 SVG 的 `svg_shapes`、话题行的 `boxed_descendants`。
- `visible` 由实际 CSS、祖先透明度、display/visibility、画布和矩形 overflow 裁剪计算，不能读取作者自填的 `data-visible` 作为结论。角色属性只用于选节点。加载图片只证明解码与显现，不证明头像身份。
- 主画布固定 1920×1080；其他尺寸返回未检查，不能套用此系列的像素坐标。
- 系列使用 `data-wise-series-chrome`、`data-episode-number`、`data-series-name`、`data-episode-topic`、`data-wise-signature`；兼容 `#seriesCard/.series-card` 及其 `.num/.series/.topic`、`#wise-brand-logo`。
- 收尾根使用 `data-outro-variant`；对象用 `data-outro-object="portrait|brand|topics|slogan|subscribe|bookmark|support|bye|bell|interest-chip"`。兼容 `#signature-*` / `.signature-*`。旧工程不具备这些对应节点时先适配选择器/角色，再运行；不能手造一个 `pass` JSON。
- 书签根据实际 `path d="M2 2H38V52L20 40L2 52Z"` 与金色 paint 核对随包几何；相同标签配未知图形为 `not_checked`，无收藏/实际 SVG 为失败。其他合法图形实现需增加独立验证或实际帧审阅，不能靠 `aria-label="书签"` 放行。

## 回归验证

`python3 -m unittest discover -s "$SKILL_DIR/tests" -p 'test_chrome_outro.py'` 运行正常证据、八项已承诺错误码及缺证据/坏输入测试。设置 `WISE_CHROME` 与 `WISE_PUPPETEER` 后同时打开随包模板，在真实浏览器里测量正常版，再注入左侧署名、藏青期数块、错误系列文案、开场/片尾隐藏父节点、隐藏话题行、改成铃铛角色、兴趣块压头像的变体。未配置浏览器时该项明确 **skip**，不能写作浏览器测试通过。
