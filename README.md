## 剧本agent
剧本扩充 分镜 by deepseek
角色图 场景图 by flux
图生视频 by mini-max-h3（antirez/h3.c，BF16 未量化）

## 使用说明
1. 填 key：`cp .env.example .env`，填入 `DEEPSEEK_API_KEY`
2. 装依赖：`pip install -r requirements.txt`
3. 运行：`python main.py --story "小故事"`，成品在 `outputs/<时间戳>/final.mp4`
中断后续跑（跳过已生成产物）：`python main.py --run-dir outputs/<时间戳>`
输出结构见 `outputs/README.md`，配置见 `config.py`

