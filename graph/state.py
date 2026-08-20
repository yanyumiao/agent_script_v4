"""LangGraph 状态定义"""
from typing import Optional, TypedDict


class AgentState(TypedDict, total=False):
    story: str
    run_dir: str
    script: Optional[dict]
    storyboard: Optional[dict]
    characters: list[dict]
    shots: list[dict]
    final_video: str
