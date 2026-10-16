# SRT → 计划 → 实现接线检查

`validate_handoff.py` 检查输入和实际实现之间有没有断线，不以计划中自己填写的“通过”作为证据。结果分 `passed`、`pending`、`failed`；它不判断图是否表达了正确含义，也不读取屏幕像素。

## 新增字段：只增加实际绑定，不复制原文

已有 `coverage` 继续负责“字幕 → 语义 beat”。已有 `render_spec` 继续负责场景、对象和动作。新增一个顶层数组 `render_bindings`，负责“字幕 → 实际画面对象”：

```json
{
  "render_bindings": [
    {
      "caption_id": 1,
      "segments": [
        {
          "scene_id": "boundary",
          "object_ids": ["boundary-exchange", "boundary-broker"],
          "start_ms": 133,
          "end_ms": 1100
        }
      ]
    }
  ]
}
```

- ID 来自 `captions.scope.json`；所有目标字幕都要出现。
- `start_ms` / `end_ms` 使用原 SRT 的**绝对毫秒**，与计划的 `render_spec.scenes` 时间一致。
- `object_ids` 使用实际 HTML ID，不是仅存在于分镜文字中的昵称。开场组件可用实际 `portrait`、`channel` 等，不要求人为伪造 `greeting-*` 前缀。
- 同一字幕跨场景时，使用两个或多个 `segments`；片段并集必须无缺口地覆盖字幕显示区间。
- 同屏复用多个对象有效。一个句子不必生成新对象；绑定到旧对象后如何聚焦由语义动作计划说明。
- 不能用字幕本身、场景根节点或其他场景的对象充当正文主体。
- 使用 `exact` 范围策略时，绑定只覆盖目标范围内实际显示的部分；原文仍从输入读取，不另行改写。

这是接线清单，不是自动通过清单。即使对象存在，它可能仍为透明、被遮挡、太小或表达错误；运行期可见性、几何和语义检查必须另做。

## 概念选择是否实际落地

新制作或本次重制同时引用 [概念清单](concept-inventory.md)。用实际 `render_bindings` 对照重要概念的各次讲述：计划选择的图像、数据图、关系是否真的由绑定对象承担，还是实现时退化成同名字卡。本文脚本不读取像素，也不能验证表达类型，需在实际画面审阅中记录证据；不能仅凭对象ID存在宣布落实。

## 调用

```sh
python3 scripts/validate_handoff.py \
  --intake /absolute/path/episode/intake/run-001 \
  --plan /absolute/path/episode/semantic_plan.json \
  --composition /absolute/path/episode/composition \
  --out /absolute/path/episode/qa/handoff-001.json
```

默认实际 HTML 场景和 `cue_sheet.json` 动作使用从 0 开始的局部时间；工具依据 `effective_start_ms` 转换。计划和绑定始终使用 SRT 绝对时间。仅当实现保留原时间轴时，显式传 `--composition-timebase source`。

修改计划后必须重新生成实现及 provenance。不能为新增绑定字段伪造旧 `plan_sha256`，也不能只手动写一个“passed”。

## 实现适配器契约

本工具直接适配当前项目已有的 HyperFrames 文件结构，不另建动作系统：

- `composition/index.html`：`data-composition-id` 根的 `data-duration`；`.scene` 场景的 ID、`data-start`、`data-duration`；正文对象真实 DOM ID。
- `cue_sheet.json`：`plan_sha256` 和 `cues` 数组。每个 cue 包含 `target`、`scene_id`、`op`、`at_ms`、`duration_ms`，以及计划已有的 `initial`、`values` 等字段。
- 实际 HTML 中 `const cues = [...]`（也支持 `let`、`var`）必须是同一 JSON 数组，工具读取而不执行 JavaScript。
- `provenance.json`：`plan_sha256`、`html_sha256`、`source_captions_sha256`。
- 常规计划对象的真实 ID 为 `场景ID-对象ID`；计划动作也允许直接使用已有的真实 DOM ID。
- 本地图片以 `asset_id.扩展名` 冻结，保持现有编译器约定。素材实际名称若不同，需在制作适配器统一命名或补充可核验的映射；本工具会保留 `pending`，不猜同名含义。
- 已批准的独立开场组件可保持其原 DOM 和原动画。这里核对正文 cue_sheet 和对应计划；开场真实动态效果仍属于运行期检查。

换用其他引擎或运行时生成 DOM 时，不能把检查器的限制伪装成已验证：调整相应适配器或提供等价的机器证据，再扩展检查器。

## 检查与状态

| 状态 | 例子 |
| --- | --- |
| `failed` | 原文/时间变动、漏字幕、未知对象、错误场景、绑定时间缺口、计划与实际动作不一致、缺少本地媒体文件、provenance 不匹配。 |
| `pending` | 整个 `render_bindings` 还未填写、实体素材为 missing/review、ready 图标仍找不到实际图片、使用未冻结远程素材、缺乏可读取的实际 cue 接线。 |
| `passed` | 目标字幕全部绑定真实对象，原文、时间、动作、实际文件和生成记录符合契约。仅限机械接线。 |

无论结果为何，以下状态都单独写成 `not_verified`：`geometry`、`runtime_visibility`、`semantic_expression`、`audio_content_sync`。工具不会采纳计划自填的 `passed` / `verified` / `review` 字段改变结论。

输入依赖也参与结论：接入 `status: failed` 或硬错误归 failed；`status: pending`、`effective_range_content_complete: false` 或重新读取原 SRT 后发现实际范围超过源末尾，均归 pending。即使所有已有字幕对象接线通过，也不能放行未提供的尾部。whole-cues 已收缩为实际已有范围时可以检查通过，但不会声称满足更长的原请求。

退出码：0 = passed，3 = pending，2 = failed。产物不会覆盖同名旧结果。

## 测试和实际运行

```sh
python3 -m unittest discover -s tests -v
```

包内测试包含接入、计划校验、接线及编译依赖回归。以当前执行输出为准；历史作者环境曾通过接入 26 项和接线 22 项。接线反例包括：

- 范围从第 10 秒开始，局部实现仍正确对齐原字幕；不依赖两分钟或第 0 秒。
- 跨场景绑定允许连续的多个片段；缺一毫秒区间也能发现。
- 删除一句、引用不存在对象、引用别的场景对象或用场景根冒充主体均失败。
- 自填 passed 不能覆盖绑定缺口。
- 篡改原始 SRT、接入原文、计划原文或生成动作会被发现。
- 修改实际 HTML cue 后即使重写 HTML 哈希，仍因不符合 cue_sheet 失败。
- 缺素材保持 pending；HTML 引用的文件丢失则 failed。

历史作者环境的 V1 首次接线实测为 failed = 0、pending = 64（全局尚无绑定 + 63 条字幕缺绑定）。旧计划虽有文字式 sentence_coverage，却没有机器可验证的逐条对象接线，因此工具没有把“review”文字当作通过。该历史报告和用户原始素材不随包分发；它是方法来源，不能作为当前工作区已完成测试的证据。
