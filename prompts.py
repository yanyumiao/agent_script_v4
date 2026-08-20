"""提示词模板（DeepSeek 剧本/分镜 + FLUX 图像 + H3 运镜）"""


def expand_script(story: str) -> str:
    return f"""你是资深漫剧编剧。请把下面这段小故事扩充成一份结构化的漫剧剧本。

故事：
{story}

要求：
1. 起一个吸引人的标题。
2. 提炼出所有出场角色（含旁白），为每个角色写一句外貌/服装描述（用于后续文生图保持一致）。
3. 划分 2~4 个场景，写清地点、时间、视觉描述。
4. 写出全部对白（说话人 + 台词），对白要口语化、适合配音。
5. 内容适合做成 1 分钟以内的短漫剧。
"""


def write_storyboard(script_json: str) -> str:
    return f"""你是资深分镜师。根据下面的剧本 JSON 写出分镜脚本。

剧本 JSON：
{script_json}

要求：
1. 拆成 4~8 个镜头，shot_id 从 1 开始连续编号。
2. 每个镜头写：所属场景名、画面视觉描述（image_prompt，中文、具体、可直接用于文生图）、出场角色名列表、动作（action）、运镜（camera）、时长（duration，秒，建议 2~5）、本镜头台词（有则给 dialogue，无则留空）。
3. 台词要与剧本对白对应，逐句分配到镜头。
4. 画面描述要能体现角色外貌，便于图像生成保持角色一致。
"""


def character_sheet(character: dict) -> str:
    return (
        "角色三视图设定图，character sheet，同一角色的正面、侧面、背面三个全身立姿并排，"
        "白色背景，动漫插画风格，细节清晰，人物设计一致。\n"
        f"角色：{character['name']}，{character['appearance']}"
    )


def scene_image(shot: dict, char_descs: list[str]) -> str:
    chars = "；".join(char_descs) if char_descs else ""
    prompt = shot["image_prompt"] + "。"
    if chars:
        prompt += f"\n出场角色外貌：{chars}。"
    prompt += "\n动漫插画风格，高清，电影感构图，画面精致。"
    return prompt


def shot_motion(shot: dict) -> str:
    parts = [shot["camera"]]
    if shot.get("action"):
        parts.append(shot["action"])
    return "，".join(parts) + "，画面稳定，动作自然流畅，保持与首帧一致。"
