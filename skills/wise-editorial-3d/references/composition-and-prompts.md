# 文章构图与生成提示

## 按内容选择空间结构

| 文章重点 | 适用构图 | 应避免的误读 |
| --- | --- | --- |
| 一个实体是什么 | 能代表其职责的实物，保留识别特征和材质 | 用 Logo 代替产品机制；给抽象名词堆装饰 |
| 两种形式差在哪 | 两个并列主体，同一视角与相近视觉重量，突出差异 | 大小无依据地悬殊，擅自暗示优劣 |
| A 支持 B | 两端同时可见，用承托或连接说明依赖 | A 消失后只剩 B，误成兑换或替代 |
| 过程存在等待 | 保持起点、未完成的中间状态，终点按原文的不确定性处理 | 连续粗箭头加落袋金币，暗示必然兑现 |
| 范围扩展或门槛减少 | 同一尺度的前后对照，增加清楚的分支或减少阻碍 | 随机堆物件；示意个数被当精确数量 |
| 抽象权利或责任 | 文件、钥匙、支撑结构等与机制对应的隐喻 | 为“更安全”随意加盾牌，暗示实际保证 |

不是所有概念都必须物化。精确数据图使用真实数据和确定的绘图方法；图像模型可提供旁边的概念插图。参考有银行或钱包，不表示文章主题必须金融化。

## 构图边界

正文图通常一个视觉中心，或一眼可读的对照/过程；先认出“什么与什么怎样相关”，再加细节。外缘可从约 10% 留白开始，主要物件完整，按最终栏宽调整。别用满屏巨大图片解决识别问题，先删细碎纹理和多余对象。

白/暖白底是文章默认，地面只需接触阴影。通用物件自然放在同一空间；底座本身有含义时才加入。不复制视频大背景，也不为了“自然”改成扁平或手绘。不能把几个正方形抠图直接拉伸成横图。

**参考相同，不代表构图相同。** 透明单物件素材、正文概念图和带标题的封面分别设计。正文图应能融入排版；用户要的实际标题另行排版，不默认把全部标题生成成厚重 3D 字。人物不承担万能讲解员角色。

源图大小与发布尺寸分开决定：1024 像素透明物件可在正文中显示得很小。横图等比显示，避免裁断关键物件；必要时另做窄屏构图。

## 通用提示骨架

替换下列占位内容。同批图片复用风格段，重新设计主体与关系段。参考文件用图像工具的本地引用参数传入，文字里写文件名不能代替真实传图。

```text
Use case: stylized-concept / editorial explanation.
Deliverable: [article-body landscape / comparison illustration / isolated transparent object].
Article idea: [one precise idea supported by the supplied text].
Objects and relationship: [visible objects, each role, spatial relationship, condition/uncertainty].
References: attached images are STYLE references only. Preserve materials, palette and light, not subject matter. [Identify any product reference requiring identity fidelity.]
Style: tactile restrained 3D editorial illustration; warm ivory stone, thick paper, matte ceramic/enamel or navy leather as appropriate; muted deep navy structure; small brushed champagne-gold details; clean rounded bevels and readable real-world silhouettes.
Camera and light: almost frontal with gentle three-quarter depth, compatible angles, large soft studio light, subtle contact shadows, meaningful objects in focus.
Composition: [aspect ratio], [positions/reading order], [relative visual weight], complete silhouettes, generous margins, clear separation, no oversized close-up.
Background: [clean opaque white/warm white / genuinely transparent alpha].
Text: [none / exact short labels].
Avoid: copying reference subjects, unrequested character/presenter, dominant headline, heavy extruded type, lecture-poster layout, unnecessary cards/pedestals, piles of coins, excessive gold, neon glow, fake brand marks/data, watermark, video globe/logo/caption overlay.
```

## 示例：金融关系

原意：“股票与由股票支持的代币，是不同形式。”

可画：左侧独立米白凭证；右侧另一张凭证与深蓝代币并存，一条轻连接说明支持。两组间隔适当、凭证形象复用；严格解释权利时另排短标签。不画凭证消失兑换成币，也不擅自添加“同等股东权利”。

## 示例：科技基础设施

原意：“算力背后，还需要电力和散热。”

可画：深蓝/米白计算机架为核心，配清楚可辨的电力设施和冷却模块，少量线缆/管路形成协作关系。科技物件仍继承同一材质与柔光；示意数量不代表能耗或性能。无需卡通人物、文章大标题、AI 大脑符号或金币。

## 局部改图措辞

“仅将主体组合缩小并增加四周留白，保持物件、材质、灯光和关系不变。”

“仅把无关装饰物换成能表达当前概念的实体，保持其他对象和排版。”

局部反馈落在明确改动上，已被肯定的风格继续作为约束。
