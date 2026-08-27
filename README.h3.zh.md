# h3-metal

在 Apple Silicon 上原生运行 MiniMax-H3 推理。本项目以一系列可工作的垂直切片方式构建：先是确定性的主机/模型元数据，接着是可移植的 Metal 块对等校验、提示词编码、提示词到视频/音频、首尾帧条件，最后是有序参考。

提示词到视频/音频、首尾帧条件、以及有序的 Ref2VA 图像/视频/音频参考均已端到端跑通。当前工作是在 M3 Max 和 M5 Max 上做 H3 专属的 Metal 性能与内存增量优化。

## 教程

### 1. 构建并检查模型

以下示例假设 Hugging Face 快照位于 `./MiniMax-H3`，且 `PATH` 中有 FFmpeg 和 FFprobe。

```sh
make -j8
mkdir -p outputs
./h3 --info -d ./MiniMax-H3
```

`--info` 会检查模型布局并打印选中的 Metal 设备，而不会映射所有权重或生成媒体。运行 `./h3 --help` 可查看完整 CLI 参考。

不带 `-p` 时，同一个二进制会启动一个 Iris 风格的交互式会话：

```sh
./h3 -d ./MiniMax-H3 --width 512 --height 512 --steps 6
```

输入提示词即可生成一段带编号的视频。会话会在内存中保留精确的 BF16 提示词条件、已就绪的 DiT 和视频解码器，因此用另一个种子重复同一提示词时无需重新加载和编码。常用命令有 `!status`、`!seed random`、`!seconds 2`、`!show`、`!save output.mp4` 和 `!cache`。用 `!help` 查看完整（简短的）命令列表。

首尾帧条件在会话中是持久的：

```text
h3> !first opening.png
h3> !last ending.png
h3> The camera moves slowly around the subject.
```

用 `!first clear` 或 `!last clear` 移除锚点。生成的视频写入启动时打印的会话目录。

对于一般的 Ref2VA 条件图像，改用 `!ref-image PATH`。图像按顺序追加，并以 `<Picture 1>`、`<Picture 2>` 等形式暴露给模型；文件名对模型没有意义。

```text
h3> !ref-image person.png
h3> Make the person shown in Picture 1 wave to the camera.
```

`!refs` 列出当前顺序，`!ref-remove N` 移除一项，`!refs clear` 全部清除。Ref2VA 参考不能与 `!first`/`!last` 锚点混用。

### 2. 生成第一条快速视频

从经过验证的平衡预设开始。它会以 24 fps 生成 22 帧（约 0.92 秒），在受支持的图形终端中于每次去噪过渡后显示演进中的视频中间帧，并打印各阶段耗时：

```sh
./h3 --profile \
  -d ./MiniMax-H3 \
  -p "A red fox walks through fresh snow in a pine forest. Medium tracking shot, natural winter light, realistic fur, soft footsteps and wind." \
  --width 512 --height 512 \
  --frames 22 --steps 20 \
  --layers 45 --reuse 2 \
  --show \
  -o outputs/fox-fast.mp4
```

这故意不是最激进的配置：

- `--steps 20` 执行默认的 20 遍去噪。
- `--reuse 2` 计算 11 次新鲜的（去噪器）速度而非全部 20 次，并外推被跳过的过渡。
- `--layers 45` 运行 50 个 transformer 块中的 45 个，同时减少时间和统一内存占用。
- `--show` 是可选的。它支持 Kitty/Ghostty 以及 iTerm2/WezTerm/Konsole 图形协议。它加载一个常驻的预览 VAE，在每次 Euler 过渡后显示一个有代表性的视频中间帧，然后显示所有最终帧。显示尺寸默认为 2x，使图像在 macOS Retina 屏幕上具有预期的逻辑尺寸；在非 HiDPI 显示器上用 `--zoom 1`。这会增加预览解码时间以及约 10 GiB 的临时模型常驻；不带 `--show` 的运行不受影响。
- `--profile` 是可选的，不会选择不同的生成路径。

首次进程调用还要付出模型加载和文件系统缓存的开销。用重复运行来比较性能，并在机器预热后交替不同变体，因为该负载对热降频敏感。

对于极短的迭代，直接请求四遍去噪：

```sh
./h3 --profile \
  -d ./MiniMax-H3 \
  -p "A red fox walks through fresh snow in a pine forest. Medium tracking shot, natural winter light, realistic fur." \
  --width 512 --height 512 --frames 22 \
  --steps 4 --layers 50 --reuse 1 \
  --show \
  -o outputs/fox-four-step.mp4
```

`--steps N` 始终表示恰好 N 遍去噪。四到七遍使用赢得低成本对比的同一调度；从 4 增加到 7 会逐步改善细节和运动。在如此小的预算下保持 `--reuse 1`，让每一遍都真正运行模型。`--show` 在每遍之后显示一个预览。

曾评估过若干偏尾部的调度，因为长运行中大部分可见的清理发生在后期。它们保留了太少的早期构图更新，产生了编织纹理、弱运动或裁切的颜色。保留的模式使用发布的线性基础网格加一个终点。在 512 方形、22 帧的狐狸测试上，选定的四遍结果对 29 遍参考的全视频 SSIM 为 0.556；一个独立的冲浪者测试测得 0.547。四遍去噪在 M5 Max 上约 3.5 秒，而参考为 26.4 秒。

对于低内存运行，加 `--ssd-streaming`：

