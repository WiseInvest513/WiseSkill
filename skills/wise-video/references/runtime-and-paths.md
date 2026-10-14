# 运行依赖与路径

## 工具与运行层

- **接入和校验**：Python 3.10 或更新版本，仅用标准库，不需要 pip 包。脚本为 UTF-8。macOS/Linux 通常使用 `python3`，Windows 按本机 Python 命令运行；路径含空格时加引号。
- **编译 HTML 工程**：`scripts/render_plan.py` 加同目录 `srt_intake.py`、`style-vocabulary.css`。仓库不提交第三方 GSAP 文件。首次运行先按仓库根 README 准备依赖：仓库 `package.json` 固定 GSAP 3.14.2，setup 脚本会把 npm 安装结果复制到 `assets/background/assets/gsap.min.js` 和 `assets/intro/assets/gsap.min.js`。编译时仍显式传 `--gsap PATH`，通常使用准备后的背景目录内文件；单独迁移 Skill 时一并准备该本地依赖。编译器不从祖先目录或历史样片中自动搜依赖，也不联网安装。
- **使用原声**：需要 FFmpeg 工具集的 `ffprobe`；在 `PATH` 中可调用，或在接入/编译时传 `--ffprobe PATH`。显式指定字幕与原声音频偏移；时长和文件名不能证明同源。SRT-only 接入和无声 HTML 编译无需 FFprobe。
- **预览、抽帧、MP4 导出**：需要目标环境可用的 HyperFrames CLI、其要求的 Node.js/浏览器运行时和 FFmpeg；这些可执行环境不随本 Skill 自动安装。使用已安装 HyperFrames 入口/文档检查实际版本和命令。编译 Python 成功只表示生成了工程，不等于已经渲染成片。
- **字体与图形**：系统需有中文字体。样式依次使用 PingFang SC、Noto Sans CJK SC、Microsoft YaHei 和系统回退；换字体可能改变换行，需要在目标环境复查。随包背景使用 Canvas/WebGL，需要能运行 WebGL 的浏览器；不可用时如实报告，不能声称冻结背景已复现。
- **生成或查找素材**：只在需要时使用当前环境可用的图像生成/搜索工具；工具能力和授权按本次会话确认。文章写作不在本 Skill 范围内。

## 首次准备动画运行库

在本 Skill 安装目录（有 package.json 的 wise-video 文件夹）执行：

```sh
npm install --ignore-scripts
npm run prepare-assets
```

固定依赖 GSAP 3.14.2；准备脚本把 npm 包内的运行库复制到随包背景与开场目录；片尾共用背景目录中的同一份运行库。编译时显式传 `--gsap SKILL_DIR/assets/background/assets/gsap.min.js`。此准备步骤需要 npm 网络和写入当前 Skill 目录的权限；Python 接入与校验不依赖它。若已有可信的本地同版本运行库，也可直接传该文件路径，不强制重复下载。

## 路径与个人模板

`SKILL_DIR` 指 WiseVideo 的实际安装目录，`EP` 指本期工作目录；示例中的这些大写词必须替换为本机路径。脚本参数接受本地路径；素材索引的相对 `path` 以 `--asset-root` 为基准。

- 默认个人背景：`SKILL_DIR/assets/background/`。先读其 README 和 manifest，再传 `--background`。保留冻结的地球、山峦和白底 10% 圆角小署名。
- 可选个人开场：`SKILL_DIR/assets/intro/`。先读其说明，只有原文含对应开场或用户明确要求时传 `--intro-template` 与 `--intro-at-ms`。头像和开场文字是个人模板，不代表每个新主题都要插入。此包不带历史录音，声音仍来自本期输入。
- 可选个人片尾：[固定片尾](../assets/outro/README.md)，位于 `SKILL_DIR/assets/outro/`。包含 Telegram 引导、真实头像、红色大订阅按钮和定投结语，默认 35.034 秒无声。按本期实际话术重排对象与动作，并统一原声/字幕；当前编译器没有 `--outro-template` 参数，需按现有制作引擎组合片尾，不能声称编译器自动接入。
- 自定义模板：用用户选择的路径替换上述参数，并记录来源和哈希。背景可为本地静态图或兼容 HTML 模板；HTML 背景和开场有明确接口，不能把任意网页当作兼容模板，见 [编译接口](render-adapter.md)。
- 本期输入、状态、批准记录、素材索引和历史版本保存在用户工作区。安装 Skill 不等于迁移已有制作项目。

接入报告和 provenance 会记录运行时的本地绝对路径用于追溯。换机器迁移某一期后，保留原报告，按新的输入路径在新的 intake/run 目录重新接入并重新编译；不要修改旧哈希来冒充旧证据仍可验证。包内脚本本身不依赖作者路径。

## 无历史媒体的自检

从 `SKILL_DIR` 运行：

```sh
python3 -m unittest discover -s tests -v
python3 scripts/srt_intake.py --help
python3 scripts/render_plan.py --help
python3 scripts/validate_plan.py --help
python3 scripts/validate_handoff.py --help
```

测试使用临时输入和合成夹具，不读取作者历史录音或成片，不联网、不导出视频。依赖模拟只能验证接入/打包行为；真实浏览器、背景动态、声音同步与视频质量仍需按本期范围实测。
