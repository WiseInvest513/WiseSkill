# 提示词与场景变体

这里是可调整的生成模板，不是此前作图请求的逐字记录。替换主体与构图参数，保留视觉语言。不要把未替换的占位词传给生成工具。

本文件提供共用材质与场景。制作横版时结合 [横版构图](landscape.md)，制作 3:4 竖版时结合 [竖版构图](portrait.md)，由对应版式覆盖画布、构图和文字字段；保留共同的光线、材质与真实性约束。网页图片仍以实际容器为准。

## 基础提示词

```text
Use case: stylized-concept
Asset type: {website placement and intended display ratio}
Primary request: Create a polished standalone visual of {specific subject} for {site topic}.
Input images: Image 1 is a style reference only. {Image 2 is the actual product reference; preserve its identity, proportions, branding and colors. Omit this line if no product image exists.}
Scene/backdrop: A clean white architectural studio, clear glass and silver-white structural surfaces, with restrained champagne-gold trim. Use only the environmental elements needed to support this subject.
Style/medium: High-end physically credible 3D product visualization, tangible and precise rather than a fantasy scene or generic AI wallpaper.
Materials/textures: Thick optical glass with visible edges and refraction, polished silver aluminum, finely finished surfaces, a little champagne-gold metal, realistic contact shadows.
Composition/framing: {subject position, usable negative space, camera view, crop-safe region}. Keep the subject unmistakable at the final small on-screen size.
Lighting/mood: Large soft daylight sources, bright neutral-white environment, controlled reflections, readable detail, natural exposure.
Color palette: White and silver-white dominate; gold is a small structural accent. Preserve any genuine brand colors. Subtle cyan may appear in glass edges, not as neon lighting.
Text: No invented words, slogans, captions, numbers or watermark. {Preserve only text intrinsic to the supplied real product.}
Constraints: Render image assets only, not an entire website screenshot. No UI buttons, fake controls or dashboard panels. Use the reference's material and light, not its subject or logo.
Avoid: Fantasy portals, floating trophies, gigantic gold coins, cluttered objects, purple-blue gradients, neon holograms, glowing particles, bokeh blobs, excessive lens flare, dark atmospheric stock imagery, plastic toy surfaces, cream/beige backgrounds, illegible brand text.
```

配色说明：纯白页面以 `#ffffff` 为底，轻灰可参考 `#f5f6f7`，银材质和玻璃靠反射与折射表现，而不是平涂灰色；香槟金可参考 `#c4a05a`。这些是观感锚点，不是要求渲染每个像素都符合 HEX。

## 1. 产品与入口图

参考 `assets/card-reference.webp` 或 `assets/studio-reference.webp`。福利页本次采用约 2:1 横图，同组保持一致；其他网站以自己的真实容器为准。

```text
Asset type: A wide 2:1 image above the native title in a website product entry.
Subject: {one actual product, card, or topic-specific sculptural object}.
Composition/framing: A medium-close product view, comfortably centered, occupying roughly half to two-thirds of the useful image height. Leave generous breathing room and keep the complete subject inside the crop-safe center. Eye-level or a very slight raised camera, controlled perspective.
Scene/backdrop: The same white glass studio as the reference, simple glass or silver supports only where physically appropriate. No additional showcase props competing with the product.
```

卡片改图强调：`Change only the environment and lighting. Preserve the supplied card face, logo, lettering, color, chip placement and proportions. This is a conceptual product render, not a new official card design.`

## 2. 网站大横图

参考 `assets/hero-reference.webp`。文字上方、左侧还是右侧，必须由当前页面决定；不能机械地规定全部图片右重左轻。

```text
Asset type: A full-width website hero background, {aspect ratio}.
Subject: {a clear spatial metaphor for the site's actual offering}.
Composition/framing: Place the visual subject in {the lower area / the region opposite native copy}. Keep {specified region} clean and quiet for HTML headings and actions. Elegant architectural scale, coherent vanishing points and rounded engineered edges. Preserve a useful subject through both desktop and mobile crops.
Scene/backdrop: White architecture and glass structures, a few fine champagne-gold connections. Keep the scene open and unframed; no interface cards, label boxes or baked-in page titles.
```

