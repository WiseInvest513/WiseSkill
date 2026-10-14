# Wise 固定片尾

米白、蓝金风格与真实头像沿用确认版。内容顺序为 Telegram 群交流 → 频道身份与点赞 → 投资兴趣 → 红色大订阅 → 定投美股、定投加密、定投人生 → 十年前与现在 → 下期再见。

基准时长 **35.034 秒**，1920×1080、30fps。订阅按钮原始尺寸 440×112px，颜色 `#e3312d`；后续缩放、头像位置、字幕、动效及 Telegram 图上的昵称遮挡均保留。人物照片未生成或修改。

## 文件与依赖

- `index.html`：可编辑 HyperFrames/GSAP 组成源。
- `preview.html`：无声播放、暂停及拖动预览。
- `assets/portrait.png`、`assets/tg.png`：用户已授权随个人完整版分发的头像和 Telegram 品牌图。
- `../background/`：共同依赖的确认背景、署名与 GSAP。不要单独搬走片尾目录而遗漏背景目录。
- `manifest.json`：素材、代码及文档的 SHA256 清单。

本包不含历史录音、成片、BBAE 正文图或测试快照。GSAP 3.14.2 不提交进包，按 Skill 根目录中的 `package.json` 准备：

```sh
npm install --ignore-scripts
npm run prepare-assets
```

这会生成共用的 `assets/background/assets/gsap.min.js`；片尾直接相对引用它，不需要另复制一份。

## 无声预览

在 `wise-video` Skill 根目录启动本地静态服务：

```sh
python3 -m http.server 8790 --bind 127.0.0.1
```

打开 `http://127.0.0.1:8790/assets/outro/preview.html`。需要支持 WebGL 的浏览器及中文字体。

## 在新内容中复用

只在原文含对应结尾或用户明确要求时使用。这里的固定话术与字幕用于默认节奏示例；每期应核对新录音、字幕和动作节点，不能直接重复叠加字幕或把不同语速强塞进默认时长。模板本身没有声音，音轨来自本期输入。

当前 `render_plan.py` 没有 `--outro-template` 参数。本文件可作为单独的 HyperFrames 组成使用，或在本期分镜中复用其中的对象、CSS 与动作并重新绑定字幕。不要把它误当成现有开场模板参数。

用户头像和频道图仅用于授权的 Wise 品牌内容；其他使用者需要替换自己的头像、署名和社群信息。背景地球始终作为背景，主体仍按整个画布构图。