```sh
./h3 --profile \
  -d ./MiniMax-H3 \
  -p "A red fox walks through fresh snow in a pine forest." \
  --width 512 --height 512 --frames 22 --steps 20 \
  --layers 50 --reuse 1 --ssd-streaming \
  -o outputs/fox-ssd.mp4
```

它使用原始 BF16 检查点，不做转换或量化。它只在内存中保留两个 DiT 块，并在 GPU 运行当前块的同时从 SSD 读取下一个块。在 M5 Max 上，被跟踪的 DiT 存储在 512 方形从约 36.5 GiB 降到 2.0 GiB，在 864x480 为 2.1 GiB。一次预热的 50 块前向在 512 方形测得 1.35 对比 2.49 秒（慢 84%），在 864x480 为 2.14 对比 2.68 秒（慢 26%）。这些是与相同全常驻 BF16 路径的对比，且两次检查结果字节一致。

2.0--2.1 GiB 的数字是 DiT 的被跟踪张量存储，而非总系统内存。提示词编码和两个 VAE 在独立的阶段运行，而非将其完整峰值叠加其上；OS、媒体缓冲区和输出分辨率仍需要余量。`--show` 会保留一个预览 VAE 常驻并增加约 10 GiB，因此最低内存运行应省略它。

SSD 流式是一种显式的内存/速度权衡，不是默认行为。它不能与 `--use-int8-row-fc2` 组合。在交互式会话中，用 `!ssd-streaming on`。

### 3. 逼近参考质量

评估质量时一次只改一个控制项。先恢复所有层，再恢复所有去噪器评估，最后把默认的 20 遍调度提升到更慢的 50 遍参考：

```sh
./h3 --profile \
  -d ./MiniMax-H3 \
  -p "A red fox walks through fresh snow in a pine forest. Medium tracking shot, natural winter light, realistic fur, soft footsteps and wind." \
  --width 512 --height 512 \
  --frames 22 --steps 50 \
  --layers 50 --reuse 1 \
  -o outputs/fox-close.mp4
```

默认值是 `--steps 20 --layers 50 --reuse 1`；这条 close 路径要显式保留 `--steps 50`。它执行 50 次完整的 50 块去噪器前向，比默认昂贵得多，但当某个快速模式改变了主体、解剖结构、运动或构图时，它是正确的基准（oracle）。不要期望与 MLX 逐像素一致，因为随机数和执行引擎不同；所描绘的内容和运动应当一致。

### 4. 选择速度/质量预设

除非另有说明，这些控制项彼此独立：

| 控制项 | 慢速参考 | 默认 | 激进 | 主要影响 |
|---|---:|---:|---:|---|
| 去噪遍数 | `--steps 50` | `--steps 20` | `--steps 4..7` | 数字始终表示实际去噪遍数。 |
| 整去噪器复用 | `--reuse 1` | `--reuse 2` | `--reuse 3` | 20 步时：20、11 或 8 次新鲜 DiT 评估。 |
| 激活 DiT 块 | `--layers 50` | `--layers 45` | `--layers 40` | 更少的块减少计算和常驻 transformer 权重。 |
| 核心残差复用 | `--core-reuse 1` | `--core-reuse 4` | `--core-reuse 6` | 每一步都刷新 patch/head 工作，但昂贵核心运行更少。 |
| Token 缩减 | 关 | 可选 | `--token-reduction` | 在中间块内配对水平视频 token；更快但可能改变构图。 |
| 内部画布 | 输出尺寸 | 512 方形输出用 `384x384` | `320x320` | 以更小尺寸跑 DiT/VAE，再用 vImage 放大。 |

在 M5 上，`--use-int8-row-fc2` 对每个 FC2 行使用一个激活缩放和单个全宽 TensorOps 乘积。它是可选的，因为数值上不如分组 int8 保守。在互易测试中它将完整的去噪器前向减少了约 2.6%。匹配的四步狐狸和冲浪者视频保持了相同的主体、场景和运动（全视频 SSIM 0.919 和 0.828）。在交互式会话中，用 `!int8-row-fc2 on`。

`--reuse` 和 `--core-reuse` 互斥。层削减可以与其中任意一个组合。

要让第一条命令更快同时保持输出分辨率，加 token 缩减：

```sh
./h3 --profile \
  -d ./MiniMax-H3 \
  -p "A surfer riding inside a sharp blue ocean wave, one rider and one white board, realistic spray." \
  --width 512 --height 512 --frames 22 --steps 20 \
  --layers 45 --reuse 2 --token-reduction \
  -o outputs/surfer-fast.mp4
```

在已验证的 512 方形形状上，token 缩减把 `45 layers + reuse 2` 的去噪 profile 从 16.69 降到 12.60 秒（IT M5 Max）。独立的狐狸和冲浪者渲染保持连贯，但构图可能比 close 路径偏差更大。
对于激进预览，以 320 方形内部渲染并放大到请求的 512 方形输出：

```sh
./h3 --profile \
  -d ./MiniMax-H3 \
  -p "A red fox walking through snow, realistic, tracking shot." \
  --width 512 --height 512 \
  --render-width 320 --render-height 320 \
  --frames 22 --steps 20 --layers 40 --reuse 3 \
  -o outputs/fox-aggressive.mp4
```

该组合在验证中产生了一个干净、可辨认的 22 帧狐狸，但会丢失精细细节并可能改变取景。**不要**同时给 `--layers 40` 和 `--reuse 3` 再加 `--token-reduction`：该测试组合产生了颜色振铃、轮廓和残影肢体。

