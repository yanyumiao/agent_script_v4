# 漫剧 Agent 构建方案 v1（LangGraph + DeepSeek + FLUX + H3 + TTS）

## 背景与目标

输入一段小故事，自动产出带配音的漫剧视频。

- FLUX.2 Klein 4B q8（文生图）→ `~/flux-klein/.venv/bin/mflux-generate-flux2`，已部署、7s/张
- minimax-H3（视频生成）→ `~/h3-metal/h3 -d ~/h3-metal/MiniMax-H3`，输出 MP4，支持 `--first-frame` 图片首帧条件
- DeepSeek（LLM）→ 剧本扩充 + 分镜脚本
- ffmpeg 9.0.1 → 合成
- conda base 已装 langgraph 1.2.9 / langchain-deepseek 1.1.0 / langchain-openai 等

## 决策

| 项 | 决策 |
|---|---|
| FLUX | 用已部署的 FLUX.2 Klein 4B |
| DeepSeek | 官方 OpenAI 兼容接口，`deepseek-chat`，key 由用户提供 |
| 配音 | edge-tts（免费中文），可换 MiniMax TTS / CosyVoice |
| ComfyUI | **先不引入**，用 mflux；进阶用 mflux-train 角色 LoRA 或再上 ComfyUI |
| 环境 | 复用 conda base（已装全家桶），只补 edge-tts |

## Pipeline（LangGraph StateGraph）

1. expand_script（DeepSeek）：故事 → 结构化剧本（标题/角色/场景/对白）
2. write_storyboard（DeepSeek）：剧本 → 分镜脚本（镜头号/画面/人物/动作/对白/运镜/时长）
3. generate_character_sheets（FLUX）：每个角色 → 三视图（正/侧/背）
4. generate_scene_images（FLUX）：每个分镜 → 场景图（含角色外貌描述）
5. generate_shots（H3）：场景图 → 动态视频片段（`--first-frame`）
6. generate_voices（TTS）：每句对白 → 语音（按角色分配音色）
7. compose（ffmpeg）：视频+配音对齐 → 拼接 → 最终 MP4

## 目录结构

```
agent_script_v4/
├── .env / .env.example
├── requirements.txt
├── config.py
├── prompts.py
├── models/{deepseek,flux,h3,tts}.py
├── graph/{state,nodes,build}.py
├── utils/compose.py
├── main.py
└── outputs/
```

## 关键实现要点

- 模型调用用**绝对路径**：`~/flux-klein/.venv/bin/mflux-generate-flux2`、`~/h3-metal/h3`
- DeepSeek 用 `with_structured_output(PydanticModel)` 保证 JSON 可解析
- FLUX 三视图单图输出（character sheet 正/侧/背）
- H3 首帧用 `--first-frame 场景图.png --seconds 3`
- TTS：`edge-tts --voice zh-CN-XiaoxiaoNeural`
- 合成：ffmpeg 对齐时长 + concat 拼接

## 分阶段

- Phase 1（MVP）：跑通全链路，产出第一个带配音漫剧
- Phase 2：mflux-train 角色 LoRA；评估 ComfyUI
- Phase 3：字幕、运镜细化、并行加速、重试

## 待用户提供

- DeepSeek API key（填 `.env`）