不要因为留白把场景做成空白或极小装饰。大屏能看出体系，手机仍能看出主题；不能兼容两种裁切时，为手机另做构图。

## 3. 概念与流程配图

参考 `assets/diagram-reference.webp`。视觉隐喻可以抽象，逻辑不能乱；有指定流向、节点或数字时依据用户的实际内容。

```text
Asset type: A supporting concept visual for {specified explanation}.
Subject: {the actual relationship, such as aggregation, diversification or a cross-border connection}.
Composition/framing: Express the relationship with a few well-ordered glass forms and fine metallic connections. Keep the hierarchy legible without a legend. No decorative elements that imply additional steps or capabilities.
Text: No baked-in labels or made-up numbers. Leave unobtrusive space for code-native labels only when the real page requires them.
Constraints: This is an explanatory illustration, not a chart of historical performance or a guaranteed return. Do not reuse the reference's five boxes or central ring unless those actually match the requested content.
```

ETF 可用聚合与分散的玻璃结构；出海可用通信卡、账户连接或银白服务场景；IPO 可用有序的申请与市场入口；VIP 可用克制的研究、学习或连接场景。它们是选题建议，不是必须放入的物件。

## 4. 深色章节，可选

只有当前需求明确要深色才用 `assets/dark-reference.webp`；它服务于同一网站的节奏变化，不改变默认的白色家族。

```text
Scene/backdrop: A clean charcoal architectural environment, not navy or purple. Silver metal, thick glass and finely restrained champagne-gold details maintain the same physical language as the white family.
Subject: {the real topic or product}. Make identity and details inspectable, not hidden in darkness.
Lighting/mood: Carefully controlled studio illumination, crisp but not harsh. Do not turn subtle brand colors into a screen of neon circuits or add unrequested futuristic props.
Composition/framing: {copy-safe area and crop-safe focal point}. Preserve genuine supplied logos and colors; do not invent corporate products or partnership claims.
```

## 连续出图与单点修正

- 后续图片引用已选定的锚定图：`Keep the same white temperature, glass thickness, material finish, camera family and soft lighting. Change the subject to {new subject}; adapt the composition to its actual use.`
- 过满：`Remove the secondary props and ornamental structures. Preserve the primary subject, material and lighting. Increase clear breathing room without shrinking the subject out of usefulness.`
- 廉价金属感：`Reduce the area and brightness of gold. Use fine champagne-gold structural trim, controlled reflections and realistic material roughness. No trophy aesthetic.`
- 主体太小：`Bring the camera closer and keep the complete subject visible, while preserving the same perspective and white studio lighting.`
- 卡面被改错：使用实际产品原图再编辑，明确需要保留的标志、文字、颜色与结构；不要让模型反复凭记忆重画品牌。
- 手机构图不适配：重新生成当前屏幕比例，不把重要主体塞进画面边缘；原图和桌面版本保留。

## 参考来源

素材来自用户已采用的 Wise 主站首页和福利页，2026-10-10 的实现。本 skill 内保存的副本是完整风格参考，不是网页 UI 模板：

- `studio-reference.webp`：福利页券商概念图，原 `public/images/perks/overview/broker-studio.webp`。
- `card-reference.webp`：福利页 Gate Card 示意图，原 `public/images/perks/overview/gate-card-studio.webp`。
- `hero-reference.webp`：首页银白空间横图，原 `public/images/home/journey-hero.webp`。
- `diagram-reference.webp`：首页 ETF 聚合概念图，原 `public/images/home/journey-etf.webp`。
- `dark-reference.webp`：首页美股深色章节图，原 `public/images/home/journey-stocks.webp`。

原项目路径仅作来源记录；日后使用直接引用 skill 内的文件，不能要求其他项目复制整个博客仓库。
