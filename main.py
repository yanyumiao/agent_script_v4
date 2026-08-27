"""漫剧 Agent 入口"""
import argparse
import time
from pathlib import Path

import config
from graph.build import build_graph


def main():
    parser = argparse.ArgumentParser(description="输入小故事，生成带配音的漫剧视频")
    parser.add_argument("--story", default=None, help="输入的小故事")
    parser.add_argument("--run-dir", default=None, help="复用已有 run 目录（跳过已生成产物，用于续跑）")
    parser.add_argument("--fast", action="store_true", help="快速模式：H3 低步数+低分辨率（快速看原型）")
    args = parser.parse_args()

    if not config.DEEPSEEK_API_KEY:
        raise SystemExit("错误：请在 .env 中填入 DEEPSEEK_API_KEY 后重试。")
    if not args.run_dir and not args.story:
        raise SystemExit("错误：请提供 --story，或用 --run-dir 续跑已有目录。")

    if args.run_dir:
        # 把命令行传入的目录参数转成绝对路径
        run_dir = Path(args.run_dir).resolve()
    else:
        run_dir = config.OUTPUTS_DIR / time.strftime("%Y%m%d-%H%M%S")
    for sub in ("images", "shots", "voices"):
        (run_dir / sub).mkdir(parents=True, exist_ok=True)

    if args.fast:
        config.H3_STEPS = config.H3_FAST_STEPS
        config.H3_WIDTH = config.H3_FAST_WIDTH
        config.H3_HEIGHT = config.H3_FAST_HEIGHT
        config.H3_RENDER_WIDTH = config.H3_FAST_RENDER_WIDTH
        config.H3_RENDER_HEIGHT = config.H3_FAST_RENDER_HEIGHT

    graph = build_graph()
    result = graph.invoke({"story": args.story or "", "run_dir": str(run_dir)})
    print(f"\n完成！最终视频：{result.get('final_video')}")


if __name__ == "__main__":
    main()
