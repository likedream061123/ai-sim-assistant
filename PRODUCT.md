# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Stack

Python + Streamlit + scipy + matplotlib + DeepSeek（OpenAI SDK，仅解析/解读）+ SerpApi（查典型参数）。

## Users

- 主要用户：hackathon 评审（DevNetwork [API+Cloud+AI] Hackathon 2026，截止 2026-09-04 01:00）。
  看 demo + 亲手试用，判断工程能力与 AI 集成的完成度。第一印象决定评分走向。
- 真实目标用户：工程师、工程学习者——用一句中文描述工程问题，免学 MATLAB 语法拿到可复核的数值仿真结果。

## Product Purpose

用户用一句中文描述工程问题（"4米钢梁受10kN力挠度多少"），AI 解析出参数，交给 scipy 确定性求解
（单摆/钢件冷却/钢梁挠度/压力容器壁厚），输出图表 + 关键数据 + 大白话解读。
成功 = demo 2 分钟内跑通 4 场景，且评审信服"数值是真的、可被 MATLAB 复核"。

## Positioning

LLM 只做"人话→参数"翻译，**绝不参与计算**——数值由 scipy 求解、MATLAB 基准验证。
这是与"AI 直接给答案"类工具的本质差异：可复核、可信任、数值永不猜。

## Operating Context

- demo 用 `streamlit run app.py` 本地起服务、浏览器操作；docs/demo_script.md 提供 2 分钟分段脚本。
- 手动输入模式是自然语言解析失败/无 API key 时的兜底，必须始终可用。
- 中文字体（微软雅黑优先）是硬约束：图与 UI 同时渲染中文+英文且零 Glyph 警告。
- 无 DEEPSEEK_API_KEY / SERPAPI_KEY 时优雅降级不崩。
- MATLAB 是验证基准（docs 下 .m 文件），非运行时依赖。

## Capabilities and Constraints

- 4 场景引擎统一接口 solve(params) -> {"figures","data"}，模块级别名；app.py 编排层只串不算。
- 自然语言模式：LLM 解析 → 引擎真算 → AI 解读；手动模式：表单直算（兜底）。
- 参数溯源：展示"你给的/已用默认"；数值异常（NaN/发散）红框提示。
- SerpApi 查钢梁典型参数（E/I），无 key 优雅降级。
- 约束：scipy 结果与 MATLAB 基准一致（测试断言咬死）；UI 文案中文为主、英文可混排。

## Brand Commitments

- 作品名：「AI 工程仿真助手」；副标题"工程问题一句话 → AI 解析 → 数值真算 → 图表 + 大白话解读。数值永不猜。"
- 无既有品牌资产/logo，hackathon 新作品。

## Evidence on Hand

- 测试 29 passed（MATLAB 基准断言：beam v_max=1.2265e-4 @1.859m、M_max=9375N·m；heat 中心 872.5s；pendulum T_ratio>1）。
- AppTest 冒烟：四场景手动 + 自然语言降级 + 溯源 + SerpApi 降级全过。
- docs/demo_script.md、README.md 已写。
- 尚无真实 API key：LLM 解析/解读均为 mock 影子验收，未跑真 LLM。

## Product Principles

1. 数值永不猜：LLM 只翻译参数，计算只信 scipy，结论可被 MATLAB 复核。
2. 优雅降级：无 key、SerpApi 失败、解析失败，都不该让用户卡死。
3. 透明可溯源：每个结果展示参数来源，用户知道什么来自他、什么用了默认。
4. 评审友好：demo 2 分钟内讲清"一句话→真算→解读"，观感配得上完成度。

## Accessibility & Inclusion

- 中文字体覆盖保证 CJK 正常渲染、英文混排不丢字形。
- 图 + 数据双通道输出，色弱用户也能读数值。
