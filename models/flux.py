"""FLUX 文生图客户端（subprocess 调 mflux-generate-flux2）"""
import subprocess

import config


def generate_image(prompt, output_path, width=None, height=None, steps=None, seed=None):
    width = width or config.FLUX_WIDTH
    height = height or config.FLUX_HEIGHT
    steps = steps or config.FLUX_STEPS
    cmd = [
        str(config.FLUX_BIN),
        "-m", config.FLUX_MODEL,
        "--prompt", prompt,
        "--width", str(width),
        "--height", str(height),
        "--steps", str(steps),
        "--output", str(output_path),
    ]
    if seed is not None:
        cmd += ["--seed", str(seed)]
    subprocess.run(cmd, check=True)
    return str(output_path)
