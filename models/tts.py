"""本地 Qwen3-TTS 配音客户端（MLX）"""
import numpy as np
import soundfile as sf

import config
from mlx_audio.tts.utils import load_model

_model = None


def _get_model():
    global _model
    if _model is None:
        _model = load_model(config.TTS_MODEL)
    return _model


def generate_voice(text, voice, output_path):
    model = _get_model()
    results = list(model.generate_custom_voice(
        text=text,
        speaker=voice,
        language=config.TTS_LANGUAGE,
    ))
    audio = np.concatenate([np.array(r.audio, copy=False) for r in results])
    sf.write(str(output_path), audio.astype(np.float32), results[0].sample_rate)
    return str(output_path)
