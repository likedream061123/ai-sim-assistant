"""AI 工程仿真助手 —— Streamlit 主入口（编排层）。

架构: 输入 → (可选) LLM 解析 → 引擎计算 → 图+数据+解读+参数溯源。
引擎只管算，本文件只管串。手动表单是解析失败的兜底。

前端设计：
- 背景：ReactBits Aurora 极光（原生 WebGL 移植，蓝色系流动光带）+ 深蓝底
- 内容：白色卡片浮层（对比/层次）+ 大圆角 + 柔和深阴影
- 动效：极光流动（背景）· Count Up 数字滚动（数据时刻）· 页面入场 · 卡片 hover
- 克制：单 accent 亮靛蓝 #3D7BFF，琥珀只做示例点缀；metric 只用真实数据
"""
import io
import json
import math
import os
from pathlib import Path

import matplotlib
# 统一图表主题（所有引擎图共享，白底、统一色板——在深色页里呈"白板"感）
matplotlib.rcParams.update({
    "font.sans-serif": ["Microsoft YaHei", "SimHei", "DejaVu Sans"],  # 雅黑自带中英文字形（3.9 无逐字形回退，放第一最稳）
    "axes.unicode_minus": False,
    "figure.facecolor": "white",
    "axes.facecolor": "white",
    "axes.edgecolor": "#E1E1DB",
    "axes.linewidth": 0.8,
    "axes.grid": True,
    "grid.color": "#F0F0EB",
    "grid.linewidth": 0.6,
    "axes.titlesize": 13,
    "axes.titleweight": 600,
    "axes.labelsize": 11,
    "xtick.labelsize": 10,
    "ytick.labelsize": 10,
    "legend.frameon": False,
    "axes.prop_cycle": matplotlib.cycler(color=["#2F5BFF", "#E07B3A", "#2A9D8F", "#7A6FE0"]),
})
import streamlit as st
# set_page_config 必须是第一个 Streamlit 命令（layout=wide 与 favicon 在此生效）
st.set_page_config(page_title="AI 工程仿真助手", page_icon="assets/favicon.svg", layout="wide")

import engine.pendulum, engine.heat, engine.beam, engine.vessel, engine.design as design
from agent import llm

# ---- 背景极光（ReactBits Aurora · 原生 WebGL 移植，蓝色系）----
AURORA = r"""
<style>
html,body{margin:0;background:transparent;height:100%;overflow:hidden}
/* 流星（参考 aceternity shooting-stars）：掠过即消失，给背景一点生命感 */
.meteor{position:absolute;width:2px;height:2px;border-radius:50%;background:#fff;opacity:0;
  box-shadow:0 0 6px 2px rgba(154,140,255,.75), 0 0 20px 5px rgba(61,123,255,.4);}
.meteor::before{content:"";position:absolute;top:50%;right:0;width:150px;height:1.5px;
  background:linear-gradient(90deg,rgba(255,255,255,.85),transparent);}
@keyframes meteor-fall{0%{transform:rotate(215deg) translateX(0);opacity:0}
  4%{opacity:1} 14%{transform:rotate(215deg) translateX(-70vw);opacity:0}
  100%{transform:rotate(215deg) translateX(-70vw);opacity:0}}
.meteor.m1{top:6%;left:78%;animation:meteor-fall 7s linear infinite}
.meteor.m2{top:16%;left:62%;animation:meteor-fall 10s linear infinite 3.5s}
.meteor.m3{top:4%;left:92%;animation:meteor-fall 13s linear infinite 7s}
.meteor.m4{top:24%;left:55%;animation:meteor-fall 16s linear infinite 10s}
@media (prefers-reduced-motion: reduce) {.meteor{animation:none;opacity:0}}
</style>
<div id="aurora" style="position:fixed;inset:0;z-index:0;pointer-events:none;overflow:hidden">
  <div class="meteor m1"></div><div class="meteor m2"></div>
  <div class="meteor m3"></div><div class="meteor m4"></div>
</div>
<script>
(function(){
if (window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches) { return; }
var VERT = `#version 300 es
in vec2 position;
void main() {
  gl_Position = vec4(position, 0.0, 1.0);
}
`;
var FRAG = `#version 300 es
precision highp float;

uniform float uTime;
uniform float uAmplitude;
uniform vec3 uColorStops[3];
uniform vec2 uResolution;
uniform float uBlend;

out vec4 fragColor;

vec3 permute(vec3 x) {
  return mod(((x * 34.0) + 1.0) * x, 289.0);
}

float snoise(vec2 v){
  const vec4 C = vec4(
      0.211324865405187, 0.366025403784439,
      -0.577350269189626, 0.024390243902439
  );
  vec2 i  = floor(v + dot(v, C.yy));
  vec2 x0 = v - i + dot(i, C.xx);
  vec2 i1 = (x0.x > x0.y) ? vec2(1.0, 0.0) : vec2(0.0, 1.0);
  vec4 x12 = x0.xyxy + C.xxzz;
  x12.xy -= i1;
  i = mod(i, 289.0);

  vec3 p = permute(
      permute(i.y + vec3(0.0, i1.y, 1.0))
    + i.x + vec3(0.0, i1.x, 1.0)
  );

  vec3 m = max(
      0.5 - vec3(
          dot(x0, x0),
          dot(x12.xy, x12.xy),
          dot(x12.zw, x12.zw)
      ),
      0.0
  );
  m = m * m;
  m = m * m;

  vec3 x = 2.0 * fract(p * C.www) - 1.0;
  vec3 h = abs(x) - 0.5;
  vec3 ox = floor(x + 0.5);
  vec3 a0 = x - ox;
  m *= 1.79284291400159 - 0.85373472095314 * (a0*a0 + h*h);

  vec3 g;
  g.x  = a0.x  * x0.x  + h.x  * x0.y;
  g.yz = a0.yz * x12.xz + h.yz * x12.yw;
  return 130.0 * dot(m, g);
}

struct ColorStop {
  vec3 color;
  float position;
};

#define COLOR_RAMP(colors, factor, finalColor) {              \\
  int index = 0;                                            \\
  for (int i = 0; i < 2; i++) {                               \\
     ColorStop currentColor = colors[i];                    \\
     bool isInBetween = currentColor.position <= factor;    \\
     index = int(mix(float(index), float(i), float(isInBetween))); \\
  }                                                         \\
  ColorStop currentColor = colors[index];                   \\
  ColorStop nextColor = colors[index + 1];                  \\
  float range = nextColor.position - currentColor.position; \\
  float lerpFactor = (factor - currentColor.position) / range; \\
  finalColor = mix(currentColor.color, nextColor.color, lerpFactor); \\
}

void main() {
  vec2 uv = gl_FragCoord.xy / uResolution;

  ColorStop colors[3];
  colors[0] = ColorStop(uColorStops[0], 0.0);
  colors[1] = ColorStop(uColorStops[1], 0.5);
  colors[2] = ColorStop(uColorStops[2], 1.0);

  vec3 rampColor;
  COLOR_RAMP(colors, uv.x, rampColor);

  float height = snoise(vec2(uv.x * 2.0 + uTime * 0.1, uTime * 0.25)) * 0.5 * uAmplitude;
  height = exp(height);
  height = (uv.y * 2.0 - height + 0.2);
  float intensity = 0.6 * height;

  float midPoint = 0.32;
  float auroraAlpha = smoothstep(midPoint - uBlend * 0.5, midPoint + uBlend * 0.5, intensity);

  vec3 auroraColor = intensity * rampColor;

  fragColor = vec4(auroraColor * auroraAlpha, auroraAlpha);
}
`;
function hex2rgb(hex){var h=hex.replace('#','');return[parseInt(h.slice(0,2),16)/255,parseInt(h.slice(2,4),16)/255,parseInt(h.slice(4,6),16)/255];}
var colorStops=['#071033','#2F5BFF','#9A8CFF'];
var ctn=document.getElementById('aurora');
var canvas=document.createElement('canvas');
canvas.style.cssText='width:100%;height:100%;display:block;';
ctn.appendChild(canvas);
var gl=canvas.getContext('webgl2',{preserveDrawingBuffer:true});
if(!gl){return;}
gl.clearColor(0,0,0,0);
gl.enable(gl.BLEND);
gl.blendFunc(gl.ONE,gl.ONE_MINUS_SRC_ALPHA);
var buf=gl.createBuffer();
gl.bindBuffer(gl.ARRAY_BUFFER,buf);
gl.bufferData(gl.ARRAY_BUFFER,new Float32Array([-1,-1,3,-1,-1,3]),gl.STATIC_DRAW);
function compile(type,src){var s=gl.createShader(type);gl.shaderSource(s,src);gl.compileShader(s);if(!gl.getShaderParameter(s,gl.COMPILE_STATUS)){throw new Error(gl.getShaderInfoLog(s));}return s;}
var vs=compile(gl.VERTEX_SHADER,VERT);
var fs=compile(gl.FRAGMENT_SHADER,FRAG);
var prog=gl.createProgram();
gl.attachShader(prog,vs);gl.attachShader(prog,fs);gl.linkProgram(prog);
if(!gl.getProgramParameter(prog,gl.LINK_STATUS)){return;}
gl.useProgram(prog);
var posLoc=gl.getAttribLocation(prog,'position');
gl.enableVertexAttribArray(posLoc);
gl.vertexAttribPointer(posLoc,2,gl.FLOAT,false,0,0);
var uTime=gl.getUniformLocation(prog,'uTime');
var uRes=gl.getUniformLocation(prog,'uResolution');
var uAmp=gl.getUniformLocation(prog,'uAmplitude');
var uBlend=gl.getUniformLocation(prog,'uBlend');
var uStops=gl.getUniformLocation(prog,'uColorStops[0]');
function resize(){
  var dpr=Math.min(window.devicePixelRatio||1,2);
  var w=Math.max(1,Math.round(window.innerWidth*dpr));
  var h=Math.max(1,Math.round(window.innerHeight*dpr));
  if(w!==canvas.width||h!==canvas.height){
    canvas.width=w; canvas.height=h;
    gl.viewport(0,0,w,h);
    gl.uniform2f(uRes,w,h);
  }
}
window.addEventListener('resize',resize);
resize();
gl.uniform1f(uAmp,1.0);
gl.uniform1f(uBlend,0.5);
gl.uniform3fv(uStops,colorStops.map(hex2rgb).reduce(function(a,c){return a.concat(c);},[]));
var start=performance.now();
function frame(now){resize();gl.uniform1f(uTime,(now-start)*0.001*0.6);gl.drawArrays(gl.TRIANGLES,0,3);setTimeout(function(){frame(performance.now());},16);}
setTimeout(function(){frame(performance.now());},16);
})();
</script>
"""