作为整速度复用的替代，这会在每次过渡时保持与时间步相关的 patch 和输出头新鲜：

```sh
./h3 --profile \
  -d ./MiniMax-H3 \
  -p "A surfer riding a blue ocean wave." \
  --width 512 --height 512 --frames 22 --steps 20 \
  --layers 45 --core-reuse 4 \
  -o outputs/surfer-core-reuse.mp4
```

仅在激进预览时用 `--core-reuse 6`。高于 6 的值不开放，因为验证中丢失了主体保真度。

### 5. 选择分辨率和时长

宽和高必须各为 32 的倍数、至少 32，且乘积不得超过 `768 * 1344` 像素。这些是机械限制，并非承诺每个小画布都有好的模型质量。H3-Base 是一个 768p 模型。

| 画布 | 当前建议 |
|---|---|
| `512x512` | 最安全的开发尺寸；用多个提示词反复验证过。 |
| `768x768` | 已验证的 close 质量方形输出；明显更昂贵。 |
| `1344x768`, `768x1344` | 发布的 768p 级横屏/竖屏上限。 |
| `1024x768`, `768x1024` | 有效的 4:3 和 3:4 768p 级画布。 |
| `384x384` 内部到 `512x512` | 已验证的快速质量缩放点。 |
| `320x320` 内部到 `512x512` | 已验证的激进缩放点。 |
| `256x256` | 原生快速预览画布，带自动低分辨率 RoPE 适配。 |

对于快速原生 256 方形预览：

```sh
./h3 -d ./MiniMax-H3 \
  -p "A red fox walks through fresh snow in a pine forest." \
  --width 1344 --height 768 \
  --frames 22 --steps 20 \
  --layers 50 --reuse 1 \
  -o outputs/fox-1344-768.mp4
```

在 256 方形，H3 只有一个 `8x8` 的有效空间 token 网格，因此精细细节和复杂构图的空间较小。H3 在恰好 256 方形时自动将空间 RoPE 坐标减半。这消除了长狐狸渲染中的重复晶格伪影，并在独立的肖像上保持连贯，而无需增加 token 或运行时间。用 `--use-reference-rope` 恢复发布的/MLX 坐标以做对等校验。在此尺寸下保持 token 缩减关闭。原生 128 方形仍不支持：即使调整 RoPE，其 `4x4` token 网格也无法恢复可辨认的主体。

`--render-width` 和 `--render-height` 必须一起设置，必须与输出具有相同的宽高比，且不能超过输出尺寸。模型和 VAE 使用内部尺寸；终端帧和编码视频保留请求的输出尺寸。

H3 输出 24 fps，并将帧请求向上对齐到 `5 + 17*n`：

用 `--seconds N` 做以时长为导向的请求，或用 `--frames N` 直接控制帧数；两者互斥。接受小数秒。秒数按 24 fps 转换，然后向上取整到下一个合法的 H3 时间形状，因此 `--seconds 10` 产生 243 帧（10.125 秒）。

| 帧数 | 近似视频时长 |
|---:|---:|
| 22 | 0.917 秒 |
| 39 | 1.625 秒 |
| 56 | 2.333 秒 |
| 107 | 4.458 秒 |
| 243 | 10.125 秒 |
| 362 | 15.083 秒 |

短片适合开发。发布的工作流面向约 4–15 秒的视频。像 `--frames 23` 这样的请求会向上取整到 39 帧，而非产生任意时间形状。

### 6. 优化提示词

短提示词也能用，但发布的系统期望类似 Context-IR 的描述。陈述主体、动作、场景、镜头、光影/风格以及期望的声音。例如（结构：Scene/Action/Camera/Look/Audio 五要素）：

```text
Scene: a single red fox in a snow-covered pine forest at dawn.
Action: the fox walks steadily left to right and looks toward the camera once.
Camera: medium-height lateral tracking shot, 50 mm lens, stable framing.
Look: photorealistic fur, cold blue ambient light, warm sunrise rim light.
Audio: soft footsteps in snow, light wind through pine branches, no music.
```

在重要时明确说明身份和对象数量。`--seed N` 控制原生随机流；默认是 42。用相同的提示词、种子、分辨率、帧数和步数来比较选项。

### 7. 预览帧并诊断性能

- `--show` 在每次去噪过渡后显示一个有代表性的帧，然后显示完成视频的所有帧。像 Iris 一样，默认对 Retina 终端声明 2x 显示尺寸；`--zoom N` 改变该系数而不调整生成的视频或编码的终端图像。
- `--frames-dir DIR` 将最终回调帧写成 PPM 文件。中间的 `--show` 预览不写入那里。
- `-o ''` 禁用 MP4 编码；当 FFmpeg 不可用时与 `--frames-dir` 组合。
- `--profile` 报告各阶段 wall 时间、Metal 编码/等待时间、峰值活跃张量存储、累计分配和 dispatch 次数。

例如：

```sh
./h3 --profile -d ./MiniMax-H3 -p "A hummingbird hovering over red flowers." \
  --width 512 --height 512 --frames 22 --steps 20 \
  --layers 45 --reuse 2 --frames-dir outputs/hummingbird-frames \
  -o ''
```

### 8. 添加图像、视频和音频参考

首尾帧锚点选择 FL2VA 路径：

```sh
./h3 -d ./MiniMax-H3 -p "The fox keeps walking through the snow." \
  --width 512 --height 512 --frames 22 --steps 20 \
  --layers 45 --reuse 2 \
  --first-frame fox.png --last-frame fox-later.png \
  -o outputs/fox-anchored.mp4
```

