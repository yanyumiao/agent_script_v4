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
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-v4-flash")

# ---- FLUX 文生图（绝对路径，不依赖 PATH）----
FLUX_BIN = HOME / "flux-klein/.venv/bin/mflux-generate-flux2"
FLUX_MODEL = "mlx-community/flux2-klein-4b-8bit"
FLUX_WIDTH = 512
FLUX_HEIGHT = 512
FLUX_STEPS = 4
FLUX_SHEET_WIDTH = 1344   # 三视图拼图宽度（三栏）
FLUX_SHEET_HEIGHT = 768

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

# ---- TTS 音色池（按出场角色顺序分配）----
TTS_DEFAULT_VOICE = "zh-CN-XiaoxiaoNeural"
TTS_VOICES = [
    "zh-CN-XiaoxiaoNeural",  # 女 晓晓
    "zh-CN-YunxiNeural",     # 男 云希
    "zh-CN-XiaoyiNeural",    # 女 晓伊
    "zh-CN-YunjianNeural",   # 男 云健
    "zh-CN-YunyangNeural",   # 男 云扬（旁白）
]
