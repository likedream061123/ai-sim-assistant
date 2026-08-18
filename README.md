# ⚙️ AI 工程仿真助手

一句话工程问题 → AI 解析 → 数值真算（scipy）→ 图表 + 大白话解读。

**数值永不猜**：LLM 只负责把中文翻译成参数，所有数值由 scipy 求解器计算，并对照验证基准（MATLAB / ASME 标准值）。

## 场景（4 个，工程味）

| 场景 | 验证基准 |
|---|---|
| 单摆（动力学） | MATLAB `simple_pendulum_cn.m` |
| 钢件冷却（热处理） | MATLAB `heat1d_explicit.m`（同差分内核） |
| 钢梁挠度（结构校核） | MATLAB `beam_deflection.m` |
| 压力容器壁厚（设计） | ASME 薄壁公式标准值 |

## 技术栈

Streamlit · numpy/scipy/matplotlib · DeepSeek（OpenAI 兼容）· SerpApi

## 快速开始

```bash
pip install -r requirements.txt
DEEPSEEK_API_KEY=xxx streamlit run app.py
```

## 架构

app.py（编排）→ agent/llm.py（中文→JSON）+ agent/serpapi.py（查参）→ engine/*.py（纯数值）→ 图 + 数据 + 解读

## 测试

```bash
python -m pytest tests/ -v
```

## 参赛

DevNetwork [API + Cloud + AI] Hackathon 2026 · 投 SerpApi Best AI Use Case + Overall Winner
