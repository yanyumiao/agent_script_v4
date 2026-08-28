# 漫剧 Agent 项目说明

输入小故事 → 自动产出带配音的漫剧视频，LangGraph 编排。

## Pipeline（graph/build.py 线性 7 节点）

```
story → script → storyboard → characters(三视图) → shots(场景图) → voices(配音) → shots(视频) → final.mp4
        DeepSeek    DeepSeek         FLUX               FLUX           Qwen3-TTS      H3          ffmpeg
```

节点实现见 `graph/nodes.py`，每个节点都有「产物已存在则跳过」的幂等逻辑，支持 `--run-dir` 续跑。

## 技术选型

| 环节 | 技术 | 部署 |
|---|---|---|
| 剧本/分镜 | DeepSeek V4（`deepseek-v4-flash`） | 在线 API |
| 文生图 | FLUX.2 Klein 4B q8（mflux） | 本地 |
| 图生视频 | minimax-H3（antirez/h3.c，BF16 未量化） | 本地 |
| 配音 | Qwen3-TTS（本地 MLX，CustomVoice 1.7B bf16） | 本地 |
| 合成 | ffmpeg | 本地 |

## 关键坑（避免重踩）

1. **DeepSeek V4 默认 thinking 模式不支持结构化输出**，必须 `extra_body={"thinking":{"type":"disabled"}}`。`model_kwargs` 和 `reasoning` 参数都无效，只有 `extra_body` 有效。见 `models/deepseek.py`。
2. **FLUX.2 Klein 不支持 `--negative-prompt`**（mflux 运行时直接报错）。`--help` 里列出的是全局选项，不代表特定模型支持——每个新参数都要真实跑一次验证，不能只看 help。
3. **mflux 的 `--image` 与 `--image-strength` 互斥**，必须写成 `--image PATH STRENGTH`（如 `--image x.png 0.5`）。见 `models/flux.py`。
4. **H3 怪癖**（antirez 移植版，非官方发行）：
   - 必须 `cwd=~/h3-metal` 运行（否则找不到 `h3_shaders.metal`）
   - `--seed` 只接受整数，不接受 `random`（用 Python `random.randint`）
   - 角色/场景一致性用 `--ref-image`（Ref2VA），不是 `--first-frame`
   - **帧数上限 362**：合法帧数 = 5+17k（k≤21，h3.c 直接报错）；配音时长×24fps 可能超限，`models/h3.py` 已钳制 `min(frames, H3_MAX_FRAMES)`，被钳短的视频由 compose `tpad=stop_mode=clone` 补尾帧对齐
   - 当前版本 `3fafbca`（antirez/h3.c，2026-08-17，无 tag）；权重 **BF16 全精度未量化**（DiT 45×BF16+9×F32），运行未开 `--use-int8-row-fc2`。模型目录 `MiniMax-H3/` 下 FL2VA/Ref2VA 各一份（共 279G）。
5. **Qwen3-TTS CustomVoice 只有 3 个标准普通话音色**（`vivian`女 / `serena`女 / `uncle_fu`男），`eric`=川腔、`dylan`=京腔是方言音色；多角色会自动配错性别/方言。多角色需切 **Base 音色克隆**模式（`generate(text, ref_audio=…)`，每角色一段参考音）。模型预下载到 `~/qwen3-tts/`，`TTS_MODEL` 指本地路径，`load_model` 懒加载单例。

## 关键决策

- **一致性方案**：场景母图（establishing shot，空镜）做 img2img 锚定场景元素 + 每个镜头 prompt 重复拼角色外貌文字描述。`FLUX_SEED` 用 `None`（随机）——固定 seed 只保证同 prompt 可复现，对跨镜头一致性无帮助，故不固定。彻底解决角色一致性需训练角色 LoRA（Phase 2）。
- **音画时长对齐**：先配音、量出实际时长，视频帧数按 `max(分镜预估时长, 配音实际时长)` 生成，从源头消除「定格补长」。`utils/compose.py` 仍保留 `tpad=stop_mode=clone` 作兜底（正常流程不会触发）。
- **旁白无实体**：`generate_character_sheets` 跳过 `role=="旁白"`（不生成三视图），`appearance_map` 排除旁白（不拼进场景图 prompt）。

## Python 环境

- agent 依赖（langgraph / langchain-deepseek / mlx-audio / soundfile / dotenv / pydantic）装在 **conda base**（`/opt/miniconda3/bin/python`）。
- mflux 装在独立 venv `~/flux-klein/.venv`（只装 mflux）。
- 曾因 `.zshrc` 把 flux venv 放 PATH 最前，导致 `python` 指向 flux venv、跑 agent 缺 dotenv；已改为放 PATH **末尾**。跑 agent 用 `python`（conda base）或完整路径。

## 其他

- `config.py` 是所有 CLI 绝对路径 / 默认参数的唯一来源，改调用先读它。
- 用户使用说明见 `README.md`；输出目录结构见 `outputs/README.md`；语音/音色待办见 `todo.md`。
