"""Exercise the policy independently of optional agent SDK dependencies."""

import importlib.util
from pathlib import Path
from types import SimpleNamespace

spec = importlib.util.spec_from_file_location(
    "research_policy",
    Path(__file__).parents[2] / "src/ptc_agent/agent/research_policy.py",
)
policy = importlib.util.module_from_spec(spec)
spec.loader.exec_module(policy)


def test_external_actions_and_live_data_are_not_bound():
    tools = [
        SimpleNamespace(name=name)
        for name in [
            "Bash",
            "ExecuteCode",
            "Read",
            "RunWorkflow",
            "place_order",
            "send_message",
            "schedule_wakeup",
            "get_quote",
            "get_company_overview",
        ]
    ]
    assert [t.name for t in policy.research_tools(tools)] == [
        "Bash",
        "ExecuteCode",
        "Read",
        "RunWorkflow",
    ]


def test_file_and_user_input_operations_remain_available():
    tools = [
        SimpleNamespace(name=name)
        for name in [
            "Write",
            "Edit",
            "Glob",
            "Grep",
            "AskUserQuestion",
            "TodoWrite",
            "TaskOutput",
        ]
    ]
    assert policy.research_tools(tools) == tools
