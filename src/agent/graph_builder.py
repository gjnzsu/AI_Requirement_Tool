"""Graph construction helpers for ChatbotAgent."""

from __future__ import annotations

from langgraph.graph import END, StateGraph


def build_agent_graph(
    *,
    state_type=dict,
    detect_intent,
    route_after_intent,
    handle_general_chat,
    handle_jira_creation,
    handle_evaluation,
    route_after_evaluation,
    handle_confluence_creation,
    handle_rag_query,
    handle_coze_agent,
    handle_requirement_sdlc_agent=lambda state: state,
):
    """Build and compile the LangGraph workflow for the chatbot agent."""
    graph = StateGraph(state_type)

    graph.add_node("intent_detection", detect_intent)
    graph.add_node("general_chat", handle_general_chat)
    graph.add_node("jira_creation", handle_jira_creation)
    graph.add_node("evaluation", handle_evaluation)
    graph.add_node("confluence_creation", handle_confluence_creation)
    graph.add_node("rag_query", handle_rag_query)
    graph.add_node("coze_agent", handle_coze_agent)
    graph.add_node("requirement_sdlc_agent", handle_requirement_sdlc_agent)

    graph.set_entry_point("intent_detection")
    graph.add_conditional_edges(
        "intent_detection",
        route_after_intent,
        {
            "jira_creation": "jira_creation",
            "rag_query": "rag_query",
            "general_chat": "general_chat",
            "coze_agent": "coze_agent",
            "requirement_sdlc_agent": "requirement_sdlc_agent",
            "end": END,
        },
    )

    graph.add_edge("jira_creation", "evaluation")
    graph.add_conditional_edges(
        "evaluation",
        route_after_evaluation,
        {
            "confluence_creation": "confluence_creation",
            "end": END,
        },
    )
    graph.add_edge("confluence_creation", END)
    graph.add_edge("rag_query", END)
    graph.add_edge("general_chat", END)
    graph.add_edge("coze_agent", END)
    graph.add_edge("requirement_sdlc_agent", END)

    return graph.compile()
