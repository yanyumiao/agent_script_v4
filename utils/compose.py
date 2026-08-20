"""ffmpeg 视频+配音合成"""
import subprocess
from pathlib import Path


def _probe_duration(path) -> float:
    cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration",
           "-of", "default=noprint_wrappers=1:nokey=1", str(path)]
    out = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return float(out.stdout.strip())


def _mux_shot(video, voice, duration, out_path):
    if voice:
        cmd = [
            "ffmpeg", "-y",
            "-i", str(video),
            "-i", str(voice),
            "-filter_complex", "[1:a]apad[a]",
            "-map", "0:v", "-map", "[a]",
        ]
    else:
        cmd = [
            "ffmpeg", "-y",
            "-i", str(video),
            "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo",
            "-map", "0:v", "-map", "1:a",
        ]
    cmd += [
        "-t", str(duration),
        "-c:v", "libx264", "-c:a", "aac",
        "-ar", "44100", "-ac", "2",
        str(out_path),
    ]
    subprocess.run(cmd, check=True, capture_output=True)


def compose_shots(shots, out_path):
    clips = []
    tmp = Path(out_path).parent / "clips"
    tmp.mkdir(parents=True, exist_ok=True)
    for i, shot in enumerate(shots):
        video = shot["video"]
        voice = shot.get("voice")
        duration = _probe_duration(video)
        clip = tmp / f"clip_{i:02d}.mp4"
        _mux_shot(video, voice, duration, clip)
        clips.append(clip)

    list_file = Path(out_path).parent / "concat.txt"
    list_file.write_text("".join(f"file '{c.resolve()}'\n" for c in clips), encoding="utf-8")
    subprocess.run(
        ["ffmpeg", "-y", "-f", "concat", "-safe", "0",
         "-i", str(list_file), "-c", "copy", str(out_path)],
        check=True, capture_output=True,
    )
    return str(out_path)
