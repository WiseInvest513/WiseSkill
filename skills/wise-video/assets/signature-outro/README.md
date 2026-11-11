# 关注 · 订阅 · 收藏片尾

这是已批准 EP10 结尾物件及排版的最小可运行复用版。它保留真实头像、WiseInvest、纯文字话题行、大红订阅按钮、金色书签、支持句和告别句。原社区版 `../outro/` 原样保留；仅当新口播包含电报交流时才选择它。

![本包实际渲染：告别态](reference-farewell.jpg)

## 来源和适用范围

- `source-ep10-support.jpg` / `source-ep10-farewell.jpg`：已批准成片第 325 / 327.5 秒的真实编码帧，附原字幕，仅用于对标；不是新工程字幕。
- `reference-support.jpg` / `reference-farewell.jpg`：本包真实浏览器渲染；背景、头像与署名复用同包资产；没有复制旁白或整片。
- 头像复用 `../outro/assets/portrait.png` 原字节及原裁切，未生成或改脸。
- 按已归档成片重建最小可编辑源；不是声称恢复了已清理的原工程。字体回退会产生细小字宽差，时序须按新录音重新接线。

## 使用

从 Skill 根目录运行 `python3 -m http.server 8790 --bind 127.0.0.1`，打开 `/assets/signature-outro/index.html?t=13.5`；可在控制台调用 `renderAt(t)`，单位为 signature 段开始后的秒。此例约 14.167 秒，没有音轨、字幕或自动播放计时器；无需 npm/GSAP，需 WebGL。完整 assets 相对结构须保留。

```js
setSeriesChrome({episode: 11, topic: '汇率如何影响收益？'});
configureSignature({
  backgroundStart: 300, // 用本片绝对秒保持背景连续
  sloganEnabled: true,
  cues: { subscribe: [7.8, .5], bookmark: [7.95, .45] }
});
renderAt(10.8);
```

`cues` 值为 `[进入秒, 进入时长, 可选退出秒, 可选退出时长]`。片尾话题行、订阅/收藏、支持、告别根据实际原声进入；示例时点只用于演示。没有讲“讲清楚市场”时设 `sloganEnabled:false`，重新安排后续时点，不保留多余空档。先显示肖像与品牌，话题文字在右边，不贴兴趣胶囊到头像上。口号退出后订阅进入，支持句退出后告别进入。全程不隐藏系列顶栏。

字幕须由本片自己的字幕层提供，不嵌入这些参考帧的文字。下期预告在 signature 之前另作语义场景；本例不代替主题道具、品牌身份或数据验证。

## 验证接口

`#wise-signature-outro[data-outro-variant="subscribe-only"]` 与 `data-outro-object` 标记 portrait / brand / topics / slogan / subscribe / bookmark / support / bye。书签是实际 SVG 路径 `M2 2H38V52L20 40L2 52Z`，不是将铃铛改 ID。渲染前等字体、图片解码，再调用 `renderAt()` 并等两帧。

建议检查 `2, 6.8, 10.8, 13.5` 秒的身份、口号、支持和告别态。检查器只能证明采样帧的 DOM 可见性与几何；另看实际截图、动态前中后态和原声时机。模板参考图已实际打开检查，前景无相互遮挡；新工程仍需重新验收，不继承自动通过状态。
