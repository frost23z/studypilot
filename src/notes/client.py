import json
from collections.abc import Awaitable, Callable

from langchain.mcp import MCPAdapter


def make_save_note(target) -> Callable[[str, str], Awaitable[str]]:
    """Make a function that saves a note through the notes MCP server.

    It returns a sentence for the answer and never raises.
    """

    async def save_note(title: str, content: str) -> str:
        try:
            async with MCPAdapter(target) as adapter:
                tools = {tool.name: tool for tool in await adapter.list_tools()}
                # a full tool call returns a ToolMessage with a status,
                # plain arguments return only the text
                message = await tools["add_note"].ainvoke(
                    {
                        "type": "tool_call",
                        "id": "save-note",
                        "name": "add_note",
                        "args": {"title": title, "content": content},
                    }
                )
        except Exception as error:
            return f"Saving failed: {error}"

        if message.status == "error":
            return f"Saving failed: {message.text}"
        return f"Saved as note {json.loads(message.text)['id']}: {title}"

    return save_note
