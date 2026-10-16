# Wise Skills

Wise 的个人 AI 工作方法合集：把经过实际使用和迭代的工作流程、视觉参考和自动化工具保存为可独立调用的 Skill。

这个仓库会持续加入新的能力。每项能力单独维护，可以按需安装，也可以安装全部已发布 Skill。

## 目前包含

| Skill | 适合做什么 | 调用 |
| --- | --- | --- |
| [Wise 视频封面与标题](skills/wise-thumbnail/SKILL.md) | 延续片内风格，默认左侧圆体大字、右侧仅地球背景，检查手机可读性并复用封面模板；提炼30–40字发布标题、核验数据与内容一致性 | `$wise-thumbnail` |
| [WiseVideo](skills/wise-video/SKILL.md) | 读文案/SRT/音频，分析实体和关系，盘点素材，生成语义分镜和动画工程，检查承接、布局与原声同步 | `$wise-video` |
| [Wise 立体配图](skills/wise-editorial-3d/SKILL.md) | 为文章生成米白、深蓝、少量金色的立体实物配图，让画面解释关系 | `$wise-editorial-3d` |
| [WiseInvest 企业深度研究](skills/wiseinvest-company-research/SKILL.md) | 从 Wise 的视角理解企业、核验经营与估值、形成判断并撰写深度文章 | `$wiseinvest-company-research` |
| [WiseInvest 财经写作](skills/wiseinvest-stock-writer/SKILL.md) | 保留 Wise 的观点与口吻，核验事实和数据，撰写短贴、公众号长文、财报分析与合作稿；附写作规则和样本 | `$wiseinvest-stock-writer` |
| [Wise 白金银白玻璃配图](skills/wise-silver-glass/SKILL.md) | 复用银白、玻璃与少量香槟金的视觉风格；小红书默认 3:4 竖版，视频默认 16:9 横版，分别构图 | `$wise-silver-glass` |

后续将继续加入行业研究等能力。

## 安装

### 让 Codex 帮你安装

把下面这段话发送给 Codex：

> 请使用 skill-installer，从 https://github.com/WiseInvest513/WiseSkill 安装 skills/wise-video、skills/wise-thumbnail、skills/wise-editorial-3d、skills/wiseinvest-company-research、skills/wiseinvest-stock-writer 和 skills/wise-silver-glass。先检查本机是否已有同名 Skill；如已有则保留旧版备份后按我的要求更新。安装后读取对应 SKILL.md，按实际任务准备运行依赖。

也可以只指定其中一个目录。Skill 的目录需要完整保留，包括 `references/`、`assets/`、`scripts/` 和 `agents/`。

### 从本地副本安装

下载或克隆本仓库后，在仓库根目录运行：

```sh
python3 scripts/install.py --all
```

只安装一个：

```sh
python3 scripts/install.py --skill wise-editorial-3d
```

默认安装到 `${CODEX_HOME:-~/.codex}/skills`，也可用 `--dest PATH` 指定目标。安装器遇到同名目录会停止，不覆盖已有 Skill。新对话中可直接通过名称调用；如果应用没有刷新列表，重开对话或重启应用后再用。

## 使用

### 制作视频

> 使用 $wise-video，读取这份 SRT，先处理前 5 分钟。先分析每句话应该由什么画面承接，审视缺少哪些准确品牌/产品素材，再开始制作。声音使用我提供的原始音频；缺少音频时先做无声预览。复用随 Skill 保存的背景和风格。

视频流程会保留时间戳、源文件、素材来源和版本记录。默认不会因为存在某张图片而改写文稿，也不会自动把 SRT 当成重新配音的许可。

### 封面与发布标题

> 使用 $wise-thumbnail 为这期视频准备封面和发布标题。沿用已确认的左侧圆体大字、右侧地球背景；标题按30–40字突出当下处境、核心问题和观看价值，核验数字与视频内容。

仅要求标题时只处理文案，不生成图片或重新渲染视频。封面模板位于 `skills/wise-thumbnail/assets/round-globe/`，需同时安装 `wise-video` 并按下面步骤准备GSAP；两项Skill保持同级目录。跨机器不携带系统字体，确认版使用 `Yuanti SC` / `STYuanti-SC-Bold`，缺字体时先取得可用的授权圆体，再检查中文和320×180效果。

### 为文章配图

> 使用 $wise-editorial-3d，为下面文章设计并生成 3 张正文配图。沿用随 Skill 保存的参考图材质和配色，让物件与关系解释内容，默认不要大标题和无关人物。

配图 Skill 包含实际风格参考。它负责配图，不负责把文章改写成固定模板。

### 企业深度研究

> 使用 $wiseinvest-company-research，研究【公司名 / Ticker】，直接写成一篇给普通投资者看的深度文章，使用截至今天能够核验的资料。

