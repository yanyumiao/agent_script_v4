# 语音（TTS）相关 TODO

> 当前配音实现：`Qwen3-TTS`（**本地** MLX，CustomVoice 模式 1.7B bf16），
> 已彻底消除 edge-tts 在线依赖。模型预下载到 `~/qwen3-tts/`。

## 待办

- [ ] **多角色音色不足**：CustomVoice 只有 3 个标准普通话音色（`vivian`女 / `serena`女 / `uncle_fu`男），
      `eric`=川腔、`dylan`=京腔；多角色会性别/方言错配。多角色需上 **Base 音色克隆**模式
      （`generate(text, ref_audio=…)`，每角色一段参考音，参考音可用 edge-tts 一次性生成）
- [ ] **H3 自带音轨的处理**：当前合成丢弃 H3 生成的音频、只用 TTS 对白；考虑保留环境音/音效并与 TTS 混音
- [ ] **长句切分与停顿控制**：超长台词分段合成、语速/停顿微调，让配音更自然

## 已完成

- [x] Qwen3-TTS 本地替换 edge-tts（彻底离线，消除 `NoAudioReceived` 瞬时失败）
- [x] edge-tts 接入 + 按角色分配音色（`config.TTS_VOICES`）——已随 edge-tts 移除
- [x] `NoAudioReceived` 瞬时失败重试（`models/tts.py`）——已随 edge-tts 移除
