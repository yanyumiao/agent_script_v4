"""漫剧 agent 全局配置"""
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

ROOT = Path(__file__).resolve().parent
OUTPUTS_DIR = ROOT / "outputs"
HOME = Path.home()

# ---- DeepSeek（LLM）----
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-v4-pro")

# ---- FLUX 文生图（绝对路径，不依赖 PATH）----
FLUX_BIN = HOME / "flux-klein/.venv/bin/mflux-generate-flux2"
FLUX_MODEL = "mlx-community/flux2-klein-4b-8bit"
FLUX_WIDTH = 512
FLUX_HEIGHT = 512
FLUX_STEPS = 4
FLUX_SHEET_WIDTH = 1344   # 三视图拼图宽度（三栏）
FLUX_SHEET_HEIGHT = 768
FLUX_STYLE_1 = "动漫插画风格"
FLUX_STYLE_2 = "写实电影风格，cinematic"
FLUX_STYLE_3 = "写实摄影，photorealistic"
FLUX_STYLE_4 = "3D 渲染，皮克斯动画风格"
FLUX_STYLE = FLUX_STYLE_1   # 切换风格：改成 FLUX_STYLE_2 / _3 / _4

# ---- FLUX 一致性 / 质量控制 ----
FLUX_SEED = None                # 随机种子（一致性靠母图 img2img + 文字外貌描述，不靠 seed）
FLUX_IMG2IMG_STRENGTH = 0.5     # 场景母图 img2img 参考强度
# 注：FLUX.2 Klein 不支持 --negative-prompt（mflux 直接报错），负向提示在此模型不可用

# ---- H3 视频生成（绝对路径）----
H3_BIN = HOME / "h3-metal/h3"
H3_MODEL_DIR = HOME / "h3-metal/MiniMax-H3"

# ---- H3 默认参数（参考 antirez 的 MiniMax-H3 引擎调用方式）----
H3_WIDTH = 512
H3_HEIGHT = 512
H3_STEPS = 20
H3_FPS = 24
# released 模型帧数上限：合法帧数 = 5 + 17k（k=0..21），超过 362 直接报错
H3_MAX_FRAMES = 362
H3_RENDER_WIDTH = None    # 内部渲染分辨率，None=模型原生；--fast 时降为 256
H3_RENDER_HEIGHT = None

# ---- H3 快速模式（--fast 快速看原型）----
H3_FAST_STEPS = 8
H3_FAST_WIDTH = 256
H3_FAST_HEIGHT = 256
H3_FAST_RENDER_WIDTH = 256
H3_FAST_RENDER_HEIGHT = 256

# ---- 分镜台词时长预算（配音时长由字数决定，H3 单镜头视频上限 ~15s）----
STORYBOARD_MAX_LINE_CHARS = 18       # 单句台词字数上限（约 4s @5字/s）
STORYBOARD_MAX_NARRATION_CHARS = 40  # 旁白单镜字数上限（约 13s @3字/s）
STORYBOARD_MAX_SHOT_DIALOGUE_CHARS = 50  # 每镜头台词总字数上限，超限必须拆镜

# ---- TTS 音色池（本地 Qwen3-TTS CustomVoice，MLX）----
TTS_MODEL = str(HOME / "qwen3-tts")   # 预下载到 ~/qwen3-tts 的本地路径
TTS_LANGUAGE = "chinese"
TTS_DEFAULT_VOICE = "vivian"
TTS_VOICES = [
    "vivian",     # 女 标准普通话 明亮
    "serena",     # 女 标准普通话 温柔
    "dylan",      # 男 京腔（方言）
    "eric",       # 男 川腔（方言）
    "uncle_fu",   # 男 标准普通话 权威（旁白，靠 TTS_VOICES[-1] 取到）
]
