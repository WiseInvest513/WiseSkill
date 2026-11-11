# 从仓库开始制作 Wise 视频

这是给新对话、新电脑和其他代理的共同入口。不需要历史聊天，也不需要作者机器上的导出视频。仓库提供制作规则、品牌资产、可运行模板、字幕/分镜工具、检查脚本和验证样例；每一期的文稿、声音和准确产品截图仍由本次任务提供或按授权获取。

## 1. 新对话先做什么

1. 明确本次是系列、产品教程、局部修复还是发布配套，遵守用户给定范围。已有批准版本直接继续；新内容默认先做约45–60秒代表样片，用户已要求整片时内部验证后继续，不反复确认。
2. 读取 [WiseVideo](skills/wise-video/SKILL.md)；完整交付再读 [WiseThumbnail](skills/wise-thumbnail/SKILL.md)。不要一次载入全部研究/写作/外部参考。
3. 选择工作目录，读本期磁盘状态；建立原件、工程、导出三个独立区域。不要往 Skill 源码目录里剪片。详细规则见 [工作区](skills/wise-video/references/workspace-layout.md)。
4. 运行环境检查，缺少工具先安装或说明具体缺项。普通网页聊天若没有文件、终端和浏览器执行能力，不能只凭仓库网址完成实际渲染。

代理可直接读取克隆仓库，无需先安装成特殊插件。Codex 的 `$wise-video` 和 Claude Code 的 `/wise-video` 只是安装后的调用方式，实际执行同一份文件与本地脚本。

## 2. 安装与依赖

在仓库根目录执行，二选一：

```sh
# Codex；完整复制两个相互依赖的 Skill
python3 scripts/install.py --video
# Claude Code；默认 ~/.claude/skills
python3 scripts/install.py --video --agent claude
# 也可给任意代理指定独立目录
python3 scripts/install.py --video --dest ./installed-skills
```