有序参考选择独立的 Ref2VA 检查点。用与媒体语义匹配的标志：

```sh
# 一个图像参考。
./h3 -d ./MiniMax-H3 -p "Use the animal and setting in the reference." \
  --width 512 --height 512 --frames 22 --steps 20 \
  --ref-image fox.png -o outputs/fox-reference.mp4

# 续接一段片段但忽略其配乐。
./h3 -d ./MiniMax-H3 -p "Continue the motion in this clip." \
  --width 512 --height 512 --frames 22 --steps 20 \
  --ref-silent-video fox.mp4 -o outputs/fox-video-reference.mp4

# 保留片段内嵌的音频。
./h3 -d ./MiniMax-H3 -p "Continue this audiovisual scene." \
  --width 512 --height 512 --frames 56 --steps 20 \
  --ref-video fox-with-audio.mp4 -o outputs/fox-video-audio.mp4

# 显式替换一段视频的配乐。
./h3 -d ./MiniMax-H3 -p "Continue the scene with the supplied music." \
  --width 512 --height 512 --frames 56 --steps 20 \
  --ref-video-audio silent-fox.mp4 replacement.wav \
  -o outputs/fox-replaced-audio.mp4

# 一个有序图像加独立音频参考。
./h3 -d ./MiniMax-H3 -p "Use the animal and music from the references." \
  --width 512 --height 512 --frames 56 --steps 20 \
  --ref-image fox.png --ref-audio music.wav \
  -o outputs/fox-image-audio.mp4
```

参考标志可以重复，其命令行顺序被保留。独立音频必须伴随图像或视频参考。音频参考必须为 2–15 秒；最多接受三个音频输入，其总解码时长上限为 15 秒。

## 测试与运行时要求

```sh
make test
make parity
```

`make test` 运行确定性主机套件，并且当被忽略的 MLX fixture 安装在 `misc/fixtures/` 下时，会在运行时编译 Metal 源码并针对命名的 MLX 输出检查一个完整的玩具 H3 块。运行时编译是有意为之：它遵循 Iris，不需要 Xcode 的可选离线 Metal 工具链。测试覆盖 F32 诊断路径和生产 BF16 存储路径；宽 BF16 矩阵乘法和 SDPA 使用缓存的 MPSGraph 图，并有直接的 Metal 正确性回退。`make parity` 只运行这些 Metal/MLX 检查。

FFmpeg 和 FFprobe 必须位于 `PATH` 上以供媒体输入和 MP4 输出（`H3_FFMPEG` 和 `H3_FFPROBE` 可选择显式可执行文件）。生成的 RGB24 和 32 kHz 立体声 F32 PCM 通过并发管道输送；不创建中间未压缩媒体文件。

## 实现与性能说明

余下部分记录了教程预设背后的实现，以及为精确 A/B 诊断保留的环境变量。

### 采样器与 DiT 控制

默认采样器使用发布的偏移视频/音频调度。`--steps` 始终表示去噪遍数，最后一遍之后加终点零。整去噪器复用评估第一遍和最后一遍加上每个请求的间隔，然后在各自独立的调度上外推被跳过的视频和音频速度。步数非常小时，保持 `--reuse 1`。

对于低成本路径，发布的线性基础网格战胜了实际视频 sigma 线性间隔、二次和三次扭曲、精确的 30 点尾部子集、温和的幂扭曲、零阶保持全网格速度、线性速度外推和 RES。更偏尾部的候选通常锐化了主体但损害了运动或留下重复的编织背景；稀疏 RES 和长外推间隔失败得更明显。

层削减对检查点实际的 AdaLN 门进行排序，同时保护结构上重要的首尾块。未使用的权重和调度张量不被保留，因此 `--layers 45` 和 `--layers 40` 同时减少 transformer 时间和统一内存占用。核心复用保留前一个完整 transformer 残差，同时刷新 patch 投影和感知时间步的头；它仍与整速度复用互斥。

### 精确的 DiT 融合

每个激活的 DiT 块都将其注意力残差门与随后的 MLP AdaLN 融合。取整后的 BF16 残差仍被精确写入，但同一行保留在 threadgroup 内存中用于归一化，消除了一个 dispatch 和一次全局重读。在远离 token 缩减边界处，MLP 残差门还产生下一块的注意力 AdaLN 并将该归一化状态跨循环传递。`H3_DISABLE_FUSED_GATE_ADALN=1` 和 `H3_DISABLE_FUSED_CROSS_BLOCK_ADALN=1` 恢复双内核基准。最终的音频/视频 AdaLN 内核直接绑定到残差流中的偏移，在 512x512 避免了两次切片 blit 和 18.8 MiB 的暂存（在 864 级基准形状为 29.4 MiB）。`H3_DISABLE_FUSED_FINAL_SLICE=1` 在加载时恢复复制加 AdaLN 的基准。BF16 最终头在加载其 16x16 投影瓦片时应用 AdaLN，保留了独立的取整和累加顺序，同时移除了另一个同样大小的归一化激活。这两项优化合计节省 37.5/58.9 MiB。`H3_DISABLE_FUSED_FINAL_HEAD=1` 在加载时恢复偏移 AdaLN 加线性的基准。

### Token 缩减内部实现

