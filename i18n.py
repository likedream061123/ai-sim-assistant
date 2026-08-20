"""轻量 i18n：中文原文 → 英文（提交/演示默认 en；zh 模式返回原文零变化）。

用法:
    import i18n
    i18n.set_lang(st.session_state.get("lang", "en"))   # app.py 每次 rerun 开头调用
    i18n.tr("解析并计算")     # zh→原文；en→查表英文，查不到返回原文（漏翻不空白）
    i18n.trf("共 {0} 条", 3)  # 模板翻译 + 占位填充（f-string 改 trf 模板）

架构：原文映射 dict（中文 key → 英文 value）。engine 图表/建议文案也调 tr()/trf()，
本模块不 import streamlit 保持引擎纯净。查不到原文时英文模式返回原文，宁缺毋滥。
"""
from __future__ import annotations

LANG = "en"

_EN: dict[str, str] = {
    # ================= 品牌 / 主流程 =================
    "AI 工程仿真助手": "AI Engineering Simulation Assistant",
    "一句话描述工程问题，AI 解析参数，数值真算，大白话解读。":
        "Describe an engineering problem in plain language — AI extracts the parameters, "
        "numeric solvers do the real math, charts + plain-English interpretation follow.",
    "描述你的工程问题": "Describe your engineering problem",
    "输入方式": "Input mode",
    "自然语言": "Natural language",
    "手动输入": "Manual input",
    "解析并计算": "Parse & Compute",
    "计算": "Compute",
    "场景": "Scenario",
    "想快速试？点一个直接填入：": "Want a quick try? Tap one to fill in:",
    "📐 图表大小": "📐 Chart size",
    "拖动滑块调整图表宽度（像素），比例自动保持；数据不变，只是视图缩放。":
        "Drag to resize charts (px); aspect ratio is preserved, data is unchanged.",
    "参数对比": "Parameter Comparison",
    "改一个参数，看结果怎么变 —— 帮你理解每个参数的『手感』。":
        "Change one parameter, watch the result — build intuition for each variable.",
    "该参数当前没有值，先在表单里设一个。":
        "This parameter has no value yet — set one in the form first.",
    "采样点数": "Sample points",
    "范围下限要小于上限。": "The lower bound must be below the upper bound.",
    "生成对比曲线": "Generate comparison curve",
    "采样点太少或求解失败，把范围放宽些再试。":
        "Too few sample points or solve failed — widen the range and retry.",
    # ================= 场景名（selectbox 显示） =================
    "单摆 (动力学)": "Pendulum (Dynamics)",
    "钢件冷却 (热处理)": "Steel Quenching (Heat)",
    "钢梁挠度 (结构校核)": "Beam Deflection (Structural)",
    "压力容器壁厚 (设计)": "Pressure Vessel (Design)",
    "RC 充电 (电学)": "RC Charging (Electronics)",
    "管道压降 (流体)": "Pipe Pressure Drop (Fluids)",
    # ================= 手动模式参数标签 =================
    "目标温度 (°C)": "Target temp (°C)",
    "充电目标 (%)": "Charge target (%)",
    "🔍 查钢梁典型参数（在线）": "🔍 Look up typical steel-beam params (online)",
    "🔍 查钢热扩散系数（在线）": "🔍 Look up steel thermal diffusivity (online)",
    "🔍 查管壁粗糙度（在线）": "🔍 Look up pipe wall roughness (online)",
    "🔍 查常用元件值（在线）": "🔍 Look up common component values (online)",
    "热扩散系数 α (m²/s)": "Thermal diffusivity α (m²/s)",
    "绝对粗糙度 ε (m)": "Absolute roughness ε (m)",
    "已按在线来源填入 {0} = {1}（{2} 个来源一致）。":
        "Filled {0} = {1} from {2} agreeing online sources.",
    "在线搜索未找到可靠一致值（或未配置 SerpApi Key），已填入内置典型值 {0} —— 可在输入框直接修改。":
        "No reliable consensus found online (or no SerpApi key) — filled built-in typical values {0}. Edit in the inputs above.",
    "在线搜索未找到可靠一致值（或未配置 SerpApi Key），已填入内置典型值 —— 可在输入框直接修改。":
        "No reliable consensus found online (or no SerpApi key) — filled built-in typical values. Edit in the inputs above.",
    "参数来源（多源交叉）": "Parameter sources (cross-checked)",
    "填入的是典型值，仍可在上方输入框微调。":
        "These are typical values — fine-tune them in the inputs above.",
    "已应用设计建议：{0}": "Applied design suggestion: {0}",
    # ================= 结果区 =================
    "参数与来源（溯源）": "Parameters & Sources (traceability)",
    "关键数据": "Key Results",
    "设计辅助 · 参数敏感性": "Design Help · Parameter Sensitivity",
    "（当前参数下无法完成敏感性扫描）":
        "(sensitivity scan not possible with these parameters)",
    "AI 解读": "AI Interpretation",
    "✏️ 切到手动模式微调参数": "✏️ Fine-tune in Manual Mode",
    "AI 识别到的参数：{0}": "AI extracted parameters: {0}",
    "已识别：{0}": "Recognized: {0}",
    "✨ AI 推荐：{0}（可直接用，也可改）": "✨ AI suggests: {0} (use as-is or edit)",
    "没提到的参数用工程默认值，结果区会标出哪些是默认（参数溯源）。":
        "Parameters you didn't mention use engineering defaults; the result panel marks "
        "which ones are defaults (traceability).",
    "就用这些参数计算": "Compute with these parameters",
    "荷载位置 a={0:g} m 超过了梁长 L={1:g} m —— 集中力落在梁外了，":
        "Load position a={0:g} m exceeds beam length L={1:g} m — the force lies outside the beam. ",
    "计算失败：{0}": "Solve failed: {0}",
    "参数不合理，结果发散（NaN/Inf）——请调整参数后重算。":
        "Invalid parameters, result diverged (NaN/Inf) — adjust and recompute.",
    # ================= 建议卡（design.advice 文案模板） =================
    "最大挠度 {0:.1f} mm 超过许用 {1:.1f} mm": "Max deflection {0:.1f} mm exceeds limit {1:.1f} mm",
    "（L/360）。挠度与截面惯性矩成反比：把 I 从 {2:.3g} m⁴ 加大到约 {3:.3g} m⁴（{4:.1f}×，留 25% 裕量），即可回到限内。":
        " (L/360). Deflection is inversely proportional to inertia: raise I from {2:.3g} m⁴ to "
        "≈{3:.3g} m⁴ ({4:.1f}×, 25% margin) to pass.",
    "仿真时长内中心温度未降到目标。冷却时间约与半宽 L² 成正比、随介质温度 T_wall 升高而缩短 —— 减小 L 或提高 T_wall 都能显著加快。":
        "Center didn't reach target within simulation time. Cooling time scales with L² and "
        "shrinks as T_wall rises — reduce L or raise T_wall.",
    "给定壁厚 {0:.1f} mm 下实际应力 {1:.0f} MPa，超过许用 {2:.0f} MPa。ASME 所需壁厚 {3:.1f} mm —— 建议加厚到 {4:.1f} mm（留 25% 裕量）即安全。":
        "At given thickness {0:.1f} mm the actual stress {1:.0f} MPa exceeds allowable {2:.0f} MPa. "
        "ASME requires {3:.1f} mm — thicken to {4:.1f} mm (25% margin) to be safe.",
    "流速 {0:.1f} m/s 超过水的经济流速上限 3 m/s —— 流速快、磨损大，且压降随流量平方上涨。流速与管径平方成反比：把管径从 {1:.0f} mm 加大到约 {2:.0f} mm（+25%），流速可压回 ~{3:.1f} m/s。":
        "Velocity {0:.1f} m/s exceeds the 3 m/s economic ceiling — fast flow wears pipes and "
        "pressure drop grows with flow squared. Velocity scales with 1/D²: raise diameter from "
        "{1:.0f} mm to ≈{2:.0f} mm (+25%), velocity drops to ~{3:.1f} m/s.",
    "流速 {0:.2f} m/s 低于经济流速下限 0.5 m/s —— 管径偏大、流速偏慢，杂质易沉积。建议把管径收到约 {1:.0f} mm（-25%），流速提到 ~{2:.2f} m/s。":
        "Velocity {0:.2f} m/s is below the 0.5 m/s economic floor — pipe oversized, solids may "
        "settle. Reduce diameter to ≈{1:.0f} mm (-25%), velocity rises to ~{2:.2f} m/s.",
    # ================= 导出 =================
    "📦 结果可以带走：": "📦 Export results:",
    "导出 JSON（完整数据）": "Export JSON (full data)",
    "导出 CSV（表格）": "Export CSV (table)",
    "完整结果：标量 + 参数 + 曲线（heat 温度曲线），给评审 / 归档用。":
        "Full result: scalars + parameters + curves (heat profile), for judges / archives.",
    "表格视图：参数与结果的键值表，Excel / 表格软件可直接打开。":
        "Tabular view: key-value pairs of parameters & results, opens directly in Excel.",
    "项目": "Item",
    "值": "Value",
    # ================= 历史 =================
    "📚 计算历史（本机 {0} 条）": "📚 History ({0} saved)",
    "刚才算过的都在这里，一键把参数带回来微调，不用重新打字。":
        "Past runs are here — one click reloads the parameters for fine-tuning.",
    "载入参数": "Reload params",
    # ================= 验证区 =================
    "🧪 数值可复核：每个数都对过 MATLAB / ASME": "🧪 Numerically verifiable — every value checked against MATLAB / ASME",
    "LLM 只负责「听懂中文、提取参数」，**从不参与计算**。所有数值由 scipy 求解器算出，默认参数下的结果与验证基准一致：":
        "The LLM only understands Chinese and extracts parameters — it **never does math**. "
        "All values come from scipy solvers and match the verification baselines below:",
    "单摆（动力学）": "Pendulum (Dynamics)",
    "周期 T ≈ 2.252 s（θ₀=120°，周期比 1.12 → 大角度变慢）":
        "Period T ≈ 2.252 s (θ₀=120°, ratio 1.12 → large-angle slowdown)",
    "MATLAB `simple_pendulum_cn.m` 一致": "Matches MATLAB `simple_pendulum_cn.m`",
    "钢件冷却（热处理）": "Steel Quenching (Heat)",
    "中心 ~873 s 降到 100°C": "Center reaches 100°C at ~873 s",
    "MATLAB `heat1d_explicit.m` 同差分内核": "Same finite-difference kernel as MATLAB `heat1d_explicit.m`",
    "钢梁挠度（结构校核）": "Beam Deflection (Structural)",
    "0.1227 mm @ 距左端 1.86 m": "0.1227 mm @ 1.86 m from left support",
    "MATLAB `beam_deflection.m` 基准 0.1226 mm，误差 <0.1%":
        "MATLAB `beam_deflection.m` baseline 0.1226 mm — error <0.1%",
    "压力容器壁厚（设计）": "Pressure Vessel (Design)",
    "t = 5.00 mm": "t = 5.00 mm",
    "ASME 薄壁公式 t = PD/(2σ)，解析解无误差": "ASME thin-wall t = PD/(2σ), analytic, zero error",
    "RC 充电（电学）": "RC Charging (Electronics)",
    "τ=0.1 s，充到 90% 需 0.230 s": "τ=0.1 s, 90% charge in 0.230 s",
    "教科书解析解 V=Vs(1-e^(-t/τ))": "Textbook analytic solution V=Vs(1-e^(-t/τ))",
    "管道压降（流体）": "Pipe Pressure Drop (Fluids)",
    "D=50mm·20m³/h → 流速 2.8 m/s，压降 ≈169 kPa":
        "D=50mm, 20m³/h → velocity 2.8 m/s, drop ≈169 kPa",
    "Darcy-Weisbach + Colebrook，层流段对解析解 0% 误差":
        "Darcy-Weisbach + Colebrook; laminar branch has 0% error vs analytic solution",
    # ================= 侧边栏 =================
    "API 设置": "API Settings",
    "LLM 服务商": "LLM Provider",
    "AI 解析 + 解读用的模型服务商，全部走 OpenAI 兼容接口。":
        "Model provider for AI parsing & interpretation, all OpenAI-compatible.",
    "（AI 解析需要）": "(needed for AI parsing)",
    "自然语言解析 + AI 解读需要。本地留空自动用内置 secrets；线上演示请填自己的 key，否则只能用「手动输入」。":
        "Required for natural-language parsing + AI interpretation. Leave blank to use local "
        "secrets; for the live demo fill in your own key, otherwise Manual mode only.",
    "仅「查钢梁典型参数」按钮需要，可不填。":
        "Only needed for the steel-beam lookup button. Optional.",
    "SerpApi Key": "SerpApi Key",
    "语言 / Language": "语言 / Language",
    "英语（提交/演示）": "English (submission)",
    "中文": "中文",
    # ================= _fmt 值 =================
    "是": "Yes",
    "否": "No",
    "—（未计算）": "—",
    "发散": "diverged",
    # ================= 引擎图标题（trf 模板） =================
    "钢梁挠度 | 最大 {0:.3f} mm @ x={1:.3f} m": "Beam deflection | max {0:.3f} mm @ x={1:.3f} m",
    "x (m)": "x (m)",
    "挠度 v(x) (mm, 向下为正)": "Deflection v(x) (mm, downward +)",
    "弯矩图 | 最大 |M| = {0:.0f} N·m @ x={1:.3f} m": "Bending moment | max |M| = {0:.0f} N·m @ x={1:.3f} m",
    "弯矩 M(x) (N·m)": "Moment M(x) (N·m)",
    "钢件冷却：温度分布快照": "Steel quenching: temperature snapshots",
    "x (m, 0=中心)": "x (m, 0=center)",
    "T (°C)": "T (°C)",
    "钢件中心冷却曲线": "Center temperature profile",
    "中心温度 (°C)": "Center temp (°C)",
    "t (s)": "t (s)",
    "摆角 - 时间": "Angle vs time",
    "θ (deg)": "θ (deg)",
    "角速度 - 时间": "Angular velocity vs time",
    "ω (rad/s)": "ω (rad/s)",
    "相平面": "Phase plane",
    "机械能 - 时间": "Mechanical energy vs time",
    "E (J)": "E (J)",
    "薄壁圆筒壁厚 | 当前 P={0:.2f} MPa → t={1:.2f} mm": "Thin-wall vessel | P={0:.2f} MPa → t={1:.2f} mm",
    "内压 P (MPa)": "Internal pressure P (MPa)",
    "所需壁厚 t (mm)": "Required wall thickness t (mm)",
    "RC 充电 | τ={0:.3g}s，充到 {1:.0f}% 需 {2:.3g}s": "RC charging | τ={0:.3g}s, {1:.0f}% in {2:.3g}s",
    "电容电压 Vc (V)": "Capacitor voltage Vc (V)",
    "充电电流衰减 | 初始峰值 {0:.3g} A": "Charging current decay | initial peak {0:.3g} A",
    "充电电流 i (A)": "Charging current i (A)",
    "沿程压降 | 总 {0:.2f} kPa（{1:.0f} Pa）": "Pressure drop | total {0:.2f} kPa ({1:.0f} Pa)",
    "沿程距离 x (m)": "Distance along pipe x (m)",
    "累计压降 (kPa)": "Cumulative drop (kPa)",
    "压降随流量 | Q={0:.1f} m³/h → {1:.2f} kPa": "Drop vs flow | Q={0:.1f} m³/h → {1:.2f} kPa",
    "流量 Q (m³/h)": "Flow rate Q (m³/h)",
    "压降 (kPa)": "Pressure drop (kPa)",
    # ================= design.py 图标签 =================
    "参数对比 | {0} 变化 → {1}": "Parameter sweep | {0} vs {1}",
    "该参数 ±10% 时「{0}」的变化 (%)": "Change in \"{0}\" per ±10% of the parameter (%)",
    "参数敏感性 | 改变谁影响最大？（{0}）": "Sensitivity | which parameter matters most? ({0})",
    "当前值 = {0:.3g}": "current = {0:.3g}",
    # ================= 场景示例卡按钮 label（填入的问题保持中文——LLM 中文 few-shot 解析） =================
    "动力学 · 单摆": "Dynamics · Pendulum",
    "结构 · 钢梁": "Structural · Beam",
    "设计 · 容器": "Design · Vessel",
    "传热 · 冷却": "Heat · Quenching",
    "电学 · RC充电": "Electronics · RC Charging",
    "流体 · 管道压降": "Fluids · Pipe Drop",
    # ================= 手动模式参数 label =================
    "初始角度 θ₀ (°)": "Initial angle θ₀ (°)",
    "初始角速度 ω₀ (rad/s)": "Initial angular velocity ω₀ (rad/s)",
    "时长 (s)": "Duration (s)",
    "钢件半宽 (m)": "Half-width (m)",
    "初始温度 (°C)": "Initial temp (°C)",
    "介质温度 (°C)": "Medium temp (°C)",
    "梁长 (m)": "Beam length (m)",
    "集中荷载 (N)": "Point load (N)",
    "荷载距左端 (m)": "Load position from left (m)",
    "弹性模量 E (Pa)": "Modulus E (Pa)",
    "惯性矩 I (m4)": "Moment of inertia I (m4)",
    "内压 (Pa)": "Internal pressure (Pa)",
    "内径 (m)": "Inner diameter (m)",
    "许用应力 (Pa)": "Allowable stress (Pa)",
    "校核给定壁厚": "Check given thickness",
    "给定壁厚 t (m)": "Given thickness t (m)",
    "电阻 R (Ω)": "Resistance R (Ω)",
    "电容 C (F)": "Capacitance C (F)",
    "源电压 Vs (V)": "Source voltage Vs (V)",
    "流量 Q (m³/s)": "Flow rate Q (m³/s)",
    "管内径 D (m)": "Inner diameter D (m)",
    "管长 L (m)": "Pipe length L (m)",
    # ================= DISPLAY 数据卡 label =================
    "数值周期": "Numerical period",
    "小角度理论周期": "Small-angle period",
    "周期比 T/T₀": "Period ratio T/T₀",
    "初始能量": "Initial energy",
    "终点能量": "Final energy",
    "已达稳态": "Steady state reached",
    "位置": "Position",
    "最大弯矩": "Max moment",
    "许用挠度 L/360": "Allowable deflection L/360",
    "是否在限内": "Within limit",
    "实际应力": "Actual stress",
    "是否安全": "Safe",
    "时间常数 τ": "Time constant τ",
    "5τ 电压": "5τ voltage",
    "初始充电电流": "Initial charging current",
    "雷诺数": "Reynolds number",
    "摩擦系数": "Friction factor",
    "水柱损失": "Head loss",
    "流态": "Flow regime",
    # ================= 参数溯源表 =================
    "参数": "Parameter",
    "取值": "Value",
    "来源": "Source",
    "你给的": "You provided",
    "已用默认": "Default used",
    # ================= 追问缺失参数 =================
    "#### 🤔 AI 还需要你补充几个参数": "#### 🤔 I need a few more parameters",
    "请把 a 改到 {0:.1f} ~ {1:g} m 之间再算。": "Move a between {0:.1f} ~ {1:g} m and recompute.",
    # ================= 参数对比 / 敏感性 =================
    "📈 参数对比": "📈 Parameter Comparison",
    "对比参数": "Compare parameter",
    "范围下限": "Lower bound",
    "范围上限": "Upper bound",
    "扫描各参数敏感性…": "Scanning parameter sensitivity…",
    "💡 对「{0}」影响最大的是 **{1}**：它 {2} 10%，结果变化约 **{3:.0f}%** —— 想调结果，先动它最有效。":
        "💡 Biggest lever on \"{0}\" is **{1}**: a 10% {2} moves the result by ~**{3:.0f}%** — change it first.",
    "增大": "increase",
    "减小": "decrease",
    "参数值": "Param value",
    # ================= 侧边栏 / API 设置 =================
    "⚙️ API 设置": "⚙️ API Settings",
    "可选（查钢梁参数用）": "Optional (steel-beam lookup)",
    "✅ {0} 已配置": "✅ {0} configured",
    "⚠️ {0} 未配置——AI 解析/解读不可用": "⚠️ {0} not configured — AI parse/interpret unavailable",
    "✅ SerpApi 已配置": "✅ SerpApi configured",
    "SerpApi 未配置（可选）": "SerpApi not configured (optional)",
    "💾 填过的 key 会记住到本机，下次打开自动加载（不随网页关闭丢失）。":
        "💾 Keys you enter are saved locally and auto-loaded next time.",
    "{0}（AI 解析需要）": "{0} (needed for AI parsing)",
    # ================= 自然语言主流程 =================
    "例：一根4米长的简支钢梁，距左端1.5米处承受10kN集中力，最大挠度多少？":
        "e.g. a 4 m simply-supported steel beam, 10 kN point load 1.5 m from the left end — what's the max deflection?",
    "解析工程问题…": "Parsing the engineering problem…",
    "调用 AI 识别场景与参数…": "Calling AI to detect scenario & parameters…",
    "AI 识别到的参数：": "AI extracted parameters:",
    "识别到场景：{0} ✓": "Scenario detected: {0} ✓",
    "解析失败：{0}": "Parse failed: {0}",
    "请改用手动输入。": "please switch to Manual input.",
    "离线解析：内置规则识别（未调用网络）": "Offline parse: recognized with built-in rules (no network)",
    "离线解析模式：无可用 API Key 或网络不可达，已用内置规则识别问题。":
        "Offline mode: no API key or unreachable network — recognized the question with built-in rules.",
    "未能识别场景。": "Couldn't identify the scenario.",
    "未配置 API Key —— 可用「解析并计算」体验内置离线解析（示例问题），或切到「手动输入」直接算。":
        "No API key — tap \"Parse & Compute\" for built-in offline parsing (sample questions), or switch to Manual input.",
    "未配置 {0} API Key —— AI 解析暂不可用。请在左侧「API 设置」填你的 key，或切到「手动输入」直接算。":
        "No {0} API key — AI parsing unavailable. Fill your key in the left \"API Settings\", or switch to Manual input.",
    "生成解读…": "Writing interpretation…",
    "（AI 解读暂不可用，请直接看数据和图）": "(AI interpretation temporarily unavailable — see the data and charts directly)",
    "⚡ 一键应用：{0}": "⚡ Apply: {0}",
    "已应用设计建议：": "Applied design suggestion:",
    "，结果已重算（可在上方输入框继续微调）。": ", result recomputed (fine-tune above).",
    # ================= CSV 导出表头 =================
    "参数·": "param·",
    "结果·": "result·",
    # ================= design.py：SENSITIVITY label / PARAM_LABELS / advice label =================
    "摆动周期 T": "Pendulum period T",
    "冷却到目标温度时间": "Time to reach target temp",
    "最大挠度": "Max deflection",
    "所需壁厚": "Required wall thickness",
    "充到目标时间": "Time to reach target charge",
    "沿程压降": "Pressure drop",
    "质量 m": "Mass m",
    "摆长 l": "Length l",
    "重力加速度 g": "Gravity g",
    "阻尼系数 c": "Damping c",
    "初始角度 θ₀": "Initial angle θ₀",
    "初始角速度 ω₀": "Initial angular velocity ω₀",
    "仿真时长": "Simulation time",
    "钢件半宽 L": "Half-width L",
    "初始温度 T₀": "Initial temp T₀",
    "介质温度 T_wall": "Medium temp T_wall",
    "热扩散系数 α": "Thermal diffusivity α",
    "目标温度 T_target": "Target temp T_target",
    "梁长 L": "Beam length L",
    "集中荷载 P": "Point load P",
    "荷载距左端 a": "Load position a",
    "弹性模量 E": "Modulus E",
    "惯性矩 I": "Inertia I",
    "内压 P": "Pressure P",
    "内径 D": "Diameter D",
    "许用应力 σ": "Allowable stress σ",
    "给定壁厚 t": "Given thickness t",
    "电阻 R": "Resistance R",
    "电容 C": "Capacitance C",
    "源电压 Vs": "Source voltage Vs",
    "充电目标百分比": "Charge target %",
    "流量 Q": "Flow rate Q",
    "管长 L": "Pipe length L",
    "粗糙度 ε": "Roughness ε",
    "密度 ρ": "Density ρ",
    "黏度 μ": "Viscosity μ",
    "I → {0:.3g} m⁴ 并重算": "I → {0:.3g} m⁴ & recompute",
    "L → {0:.3g} m 并重算": "L → {0:.3g} m & recompute",
    "t → {0:.1f} mm 并重算": "t → {0:.1f} mm & recompute",
    "D → {0:.0f} mm 并重算": "D → {0:.0f} mm & recompute",
    # ================= llm.py PROVIDERS label/hint（few-shot prompt 不翻译） =================
    "DeepSeek": "DeepSeek",
    "OpenAI (GPT)": "OpenAI (GPT)",
    "智谱 GLM": "Zhipu GLM",
    "通义千问": "Qwen",
    "Kimi (Moonshot)": "Kimi (Moonshot)",
    "硅基流动": "SiliconFlow",
    "性价比高、中文强，本项目默认": "Cost-effective, strong Chinese — default",
    "需海外网络": "Requires overseas network",
    "glm-4-flash 有免费额度": "glm-4-flash free tier",
    "阿里云百炼": "Alibaba Cloud Bailian",
    "长文本表现好": "Great with long text",
    "聚合多开源模型": "Aggregates open-source models",
    # ================= design.py 图轴 label 模板 =================
    "{0}（{1}）": "{0} ({1})",
}


def set_lang(lang: str) -> None:
    """设置当前语言（模块级，供 engine 图标题/建议文案跟随）。"""
    global LANG
    LANG = lang if lang in ("zh", "en") else "en"


def tr(text: str) -> str:
    """中文原文 → 当前语言文本。zh 返回原文；en 查表，查不到返回原文。"""
    if LANG == "zh":
        return text
    return _EN.get(text, text)


def trf(fmt: str, *args, **kwargs) -> str:
    """模板翻译 + format 填充。fmt 为中文模板（原文映射的 key）。"""
    tpl = fmt if LANG == "zh" else _EN.get(fmt, fmt)
    try:
        return tpl.format(*args, **kwargs)
    except (KeyError, IndexError, ValueError):
        return fmt.format(*args, **kwargs)
