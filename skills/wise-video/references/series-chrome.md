# 系列顶栏（可失败）

纳斯达克投资系列等非品牌合作栏目使用本文件的常驻顶栏。可直接复用随包 [最小模板](../assets/series-chrome/README.md)、[HTML](../assets/series-chrome/index.html)、[CSS](../assets/series-chrome/series-chrome.css) 与 [manifest](../assets/series-chrome/manifest.json)，不需要作者机器的历史工程。

[已批准 EP10 顶部参考帧](../assets/series-chrome/source-ep10-header.jpg) 是权威外观依据；[本包实际渲染](../assets/series-chrome/reference-rendered.jpg) 提供可重现对照。原成片哈希和取帧秒数随 manifest 保存，整片和旁白不分发。原成片为**红底深色期数**；早期规则里的“白字”和偏小的 54px／18px／24px 配方已按已批准成片与用户红底黑字决定纠正。

## 不同用途的角标

| 来源 | 用途 | 本系列处理 |
| --- | --- | --- |
| `assets/background/` 中默认 `#wise-brand-logo left:76px` | 无系列栏目底板 | 系列将原署名移至右上，不保留左上副本 |
| [C 小角标](../assets/brand-header/README.md) | 品牌合作视频 | 不替代非合作系列栏目卡 |
| [series-chrome](../assets/series-chrome/README.md) | 纳斯达克投资系列及同结构续期 | 左上期数／系列／主题，右上原署名 |

## 强制配方（1920×1080）

从 `t=0` 起常驻，贯穿正文、章节与收尾。不延迟出现、不随场景转场退出。

- `#seriesCard`：左76、上30，横排，半透明暖白底，约100px高，圆角8px；宽随主题变化，EP10约410–430px。外层 padding `14px 18px 14px 16px`，内部 gap15px。
- `.num`：58×58、圆角6px、珊瑚红 **#eb7169** 底、深色 **#172735** 字、28px／700。禁止藏青底或将合作方标识当期数。
- `.series`：24px／600、#596972，`纳斯达克投资 · 第N期`。
- `.topic`：30px／700、#1f3545，本期主题问句；EP10例 `加息买入，降息卖出？`。两行明确分级，不合并成一句“纳指 · 标普投资系列”。
- `#wise-brand-logo`：随包原署名图，左1634、上30、210×57.37，白底10%圆角。两角顶部对齐；系列卡和原署名不强行等高。

换期只替换期数和主题文案；保持结构与配色。新字体或较长主题需要重新检查实际字形和边界，不把当前示例宽度写死。`setSeriesChrome()` 使用 textContent 安全替换。

## 失败条件

| code | 条件 |
| --- | --- |
| `series_chrome_logo_left` | 原频道署名仍在左边或不在约定右上位置 |
| `series_chrome_signature_image_missing` | 右上原署名未加载 |
| `series_chrome_num_navy` | 期数方块不是系列珊瑚红 #eb7169 |
| `series_chrome_num_text_wrong` | 期数不是与已批准成片相符的深色字 |
| `series_chrome_copy_wrong` | 不是规定系列名＋本期主题两行，或期数不一致 |
| `series_chrome_missing_t0` | 开场无系列卡，或延迟进入 |
| `series_chrome_missing_in_outro` | 收尾丢失系列卡／原署名 |

`data-wise-series-chrome` 与各语义属性只帮助检查器定位，不代表可见性证明。实际 DOM 采样核对图片加载、祖先透明度、颜色、几何与矩形裁剪；实际绘制遮挡、蒙版和叠层仍须看渲染帧；没有采样证据不能宣称通过。至少覆盖0秒、约4秒、自我介绍、正文和收尾；仍需打开真实渲染帧与源参考比较。

地球是背景装饰，不给正文预留右栏；本文件不改变封面“主体不遮地球”的独立要求。