`--token-reduction` 是一个独立的激进 DiT 模式。第 3 块之后，它配对相邻的水平目标视频 token，同时保持文本、音频、条件和参考 token 精确。完整的全分辨率状态作为旁路保留。在前十次含噪评估中，它在第 40 块之前恢复；后续形成细节的评估在第 30 块之前恢复。每个 token 以其原始值加上其配对学到的更新返回，因此配对内的细节不会被丢弃。池化内核只将真实配对的基线写入已分配的注意力暂存缓冲区的稠密尾部；奇数宽度的单个 token 无需基线。完整旁路在放得下时使用超大的 QKV 尾部，并仅为参考密集的布局提供受保护的专用回退。因此，常见的纯文本画布在任何 token 网格宽度下都不增加激活 arena。池化还在 BF16 值已在寄存器中时对两个源 token 做快照，避免了一次独立的完整隐藏层 blit 和冗余的源读取。同一个入口内核将每个池化行保留在 threadgroup 内存中，并输出第一个缩减块的注意力 AdaLN，消除了另一次全局残差读取。在恢复边界处，第一个全分辨率注意力 AdaLN 被融合进扩展：一个 10.5 KiB 的 threadgroup 行避免了全局残差重读，同时仍写入后续残差分支所需的精确旁路。在热平衡的 512x512x22、19 前向 IT M5 Max A/B 上，这将去噪时间从 39.13 降到 28.06 秒（28.3%）。最终视频/音频潜在相对 L2 为 5.56%/15.14%。狐狸首/中/尾帧保留了一个干净的吻部、连贯的腿和锐利的皮毛；一个独立的冲浪者在浪花中始终只有一个骑手和一块板。它改变构图，因此是可选加入而非 close 参考默认。`H3_TOKEN_REDUCTION_BLOCKS` 可覆盖后面的 `4:30` 间隔；`H3_TOKEN_REDUCTION_EARLY=STEPS:END` 覆盖早期调度，`0` 禁用它。`H3_DISABLE_TOKEN_REDUCTION=1` 提供上下文内的精确基准。`H3_DISABLE_FUSED_TOKEN_POOL_ADALN=1` 和 `H3_DISABLE_FUSED_TOKEN_ADALN=1` 独立恢复双内核的入口和出口边界以做诊断。Token 缩减与已验证的 `--layers 45 --reuse 2` 设置干净地组合：在同一个 512 基准上，它把该 profile 从 16.69 降到 12.60 秒（边际 24.5%），独立的狐狸和冲浪者渲染保持连贯。不要同时与 `--layers 40` 和 `--reuse 3` 组合；那个 6.47 秒的实验尽管潜在范数可接受，却产生了色度振铃和残影肢体。

### 内部画布与视频 VAE

`--render-width` 和 `--render-height` 在一个更低的同宽高比内部画布上运行模型和 VAE，然后在回调、终端显示和编码之前用高质量 vImage 将 RGB 帧缩放到请求的输出尺寸。这是一种显式的质量/速度权衡：一次实测的 384 到 512 提示词渲染将 M5 DiT 时间减少 33%、视频 VAE 时间减少 18%，同时保持干净、可辨认的写实结果。两个值都必须为 32 的倍数；精确输出画布仍为默认。对于方形 512 输出，384 是快速质量点，320 是已验证的激进点。后者产生了一个连贯的行走狐狸，DiT 耗时 8.02 秒对比原生约 15.82 秒。原生 256 使用上述同成本的空间 RoPE 适配；它仍是快速构图预览，而非 512 或 768 级最终渲染的替代。视频 VAE 会根据请求的画布几何自动选择 256–320 像素的空间瓦片，在保持峰值存储有界的同时最小化重复重叠工作。`H3_VAE_TILE_PIXELS=256` 恢复原始保守的瓦片计划以做 close 参考诊断。

### 权重常驻与流式提示词编码

在 M5 级 GPU 上，常驻的 transformer 权重直接从其 safetensor 分片映射，而非拷贝进匿名共享缓冲区。这使得 37 GiB 模型文件可回退/可回收，并略微改善总 transformer 时间；M3 使用更快的拷贝缓冲区路径。`H3_ZERO_COPY_WEIGHTS=0` 禁用 M5 的选择以做诊断。流式的 Qwen 文本编码器预分配一个小环的未来层缓冲区，并在 Metal 执行当前层的同时用八个 I/O worker 填充它们。默认环深度在 M3/较旧硬件上为两层，在 M5 上为三层（目标机器为 128 GiB）。`H3_QWEN_PREFETCH=0` 恢复单层同步参考路径；值 1–8 选择 worker 数，`H3_QWEN_PREFETCH_DEPTH=1` 到 `6` 覆盖环深度。

`--ssd-streaming` 是 DiT 的一种独立、更激进的常驻模式。只有其小块级别的归一化权重保持常驻。两个完整的 BF16 矩阵槽交替，同时一个后台读取器按检查点偏移顺序填充下一个槽；当前 Metal 命令缓冲区并发运行。Darwin 无缓存读取避免在文件系统缓存中保留第二份副本。第一个激活块在最后一个块期间再次预取，因此缓存的交互式 DiT 已为下一次去噪评估就绪。实测从内部 SSD 达到约 13–14.6 GiB/s。`H3_PROFILE=1` 报告总字节数、读取吞吐量以及未被 GPU 工作隐藏的读取等待部分。

### Metal 4 与 TensorOps 路径

