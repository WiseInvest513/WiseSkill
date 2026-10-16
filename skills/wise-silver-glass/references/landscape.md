# 横版宽图

用于横屏视频封面、横向文章配图及网站横图；与主 Skill 和 `prompts.md` 共用同一套白金银白玻璃风格。

## 画幅

- 视频封面和独立横版预览默认宽:高为 16:9，例如 1600×900、1920×1080。
- 网页已有 2:1、4:3 等容器，或用户另给尺寸时，服从实际用途，不强制改成 16:9。
- 横版与竖版是两个交付版本，不把竖版内容缩成一小块后放进横画布。

## 构图

- 用横向空间表现一个完整场景或主体关系，主次清楚，避免为了填满画幅增加道具。
- 有标题时，在清晰安静的区域排版；主体与文字的位置由内容决定，不固定做成左右各一半，也不套网页卡片框。
- 主体在缩略图大小下仍应可识别。不要把关键物件放得极远、藏在背景里，或用巨大文字压住产品。
- 留出四周安全边距；标题、已确认的品牌署名和关键物件不贴边，方便视频剪辑与平台展示。
- 没有文字要求时保留为干净素材，不自动补宣传语。使用网页原生文字的背景图须保留对应的文字空间。

## 提示词补充

与共同材质提示词组合，替换花括号内容，只传入当前主题：

```text
Asset type: A standalone landscape {video cover / editorial image / website visual}.
Canvas: Landscape 16:9, width:height. {Use the user's exact alternate ratio for an existing container.}
Composition: Build one coherent wide scene around {primary subject}. Arrange {supporting subject or relationship, if needed} with a clear hierarchy. Keep the subject large and recognizable at thumbnail size, with generous but purposeful breathing room.
Text: {No baked-in text / Render only the approved short headline, signature and necessary caption verbatim}. Place text in a quiet area that fits this scene without obscuring the subject. Keep all essential content inside safe margins.
Constraints: Preserve the shared silver-white glass materials, soft light and restrained champagne-gold accents. Compose for this canvas; do not stretch a portrait image or paste a vertical poster into a horizontal frame.
```

## 交付检查

读取实际文件宽高，确认是 16:9 或用户另指定的比例；检查标题、主体与署名是否完整。成对交付时可用 `主题-landscape-16x9` 标识横版，扩展名按实际格式；同时报告实际像素。
