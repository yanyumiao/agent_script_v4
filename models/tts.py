"""edge-tts 配音客户端"""
import asyncio
import time

import edge_tts


async def _synth(text, voice, output_path):
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(str(output_path))


def generate_voice(text, voice, output_path, retries=3):
    last_err = None
    for attempt in range(retries):
        try:
            asyncio.run(_synth(text, voice, output_path))
            return str(output_path)
        except edge_tts.exceptions.NoAudioReceived as err:
            # NoAudioReceived 多为微软端点瞬时抖动，重试通常可恢复
            last_err = err
            time.sleep(1.5 * (attempt + 1))
    raise last_err