M5 GPU 在序列长度最高 2,048 时，自动对 DiT QKV 和注意力输出投影使用原生 BF16 Metal 4/TensorOps。紧凑的 Morton 调度将 Q/K/V 直接路由到 head-major 注意力输入，避免了三次 MPSGraph 输入转置，且与可移植路径字节一致。在反复的 IT/US M5 Max 运行中，它将完整的 512x512 50 块前向改善了约 2%。对于 2,049–3,072 行（包括 864x480），两个行偏移 Morton dispatch 保留了高效的瓦片几何，在平衡运行中改善完整前向约 2%。更大的序列仍走 MPSGraph。`H3_NAX=0` 禁用 TensorOps 以做精确 A/B 诊断。该选择在运行时受保护，若编译不可用则回退到未改动的可移植库。

`H3_NAX=1` 强制更宽的原生 BF16 线性路径。它通过了完整的 50 块 MLX fixture，但仍为可选：精确形状的微基准青睐其 128 行瓦片，而完整 DiT 运行当前青睐 MPSGraph 调度。这为后续的量化/融合内核保留了一个可用的 NAX 集成，而不让基准回退成为默认。`H3_NAX=mlp` 选择一个更专用的 Metal 4 路径：配对的 FC1 gate/up TensorOps 瓦片在 threadgroup 内存中应用 SwiGLU，并只写 14,336 宽的激活中间结果，然后 FC2 也保持 TensorOps。`H3_DISABLE_NAX_MLP=1` 在以这种方式创建的上下文中保留 MPSGraph MLP，用于同进程 A/B 测试。该路径有意设为可选，因为调度取决于 OS GPU 栈：主力的 macOS 26.5.2 M5 Max 在孤立的真实权重 MLP 运行中获益 1.3–2.0%，但在完整 50 块前向中损失约 1–3%，而一台其他方面相同的 macOS 26.5 M5 Max 在同上下文前向 A/B 中获益 1.4%。产生的 50 块速度接近（视频 1.9%、音频 2.4% 相对 L2），但并非字节一致。

### 专用投影内核

窄的 DiT 音频/视频输出头将其小的发布 F32 权重一次性转为 BF16，并直接在 BF16 激活上使用源自 Iris 的 16x16 瓦片线性。在生产 320 渲染几何上，孤立的成对头测量在 M3 Max 上快 2.30 倍、在 M5 Max 上快 1.83 倍，相对 L2 为 `8.64e-4`；M5 的绝对节省约每评估步 0.6 ms。完整的狐狸和冲浪者序列保持干净，对 F32 头渲染测得 29.9/38.4 dB。`H3_DIT_F32_FINAL=1` 恢复 close 参考头及其额外激活缓冲区。F32 的 `96->5376` 视频和 `32->5376` 音频 patch 投影使用专用的 16x16 协作瓦片，保留 F32 权重、输入和累加，同时将瓦片结果直接取整到 BF16。成对的生产形状测量在 M3 上快 1.77 倍、在 M5 上快 1.62–1.78 倍；生成的完整 RGB 流与标量路径字节一致。融合最终 cast 将 2835 行瓦片本身从 2.499 提升到 1.734 ms（M3）和 1.555 到 1.186 ms（M5），并在 512/864 级几何上去除 38.27/59.66 MiB 的 F32 暂存。`H3_DISABLE_FUSED_PATCH_CAST=1` 恢复瓦片 F32 输出加独立 cast；`H3_SCALAR_PATCH=1` 选择标量诊断路径。同一个瓦片将其输出直接绑定进打包的隐藏流，移除了 BF16 媒体暂存缓冲区及其 blit。这又节省 19.13/29.83 MiB，并将 2835 行边界从 1.847 提升到 1.730 ms（M3）和 1.282 到 1.184 ms（M5）。连续的 T2VA 使用字节偏移；FL2VA/Ref2VA 使用紧凑的目标行映射，使每个模态仍为一次大 dispatch。一次完整的六段 Ref2VA M5 ABBA 保持字节一致，并将每次测得的前向对从 5.067 提升到 5.033 秒。`H3_DISABLE_FUSED_PATCH_PACK=1` 恢复暂存缓冲区和打包 blit。

### 调度与激活内存

DiT 核心被拆分为两个有序的 Metal 命令缓冲区，使第一部分的 GPU 执行与第二部分的 CPU 编码重叠。热平衡的 ABBA 测量在 M5 上选择 60% 深度的拆分（30/50、27/45 和 24/40），大约 0.5–1.8% 的收益；M3 只自动拆分已验证的 30/50 情况（测得快 1.2%），因为 24/40 在那里回退。操作顺序和生成字节不变。`H3_DIT_COMMAND_BLOCKS=0` 恢复单个命令缓冲区；值 1–50 覆盖拆分以进一步调优。DiT 激活缓冲区也遵循其实际的块内生命周期：QKV 投影 arena 先复用于注意力头，再复用于归一化的 MLP 输入，而当前注意力输出 arena 在其分支被消费后成为 MLP 输出。这在 512 级几何上去除 61.25 MiB、在 864 级几何上去除 99.63 MiB，而不改变 dispatch 或算术。`H3_DISABLE_DIT_ACTIVATION_ALIAS=1` 恢复独立的诊断缓冲区。不可变 DiT 权重和偏置的 MPSGraph tensor-data 包装器与其常驻缓冲区一起保留。这避免了为每个块和去噪评估重建相同的绑定元数据，而不拷贝张量存储；测得的 ABBA 收益在 M3 Max 上为 1.6%、在 M5 Max 上为 0.4–1.1%。激活包装器保持瞬态，因为保留它们在 M5 上回退。输出保持字节一致，`H3_DISABLE_GRAPH_DATA_CACHE=1` 恢复所有张量的瞬态包装器。在 M3/较旧硬件上，每个 DiT 块中的四个 MPSGraph 段还复用一个 `MPSCommandBuffer` 包装器用于其共享的底层 Metal 命令缓冲区。反复热平衡运行在 M3 Max 上测得快 1.0–1.6%；M5 测得中性，因此保留新鲜包装器。`H3_REUSE_MPS_COMMAND=0` 或 `1` 覆盖自动选择。结果字节一致。在 M5 上，服务的 Euler 采样器将其 patch 打包的 F32 潜变量和缓存的 BF16 速度保留在 Metal 缓冲区中。每次选定的去噪器刷新在下一次编码之前完成，避免了 MPSGraph 背压，同时移除了所有中间的潜变量/速度回读和重新打包。两次预热的八次运行 A/B 序列测得 0.1% 和 0.3% 的小收益，最终潜变量字节一致；该路径还每个视频潜变量元素节省约 16 字节的瞬态主机状态（在 768p 形状约 136 MB）。M3 和较旧 GPU 默认保留 CPU 采样器。`H3_CPU_SAMPLER=1` 在 M5 上恢复它；`H3_GPU_SAMPLER=1` 显式选择 GPU 状态路径，`H3_GPU_SAMPLER_WINDOW=0` 启用较慢的无界提前编码诊断。

