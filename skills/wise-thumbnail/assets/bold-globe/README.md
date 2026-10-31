# Wise 硬朗字体封面确认模板

2026-10-20，用户在查看SP500封面V2及发布配套后回复“OK，把这些东西给它收敛到咱们的一个这个skills里面”。以此确认本版并收录复用；旧圆体模板保留。

- 1920×1080，左侧两行主题与一行强调，右侧仅冻结地球，米白/深蓝/哑金及左上小署名保持。
- 中文实际字体PingFangSC-Semibold（CSS PingFang SC / 700），数字Arial Bold；系统字体不随包分发。
- 标题区域left120/top248/width1130；主题128/138px，强调数字190px、标签105px、引词64px；范围44px、口径33px。参数是已选示例，需按新文案长度调整并检查320×180。
- 可替换字段：series、line-a、line-b、claim lead/number/label、scope、note。统计条件紧贴数据。没有真实数值时将claim改为短问句或删除数字强调，不强制每期百分比、胜率、选举或股票内容。
- `index.html`相对复用`../../../wise-video/assets/background/`；安装时须同时提供wise-video背景资源及其GSAP依赖，固定25秒姿态。复制到新项目后必须重算iframe相对路径；不要依赖已归档本期工程。
- `manifest.json`记录批准依据、必要依赖和哈希。模板不带本期成图副本或原始录音；文案仅为排版示例。
- 完整发布由Wise Thumbnail统一生成；标题长度、简介、真实章节次序及统一文案保存规则，以Skill的references/publish-package.md为准。
