# 模板登记与验证

首次探索先保存在本期项目，记录 `status: candidate`。只有用户明确选定某方向，才建立确认模板记录；当前生成时间、新文件名、模型推荐都不是用户确认。

## 最小记录

```json
{
  "template_id": "wise-thumbnail-series-v1",
  "status": "approved",
  "approval": {
    "evidence": "用户选择方向的消息或可核验记录",
    "selected_candidate": "实际候选ID"
  },
  "canvas": {"aspect": "16:9", "working_size": [3840, 2160]},
  "brand": {
    "palette": [],
    "font_sources": [],
    "identity_assets": [],
    "signature_placement": "来自选定实际图片的参数"
  },
  "layout": {
    "primary_focus": "来自选定图片的阅读顺序",
    "title_area": [],
    "subject_area": [],
    "protected_areas": [],
    "allowed_variants": []
  },
  "variable_fields": ["headline", "optional_support", "topic_subject", "optional_date"],
  "assets": [],
  "qa": {"full_size_viewed": true, "thumbnail_320x180_viewed": true},
  "generation_recipe": "相对路径或可复现描述"
}
```

这是字段说明，不能原样当成已确认记录。参数来自实际选定画面；可以不用某些可选字段。`assets` 仅登记复用必需的真实文件路径、来源、SHA256 与用途。品牌色、字号区间、布局参数和示例图要彼此一致。

模板允许主视觉按内容更换，不能只保留一张包含旧标题的扁平图片就声称以后可直接复用。最少保留可替换文字/主体的规则、生成配方和必需品牌原件；如已有排版源，只保存相关最小源文件。

字体或头像无法随 Skill 分发时，在 manifest 标注外部依赖和取得方式，不偷偷回退到错误人物或不支持中文的字体。跨电脑路径相对 Skill/模板根目录解析。

## 每期交付简记

保存最终文件名、尺寸、字节数、SHA256、对应视频、主命题、模板版本、实际检查结果。不为每期重复复制品牌原件。未生成或未实看部分写未完成，不将技术文件检查记成审美通过。

上传规格的官方来源可用：<https://support.google.com/youtube/answer/72431>。记录核验日期与适用设备，避免把曾经的推荐值变成永久硬约束。
