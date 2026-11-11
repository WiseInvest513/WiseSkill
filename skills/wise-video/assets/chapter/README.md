# 蓝金章节页 · 可携带版本

从已确认 `wise-chapter-blue-gold-approved-v1` 的成片 CSS、元素布局和动作参考提取。保留全画布居中的蓝金横幅、大号章序、标题／副标题、金色分隔线及 YouTube 播放标识。未带走原例字体子集、旧业务文案或原视频。

![本包实际渲染](reference-rendered.jpg)

从 Skill 根目录运行 `python3 -m http.server 8790 --bind 127.0.0.1`，打开 `/assets/chapter/index.html?t=1`。保留同级 background、series-chrome 目录；需 WebGL，不依赖 GSAP 或网络。示例顶栏供纳斯达克系列使用；其他栏目按自己的已确认角标替换，不把此例期数当新内容。

```js
setSeriesChrome({episode: 11, topic: '汇率如何影响收益？'});
setChapter({number: '02', title: '长期投资的关键', subtitle: '先理解风险，再决定行动', start: 0, hold: 2.84, exitDuration: .24});
renderAt(1);
```

`start` 是进入起点；`hold` 是相对 start 的退场起点。所有章节对象在 `start + hold + exitDuration` 后完全消失；随后才进入正文。示例按原参考的相对间隔迁移：面板0，数字+.06s，分隔线+.08s，标题+.12s，副标题+.19s，YouTube+.25s；入场.38–.42s，退出.24s。新章节长度跟实际口播。

默认系统字体栈：PingFang SC / Microsoft YaHei / Noto Sans CJK SC；数字 DIN Alternate / Arial Narrow / sans-serif。不分发商业字体，也不假设旧子集覆盖新字。长标题要检查字形、可读性和边界，不能靠挤压统一字号掩盖溢出。布局面板 `(180,292,1560,480)`；素材装饰地球可在面板后方，正文不为其预留右栏。

录帧等待字体和图片解码，`renderAt(t)` 后等待两帧。`data-object-id` 标记章节对象便于几何与退场采样。`manifest.json` 保存迁移来源哈希和当前文件哈希；本渲染样例不是新一期内容或整片批准。
