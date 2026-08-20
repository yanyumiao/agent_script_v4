"""组装 StateGraph"""
from langgraph.graph import END, StateGraph

from graph.nodes import (
    compose,
    expand_script,
    generate_character_sheets,
    generate_scene_images,
    generate_shots,
    generate_voices,
    write_storyboard,
)
from graph.state import AgentState


def build_graph():
    graph = StateGraph(AgentState)
    graph.add_node("expand_script", expand_script)
    graph.add_node("write_storyboard", write_storyboard)
    graph.add_node("generate_character_sheets", generate_character_sheets)
    graph.add_node("generate_scene_images", generate_scene_images)
    graph.add_node("generate_shots", generate_shots)
    graph.add_node("generate_voices", generate_voices)
    graph.add_node("compose", compose)

    graph.set_entry_point("expand_script")
    graph.add_edge("expand_script", "write_storyboard")
    graph.add_edge("write_storyboard", "generate_character_sheets")
    graph.add_edge("generate_character_sheets", "generate_scene_images")
    graph.add_edge("generate_scene_images", "generate_shots")
    graph.add_edge("generate_shots", "generate_voices")
    graph.add_edge("generate_voices", "compose")
    graph.add_edge("compose", END)

    return graph.compile()
