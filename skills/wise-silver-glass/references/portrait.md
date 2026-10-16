# 竖版长图

用于用户的小红书配图、竖版封面和纵向阅读；与主 Skill 和 `prompts.md` 共用同一套白金银白玻璃风格。

## 画幅

- 默认宽:高为 3:4，例如 1200×1600、1536×2048；不是 4:3，也不自动替换为 9:16。
- 用户明确要其他竖屏视频尺寸时按其要求调整。3:4 是本用户的默认竖图偏好，不宣称适用于所有平台的所有位置。
- 与横版同主题时重新安排相机、物件、文字和留白，不能直接裁掉横图两侧、旋转横图或拉长车、人像等主体。

## 构图

- 利用纵向阅读顺序组织信息：有标题时先读到标题，再看到核心主体，最后是必要的补充与署名。它是一体化画面，不必拆成上下几张卡片。
- 主体充分使用画布宽度，保留完整轮廓和可辨材质；高物件可利用纵深或纵向空间，横向物件调整视角而不是强行拉伸。
- 图中文字需短而清楚，按语义换行。不要把横版标题等比例缩小到手机看不清，也不要加入整段正文去填空。
- 已确认的品牌署名、头像和必要说明保留安全边距，不能与标题争抢位置；不为换比例新增身份素材或更改文案含义。
- 若内容较多，先减少次要元素或按用户要求分成多张 3:4 图，不擅自做成无限长信息图或把所有内容塞进单张图。

## 提示词补充

与共同材质提示词组合，替换花括号内容，只传入当前主题：

```text
Asset type: A standalone portrait {Xiaohongshu image / editorial cover / vertical visual}.
Canvas: Portrait 3:4, width:height; taller than wide. {Use another ratio only when explicitly requested.}
Composition: Recompose {primary subject and any necessary supporting subject} specifically for a vertical canvas. Build one coherent scene with a clear top-to-bottom reading hierarchy. Make the subject large, recognizable and comfortably framed, with physical proportions unchanged.
Text: {No baked-in text / Render only the approved headline, signature and necessary caption verbatim}. When text is needed, use concise, naturally wrapped lines that remain legible on a phone. Reserve quiet space for the headline, keep the primary object unobscured and respect safe margins.
Constraints: Match the companion landscape image's materials, light, color temperature and meaning, not its exact spatial arrangement. Do not crop or stretch a wide image, add blank side panels, or reproduce a horizontal scene as a tiny strip inside this portrait canvas.
```

## 交付检查

读取实际文件宽高，确认是 3:4 或用户另指定的比例；按手机大小检查标题、主体、署名和必要说明。成对交付时可用 `主题-portrait-3x4` 标识竖版，扩展名按实际格式；同时报告实际像素。
