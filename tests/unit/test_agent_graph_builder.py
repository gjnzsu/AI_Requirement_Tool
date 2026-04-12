from src.agent.graph_builder import build_agent_graph


def test_build_agent_graph_runs_jira_then_evaluation_then_confluence():
    calls = []

    def detect(state):
        calls.append("detect")
        state["intent"] = "jira_creation"
        return state

    def route_after_intent(state):
        return "jira_creation"

    def jira_creation(state):
        calls.append("jira")
        state["jira_result"] = {"success": True}
        return state

    def evaluation(state):
        calls.append("evaluation")
        return state

    def route_after_evaluation(state):
        return "confluence_creation"

    def confluence(state):
        calls.append("confluence")
        return state

    def general_chat(state):
        calls.append("general_chat")
        return state

    def rag_query(state):
        calls.append("rag")
        return state

    def coze_agent(state):
        calls.append("coze")
        return state

    graph = build_agent_graph(
        detect_intent=detect,
        route_after_intent=route_after_intent,
        handle_general_chat=general_chat,
        handle_jira_creation=jira_creation,
        handle_evaluation=evaluation,
        route_after_evaluation=route_after_evaluation,
        handle_confluence_creation=confluence,
        handle_rag_query=rag_query,
        handle_coze_agent=coze_agent,
    )

    result = graph.invoke({"messages": [], "user_input": "create jira"})

    assert result["jira_result"]["success"] is True
    assert calls == ["detect", "jira", "evaluation", "confluence"]


def test_build_agent_graph_routes_requirement_sdlc_agent_to_end():
    calls = []

    def detect(state):
        calls.append("detect")
        state["intent"] = "requirement_sdlc_agent"
        return state

    def route_after_intent(state):
        return "requirement_sdlc_agent"

    def general_chat(state):
        calls.append("general_chat")
        return state

    def jira_creation(state):
        calls.append("jira")
        return state

    def evaluation(state):
        calls.append("evaluation")
        return state

    def route_after_evaluation(state):
        return "end"

    def confluence(state):
        calls.append("confluence")
        return state

    def rag_query(state):
        calls.append("rag")
        return state

    def coze_agent(state):
        calls.append("coze")
        return state

    def requirement_sdlc_agent(state):
        calls.append("requirement_sdlc_agent")
        state["messages"].append("preview")
        return state

    graph = build_agent_graph(
        detect_intent=detect,
        route_after_intent=route_after_intent,
        handle_general_chat=general_chat,
        handle_jira_creation=jira_creation,
        handle_evaluation=evaluation,
        route_after_evaluation=route_after_evaluation,
        handle_confluence_creation=confluence,
        handle_rag_query=rag_query,
        handle_coze_agent=coze_agent,
        handle_requirement_sdlc_agent=requirement_sdlc_agent,
    )

    result = graph.invoke({"messages": [], "user_input": "approve"})

    assert result["messages"][-1] == "preview"
    assert calls == ["detect", "requirement_sdlc_agent"]
