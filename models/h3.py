"""H3 视频生成客户端（subprocess 调 h3）"""
import random
import subprocess

import config


def generate_video(prompt, output_path, ref_image=None, frames=None,
                   width=None, height=None, steps=None, seed=None):
    frames = frames if frames is not None else config.H3_FPS * 3
    # 超过 362 帧 H3 直接报错（合法帧数 5+17k，k≤21），钳到上限；
    # 若被钳短导致视频短于配音，compose 会用 tpad=stop_mode=clone 补尾帧
    frames = min(frames, config.H3_MAX_FRAMES)
    width = width or config.H3_WIDTH
    height = height or config.H3_HEIGHT
    steps = steps or config.H3_STEPS
    if seed is None:
        seed = random.randint(0, 2**31 - 1)
    cmd = [
        str(config.H3_BIN),
        "-d", str(config.H3_MODEL_DIR),
        "-p", prompt,
        "-o", str(output_path),
        "--frames", str(frames),
        "--width", str(width),
        "--height", str(height),
        "--steps", str(steps),
        "--seed", str(seed),
    ]
    if config.H3_RENDER_WIDTH:
        cmd += ["--render-width", str(config.H3_RENDER_WIDTH)]
    if config.H3_RENDER_HEIGHT:
        cmd += ["--render-height", str(config.H3_RENDER_HEIGHT)]
    if ref_image:
        cmd += ["--ref-image", str(ref_image)]
    # h3 需要在其安装目录下运行，才能找到 h3_shaders.metal
    subprocess.run(cmd, check=True, cwd=str(config.H3_MODEL_DIR.parent))
    return str(output_path)