# st.iframe 在 iframe 里执行（主文档的 markdown/html 都被剥 <script>，iframe 是唯一能跑 JS 的通道）
# iframe 由 CSS 强制 position:fixed 全屏覆盖视口，作深蓝极光背景层
st.iframe(AURORA, height=2)

# ---- 全站设计语言（CSS · 深蓝极光主题）----
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Sora:wght@400;500;600;700;800&display=swap');

.stApp { background:#05091A; }
.block-container { position:relative; z-index:1; max-width:76rem; padding-top:1.8rem; padding-bottom:4.5rem;
  animation:page-rise .55s cubic-bezier(.16,1,.3,1) backwards;}
@keyframes page-rise { from{opacity:0;transform:translateY(12px)} to{opacity:1;transform:none} }

/* ---- 品牌 header（深色版）---- */
.brand-header {display:flex; align-items:center; gap:.7rem; margin-bottom:.2rem;}
.brand-logo {width:2.7rem; height:2.7rem; border-radius:.85rem; background:linear-gradient(135deg,#3D7BFF,#7A6FE0);
  display:flex; align-items:center; justify-content:center; color:#fff; font-size:1.4rem;
  box-shadow:0 4px 18px rgba(61,123,255,.45);}
.brand-name {font-size:1.6rem; font-weight:800; letter-spacing:-.02em; color:#fff; line-height:1.1;
  font-family:'Sora','Segoe UI','Microsoft YaHei',sans-serif;
  text-shadow:0 2px 24px rgba(61,123,255,.35);}
.brand-sub {font-size:.82rem; color:#9fb4ff; margin-top:.12rem;}
.accent-line {height:3px; width:100%; background:linear-gradient(90deg,#3D7BFF 0%,#3D7BFF 60%,#9A8CFF 100%);
  border-radius:2px; margin:.95rem 0 1.1rem; box-shadow:0 0 18px rgba(61,123,255,.45);}

/* hero 聚焦光斑（aceternity spotlight 手法）：输入区后的一团蓝光，不遮挡内容 */
.hero-glow {position:fixed; top:16%; left:50%; transform:translateX(-50%);
  width:min(880px,94vw); height:460px; z-index:0; pointer-events:none;
  background:radial-gradient(50% 50% at 50% 45%, rgba(61,123,255,.17), rgba(61,123,255,.065) 46%, transparent 72%);}

/* ---- 问题输入 hero：页面的唯一主角，大、淡、无压迫感 ---- */
[data-testid="stTextArea"] {margin-top:1.6rem;}
[data-testid="stTextArea"] textarea {
  background:rgba(255,255,255,.045); color:#F0F4FF; caret-color:#3D7BFF;
  border-radius:18px; border:1px solid rgba(255,255,255,.1);
  font-size:1.02rem; line-height:1.7; padding:1.05rem 1.15rem;
  box-shadow:0 0 0 1px rgba(61,123,255,.10), 0 0 55px rgba(47,91,255,.13), inset 0 1px 0 rgba(255,255,255,.05);
  transition:border-color .15s ease, box-shadow .15s ease;}
[data-testid="stTextArea"] textarea:focus {border-color:#3D7BFF;
  box-shadow:0 0 0 3px rgba(61,123,255,.25), 0 0 80px rgba(47,91,255,.3), inset 0 1px 0 rgba(255,255,255,.06);}
[data-testid="stTextArea"] textarea::placeholder {color:#7A8CB3;}  /* 4.5:1 AA 达标 */

/* ---- 其他原生控件（手动模式参数输入）：浅玻璃小圆角，不抢戏 ---- */
[data-testid="stTextInput"] input,
[data-testid="stNumberInput"] input,
[data-testid="stSelectbox"] > div > div > div {
  background:rgba(255,255,255,.06); color:#F0F4FF; caret-color:#3D7BFF;
  border-radius:10px; border:1px solid rgba(255,255,255,.13);}
[data-testid="stTextInput"] input:focus,
[data-testid="stNumberInput"] input:focus {
  border-color:#3D7BFF; box-shadow:0 0 0 3px rgba(61,123,255,.3);}
[data-testid="stWidgetLabel"] p, [data-testid="stWidgetLabel"] {color:#dbe6ff !important; font-size:.85rem; font-weight:600;}
/* radio：纯文字 tab（无框），选中下划线靛蓝 */
[data-testid="stRadio"] {display:flex; gap:.3rem;}
[data-testid="stRadio"] label {background:transparent !important; border:none !important; border-radius:0;
  padding:.2rem .5rem; color:#7D8DB8; font-size:.9rem; font-weight:600; letter-spacing:.02em;
  border-bottom:2px solid transparent !important; backdrop-filter:none; cursor:pointer; transition:color .15s ease, border-color .15s ease;}
[data-testid="stRadio"] label:hover {color:#C9D6FF;}
[data-testid="stRadio"] label:has(input:checked) {background:transparent !important; color:#fff;
  border-bottom:2px solid #3D7BFF !important; box-shadow:none !important;}
[data-testid="stRadio"] label:has(input:focus-visible) {outline:2px solid #3D7BFF; outline-offset:2px; border-radius:6px;}
[data-testid="stRadio"] label p {margin:0 !important; font-weight:600;}

.stButton > button {border-radius:10px; font-weight:600; font-size:.92rem; transition:transform .12s ease, box-shadow .15s ease;}
/* 主按钮：极光渐变 + shimmer 扫光（aceternity）+ 霓虹辉光（uiverse） */
.stButton > button[kind="primary"] {
  background-image:linear-gradient(135deg,#1D4ED8 0%,#2F5BFF 28%,#9A8CFF 50%,#2F5BFF 72%,#1D4ED8 100%);
  background-size:220% 220%; background-position:0% 50%;
  border:none; border-radius:12px; color:#fff; font-weight:700; letter-spacing:.015em;
  text-shadow:0 1px 8px rgba(10,20,60,.45);
  box-shadow:0 0 14px rgba(47,91,255,.4), 0 0 38px rgba(47,91,255,.2), inset 0 1px 0 rgba(255,255,255,.3);
}
@keyframes btn-shimmer {from{background-position:0% 50%} to{background-position:100% 50%}}
.stButton > button[kind="primary"]:hover {
  transform:translateY(-1px);
  background-position:100% 50%;
  animation:btn-shimmer .9s ease-out 1 forwards;
  box-shadow:0 0 22px rgba(47,91,255,.6), 0 0 62px rgba(47,91,255,.32), inset 0 1px 0 rgba(255,255,255,.4);}
.stButton > button[kind="primary"]:active {transform:translateY(0);
  box-shadow:0 0 12px rgba(47,91,255,.5), inset 0 2px 8px rgba(0,0,0,.3);}
.stButton > button[kind="primary"]:focus {box-shadow:0 0 0 3px rgba(61,123,255,.4), 0 0 24px rgba(47,91,255,.5);}
.stButton > button[kind="secondary"] {background:rgba(255,255,255,.08); border-color:rgba(255,255,255,.18); color:#F0F4FF;
  backdrop-filter:blur(10px); -webkit-backdrop-filter:blur(10px);}
.stButton > button[kind="secondary"]:hover {border-color:#3D7BFF; color:#fff; background:rgba(61,123,255,.2);}

/* ---- 数据卡（深色玻璃）---- */
[data-testid="stMetric"] {background:rgba(255,255,255,.06); border:1px solid rgba(255,255,255,.12); border-radius:14px;
  padding:.8rem .95rem; backdrop-filter:blur(18px) saturate(1.3); -webkit-backdrop-filter:blur(18px) saturate(1.3);
  box-shadow:0 12px 36px rgba(0,5,25,.5);}
[data-testid="stMetricLabel"] {font-size:.76rem; color:#9FB4FF;}
[data-testid="stMetricValue"] {font-size:1.55rem; font-weight:800; letter-spacing:-.01em;
  font-variant-numeric:tabular-nums;
  font-family:'Sora','Segoe UI','Microsoft YaHei',sans-serif; color:#FFFFFF;
  text-shadow:0 2px 18px rgba(61,123,255,.35);}

/* ---- 完成时刻（orchestrated reveal，唯一编排动效）：图表先淡入，数据卡依次浮起 ---- */
@keyframes card-rise { from{opacity:0; transform:translateY(14px)} to{opacity:1; transform:none} }
@keyframes chart-fade { from{opacity:0; transform:scale(.99); filter:blur(5px)} to{opacity:1; transform:none; filter:blur(0)} }
[data-testid="stImage"], .stImage, .element-container:has(img) {animation:chart-fade .6s cubic-bezier(.16,1,.3,1) .05s both;}
[data-testid="stMetric"] {animation:card-rise .5s cubic-bezier(.16,1,.3,1) .2s both;}
[data-testid="stColumn"]:nth-child(2) [data-testid="stMetric"] {animation-delay:.27s;}
[data-testid="stColumn"]:nth-child(3) [data-testid="stMetric"] {animation-delay:.34s;}
[data-testid="stColumn"]:nth-child(4) [data-testid="stMetric"] {animation-delay:.41s;}

/* ---- 标题/层级（深色页）---- */
h1 {color:#fff !important; letter-spacing:-.02em; font-weight:800; text-wrap:balance;}
h2, h3 {color:#fff !important; letter-spacing:-.02em; font-weight:800;}
h2 {font-size:1.15rem; margin-top:1.9rem; font-weight:700;}
.stCaption {color:#9fb4ff;}

/* ---- 结果/提示区 ---- */
[data-testid="stInfo"] {border-radius:12px; background:rgba(61,123,255,.14); border:1px solid rgba(61,123,255,.3);
  border-left:none; color:#dbe6ff;}
[data-testid="stSuccess"] {border-radius:12px; border:none; background:rgba(42,157,143,.16); color:#d8fff9;}
[data-testid="stWarning"] {border-radius:12px; border:none; background:rgba(224,123,58,.14); color:#ffe9d8;}
[data-testid="stError"] {border-radius:12px; border:none; background:rgba(231,76,90,.16); color:#ffdadd;}
[data-testid="stExpander"] {border-radius:12px; border:1px solid rgba(255,255,255,.12); background:rgba(255,255,255,.05);}
[data-testid="stExpander"] summary {color:#dbe6ff;}

/* AI 解析状态条（st.status）：发光玻璃，随阶段 running/complete/error 走系统色 */
[data-testid="stStatusWidget"] {
  border-radius:14px; border:1px solid rgba(61,123,255,.32);
  background:rgba(61,123,255,.10);
  box-shadow:inset 0 0 40px rgba(47,91,255,.12), 0 0 24px rgba(47,91,255,.12);
  backdrop-filter:blur(10px); -webkit-backdrop-filter:blur(10px);}
[data-testid="stStatusWidget"] p {color:#dbe6ff;}
[data-testid="stDataFrame"] {border-radius:12px; overflow:hidden;}

/* 图容器：白底图在深色页里呈"白板" */
[data-testid="stImage"], .stImage, .element-container:has(img) {border-radius:14px; overflow:hidden;
  box-shadow:0 12px 36px rgba(0,10,40,.5);}

/* ---- 极光背景层：st.components.v1.html 的 iframe 强制全屏 fixed，作深蓝背景 ---- */
[data-testid="stIFrame"] {
  position:fixed !important; inset:0 !important;
  width:100vw !important; height:100vh !important;
  z-index:0 !important; pointer-events:none; border:0; background:transparent;
}

/* ---- Streamlit 系统条（顶部 header / 右上工具栏 / 底部 footer）：透明融入极光，去掉平涂黑条 ---- */
[data-testid="stHeader"] {
  background:linear-gradient(180deg, rgba(5,9,26,.9), rgba(5,9,26,.32) 55%, rgba(5,9,26,0)) !important;
  border-bottom:1px solid rgba(255,255,255,.05);}
[data-testid="stToolbar"], [data-testid="stMainMenu"], [data-testid="stDecoration"] { background:transparent !important; }
[data-testid="stFooter"] { background:linear-gradient(0deg, rgba(5,9,26,.9), rgba(5,9,26,0)) !important; }

/* ---- 浏览器表面主题化（craft-floor：页面是搭出来的信号）---- */
::-webkit-scrollbar {width:10px; height:10px;}
::-webkit-scrollbar-track {background:transparent;}
::-webkit-scrollbar-thumb {background:#1C2A4A; border-radius:6px; border:2px solid #05091A;}
::-webkit-scrollbar-thumb:hover {background:#2A3550;}
* {scrollbar-color:#1C2A4A rgba(255,255,255,.04); scrollbar-width:thin;}
::selection {background:rgba(61,123,255,.45); color:#fff;}
:focus-visible {outline:2px solid #3D7BFF; outline-offset:2px; border-radius:4px;}

@media (prefers-reduced-motion: reduce) {
  .block-container, [data-testid="stMetric"], [data-testid="stImage"], .element-container:has(img) {animation:none;}
  .stButton > button[kind="primary"]:hover {animation:none;}
}
</style>
""", unsafe_allow_html=True)

SCENARIOS = {
    "单摆 (动力学)": "pendulum",
    "钢件冷却 (热处理)": "heat",
    "钢梁挠度 (结构校核)": "beam",
    "压力容器壁厚 (设计)": "vessel",
}
SCENARIOS_REV = {v: k for k, v in SCENARIOS.items()}
ENGINES = {
    "pendulum": engine.pendulum,
    "heat": engine.heat,
    "beam": engine.beam,
    "vessel": engine.vessel,
}
ENGINE_DEFAULTS = {
    # pendulum 物理参数 + 控制参数（th0_deg=0 摆不起来 → T_num 为 None，手动模式首开会白屏）
    "pendulum": {**engine.pendulum.DEFAULT_PARAMS, "th0_deg": 120.0, "w0": 0.0, "t_end": 20.0},
    "heat": engine.heat.DEFAULT_PARAMS,
    "beam": engine.beam.DEFAULT_PARAMS,
    "vessel": engine.vessel.DEFAULT_PARAMS,
}
# 缺失参数追问：AI 识别场景后，用户口语没提到的关键参数 → 反问补齐再算。
# 只问「用户语言里会出现的东西」（角度/尺寸/荷载/温度）；工程常数（E/I/alpha/σ/重力）
# 用户口语几乎不说，给默认值即可。也是「AI 理解了多少」的透明展示。
ASKABLE_PARAMS = {
    "pendulum": ["th0_deg", "l"],          # 初始角度 + 摆长
    "heat": ["L", "T0", "T_wall", "T_target"],
    "beam": ["L", "P", "a"],               # 荷载位置也问；E/I 默认工程值
    "vessel": ["P", "D", "sigma_allow", "t_given"],
}
# 追问表单 number_input 的允许范围（与手动模式一致）
PARAM_RANGES = {
    "pendulum": {"th0_deg": (0.0, 180.0), "l": (0.1, 10.0)},
    "heat": {"L": (0.01, 1.0), "T0": (100.0, 1500.0), "T_wall": (0.0, 500.0), "T_target": (0.0, 1500.0)},
    "beam": {"L": (0.1, 20.0), "P": (100.0, 1e6), "a": (0.1, 19.9)},
    "vessel": {"P": (1e4, 1e8), "D": (0.1, 10.0), "sigma_allow": (1e7, 1e9), "t_given": (0.001, 0.5)},
}
# 每场景关键数据卡：(data 键, 中文名, 单位) —— 只展示对用户有意义的键
DISPLAY = {
    "pendulum": [
        ("T_num", "数值周期", "s"),
        ("T0_small", "小角度理论周期", "s"),
        ("T_ratio", "周期比 T/T₀", ""),
        ("E0", "初始能量", "J"),
        ("E_end", "终点能量", "J"),
    ],
    "heat": [
        ("t_center_target", "冷却到目标温度时间", "s"),
        ("steady_reached", "已达稳态", ""),
    ],
    "beam": [
        ("v_max_mm", "最大挠度", "mm"),
        ("x_max", "位置", "m"),
        ("M_max", "最大弯矩", "N·m"),
        ("v_allow", "许用挠度 L/360", "m"),
        ("within_limit", "是否在限内", ""),
    ],
    "vessel": [
        ("t_req_mm", "所需壁厚", "mm"),
        ("sigma_actual", "实际应力", "Pa"),
        ("safe", "是否安全", ""),
    ],
}


def _fmt(v, unit):
    """把标量格式化成人类可读文本。"""
    if isinstance(v, bool):
        return "是" if v else "否"
    if v is None:
        return "—（未计算）"
    if isinstance(v, float):
        if math.isnan(v) or math.isinf(v):
            return "发散"
        if abs(v) < 1e-3 or abs(v) > 1e6:
            return f"{v:.3e} {unit}".strip()
        return f"{v:.4g} {unit}".strip()
    return f"{v} {unit}".strip()


_DEEP = "#0B1229"    # 图表深蓝底（与页面背景一致）
_TEXT = "#DCE6FF"    # 主文字
_SUB = "#9FB4FF"     # 次级文字
_GRID = "#1C2A4A"    # 网格线
_EDGE = "#2A3550"    # 坐标轴边框


def _darkfig(fig):
    """把引擎图统一深色化（不侵入引擎代码）：白底 matplotlib 图在深色玻璃主题里是唯一的白块，
    这里在渲染层把所有轴/文字/网格换成深色主题色，让图和玻璃卡融为一体。"""
    fig.patch.set_facecolor(_DEEP)
    for ax in fig.axes:
        ax.set_facecolor(_DEEP)
        ax.tick_params(colors=_SUB)
        for lab in list(ax.get_xticklabels()) + list(ax.get_yticklabels()):
            lab.set_color(_SUB)
        ax.xaxis.label.set_color(_TEXT)
        ax.yaxis.label.set_color(_TEXT)
        if ax.get_title():
            ax.title.set_color(_TEXT)
        for sp in ax.spines.values():
            sp.set_edgecolor(_EDGE)
        ax.grid(True, color=_GRID, linewidth=0.6)
        leg = ax.get_legend()
        if leg is not None:
            for t in leg.get_texts():
                t.set_color(_TEXT)


@st.fragment
def _plot_section(figs: list) -> None:
    """图表展示 + 大小调节（fragment 隔离）。

    拖动「图表大小」滑块只 rerun 本 fragment —— 主脚本不重跑，图即时缩放，
    而不会触发重新计算 / 重新调用 AI 解读。图以 PNG 缓存后 st.image 等比缩放，
    避免 st.pyplot 固定宽度导致纵横比被拉扁。
    """
    w = st.slider("📐 图表大小", 480, 1280, 960, 20, key="plot_width")
    st.caption("拖动滑块调整图表宽度（像素），比例自动保持；数据不变，只是视图缩放。")
    for fig in figs:
        _darkfig(fig)
        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=110, bbox_inches="tight")
        st.image(buf.getvalue(), width=w)


@st.fragment
def _compare_section(scenario: str, params: dict) -> None:
    """参数对比（fragment 隔离）：改一个参数，看目标输出怎么变。

    扫描复用 design.compare（SENSITIVITY_SPEC 白名单 + 目标键），曲线 + 当前值红点。
    fragment 内换参数/调范围/改采样只 rerun 本区，不重算主流程、不重复调用 AI。
    """
    labels = design.PARAM_LABELS.get(scenario, {})
    opts = [p for p in design.SENSITIVITY_SPEC[scenario]["params"] if p in labels]
    if not opts:
        return
    st.markdown("---")
    st.subheader("📈 参数对比")
    st.caption("改一个参数，看结果怎么变 —— 帮你理解每个参数的『手感』。")
    c1, c2, c3 = st.columns([2, 2, 1])
    pname = c1.selectbox("对比参数", opts, format_func=lambda p: labels[p], key="cmp_param")
    cur = params.get(pname)
    if cur is None:
        cur = ENGINE_DEFAULTS[scenario].get(pname)
    if cur is None:
        st.warning("该参数当前没有值，先在表单里设一个。")
        return
    cur = float(cur)
    lo = c2.number_input("范围下限", value=cur * 0.5 if cur > 0 else cur * 0.1,
                         key=f"cmp_lo_{pname}", format="%.3g")
    hi = c3.number_input("范围上限", value=cur * 1.5,
                         key=f"cmp_hi_{pname}", format="%.3g")
    n = st.slider("采样点数", 5, 60, 25, key="cmp_n")
    if lo >= hi:
        st.warning("范围下限要小于上限。")
        return
    if not st.button("生成对比曲线", key="cmp_go", type="primary", use_container_width=True):
        return
    vals = [lo + (hi - lo) * i / (n - 1) for i in range(n)]
    rows = design.compare(ENGINES[scenario].solve, scenario, params, pname, vals)
    if len(rows) < 2:
        st.warning("采样点太少或求解失败，把范围放宽些再试。")
        return
    fig = design.plot_compare(rows, scenario, pname, cur)
    if fig is not None:
        _darkfig(fig)
        st.pyplot(fig)
    spec = design.SENSITIVITY_SPEC[scenario]
    st.dataframe(
        {"参数值": [f"{v:.3g}" for v, _ in rows],
         f"{spec['label']}（{spec['unit']}）": [f"{y:.4g}" for _, y in rows]},
        use_container_width=True, hide_index=True,
    )


def _ask_missing(scenario: str, given: dict, missing: list,
                 recommended: dict | None = None) -> None:
    """缺失参数追问：AI 已识别部分，把用户没说但需要的关键参数反问出来。

    given: AI 从中文提取到的参数；missing: 用户没提、需要补齐的参数；
    recommended: LLM 对缺失参数的推荐值 {"param": {"value": 数字, "reason": "..."}}，
    预填进输入框（用户可改）——从「让用户填」升级为「AI 替你想好方案」。
    补齐后带着完整参数 render_result —— 「AI 会主动要参数」的透明感卖点。
    """
    labels = design.PARAM_LABELS.get(scenario, {})
    recommended = recommended or {}
    st.markdown("---")
    st.markdown("#### 🤔 AI 还需要你补充几个参数")
    if given:
        shown = "、".join(f"{labels.get(k, k)}={v:g}" for k, v in given.items())
        st.caption(f"已识别：{shown}")
    filled: dict = {}
    cols = st.columns(2)
    for i, p in enumerate(missing):
        lo, hi = PARAM_RANGES[scenario][p]
        rec = recommended.get(p) or {}
        rec_val = rec.get("value")
        dft = _clamp(rec_val if isinstance(rec_val, (int, float)) and not isinstance(rec_val, bool)
                     else ENGINE_DEFAULTS[scenario].get(p) or lo, lo, hi)
        with cols[i % 2]:
            filled[p] = st.number_input(
                labels.get(p, p), lo, hi, dft, format="%.3g",
                key=f"ask_{scenario}_{p}",
            )
            if rec.get("reason"):
                st.caption(f"✨ AI 推荐：{rec['reason']}（可直接用，也可改）")
    st.caption("没提到的参数用工程默认值，结果区会标出哪些是默认（参数溯源）。")
    if st.button("就用这些参数计算", type="primary", key="ask_go", use_container_width=True):
        st.session_state.pop("pending_ask", None)   # 补齐完成，清除追问状态
        params = {**given, **filled}
        st.session_state["last_parse"] = {"scenario": scenario, "params": params}
        # 结果入 session_state 而非直接渲染：后续 rerun（比如再改追问参数）结果卡仍在，
        # 由主流程 ask_result 分支统一渲染（持久化）。
        st.session_state["ask_result"] = {"scenario": scenario, "params": params}


def render_metrics(scenario: str, data: dict):
    """关键数据卡：每行 3 个 st.metric（真实数值 + 溯源支撑，Count Up 数字滚动）。"""
    items = [(k, label, unit) for k, label, unit in DISPLAY[scenario] if k in data]
    for i in range(0, len(items), 3):
        row = items[i:i + 3]
        cols = st.columns(len(row))
        for col, (key, label, unit) in zip(cols, row):
            col.metric(label, _fmt(data[key], unit))


def _show_sources(scenario: str, given: dict):
    """参数溯源：哪些是你/AI 给的、哪些用了默认值（透明性卖点）。"""
    defaults = ENGINE_DEFAULTS[scenario]
    rows = []
    for k, v in {**defaults, **(given or {})}.items():
        val = "—" if v is None else f"{v:g}"
        rows.append({"参数": k, "取值": val, "来源": "你给的" if k in given else "已用默认"})
    with st.expander("参数与来源（溯源）", expanded=False):
        st.dataframe(rows, hide_index=True)


def render_result(scenario: str, params: dict, note: str = "",
                  can_apply: bool = False, manualize: bool = False):
    if note:
        st.info(note)
    # 物理参数合法性前置校验：简支梁荷载位置必须落在梁内（UI 范围静态，a 可超过 L）
    if scenario == "beam":
        _L, _a = params.get("L"), params.get("a")
        if _L and _a and _a > _L:
            st.error(f"荷载位置 a={_a:g} m 超过了梁长 L={_L:g} m —— 集中力落在梁外了，"
                     f"请把 a 改到 {0:.1f} ~ {_L:g} m 之间再算。")
            return
    try:
        res = ENGINES[scenario].solve(params)
    except Exception as e:
        st.error(f"计算失败：{e}")
        return
    # 数值异常兜底（spec §5）：NaN/发散 → 提示参数不合理
    if any(isinstance(v, float) and (math.isnan(v) or math.isinf(v)) for v in res["data"].values()):
        st.error("参数不合理，结果发散（NaN/Inf）——请调整参数后重算。")
        return
    _plot_section(res["figures"])
    st.subheader("关键数据")
    render_metrics(scenario, res["data"])

    # ---- 设计辅助 · 参数敏感性（改变谁对结果影响最大）----
    with st.expander("设计辅助 · 参数敏感性", expanded=True):
        full = {**ENGINE_DEFAULTS[scenario], **params}
        with st.spinner("扫描各参数敏感性…"):
            rows = design.sensitivity(ENGINES[scenario].solve, scenario, full)
        if rows:
            fig = design.plot_sensitivity(rows, scenario)
            _darkfig(fig)
            st.pyplot(fig)
            top = rows[0]
            verb = "增大" if top[1] > 0 else "减小"
            label = design.SENSITIVITY_SPEC[scenario]["label"]
            st.caption(
                f"💡 对「{label}」影响最大的是 **{top[0]}**：它 {verb} 10%，结果变化约 "
                f"**{abs(top[1]):.0f}%** —— 想调结果，先动它最有效。")
        else:
            st.caption("（当前参数下无法完成敏感性扫描）")

    # ---- 设计辅助 · 超限自动建议（一键应用）----
    adv = design.advice(scenario, res["data"])
    if adv:
        st.warning(adv["message"])
        # 按钮回调走 on_click：点按钮重跑脚本时，render_result 不在执行路径上（「计算」
        # 按钮未被点击，主流程不会再次进入本函数），返回值分支的 advice_apply 永远写
        # 不进 session_state；on_click 在点击当下就写入，重跑由主流程 applied 分支消费。
        if can_apply and adv.get("adjust"):
            st.button(f"⚡ 一键应用：{adv['label']}",
                      key=f"apply_{scenario}", type="primary", use_container_width=True,
                      on_click=_apply_advice, args=(adv["adjust"],))

    _show_sources(scenario, params)
    try:
        simple = {k: v for k, v in res["data"].items()
                  if isinstance(v, (int, float, str, bool)) or v is None}
        with st.spinner("生成解读…"):
            text = llm.explain(scenario, simple, api_key=_ds_key() or None)
        st.subheader("AI 解读")
        st.info(text)
    except Exception:
        pass
    # AI 解析模式专属：一键把参数带到手动表单微调（完整工作流闭环）。
    # 状态切换走 on_click 回调：render_result 在 radio/selectbox 实例化之后才执行，
    # 直接写 input_mode/scenario_select 会被 Streamlit 判为「widget 已实例化后修改」报错。
    if manualize:
        st.button("✏️ 切到手动模式微调参数", key="manualize_btn", use_container_width=True,
                  on_click=_manualize, args=(scenario, params))


def _apply_advice(adjust: dict):
    """「一键应用」on_click 回调：点击当下把调整参数写入 session_state。

    用 on_click 而非按钮返回值分支，是因为 render_result 只在「计算」按钮被点时
    才会被调用；点「一键应用」重跑脚本时 render_result 不在执行路径上，返回值
    分支永远拿不到点击。on_click 在点击瞬间写入，主流程的 applied 分支消费。
    """
    st.session_state["advice_apply"] = adjust


def _set_steel_defaults():
    """SerpApi 按钮 on_click：点击当下写入典型钢梁参数，rerun 后输入框真实生效。"""
    st.session_state["beam_E"] = 200e9
    st.session_state["beam_I"] = 5e-4


def _manualize(scenario: str, params: dict):
    """「切到手动模式」on_click 回调：点击当下把 AI 参数带入手动表单并清残留。

    用 on_click 而非按钮返回值分支：render_result 在 input_mode/scenario_select
    widget 实例化之后才被调用，返回值分支在脚本执行路径里写这两个 key 会报
    「widget 已实例化后不可修改」；on_click 在点击瞬间写入，rerun 时从新状态开始。
    """
    st.session_state.pop("ask_result", None)
    st.session_state.pop("pending_ask", None)
    # 手动化会带入 AI 新解析的参数；清掉本场景输入框 key，让表单以新值重新初始化
    for _k in _MANUAL_WIDGET_KEYS.get(scenario, []):
        st.session_state.pop(_k, None)
    st.session_state["last_parse"] = {
        "scenario": scenario,
        "params": {**ENGINE_DEFAULTS[scenario], **params},
    }
    st.session_state["input_mode"] = "手动输入"
    st.session_state["scenario_select"] = SCENARIOS_REV.get(scenario, list(SCENARIOS)[0])


# 手动模式输入框的 widget key（有 key 后值由 session_state 主导：advice 一键应用要同步
# 写这些 key，manualize 带入 AI 新解析值要清掉这些 key，否则输入框不跟随更新）。
_MANUAL_WIDGET_KEYS = {
    "pendulum": ["pend_th0", "pend_w0", "pend_t_end"],
    "heat": ["heat_L", "heat_T0", "heat_T_wall", "heat_T_target"],
    "beam": ["beam_L", "beam_P", "beam_a", "beam_E", "beam_I"],
    "vessel": ["ves_P", "ves_D", "ves_sigma", "ves_t_given"],
}
# 参数名 → widget key（advice 返回 adjust 用参数名，需要映射到带 key 的输入框）
_ADVICE_KEY_MAP = {
    "heat": {"L": "heat_L"},
    "beam": {"E": "beam_E", "I": "beam_I"},
    "vessel": {"t_given": "ves_t_given"},
}


# ---- API key 本机持久化：填过一次就记住，下次打开免重填 ----
_LOCAL_KEYS_FILE = Path(__file__).resolve().parent / ".streamlit" / "local_keys.json"


def _load_local_keys() -> None:
    """启动时把本机保存的 key 注入环境变量（secrets.toml 已有则不覆盖）。

    只影响 env fallback：用户会话里填的 key 优先级最高（_ds_key 先读 session_state）。
    """
    try:
        if _LOCAL_KEYS_FILE.exists():
            data = json.loads(_LOCAL_KEYS_FILE.read_text(encoding="utf-8"))
            if data.get("deepseek") and not os.environ.get("DEEPSEEK_API_KEY"):
                os.environ["DEEPSEEK_API_KEY"] = data["deepseek"]
            if data.get("serpapi") and not os.environ.get("SERPAPI_KEY"):
                os.environ["SERPAPI_KEY"] = data["serpapi"]
    except Exception:
        pass


def _save_local_keys() -> None:
    """侧边栏 key 输入框 on_change：把当前填的值存到本机文件（gitignore，不进仓库）。

    清空输入框再改别处 = 不保存该 key；文件仍保留旧的，可后续覆盖或手动删除。
    """
    try:
        data = {}
        if st.session_state.get("api_key_ds"):
            data["deepseek"] = st.session_state["api_key_ds"]
        if st.session_state.get("api_key_serp"):
            data["serpapi"] = st.session_state["api_key_serp"]
        _LOCAL_KEYS_FILE.parent.mkdir(parents=True, exist_ok=True)
        _LOCAL_KEYS_FILE.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass


_load_local_keys()


def _ds_key() -> str:
    """DeepSeek API Key：应用内设置优先，回落环境变量（secrets.toml 或本机记忆）。

    评委/用户没有项目 secrets 时，可在左侧「API 设置」填自己的 key（填过会自动记住，
    下次打开免重填）；本地开发留空自动用 secrets.toml 的。无 key 时 AI 解析/解读降级。
    """
    return st.session_state.get("api_key_ds") or os.environ.get("DEEPSEEK_API_KEY", "")


def _serp_key() -> str:
    """SerpApi Key：同上（仅「查钢梁典型参数」按钮需要，可选）。"""
    return st.session_state.get("api_key_serp") or os.environ.get("SERPAPI_KEY", "")


def _clamp(v, lo, hi):
    """把 AI 解析的参数 clamp 进 number_input 允许范围，越界不炸。"""
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        return min(hi, max(lo, float(v)))
    return lo


def _fill_example(text: str):
    """示例卡按钮回调：在 widget 实例化前（脚本重跑前）把示例填入问题输入框。"""
    st.session_state["q_text"] = text


# ---- 品牌 header ----
st.markdown("""
<div class="brand-header">
  <div class="brand-logo"><svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="12" r="3.2"/><path d="M19.4 15a1.7 1.7 0 0 0 .34 1.87l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.7 1.7 0 0 0-1.87-.34 1.7 1.7 0 0 0-1.03 1.56V21a2 2 0 1 1-4 0v-.09a1.7 1.7 0 0 0-1.11-1.56 1.7 1.7 0 0 0-1.87.34l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.7 1.7 0 0 0 .34-1.87 1.7 1.7 0 0 0-1.56-1.03H3a2 2 0 1 1 0-4h.09a1.7 1.7 0 0 0 1.56-1.11 1.7 1.7 0 0 0-.34-1.87l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.7 1.7 0 0 0 1.87.34h.01a1.7 1.7 0 0 0 1.03-1.56V3a2 2 0 1 1 4 0v.09a1.7 1.7 0 0 0 1.03 1.56h.01a1.7 1.7 0 0 0 1.87-.34l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.7 1.7 0 0 0-.34 1.87v.01a1.7 1.7 0 0 0 1.56 1.03H21a2 2 0 1 1 0 4h-.09a1.7 1.7 0 0 0-1.51 1.03Z"/></svg></div>
  <div>
    <div class="brand-name">AI 工程仿真助手</div>
    <div class="brand-sub">一句话描述工程问题，AI 解析参数，数值真算，大白话解读。</div>
  </div>
</div>
<div class="accent-line"></div>
<div class="hero-glow"></div>
""", unsafe_allow_html=True)

# ---- 侧边栏：API 设置（评委/用户自带 key 的入口）----
# 本地开发 secrets.toml 注入环境变量，留空即用；线上评审填自己的 key。
# password 输入只读不回显，状态 caption 随 rerun 实时刷新。
with st.sidebar:
    st.markdown("##### ⚙️ API 设置")
    st.text_input(
        "DeepSeek API Key", type="password", key="api_key_ds",
        placeholder="sk-...（AI 解析需要）",
        on_change=_save_local_keys,
        help="自然语言解析 + AI 解读需要。本地留空自动用内置 secrets；线上演示请填自己的 key，否则只能用「手动输入」。",
    )
    st.text_input(
        "SerpApi Key", type="password", key="api_key_serp",
        placeholder="可选（查钢梁参数用）",
        on_change=_save_local_keys,
        help="仅「查钢梁典型参数」按钮需要，可不填。",
    )
    st.caption(
        ("✅ DeepSeek 已配置" if _ds_key() else "⚠️ DeepSeek 未配置——AI 解析/解读不可用")
        + " · "
        + ("✅ SerpApi 已配置" if _serp_key() else "SerpApi 未配置（可选）")
    )
    st.caption("💾 填过的 key 会记住到本机，下次打开自动加载（不随网页关闭丢失）。")

mode = st.radio("输入方式", ["自然语言", "手动输入"], horizontal=True,
                label_visibility="collapsed", key="input_mode")

if mode == "自然语言":
    st.text_area(
        "描述你的工程问题", key="q_text", height=110,
        placeholder="例：一根4米长的简支钢梁，距左端1.5米处承受10kN集中力，最大挠度多少？",
    )
    _btn = st.columns([5, 1, 2])
    _ds_ready = bool(_ds_key())
    if _btn[2].button("解析并计算", type="primary", use_container_width=True,
                      disabled=not _ds_ready, key="parse_go"):
        st.session_state.pop("pending_ask", None)   # 重新解析，作废旧的追问
        st.session_state.pop("ask_result", None)    # 旧的结果卡也让位给新解析
        parsed, err = None, None
        with st.status("解析工程问题…", expanded=True) as s:
            try:
                s.update(label="调用 AI 识别场景与参数…", state="running")
                parsed = llm.parse_query(st.session_state.get("q_text", ""),
                                         api_key=_ds_key() or None)
                name = SCENARIOS_REV.get(parsed["scenario"], parsed["scenario"])
                if parsed.get("params"):
                    st.write("AI 识别到的参数：", {k: v for k, v in parsed["params"].items()})
                s.update(label=f"识别到场景：{name} ✓", state="complete")
            except ValueError as e:
                err = str(e)
                s.update(label=f"解析失败：{err}", state="error", expanded=False)
        if parsed:
            scenario = parsed["scenario"]
            given = parsed.get("params", {})
            missing = [p for p in ASKABLE_PARAMS.get(scenario, []) if p not in given]
            if missing:
                # 有用户没说但需要的关键参数 → 追问补齐，不让默认值悄悄替用户做决定。
                # 状态入 session_state：用户填参数触发 rerun 时解析不在路径上，靠它恢复表单。
                # recommended：LLM 给的推荐值（预填进输入框，可改）。
                st.session_state["pending_ask"] = {
                    "scenario": scenario, "given": given, "missing": missing,
                    "recommended": parsed.get("recommended", {}) or {}}
            else:
                # 参数齐全 → 直接算；结果同样入 ask_result 持久渲染（自然语言模式结果卡
                # 不因后续 rerun 丢失，直到下一次解析或切到手动模式）。
                st.session_state["last_parse"] = {
                    "scenario": scenario,
                    "params": {**ENGINE_DEFAULTS.get(scenario, {}), **given},
                }
                st.session_state["ask_result"] = {"scenario": scenario, "params": given}
        else:
            st.warning(f"{err} —— 请改用手动输入。")
    elif not _ds_ready:
        st.warning("未配置 DeepSeek API Key —— AI 解析暂不可用。请在左侧「API 设置」填你的 key，或切到「手动输入」直接算。")

    # rerun 恢复追问表单（用户填值触发 rerun 时解析不在路径上，靠 session_state 恢复）
    _pending = st.session_state.get("pending_ask")
    if _pending:
        _ask_missing(_pending["scenario"], _pending["given"], _pending["missing"],
                     _pending.get("recommended"))
    # 持久结果卡：补齐/直接算的结果在后续 rerun 中持续显示（渲染本身是幂等的）
    _ask_res = st.session_state.get("ask_result")
    if _ask_res:
        render_result(_ask_res["scenario"], _ask_res["params"], manualize=True)

    st.markdown('<div style="height:.5rem"></div>', unsafe_allow_html=True)
    st.caption("想快速试？点一个直接填入：")
    EXAMPLES = [
        ("结构 · 钢梁", "一根4米简支钢梁，距左端1.5米处受10kN集中力，最大挠度多少？"),
        ("设计 · 容器", "内压1MPa、内径1米的压力容器，许用应力100MPa，需要多厚壁？"),
        ("传热 · 冷却", "半宽0.1米的钢件初始800度，放到20度空气中，中心要多久降到100度？"),
    ]
    for col, (sc, q) in zip(st.columns(3), EXAMPLES):
        with col:
            st.button(sc, key=f"ex_{sc}", on_click=_fill_example, args=(q,), use_container_width=True)

else:
    scenario_label = st.selectbox("场景", list(SCENARIOS), key="scenario_select")
    scenario = SCENARIOS[scenario_label]
    # 上次 AI 解析/计算过的参数（跨模式记忆，表单用它做默认值；缺省回落到引擎默认值，
    # 避免首次打开手动模式时所有输入框都落在下限，得到一个离谱的边界工况）
    _last = {**ENGINE_DEFAULTS[scenario],
             **((st.session_state.get("last_parse") or {}).get("params") or {})}
    params = {}
    if scenario == "pendulum":
        c1, c2, c3 = st.columns(3)
        params["th0_deg"] = c1.number_input("初始角度 θ₀ (°)", 0.0, 180.0, _clamp(_last.get("th0_deg"), 0.0, 180.0), key="pend_th0")
        params["w0"] = c2.number_input("初始角速度 ω₀ (rad/s)", 0.0, 20.0, _clamp(_last.get("w0"), 0.0, 20.0), key="pend_w0")
        params["t_end"] = c3.number_input("时长 (s)", 1.0, 60.0, _clamp(_last.get("t_end"), 1.0, 60.0), key="pend_t_end")
    elif scenario == "heat":
        c1, c2, c3 = st.columns(3)
        params["L"] = c1.number_input("钢件半宽 (m)", 0.01, 1.0, _clamp(_last.get("L"), 0.01, 1.0), format="%.3f", key="heat_L")
        params["T0"] = c2.number_input("初始温度 (°C)", 100.0, 1500.0, _clamp(_last.get("T0"), 100.0, 1500.0), key="heat_T0")
        params["T_wall"] = c3.number_input("介质温度 (°C)", 0.0, 500.0, _clamp(_last.get("T_wall"), 0.0, 500.0), key="heat_T_wall")
        params["T_target"] = st.number_input("目标温度 (°C)", 0.0, 1500.0, _clamp(_last.get("T_target"), 0.0, 1500.0), key="heat_T_target")
    elif scenario == "beam":
        c1, c2, c3 = st.columns(3)
        params["L"] = c1.number_input("梁长 (m)", 0.1, 20.0, _clamp(_last.get("L"), 0.1, 20.0), key="beam_L")
        params["P"] = c2.number_input("集中荷载 (N)", 100.0, 1e6, _clamp(_last.get("P"), 100.0, 1e6), format="%.0f", key="beam_P")
        params["a"] = c3.number_input("荷载距左端 (m)", 0.1, 19.9, _clamp(_last.get("a"), 0.1, 19.9), key="beam_a")
        c4, c5 = st.columns(2)
        params["E"] = c4.number_input("弹性模量 E (Pa)", 1e9, 1e12, _clamp(_last.get("E"), 1e9, 1e12),
                                      format="%.3g", key="beam_E")
        params["I"] = c5.number_input("惯性矩 I (m4)", 1e-8, 1.0, _clamp(_last.get("I"), 1e-8, 1.0),
                                      format="%.3g", key="beam_I")
        # 填典型参数走 on_click（点击当下写 session_state，rerun 后 number_input 真读新值）；
        # 在线搜索仅作参考，不依赖它生效。
        if st.button("SerpApi 查钢梁典型参数", key="serp_btn", on_click=_set_steel_defaults):
            if _serp_key():
                try:
                    from agent import serpapi
                    info = serpapi.search("standard steel I-beam elastic modulus moment of inertia",
                                          api_key=_serp_key())
                    st.write("搜索结果参考：", info[:2])
                except Exception as e:
                    st.error(f"SerpApi 查询失败：{e}")
            else:
                st.info("未配置 SerpApi Key，已直接填入典型钢梁参数（E=200 GPa、I=5e-4 m⁴），点「计算」生效。")
            st.success("已填入典型钢梁参数 E=200 GPa、I=5e-4 m⁴（可在上方输入框修改）。")
    elif scenario == "vessel":
        c1, c2, c3 = st.columns(3)
        params["P"] = c1.number_input("内压 (Pa)", 1e4, 1e8, _clamp(_last.get("P"), 1e4, 1e8), format="%.3g", key="ves_P")
        params["D"] = c2.number_input("内径 (m)", 0.1, 10.0, _clamp(_last.get("D"), 0.1, 10.0), key="ves_D")
        params["sigma_allow"] = c3.number_input("许用应力 (Pa)", 1e7, 1e9, _clamp(_last.get("sigma_allow"), 1e7, 1e9), format="%.3g", key="ves_sigma")
        # 校核模式：给「给定壁厚」→ 算实际应力是否超许用（补全 safe/advice 链路）
        adv_t = st.session_state.get("advice_apply", {}).get("t_given")
        do_check = st.checkbox("校核给定壁厚", value=bool(adv_t or _last.get("t_given")))
        if do_check:
            params["t_given"] = st.number_input(
                "给定壁厚 t (m)", 0.001, 0.5, _clamp(adv_t or _last.get("t_given") or 0.006, 0.001, 0.5),
                format="%.4f", key="ves_t_given")
    _calc = st.columns([5, 1, 2])
    # 「一键应用建议」：advice 按钮把调整参数存入 session_state 并 rerun，这里消费后
    # 更新 last_parse（输入框同步显示新值）+ auto_run 触发自动重算。
    applied = st.session_state.pop("advice_apply", None)
    if applied:
        params.update(applied)
        # 带 key 的输入框值由 session_state 主导：同步写入，否则 input 框仍显示旧值
        for _pname, _wkey in _ADVICE_KEY_MAP.get(scenario, {}).items():
            if _pname in applied:
                st.session_state[_wkey] = applied[_pname]
        st.session_state["last_parse"] = {"scenario": scenario, "params": {**params}}
        st.session_state["last_applied"] = applied
        st.session_state["auto_run"] = True
        st.rerun()
    if st.session_state.pop("auto_run", False):
        la = st.session_state.pop("last_applied", {}) or {}
        st.success("已应用设计建议：" + "，".join(f"{k} = {v:.3g}" for k, v in la.items())
                   + "，结果已重算（可在上方输入框继续微调）。")
        render_result(scenario, params, can_apply=True)
    elif _calc[2].button("计算", type="primary", use_container_width=True, key="calc_go"):
        render_result(scenario, params, can_apply=True)
    _compare_section(scenario, params)
