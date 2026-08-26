"""LangGraph 节点实现"""
import json
from pathlib import Path

import config
import prompts
from models.deepseek import Script, Storyboard, structured_llm
from models.flux import generate_image
from models.h3 import generate_video
from models.tts import generate_voice
from utils.compose import compose_shots


def _save_json(run_dir, filename, data) -> Path:
    path = Path(run_dir) / filename
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def _load_json(run_dir, filename):
    return json.loads((Path(run_dir) / filename).read_text(encoding="utf-8"))


def expand_script(state: dict) -> dict:
    run_dir = state["run_dir"]
    if (Path(run_dir) / "script.json").exists():
        return {"script": _load_json(run_dir, "script.json")}
    script = structured_llm(Script).invoke(prompts.expand_script(state["story"]))
    script_dict = script.model_dump()
    _save_json(run_dir, "script.json", script_dict)
    return {"script": script_dict}


def write_storyboard(state: dict) -> dict:
    run_dir = state["run_dir"]
    if (Path(run_dir) / "storyboard.json").exists():
        return {"storyboard": _load_json(run_dir, "storyboard.json")}
    script_json = json.dumps(state["script"], ensure_ascii=False, indent=2)
    storyboard = structured_llm(Storyboard).invoke(prompts.write_storyboard(script_json))
    storyboard_dict = storyboard.model_dump()
    _save_json(run_dir, "storyboard.json", storyboard_dict)
    return {"storyboard": storyboard_dict}


def generate_character_sheets(state: dict) -> dict:
    characters = state["script"]["characters"]
    out_dir = Path(state["run_dir"]) / "images"
    out_dir.mkdir(parents=True, exist_ok=True)
    result = []
    for i, ch in enumerate(characters):
        if ch.get("role") == "旁白":
            result.append({**ch, "sheet_path": None})
            continue
        path = out_dir / f"character_{i:02d}.png"
        if path.exists():
            result.append({**ch, "sheet_path": str(path)})
            continue
        generate_image(
            prompts.character_sheet(ch),
            path,
            width=config.FLUX_SHEET_WIDTH,
            height=config.FLUX_SHEET_HEIGHT,
            seed=config.FLUX_SEED,
        )
        result.append({**ch, "sheet_path": str(path)})
    _save_json(state["run_dir"], "characters.json", result)
    return {"characters": result}


def generate_scene_images(state: dict) -> dict:
    shots = state["storyboard"]["shots"]
    scenes = state["script"]["scenes"]
    appearance_map = {c["name"]: c["appearance"] for c in state["characters"]
                      if c.get("role") != "旁白"}
    out_dir = Path(state["run_dir"]) / "images"

    # 1) 每个场景先生成一张「场景母图」（空镜），后续镜头用 img2img 锚定场景元素
    scene_refs = {}
    for i, scene in enumerate(scenes):
        path = out_dir / f"scene_setting_{i:02d}.png"
        if not path.exists():
            generate_image(
                prompts.scene_setting(scene),
                path,
                width=config.FLUX_WIDTH,
                height=config.FLUX_HEIGHT,
                seed=config.FLUX_SEED,
            )
        scene_refs[scene["name"]] = str(path)

    # 2) 逐镜头生成场景图：以对应场景母图为参考做 img2img
    result = []
    for shot in shots:
        idx = shot["shot_id"]
        path = out_dir / f"scene_{idx:02d}.png"
        if path.exists():
            result.append({**shot, "scene_image": str(path)})
            continue
        char_descs = [appearance_map[n] for n in shot["characters"] if n in appearance_map]
        ref = scene_refs.get(shot["scene_name"])
        generate_image(
            prompts.scene_image(shot, char_descs),
            path,
            width=config.FLUX_WIDTH,
            height=config.FLUX_HEIGHT,
            seed=config.FLUX_SEED,
            image=ref,
            image_strength=config.FLUX_IMG2IMG_STRENGTH,
        )
        result.append({**shot, "scene_image": str(path)})
    return {"shots": result}


def generate_shots(state: dict) -> dict:
    shots = state["shots"]
    out_dir = Path(state["run_dir"]) / "shots"
    out_dir.mkdir(parents=True, exist_ok=True)
    result = []
    for shot in shots:
        idx = shot["shot_id"]
        path = out_dir / f"shot_{idx:02d}.mp4"
        if path.exists():
            result.append({**shot, "video": str(path)})
            continue
        generate_video(
            prompts.shot_motion(shot),
            path,
            ref_image=shot["scene_image"],
            frames=int(round(shot["duration"] * config.H3_FPS)),
        )
        result.append({**shot, "video": str(path)})
    return {"shots": result}


def generate_voices(state: dict) -> dict:
    shots = state["shots"]
    characters = state["script"]["characters"]
    voice_map = {c["name"]: config.TTS_VOICES[i % len(config.TTS_VOICES)]
                 for i, c in enumerate(characters)}
    voice_map["旁白"] = config.TTS_VOICES[-1]
    out_dir = Path(state["run_dir"]) / "voices"
    out_dir.mkdir(parents=True, exist_ok=True)
    result = []
    for shot in shots:
        dialogue = shot.get("dialogue")
        if not dialogue:
            result.append(shot)
            continue
        idx = shot["shot_id"]
        path = out_dir / f"voice_{idx:02d}.mp3"
        if path.exists() and path.stat().st_size > 0:
            result.append({**shot, "voice": str(path)})
            continue
        voice = voice_map.get(dialogue["speaker"], config.TTS_DEFAULT_VOICE)
        generate_voice(dialogue["text"], voice, path)
        result.append({**shot, "voice": str(path)})
    return {"shots": result}


def compose(state: dict) -> dict:
    out_path = Path(state["run_dir"]) / "final.mp4"
    compose_shots(state["shots"], out_path)
    return {"final_video": str(out_path)}
