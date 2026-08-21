# FLUX.2 Klein 4B (MLX q8) 本地部署

在 M5 Pro 64G Mac 上部署的本地文生图模型，用于漫剧分镜批量出图。使用 mflux 官方命令 `mflux-generate-flux2` 调用，接口与 minimax-H3 同为「提示词进 → 文件出」，供 agent 统一调度。

## 部署位置

| 内容 | 位置 |
|---|---|
| 工具 | `~/flux-klein/.venv/`（mflux 0.19.0 + MLX） |
| 官方命令 | `mflux-generate-flux2`（已加入 PATH，见 `~/.zshrc`） |
| 模型权重 | `~/.cache/huggingface/hub/models--mlx-community--flux2-klein-4b-8bit/`（约 8GB） |

## 模型信息

- 模型：`mlx-community/flux2-klein-4b-8bit`（FLUX.2 Klein 4B，8-bit 量化）
- 许可：Apache 2.0，可商用
- 特性：4 步蒸馏，出图快；**不支持 negative prompt，guidance 固定 1.0**

## 使用方法（官方命令）

```bash
mflux-generate-flux2 \
  --model mlx-community/flux2-klein-4b-8bit \
  --prompt "提示词" \
  --output 输出.png \
  --steps 4 --width 1024 --height 768 --seed 42
```

示例：

```bash
mflux-generate-flux2 --model mlx-community/flux2-klein-4b-8bit --prompt "一个中国水墨画风格的少女，站在竹林中" --output demo.png --steps 4 --width 1024 --height 768 --seed 42
```

参数与官方文档一致，可直接查 mflux 资料。常用：`--steps`、`--width`、`--height`、`--seed`、`--low-ram`、`--mlx-cache-limit-gb`。

## 与 minimax-H3 的统一调度接口

两者都是「提示词进 → 文件出」：

```bash
# minimax-H3（多模态）
~/h3-metal/h3 -d ~/h3-metal/MiniMax-H3 -p "提示词" -o out.mp4

# FLUX.2 Klein 4B q8（文生图）
mflux-generate-flux2 --model mlx-community/flux2-klein-4b-8bit --prompt "提示词" --output out.png --steps 4
```

agent 只需维护一张 `模型名 → 命令` 映射表即可统一调度。

## 实测数据

| 项 | 值 |
|---|---|
| 模型下载 | 约 2.5 分钟（hf-mirror） |
| 单张生成（4 步，1024×768） | 约 7 秒 |
| 峰值 MLX 内存 | 11.79 GB |

## 注意事项

- **网络镜像**：HuggingFace 直连被墙，已在 `~/.zshrc` 配置 `HF_ENDPOINT=https://hf-mirror.com`（可用环境变量覆盖）。
- **蒸馏模型限制**：不支持 negative prompt，`guidance` 固定 1.0。
- **尺寸约束**：宽高需为 16 的倍数（如 1024×768、1024×1024）。
- **冷启动**：mflux 每次调用会重载模型（约数秒）；批量场景可后续上 HTTP 常驻服务或进程复用。

## 重新安装（可选）

```bash
python3 -m venv ~/flux-klein/.venv
~/flux-klein/.venv/bin/pip install -U pip
~/flux-klein/.venv/bin/pip install mflux -i https://pypi.tuna.tsinghua.edu.cn/simple
```