### 检查点布局与媒体管线

发布的检查点按注意力头交错存储 DiT QKV 行。原生 Metal 在融合的 QK 归一化/RoPE 内核中直接消费该布局，避免了检查点转置和额外 RAM。早先的单位解释是噪声诊断输出的原因。

公共生成路径用流式原生 BigVGAN/AudioVAE 解码联合音频潜变量，并写出同步的 H.264 加 32 kHz 立体声 AAC。原生波形与修正后的 MLX 基准在相对 L2 `6.94e-5` 上一致。`--first-frame`、`--last-frame` 及其组合使用发布的视觉 VAE 编码器、Qwen3-VL 视觉塔和三深栈多模态呈现、0.999 条件增强，以及原生 DiT 中的固定条件行。第一张图像被拉伸到目标画布；最后一张图像做宽高比覆盖缩放并中心裁剪，与参考实现匹配。`--ref-image` 选择独立的 Ref2VA transformer，保留有序的 `<Picture N>` 呈现，并使用发布的仅缩小的宽高比保持参考画布。`--ref-silent-video` 额外执行有界的 24 fps 解码、视觉 VAE 的因果 `ceil(T/4)` 压缩、两帧 Qwen 采样，以及带时间戳的 `<Video N>` 呈现。`--ref-video` 保留嵌入的配乐，`--ref-video-audio VIDEO AUDIO` 提供显式替换，`--ref-audio` 追加一个有序的独立片段。参考音频被解码为 32 kHz 立体声 F32，由原生 AudioVAE 后验均值路径编码，以 0.999 干净潜变量加 0.001 种子噪声混合，钉在音频条件时间步 1.0，并作为宽 32 的行打包在与视觉参考相同的旋转时间线上。音频输入为 2–15 秒，最多接受三个，其总解码时长上限为 15 秒，独立音频参考必须与图像或视频参考组合。

原生音频编码器在一个真实的两秒立体声 fixture 上与修正后的 MLX 基准在相对 L2 `3.59e-6` 上匹配。该修正是重要的：原始 MLX reshape 交错了左/右样本，而官方 PyTorch/SGLang 路径将完整立体声通道折叠进批次维度。在 128 GB 的 M5 Max 上，干净的端到端图像+音频和嵌入视频+音频渲染分别耗时 74.58 和 76.99 秒，各约 40.1 GB 峰值物理占用，零交换。

### 剖析与诊断路径

`--profile` 分别报告每个 Metal 支持的阶段：wall 时间、CPU 侧命令编码、完整的 commit-to-fence 等待、根命令 GPU 时间戳、峰值活跃张量存储、累计分配和 dispatch 次数。等待测量是完整的命令周转；仅根 GPU 时间戳可能遗漏由 MPSGraph 内部调度的子缓冲区，并相应标注。

DiT 快速路径将每个 BF16 `fc1 -> SwiGLU -> fc2` 块作为一个缓存图来评估，避免了独立的图边界和常驻中间张量。设 `H3_DISABLE_FUSED_MLP=1` 保留 close 参考的操作边界以做数值诊断。

在受支持的 M5 Metal 4 TensorOps 硬件上，原生 int8 MLP 引擎是默认的。它动态量化激活，使用每输出通道权重缩放，并给敏感的 FC2 输入每 1,024 通道一个缩放。选定的 FC2 内核将缩放的偏积保留在私有协作片段中，而非反复溢出 32 KiB 的 threadgroup 瓦片。一次固定的 50 层、19 过渡 512x512 渲染在 M5 Max 上用 BF16 MPS 测得 36.30 秒、用 int8 测得 25.80 秒。首/中/尾解码帧保留相同的主体、构图和运动；小的边缘和皮毛细节可能不同。当前诊断实现仅在 A/B 诊断请求时保留 BF16 和 int8 MLP 权重。正常 int8 加载会在每个块的 BF16 FC1/FC2 缓冲区提交的量化完成后释放它们，将测得的峰值张量存储从 BF16 路径的 36.4 GiB 降到 25.9 GiB。运行时权重量化仍增加启动时间。