安装器不覆盖已有同名目录。更新时先对比本地修改，保留必要差异，再明确替换；不能用强制删除掩盖冲突。Claude Code 的目录与调用规则参照 [官方 Skills 文档](https://code.claude.com/docs/en/skills)。

以下 `SKILL_DIR` 是实际 wise-video 目录，`EP` 是本期工程目录；换成自己的绝对路径。若系统的 `python3` 仍为3.9，请改用已安装的 `python3.11` 等新版本，先运行 `--version` 确认。系统需 Python 3.10+、Node.js 22.12.0+、FFmpeg/ffprobe、Chromium/Chrome 和中文字体。仓库不分发系统软件、字体授权、账号或密钥。

```sh
python3 scripts/doctor.py --skill-root "$SKILL_DIR"
cd "$SKILL_DIR"
npm ci --ignore-scripts
npm run prepare-assets
```

固定版本见 `package-lock.json`。渲染 CLI 在 `node_modules/.bin/hyperframes`；DOM测量可用 `--puppeteer "$SKILL_DIR/node_modules/puppeteer-core" --chrome PATH`。在仓库根运行 `python3 scripts/doctor.py --skill-root "$SKILL_DIR" --render --chrome PATH` 检查依赖。doctor 不会证明浏览器能启动、中文没缺字或画面好看；这些要真实打开看。

Windows 将示例里的 `python3` 换成实际安装的 `python`，使用 PowerShell 的路径/变量语法。终端或代理捕获中文输出时，先设置 `$env:PYTHONUTF8="1"`（POSIX shell 用 `export PYTHONUTF8=1`），让子进程也使用 UTF-8；单次调用也可用 `python -X utf8`。仓库用 `.gitattributes` 固定文本LF换行，避免Windows检出改变模板哈希。

## 3. 先跑安装验证，再做本期

```sh
# 仓库根：不读旧工程、不联网
python3 scripts/check-package.py
python3 -m unittest discover -s tests
python3 -m unittest discover -s skills/wise-video/tests
# 建立独立的合成验证工程，不使用任何私人旁白
python3 scripts/make-smoke-project.py --skill-root "$SKILL_DIR" --out "$EP/runtime-smoke"
# 本机实际导出（先用 CLI --help 核对本版选项）
"$SKILL_DIR/node_modules/.bin/hyperframes" render "$EP/runtime-smoke/composition" --output "$EP/runtime-smoke/smoke.mp4" --quality draft --fps 30
ffprobe -v error -show_entries format=duration -of json "$EP/runtime-smoke/smoke.mp4"
```

该样例为6秒工程，验证本地背景、相对素材路径、字幕、计划动作和测试音轨打包。音轨是明确标注的合成测试音，不是配音，不代替真实原声同步验收。脚本只生成全新目录。查看开始、中间、结尾的编码帧和声音后，再开始生产；它不代表已完成本期语义/美术验收。

## 4. 制作流程和可复用东西

- **无音频/SRT的小样**：仅有文稿且用户要无声预览时，可按阅读时间建立临时SRT/字幕ID，标记 `timing_source=editorial_draft`，不声称与原声对齐；拿到录音后重新对时。期数不明不能沿用示例第10期，用明确待定占位并记录。
- **内容先行**：文稿为权威内容，SRT/音频负责实际时间；先核对差异与偏移，保持原声。不从旧图倒推文稿。
- **实体与素材**：识别人名、品牌、产品、数字和关系。准确身份用真实素材；通用物件可从 [30个概念素材](skills/wise-video/assets/library/README.md) 选择。缺图不能默认为随便画个框；需要生成时使用当前代理可用工具，没有工具则先完成不依赖它的工作并说明缺项。
- **语义与动作**：按照 [动效方法](skills/wise-video/references/motion-methods.md) 和 [素材展示方法](skills/wise-video/references/asset-display-methods.md) 设计前/中/后状态；增长、转移、比较要有可观察变化，不把每句话都套翻书、漂浮、淡入淡出。
- **第10期整套基准**：先看 [当前系列视觉规范与可复制提示词](skills/wise-video/references/approved-series-profile.md)，包含左右顶栏、三比例封面与订阅片尾。
- **视觉实物参考**：默认 [背景](skills/wise-video/assets/background/README.md)、[系列顶栏](skills/wise-video/assets/series-chrome/README.md)、[品牌小角标](skills/wise-video/assets/brand-header/README.md)、[章节与YouTube](skills/wise-video/assets/chapter/README.md)、[订阅片尾](skills/wise-video/assets/signature-outro/README.md) 均随包。系列左上内容、右上原头像。订阅片尾与含社群引导的旧片尾按本期真实话术选择。
- **实现**：计划与实际动作绑定，接口见 [编译器](skills/wise-video/references/render-adapter.md)。编译器是基础适配器，不是自动美术导演；自定义HTML也必须保留确定性时间轴、素材索引和证据。新模板的组合接口分别写在其README，不要假传不存在的编译参数。
- **检查**：结构、布局、句子展示、顶栏/片尾分别执行。自动覆盖与人工边界见 [覆盖表](skills/wise-video/references/automation-coverage.md)。真实浏览器时点测量、实际编码帧、原声同步都要检查；没运行的项目记为未验证。最终画面仍要看，不能靠PASS代替审美判断。
- **发布**：三比例封面16:9/3:4/4:3分别排版，左上内容、右上头像；封面手机正放、不挡地球；正文地球是背景，不挤占主内容宽度。标题/简介/真实章节合并为`介绍.txt`。系列默认约30字标题与200–300字简介；教程约50字标题与500–600字完整单段，内容按需求→产品→功能与操作→成本条件→核实福利。具体要求以 [发布规范](skills/wise-thumbnail/references/publish-package.md) 和本次用户决定为准。
- **归档**：系列放`exports/纳斯达克投资系列/第NN期-主题/`。确认且用户授权后只清本期中间态，保护原件、模板、最终交付；新对话读本期状态而不是猜上次做到了哪一步。

## 5. 给下一位代理的话

> 请克隆并读取 https://github.com/WiseInvest513/WiseSkill 的 START_HERE.md，按其中 WiseVideo 和 WiseThumbnail 制作本次视频。先检查环境与本期输入，使用随包的品牌素材、模板、动效规则和质量检查，不依赖任何旧聊天。文稿是内容依据，音频/SRT负责时轴。先做约一分钟样片给我看，再继续完整片；如果我已批准样片或明确要求整片，直接接着完成。最终交付视频、校正字幕、介绍.txt及三比例封面。

同时附本期文稿、音频、SRT及已有截图；缺少什么由代理核对后集中说明。转移正在制作的一期时，还需转移该期原件与工程状态；仓库本身不会包含私人项目。
