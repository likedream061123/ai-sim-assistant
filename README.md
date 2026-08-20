# ⚙️ AI 工程仿真助手

一句话工程问题 → AI 解析 → 数值真算（scipy）→ 图表 + 大白话解读。

**数值永不猜**：LLM 只负责把中文翻译成参数，所有数值由 scipy 求解器计算，并对照验证基准（MATLAB / ASME 标准值）。

## 场景（6 个，四大工程领域）

| 场景 | 验证基准 |
|---|---|
| 单摆（动力学） | MATLAB `simple_pendulum_cn.m` |
| 钢件冷却（热处理） | MATLAB `heat1d_explicit.m`（同差分内核） |
| 钢梁挠度（结构校核） | MATLAB `beam_deflection.m` |
| 压力容器壁厚（设计） | ASME 薄壁公式标准值 |
| RC 充电（电学） | 教科书解析解 V=Vs(1-e^(-t/τ))，充到 90% 需 0.230 s |
| 管道压降（流体） | Darcy-Weisbach + Colebrook；层流段对 Poiseuille 解析解 0% 误差 |

## 技术栈

Streamlit · numpy/scipy/matplotlib · LLM（OpenAI 兼容，多服务商）· SerpApi

## 快速开始

```bash
pip install -r requirements.txt
DEEPSEEK_API_KEY=xxx streamlit run app.py
```

**没有 key 也能跑**：手动输入模式完整可用（不调用 AI）。填 key 后 AI 解析 + 大白话解读全开。
可以在网页左侧「API 设置」直接填 key（填过会记住在本机，下次打开免重填），也可以用环境变量注入：

| 服务商 | 环境变量 | 默认模型 |
|---|---|---|
| DeepSeek | `DEEPSEEK_API_KEY` | deepseek-chat |
| OpenAI | `OPENAI_API_KEY` | gpt-4o-mini |
| 智谱 GLM | `ZHIPU_API_KEY` | glm-4-flash |
| 通义千问 | `DASHSCOPE_API_KEY` | qwen-plus |
| Kimi | `MOONSHOT_API_KEY` | moonshot-v1-8k |
| 硅基流动 | `SILICONFLOW_API_KEY` | deepseek-ai/DeepSeek-V3 |

## AI 做了什么（评审关注点）

1. **听懂**：一句中文 → 识别场景 + 提取参数（判别词 few-shot）
2. **方案推荐**：你没说全的关键参数，AI 给出工程推荐值预填进追问表单，一键采纳
3. **不算数**：所有数值由 scipy 求解器计算，MATLAB / ASME 基准复核
4. **溯源透明**：结果区标注每个参数是你给的还是默认值，AI 解读大白话收尾

## 架构

app.py（编排）→ agent/llm.py（中文→JSON）+ agent/serpapi.py（查参）→ engine/*.py（纯数值）→ 图 + 数据 + 解读

## 测试

```bash
python -m pytest tests/ -v
```

## 参赛

DevNetwork [API + Cloud + AI] Hackathon 2026 · 投 SerpApi Best AI Use Case + Overall Winner
