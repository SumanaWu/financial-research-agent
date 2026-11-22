"""Native tool surface for a scoped company-research turn."""

_LOCAL_TOOLS = frozenset(
    {
        "bash",
        "executecode",
        "read",
        "write",
        "edit",
        "glob",
        "grep",
        "todowrite",
        "writetodos",
        "readtodos",
        "task",
        "taskoutput",
        "runworkflow",
        "askuser",
        "askuserquestion",
        "think",
        "showwidget",
        "getpreviewurl",
        "previewurl",
    }
)


def research_tools(tools):
    """Retain local research operations; omit external actions and current feeds."""
    return [
        tool for tool in tools if tool.name.replace("_", "").lower() in _LOCAL_TOOLS
    ]
