# 素材与来源

本包按作者要求保留个人视觉资产：

- `skills/wise-thumbnail/assets/round-globe/`：已确认的左侧圆体大字封面排版源，相对复用wise-video背景；系统Yuanti SC字体不打包，运行依赖按仓库说明准备。
- `skills/wise-video/assets/background/`：已确认的动态背景代码与底图、地球纹理、Wise 小署名。原版代码与图片哈希记录在该目录 manifest；未包含历史成片或正文截图。
- `skills/wise-video/assets/intro/`：已确认的头像、品牌文字及左移/欢迎语动效。移除了历史开场录音，保留视觉模板。
- `skills/wise-video/assets/outro/`：已确认的 Telegram 引导、Wise 真实头像和红色大订阅片尾；35.034 秒无声模板，背景从同包 background 目录复用。
- `skills/wise-video/assets/visual-anchors/`：用户认可的银行、钱包、券商和凭证素材及关系构图参考，用来核对风格与实际显示尺度。
- `skills/wise-editorial-3d/assets/`：来自原视频配图流程的生成素材，用于保持米白、深蓝及少量金色的立体材质风格。
- `skills/wise-editorial-3d/references/avoid-poster.png`：作者提供的反例，仅供比较构图；不得作为正向生成风格参考。
- `skills/wise-silver-glass/assets/`：来自 Wise 主站首页与福利页已采用的五张银白玻璃风格参考，保留原始图像；用于核对材质、光线与构图，不代表真实品牌产品、市场表现或服务覆盖范围。

`skills/wiseinvest-stock-writer/` 同步作者本地 3.2.0 版本，包含写作指南、研究标准、按类型整理的样本、输入输出模板及初稿检查脚本。写作样本用于理解作者表达，不能将其中的历史数字、观点或持仓当成当前事实，也不能替其他使用者编造个人经历。

`skills/wiseinvest-company-research/` 来自用户提供的 Skill ZIP，保留原始研究框架，并同步作者后续确认的企业介绍、经营机制、阶段评级和写作规则；界面元数据使用有效 YAML 引号格式。原始压缩包与历史文章不随仓库发布。

个人头像与署名用于 Wise 品牌内容。复制本包不代表获得冒充人物、官方品牌或商标的授权。仓库未将素材重新标成公共领域或额外授予第三方权利。

GSAP 固定版本为 3.14.2，通过 npm 获取；源地址 https://gsap.com/ ，许可条款由该依赖自身提供。HyperFrames、FFmpeg、浏览器、字体和图像生成工具均为外部运行依赖，没有随本仓库重新分发其完整工具或授予其许可。
