# 素材侦察记录 — 状态反馈系统化（Phase 2）

> 承接 Phase 0/1 批准方向：**计算中 / 成功 / 出错 / 空态** 四态 token 化。
> Design Read 关键词：深蓝极光 `#05091A` + 靛蓝 accent `#3D7BFF`、玻璃卡、克制动效（MOTION_INTENSITY 4）、Sora。
> 素材侦察关键词：**loading 反馈 / 成功打勾 / 骨架空态 / 状态文案轮播**

## 一、覆盖表（四源全覆盖）

| 源 | 看了什么 | 技法要点 | 契合度 |
|----|---------|---------|:---:|
| **ui.aceternity.com** | `components` 清单 → 重点抓 `stateful-button`、`multi-step-loader`、`features-section-with-skeletons` 三个组件页 | ①**stateful-button**：提交→成功态打 ✓，`scale:0→scale:1, width:20px, 0.2s`（打勾收窄+弹入）；②**multi-step-loader**：多步骤线性进度条逐格点亮；③**skeletons**：shimmer 扫光 + 骨架占位 | ⭐⭐⭐ |
| **reactbits.dev** | 全部组件分类翻查（CDP 扫 DOM 99279 字节） | 无 loader/状态类组件；WebGL 背景动画为主（Aurora / Particles / Waves） | ⭐ |
| **uiverse.io** | `/loaders` 分类页 → 逐个 eval 提取渲染后 CSS，落地 2 枚 | ①**均衡器三 bar**：`scaleY` 呼吸 + `background-color` 亮度 + `animation-delay` stagger（0/.25/.5s）；②**文字轮播**：`overflow:hidden` + `translateY` 步进 + 上下 `linear-gradient` 渐变遮罩裁剪 | ⭐⭐⭐ |
| **motionsites（MCP）** | `search_prompts("Loader Animation")` | 免费账号结果全 premium 不可开（余量留给方向级参考）；提示词偏「站点级动效叙事」粒度，与四态 token 不匹配 | ⭐ |

## 二、筛选记录

**筛掉**：
- uiverse 液态 / 粒子 / 3D 系列 loader：视觉强度超克制动效红线（MOTION_INTENSITY 4），且部分依赖 JS 库，Streamlit 剥 script 后难落地。
- reactbits 全部 WebGL 背景：第一轮 Aurora 已吸收同类技法，无新增量。
- aceternity `spotlight` / `card-hover` 等动效卡：第一轮已用。
- motionsites「Loader Animation」premium：免费账号打不开；即使开了，站点级动效叙事与「按钮/表单级状态反馈」粒度不符。

**留下 5 个素材**：

1. **stateful-button 的 ✓ 打勾**（aceternity）— 对应 **success 态**
   - 为什么留：成功反馈最直白的锚点——「计算完成」不只是换文字，是把结果宣告变成一个小动作。
   - 怎么转纯 CSS：`@keyframes check-in { from { scale:0; width:0 } to { scale:1; width:20px } }` 0.2s 单次播放。Streamlit 里用 `st.success` 容器 + CSS 注入 class，或按钮 label 前缀换 emoji 态。
   - 签名位置：**计算完成瞬间**的结果区入场前奏。

2. **均衡器三 bar**（uiverse `kennyotsu/fresh-lizard-20`）— 对应 **loading 态**
   - 为什么留：纯 CSS 无 JS，Streamlit 友好；`animation-delay` stagger 三行搞定，比转圈 spinner 更有「工程在算」的质感。
   - 怎么转纯 CSS：`@keyframes scale-up4 { 20% { background-color:#fff; scaleY(1.5) } 40% { scaleY(1) } }` + 三 bar 各自 delay 0/.25/.5s。
   - 签名位置：**计算中** 按钮旁 / `st.spinner` 的替代注入。

3. **文字轮播**（uiverse `kennyotsu/fresh-lizard-20` 同作者 .words 技法）— 对应 **loading 态文案**
   - 为什么留：文字反馈比 spinner 更有信息量——「识别场景 → 求解方程 → 渲染图表」三步给用户进度预期。
   - 怎么转纯 CSS：`overflow:hidden` 定高容器 + 文案 translateY 步进 + 上下渐变遮罩模拟裁剪。
   - 签名位置：loading 状态条旁的行内文案轮播。

4. **multi-step-loader 线性进度**（aceternity）— 对应 **loading 态结构**
   - 为什么留：多步骤流程（解析→查参→计算→解读）分段点亮，让「AI 在干嘛」透明化，消解等待焦虑。
   - 怎么转纯 CSS：Streamlit 用 `st.status` 分段 update 即可（原生载体），不额外造轮子。
   - 签名位置：自然语言解析主流程。

5. **骨架 shimmer**（aceternity skeletons）— 对应 **空态 / 占位**
   - 为什么留：初次打开、无历史、无结果时，骨架占位比空白页更有「有货」的预期感。
   - 怎么转纯 CSS：`linear-gradient` 背景偏移 + `background-position` 动画的 shimmer 扫光；Streamlit 用 `st.empty` + 占位卡。
   - 签名位置：**无结果/未计算** 的结果区占位。

## 三、跳过声明

- **reactbits**：全组件翻查确认无 loader/状态反馈类组件（WebGL 背景动画为主），第一轮 Aurora 已吸收 → 跳过，不凑数。
- **motionsites**：仅搜「Loader Animation」一次即确认 premium 墙，免费 3 次额度不浪费在无关搜索 → 跳过，余量留 Phase 3 做方向级参考。

## 四、Phase 3 输入

- 状态 token 四态锚点齐了：loading=均衡器+文案轮播+线性进度、success=✓ 打勾、error=复位+警示色、empty=骨架 shimmer。
- 下一步：token 表 + ASCII wireframe + 签名元素一句话 + 编排时刻。
