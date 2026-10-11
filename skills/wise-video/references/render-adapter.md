# 可复用的 HyperFrames 编译接口

`scripts/render_plan.py` 编译已经完成的分镜，不能替代语义判断。先按 [运行依赖与路径](runtime-and-paths.md) 配置环境。以下命令从 Skill 目录执行；EP、START、DURATION、SKILL_DIR 是待替换占位符。新SRT默认先走接入工具，编译时使用其 `captions.scope.json`，避免第二次解析给重复编号或非标准SRT带来ID差异。

```sh
python3 scripts/render_plan.py \
  --plan EP/plan/semantic_plan.json \
  --captions EP/intake/run-001/captions.scope.json \
  --source-srt EP/input/captions.srt \
  --asset-index EP/plan/asset-index.json --asset-root EP \
  --source-start-ms START --duration-ms DURATION \
  --background SKILL_DIR/assets/background \
  --gsap SKILL_DIR/assets/background/assets/gsap.min.js \
  --out EP/composition/v1
```

START与DURATION取接入报告的实际范围，单位毫秒。不要把示例大写占位符直接执行。示例 `gsap.min.js` 在首次按仓库 README 准备依赖后才存在，第三方库不直接随仓库提交。

- 需原声时加 `--audio EP/input/voice.mp3 --audio-offset-ms OFFSET`；FFprobe 不在 PATH 时另传 `--ffprobe PATH`。映射定义与接入工具一致，但此处单位毫秒。只有已确定偏移才能传入；无音频则输出无声工程。
- 已确认固定开场可通过 `--intro-template PATH --intro-at-ms SOURCE_TIME` 显式复用。本个人包的默认模板为 `SKILL_DIR/assets/intro/index.html`；可替换为用户显式选定的兼容模板。只在文稿确实含固定开场且范围包含它时安排，不重复添加。
- 场景、对象、动作和caption ID来自同一计划。正文对象实际ID为 `scene_id-object_id`。使用布局DSL中的对象与fromTo/to动作；不支持的字段或属性会报错，不能静默忽略。
- 布局是1920×1080，30fps；任意主题、时长与源时间范围，不写死币安或两分钟。
- `render_spec`、`render_bindings`仍为源绝对时间。生成 `cue_sheet`与HTML使用局部时间，编译器保留历史状态使中途取片与倒序seek可重现。直接裁大计划不代表内容范围校验通过；计划scope、场景、coverage和绑定仍应按目标范围整理。
- SVG仅允许本地、无脚本的图形；媒体需本地冻结并通过哈希检查。不读取远程素材、不安装依赖、不生成声音。
- 通用形状样式在同目录 `style-vocabulary.css`。新种类须在计划 `render_css` 明确实现。不得只改变元数据假装产生新画面。

输出：index.html、assets、captions.local.json、cue_sheet.json、provenance.json。随后执行计划校验、接线检查、HyperFrames check、真实抽帧与语义审阅，再按用户授权导出MP4并检查解码。遇到编译器未支持的表达，可扩展适配器并实测，或使用现有兼容编译器；不能降低语义目标来迎合模板。

## 模板接口与验证边界

- HTML 背景须保留随包模板的 `function draw(t)`、`const state=` 分界及 `surface` 的 load/upload 就绪契约；适配器提取 draw 函数并以源时间驱动。其他 HTML 必须先适配，不静默执行任意背景脚本。
- 开场须包含 `<div class="intro-copy">`，其内部首个 `<div class="clip caption"` 作为正文提取边界；`const introCues=[…];for` 提供 JSON 动作，组合根 `data-duration` 提供时长。原模板字幕和音频不导入，统一使用本期 SRT 与原声。
- HTML `src` 及模板 CSS `url(...)` 的本地资源会复制到输出 assets 并登记哈希；CSS 内嵌 data URI 和 `#fragment` 保持原样。`@import`、动态脚本加载、srcset 等额外资源形式未实现，不应作为兼容模板依赖。
- 直接读 SRT 的简化接口只接受标准编号、三位毫秒；正式流程优先传接入工具生成的 JSON，保留非标准或重复编号的稳定 caption ID。

作者历史上曾进行关键时点/中途裁切状态对照、10 分钟无关主题编译输入回归，以及旧渲染适配器的三轮样片。这些历史工程不随包分发。本包 tests 使用独立临时夹具；当前安装环境的运行期画面、跨主题长片质量和声音仍需实测。
