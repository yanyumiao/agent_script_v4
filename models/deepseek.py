"""DeepSeek LLM 封装 + 结构化输出 schema"""
from typing import Optional

from langchain_deepseek import ChatDeepSeek
from pydantic import BaseModel, Field

import config


class Character(BaseModel):
    name: str = Field(description="角色名")
    role: str = Field(description="角色定位，如 主角/配角/旁白")
    appearance: str = Field(description="外貌与服装描述，用于文生图保持一致性")
    personality: str = Field(description="性格特征")


class Dialogue(BaseModel):
    speaker: str = Field(description="说话人，对应角色名")
    text: str = Field(description="台词")


class Scene(BaseModel):
    name: str = Field(description="场景名")
    location: str = Field(description="地点")
    time_of_day: str = Field(description="时间，如 白天/夜晚/黄昏")
    description: str = Field(description="场景视觉描述")


class Script(BaseModel):
    title: str = Field(description="漫剧标题")
    summary: str = Field(description="一句话故事梗概")
    characters: list[Character]
    scenes: list[Scene]
    dialogues: list[Dialogue]


class Shot(BaseModel):
    shot_id: int = Field(description="镜头序号，从 1 开始")
    scene_name: str = Field(description="所属场景名")
    image_prompt: str = Field(description="画面视觉描述（中文，可直接用于文生图）")
    characters: list[str] = Field(description="本镜头出场角色名列表")
    action: str = Field(description="动作描述")
    camera: str = Field(description="运镜描述，如 缓慢推进/固定机位/轻微摇镜")
    duration: float = Field(description="镜头时长（秒），建议 2~5")
    dialogue: Optional[Dialogue] = Field(default=None, description="本镜头台词，无对白则为空")


class Storyboard(BaseModel):
    shots: list[Shot]


def get_llm() -> ChatDeepSeek:
    return ChatDeepSeek(
        model=config.DEEPSEEK_MODEL,
        api_key=config.DEEPSEEK_API_KEY,
        temperature=0.7,
        # V4 默认思考模式不支持 tool_choice，需显式关闭思考才能用结构化输出
        extra_body={"thinking": {"type": "disabled"}},
    )


def structured_llm(schema):
    return get_llm().with_structured_output(schema)