随包保留最新企业介绍框架、证据与估值规则、阶段评级和 Wise 写作规范。涉及最新资料时需要联网核验；没有资料或依据时不得编造。

### 财经写作

> 使用 $wiseinvest-stock-writer，按 WiseInvest 的口吻把下面的观点写成一篇公众号长文。保留我的核心判断，核验事件和关键数据，解释影响机制，不编造持仓或个人经历。

随包保留本地 3.2.0 版本的写作规则、研究标准、短贴与长文指南、合作稿指南、样本及检查脚本。企业研究负责理解和判断公司，财经写作负责将研究与观点写成适合当前用途的内容；不必为每次短评启动完整企业研究。

### 白金银白玻璃配图

> 使用 $wise-silver-glass，为这个主题做小红书版，3:4 竖图，保留白金银白玻璃质感。

> 使用 $wise-silver-glass，为这个主题做视频版，16:9 横图，保持同一套材质和光线。

横版和竖版共用风格，但分别安排主体、标题和留白，不默认拉伸或裁切；明确指定的比例优先。随包包含五张实际风格参考、共用提示词、横版与竖版构图规则。与米白深蓝的 `wise-editorial-3d` 是两套不同的视觉风格，按任务选择，不混用。

## 运行依赖

- **读内容、规划和 Python 校验**：Python 3.10+，脚本仅用标准库。
- **文章生图**：当前环境需要可用的图像生成工具；本仓库不提供模型账号、API 密钥或额度。
- **视频动画工程**：需要 GSAP 3.14.2。进入已安装的 `wise-video` 目录，执行：

```sh
npm install --ignore-scripts
npm run prepare-assets
```

这会从 npm 安装固定版本，并将运行库复制到背景与开场目录；片尾共用背景运行库。仓库不提交 `node_modules` 或第三方 JS 构建文件。

- **带原声的视频**：需要 `ffprobe`；导出 MP4 还需要 FFmpeg、Node.js、可用的浏览器和 HyperFrames CLI。历史样片使用 HyperFrames 0.8.32；安装或切换版本后按该版本文档验证，不能把 HTML 编译通过当成视频导出通过。
- **背景**：需要 WebGL 和可用中文字体。跨机器可能发生字体换行差异，导出前必须抽帧检查。

完整接口见 [运行依赖与路径](skills/wise-video/references/runtime-and-paths.md) 和 [编译器接口](skills/wise-video/references/render-adapter.md)。

## 随包素材

本仓库为 Wise 个人完整版，包含已确认的动态地球与山峦背景、白底 10% 圆角小署名、固定开场、红色大订阅片尾、Telegram 引导图和 Wise 头像，以及文章立体配图、白金银白玻璃配图参考和财经写作样本。**不包含历史录音、视频成片或整期私有工程。**

背景与署名跟随 Skill 一起保存，因此不依赖旧聊天。其他使用者可以替换自己的品牌和头像；不要将 Wise 本人形象当成通用模板身份。图片风格会受模型和新主题影响，Skill 提供稳定参考与检查方法，不保证每次生成完全相同。

## 本版视频流程

- 全文提取信息性名词与概念，判断文字、准确身份、概念素材、数据图和关系表达；逐句回查与素材检查通过后再进入批量制作。
- 从每句话的含义规划当前焦点、旧元素退场和前后承接；把地球视为背景，按整幅画布构图。
- 先理解和取得元素，再验证静态构图、实现动作、检查原声同步，最后导出。
- 实际操作截图按任务切幕，复用统一加载方式、尺寸与标注；下载完成后的注意事项单独成幕。
- 章节、定义和结论独立建立焦点，同级列举完成态保持平衡；金额单位不因换成纸钞图就从USDT变为USD。
- 完整视频交付包含封面和发布标题，沿用确认模板；数字核验、内容对应与手机可读性分别检查。
- 原件、固定模板、当前工程、最终导出分开保存；用户确认并授权后清理重复与临时文件。

## 验证与扩展

```sh
python3 -m unittest discover -s skills/wise-video/tests -v
python3 scripts/check-package.py
```

当前分发版包含内容、交接及编译器单元测试，并对实际背景与开场做过无声工程编译检查。历史成片验证来自原制作环境，不能替代新内容、新机器的画面和声音验收。

后续新增能力放在 `skills/<skill-name>/`，至少包含带 `name` 和 `description` 的 `SKILL.md`，按需要附脚本、参考及测试；然后更新本页目录。不要把企业分析、配图、剪辑的全部规则挤进同一入口。

## 素材与依赖说明

参见 [素材说明](ASSETS.md)。本次整理没有替作者选择新的开源许可证，也没有改变第三方依赖的许可；使用第三方库应遵循其自身许可。
