# 语音（TTS）相关 TODO

> 当前配音实现：`edge-tts`（**在线**服务，微软 Edge 免费神经语音，`zh-CN-*` 音色），
> 已加 `NoAudioReceived` 瞬时失败重试（见 `models/tts.py`）。

## 待办

- [ ] **评估本地化配音方案**（彻底离线、摆脱微软依赖）
  - CosyVoice（阿里，开源本地，中文效果好，Mac 上偏重）
  - GPT-SoVITS / Bert-VITS2（可克隆音色，需先准备目标音色）
- [ ] **评估在线付费方案**（音质/稳定性更好，仍走 API）
  - MiniMax TTS API
  - Azure TTS
- [ ] **H3 自带音轨的处理**：当前合成丢弃 H3 生成的音频、只用 TTS 对白；考虑保留环境音/音效并与 TTS 混音
- [ ] **音色分配细化**：当前按角色出场顺序从 `config.TTS_VOICES` 池顺序分配，旁白固定最后一个；可改为按性别/年龄更精细匹配
- [ ] **长句切分与停顿控制**：超长台词分段合成、语速/停顿微调，让配音更自然

## 已完成

- [x] edge-tts 接入 + 按角色分配音色（`config.TTS_VOICES`）
- [x] `NoAudioReceived` 瞬时失败重试（`models/tts.py`）
