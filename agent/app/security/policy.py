ALLOWED_TOOLS = {

    "get_system_info",

    "docker_ps",

    "network_status",
}


def is_tool_allowed(
    tool_name: str
) -> bool:

    return (
        tool_name
        in ALLOWED_TOOLS
    )