最快的 M5 路径还量化每个 DiT QKV 投影，并在现有的 Q/K 归一化和 RoPE 内核之前直接以 head-major 注意力布局写出其 Q/K/V 瓦片。在一次固定的 50 层、19 过渡 512x512 渲染中，这再次将去噪从 25.80 降到 19.32 秒。采样的首/中/尾帧仍是一只连贯、细节丰富的行走雪狐；量化注意力可能改变取景和精细细节。用 `--use-slower-bf16-qkv` 使用 close 参考的 BF16 投影。正常 int8 加载在量化后释放冗余的 BF16 QKV 权重。

随后的注意力输出投影在默认 M5 路径上也是 int8。交叉同模型测试在 512 和 864 将完整前向再改善 4.5–5.5%。一个解码的狐狸渲染保持干净，并与仅 int8 QKV 的构图紧密匹配；其热态去噪测得 19.18 秒。用 `--use-slower-bf16-attention-output` 将该投影保留为 BF16。

在该 int8 路径上，SDPA 现在将其结果保留为原生 `[head,row,dimension]` 顺序。一个专用的 256 线程内核将每个 H3 行直接收集并量化到投影的行主 int8 缓冲区，消除了中间的完整宽度 BF16 转置而不改变任何输出字节。热控交叉运行将完整 512 和 864 前向改善约 0.2–1.2%。用 `--use-slower-row-major-attention-output` 恢复显式的 BF16 行主 SDPA 输出和普通量化器。

M5 路径还将 QKV 和 MLP 激活量化折叠进前面的门控 AdaLN 内核。这每 50 层前向移除了 99 个独立量化器 dispatch，同时保留先前的输出字节，将交叉 512/864 测量改善约 0.3–0.6%。用 `--use-slower-unfused-int8-inputs` 恢复独立量化器。

融合的门控 AdaLN 路径将其完整 5,376 宽的 H3 行作为 BF16x4 向量加载并写出 int8x4。它在计算原始每线程 RMS 序列之前本地暂存取整值，因此归约树和每个输出字节保持不变。交叉测量再节省约 0.1–0.5%。现有的 `--use-slower-unfused-int8-inputs` 选项保留可移植标量和独立量化器回退。

Q/K RMS 归一化和 RoPE 也在 int8 QKV 投影瓦片内执行。融合的尾声字节一致，并在交叉 M5 测量中将完整前向改善 2.1–3.2%（512）和 1.0–1.8%（864）。用 `--use-slower-unfused-qkv-rope` 恢复独立的 Q/K 内核。

该尾声每个工作项处理四个相邻的 Q/K 维度，使用 BF16x4 加载和存储。逐元素算术和 BF16 取整顺序不变，而交叉冷态测量在 512 和 864 都将完整前向改善约 0.4–1.0%。同一个 `--use-slower-unfused-qkv-rope` 选项恢复标量独立路径。

在最多 2,048 行时，精确 RMS 循环使用 BF16x4 加载后跟四个显式有序 FMA。这保留每个输出位，并将 512 级前向再改善 0.5–0.6%；更大的形状保留标量加载，因为两种形式在那里打平。用 `--use-slower-scalar-qkv-rms` 强制标量加载。

int8 注意力输出投影将其 128 个行和列缩放缓存在 1 KiB 的 threadgroup 内存中，而非为每个协作片段元素重新读取。高于 2,048 行时，融合的 QKV 内核使用同样的思路，然后将该存储回收用于逆 RMS 值；更小的 QKV 形状保留直接加载，因为两种形式在那里打平。两者都字节一致，并在被选择处将完整前向改善约 0.2–0.7%。用 `--use-slower-uncached-int8-scales` 恢复直接设备缩放加载。

对于最多 2,048 行的序列，H3 注意力输出投影还将其 7,168×5,376 的形状编译进 TensorOps 内核。结果保持字节一致，同时在交叉完整 512 前向测量中节省约 0.2–0.8%。更大的序列保留动态形状内核，因为该特化在那里回退。`--use-slower-uncached-int8-scales` 恢复通用的动态、直接缩放加载实现。

FC1 也使用 H3 特化的、编译期 5,376 宽的 TensorOps 循环。它与通用循环字节一致，并在交叉完整前向中节省约 0.1–0.4%。用 `--use-slower-dynamic-fc1-k` 恢复运行时绑定循环。

```sh
./h3 --profile -d ./MiniMax-H3 \
  -p "A red fox walks through fresh snow." \
  --width 512 --height 512 --frames 22 --steps 20 \
  --layers 50 --reuse 1 -o outputs/fox-int8.mp4
```

用 `--use-slower-bf16-mlp` 强制可移植的 close 参考 MPS/BF16 MLP 路径以做数值比较。较旧的 Metal 硬件在所需的原生 TensorOps 内核不可用时自动选择该路径。对于 FC2 激活量化，最多 2,048 行的序列使用精确的 128 线程归约。每个线程在计算组最大值时保留其八个 BF16 输入值，避免在其发出 int8 值时第二次设备内存读取；交叉 M5 测量将完整 512 前向改善约 0.2–0.8% 而不改变任何输出字节。更大的序列保留已测量的 256 线程内核。`--use-slower-grouped-quantizer` 在每个尺寸都强制后者以做 A/B 比较。

原生基线面向原始的 `FL2VA/` 和 `Ref2VA/` 检查点树。模型各阶段被分别加载和释放，因此 33B transformer、Qwen 编码器和解码器永远不必共存于统一内存中。
