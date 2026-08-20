# 设计计划 — 状态反馈系统化（Phase 3）

> 承接 Phase 2 `_recon.md`。方向：**计算中 / 成功 / 出错 / 空态** 四态 token 化。
> 现状盘点（读 app.py 主流程）：loading 用原生 `st.spinner` + `st.status`（已发光玻璃）；success/error/warning/info 已有四色圆角容器但**全部静态无入场动效**；**空态完全缺失**（未计算时结果区整段空白）。

## 一、Token 表（全部 CSS 从此派生，不即兴新色）

### 色板（沿用第一轮，不改）
| token | 值 | 用途 |
|-------|-----|------|
| `--bg` | `#05091A` | 页面底 |
| `--surface` | `#0B1229` | 卡片底 |
| `--accent` | `#3D7BFF` | 主操作/loading bar |
| `--accent-2` | `#9A8CFF` | 渐变第二极 |
| `--text` | `#F0F4FF` | 正文 |
| `--text-dim` | `#9fb4ff` | 次要文字 |

### 字体（沿用）
display: Sora 700/800 · body: Segoe UI / Microsoft YaHei · mono: Consolas（数值）

### 状态 token（本轮核心新增）
| 状态 | 触发场景 | 载体 | 视觉 token |
|------|---------|------|-----------|
| **loading** | 计算 / AI 解析 / 敏感性扫描 / 解读生成 | `st.spinner` + `st.status` | **均衡器三 bar**：`scaleY 1→1.5` 呼吸 + `background-color #3D7BFF→#fff` 亮度 + stagger delay `.25s`（uiverse 技法）；阶段文案靠 `s.update(label=…)` 轮播 |
| **success** | 参数填入 / 建议应用 / 识别成功 | `st.success` | **check-in 弹入**：`scale(.6)→1` `.25s expo`（stateful-button ✓ 技法），青绿底 `#2A9D8F` |
| **error** | 计算失败 / NaN / 越界 / SerpApi 失败 | `st.error` | **shake-x** `.3s` 抖动入场，红底 `#E74C5A` |
| **empty** | 未计算 / 无结果 | **自建骨架占位**（`st.markdown` HTML，无 JS 可跑） | shimmer 扫光卡 ×3 + 有态度引导文案 |

### 动效 token
| token | 值 | 用在哪 |
|-------|-----|--------|
| ease | `cubic-bezier(.16,1,.3,1)` | 全部入场 |
| dur-enter | `.5-.6s` | 编排时刻（沿用） |
| dur-micro | `.2-.3s` | check-in / shake-x / hover |
| eq-stagger | `.25s` | 均衡器三 bar |
| reduced | `@media (prefers-reduced-motion)` | 全关 |

规则：**编排时刻仍只有一个**（计算完成），loading/success/error 动效均 ≤ dur-micro。

## 二、Wireframe 对比（2 方案）

### 方案 A —— 就地四态（✅ 选中）
```
[品牌 header + accent-line + hero-glow]        ← 沿用
[radio 自然语言 | 手动输入]                     ← 沿用
[输入 hero textarea]                            ← 沿用
[解析并计算 / 计算]      ⬅ loading: spinner 换均衡器
[空态骨架占位]            ⬅ 新增：未计算时 shimmer ×3 + 引导文案
[st.status 解析条]        ⬅ 沿用，spinner 换均衡器
[结果区] 图表淡入 → 数据卡浮起 → Count Up       ← 编排时刻（沿用）
         ⬇ 若有超限：warning 建议卡 + 一键应用    ← 沿用
         ⬇ success/error 就地 check-in / shake   ← 新增动画
```
**选它**：改动是纯增量（CSS + 一个空态函数），不重构布局，风险低；四态落在各自天然位置（哪儿发生就在哪儿反馈），符合 Operate 模式「一致性强于表达」。

### 方案 B —— 集中状态卡（弃）
所有四态收敛进结果区顶部一个状态容器：
```
[按钮]
[状态卡] loading均衡器 / success ✓ / error ✗ / empty骨架 ← 统一出现
[结果区]
```
**弃它**：四态分布在不同代码路径（解析失败、建议应用、计算异常各在别处），强收进一个容器 = 重构所有反馈分支，改动面大；且 Streamlit 的 st.success/error 就地出现更自然，强行收敛反而「为统一而统一」。

## 三、签名元素（一句话，不许留白）

> **签名元素 = 结果区的「骨架空态」——未计算时不空白、不编数，用 shimmer 骨架占位 + 一句有态度的引导：「还没开算。数值不会骗你，但也不会自己跑来 —— 说一句工程问题，或点个示例。」** 来自产品主题「数值永不猜」：没算就诚实说没算，绝不预填假结果。

有意的不完美：骨架卡是**半透明虚线描边** + 微错位（第二张比第一张矮一点），一眼看出是「占位」而不是「残缺真结果」——跟同类工具整齐划一的空态区分开。

## 四、编排时刻

**唯一编排时刻：计算完成**（沿用第一轮，收束成完整链路）：
`点击计算 → [loading 均衡器] → 图表淡入(.6s) → 数据卡依次浮起(stagger 70ms) → 数值 Count Up → (若有超限) warning 建议卡 check-in`

其余动效一律 ≤ dur-micro：success/error 只在「反馈出现」那一下动（check-in / shake），不循环、不飘移。

## 五、对照 brief 检查

- 默认风险：「改完像没改」。→ 修正：空态骨架是**肉眼可见的新元素**（占了未计算时的大块空白区），均衡器替换原生转圈、成功失败动画化，四态统一 token 族，视觉语言连贯。
- 反默认：没有三个等宽 feature 卡、没有无限微动画、没有 AI-紫渐变（accent 仍靛蓝 #3D7BFF）。
- 动效闸门（Phase 1 定死）：全部 CSS 可做 → 不上 GSAP。均衡器/打勾/抖动/骨架 shimmer 均为 keyframes，无滚动触发、无时间线、无物理。

---
**Phase 4 落地清单**：
1. CSS：均衡器（stSpinner + stStatus 内 spinner 替换）、check-in（stSuccess）、shake-x（stError）、骨架 shimmer（新类 `.sk-*`）、reduced-motion
2. Python：`_empty_state_hint()`（手动模式未计算 + 自然语言未解析时渲染骨架 + 引导文案）
3. 不动：布局、配色、字体、编排时刻主体
