# 大模型横评报告 · Model Ranking Report

面向 Codex 的大模型比较技能。从中英文榜单、实测和用户反馈核对最新旗舰，产出能力排行、场景首选与次选、成本对照，以及可离线浏览的单文件 HTML。

## 安装与使用

从本仓库安装 `model-ranking-report/` 这个子目录。使用 Codex 的 `$skill-installer` 时，可以给它仓库 URL 和该子目录。也可以手动把整个子目录放进 `$CODEX_HOME/skills/`，未配置 `CODEX_HOME` 时用 `~/.codex/skills/`。安装后打开新会话并输入：

> 用 $model-ranking-report 横评我列出的模型。核对当前可用的旗舰、版本和价格，按科学推理、编程、事实可靠性、智能体办公和文学与对话五维打分。给出做课件、编程、日常搜索和题目答疑的首选与次选，最后交付 HTML。

可以在请求里限定地区、预算、工具、日期、来源权重和维度。默认五维总分 500，成本另列。报告把榜单、复现实测、评论和缺测分开说明。

## HTML 渲染

需要 Python 3.9 或更新版本。渲染器用标准库，读取 UTF‑8 JSON、自动计算中文列名次和总分、嵌入样式，不访问网络。输入格式见 [报告数据与交付](model-ranking-report/references/report-format.md)。

```sh
python model-ranking-report/scripts/render_report.py report.json model-ranking.html
```

联网证据由使用此技能的 Codex 收集。评分由证据支持，注明暂定和缺测。官方版本、套餐和时效性数据随报告日期重新核对。

MIT License
