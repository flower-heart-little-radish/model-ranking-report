# 报告数据与交付

编写 UTF‑8 JSON。表内正文、标题和出处名称用纯文本。按用户要求组织段落，多条具体证据放进 `evidence` 卡，版本和价格尽量用官方来源。每个正式或暂定分填写相应的 `score_sources`，覆盖不足时在 `evidence` 或 `methodology` 说明。报告里的分数是你的证据判断，脚本计算名次、总分与排序。

## 字段

| 字段 | 类型和用法 |
| --- | --- |
| `title`, `as_of`, `summary` | 标题、ISO 日期 `YYYY-MM-DD`、简短结论 |
| `dimensions` | 至少一项，各含 `id`, `name`, `finding`, `sources`。顺序就是表列顺序 |
| `models` | 至少两项，各含 `name`, `vendor`, `availability`, `sources`, `scores`, `score_sources`，可选 `provisional` |
| `scores` | 所有维度 ID 到 0–100 的数值或 `null`。缺测用 `null`。保留一位小数，渲染器按四舍五入取一位 |
| `score_sources` | 所有维度 ID 到来源 ID 数组。数值分至少一个来源，缺测允许空数组 |
| `provisional` | 暂定分的维度 ID 数组。每个 ID 必须有数值分 |
| `scenarios` | 各含 `name`, `first`, `first_reason`, `second`, `second_reason`, `sources`。有充分证据的可用次选才写实，没有就解释 |
| `cost_context` | 成本假设、币种/汇率日期、时间和入口等适用范围 |
| `costs` | 按可比成本从低到高填，各含 `model`, `unit_price`, `example_cost`, `sources`。可选 `rank` 表示文字名次，套餐和口径不同比较放末尾 |
| `methodology` | 非空字符串数组，简述权重、标尺、缺测、覆盖和已验证范围 |
| `evidence` | 各含 `title`, `text`, `sources`，可用换行分段 |
| `sources` | 各含 `id`, `title`, `url`。ID 用小写字母、数字和连字符。引用为来源 ID 数组 |

除 `provisional` 和 `rank` 外，上表字段均需提供；`costs` 可以是空数组，此时在 `cost_context` 说明原因。按总分降序，缺测行放表尾并用“—”表示总分。列与总分都用竞赛排名，例如 1、1、3。

## 最小结构示例

以下条目为结构占位，正式报告替换为核验结果，不引用示例来源。

```json
{
  "title": "两款模型编程横评",
  "as_of": "2026-01-01",
  "summary": "这是结构示例。",
  "dimensions": [
    {"id": "coding", "name": "编程", "finding": "例款乙缺直接证据。", "sources": ["same-task"]}
  ],
  "models": [
    {"name": "例款甲", "vendor": "例厂商甲", "availability": "入口说明。",
     "sources": ["same-task"], "scores": {"coding": 90.2},
     "score_sources": {"coding": ["same-task"]}, "provisional": ["coding"]},
    {"name": "例款乙", "vendor": "例厂商乙", "availability": "入口说明。",
     "sources": [], "scores": {"coding": null}, "score_sources": {"coding": []}}
  ],
  "scenarios": [
    {"name": "维护项目", "first": "例款甲", "first_reason": "有同题修复记录。",
     "second": "待补证据", "second_reason": "例款乙暂无可比较的记录。", "sources": ["same-task"]}
  ],
  "cost_context": "示例没有可比定价。",
  "costs": [],
  "methodology": ["示例为单维比较，评分仅展示数据格式。"],
  "evidence": [{"title": "同题记录", "text": "概括提示词、结果与限制。", "sources": ["same-task"]}],
  "sources": [{"id": "same-task", "title": "来源占位", "url": "https://example.com/"}]
}
```

## 渲染与核对

在工作目录保存输入文件。可从任意目录执行 `python "<技能绝对路径>/scripts/render_report.py" "<输入文件>" "<输出文件.html>"`。输出目录须已存在。若命令不在 PATH，使用当前环境提供的 Python 3.9 或更新解释器。无需外部依赖。脚本校验输入与引文，再生成各列排行、按指定维度等权加总的总榜、证据卡与可展开的逐项评分来源。报告内链可离线使用，原始出处需联网打开。如果用户指定非等权能力总分，按用户规则调整计算与验收，同时保留原始分项。

用浏览器核对桌面宽度、手机可滚动评分表与目录跳转。抽查首尾模型名次和总分、可访问入口、重要引用、用户要求的所有场景。受工具限制无法渲染时，验证文件与链接结构并说明。保留用户要求的成品，临时数据和截图按当前工作区约定清理。
