"""ffmpeg 视频+配音合成"""
import subprocess
from pathlib import Path


def probe_duration(path) -> float:
    cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration",
           "-of", "default=noprint_wrappers=1:nokey=1", str(path)]
    out = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return float(out.stdout.strip())


def _mux_shot(video, voice, out_path):
    video_dur = probe_duration(video)
    voice_dur = probe_duration(voice) if voice else 0.0
    target = max(video_dur, voice_dur)
    pad = max(0.0, voice_dur - video_dur)

    if voice:
        cmd = ["ffmpeg", "-y", "-i", str(video), "-i", str(voice)]
        v_fc = (f"[0:v]tpad=stop_mode=clone:stop_duration={pad:.3f}[v]"
                if pad > 0 else "[0:v]null[v]")
        cmd += ["-filter_complex", f"{v_fc};[1:a]apad[a]",
                "-map", "[v]", "-map", "[a]"]
    else:
        cmd = ["ffmpeg", "-y", "-i", str(video),
               "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo",
               "-map", "0:v", "-map", "1:a"]
    cmd += [
        "-t", f"{target:.3f}",
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
        clip = tmp / f"clip_{i:02d}.mp4"
        _mux_shot(video, voice, clip)
        clips.append(clip)

    list_file = Path(out_path).parent / "concat.txt"
    list_file.write_text("".join(f"file '{c.resolve()}'\n" for c in clips), encoding="utf-8")
    subprocess.run(
        ["ffmpeg", "-y", "-f", "concat", "-safe", "0",
         "-i", str(list_file), "-c", "copy", str(out_path)],
        check=True, capture_output=True,
    )
    return str(out_path)
