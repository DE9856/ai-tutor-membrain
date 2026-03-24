from mcp import ClientSession, StdioServerParameters
import asyncio


class MembrainClient:
    def __init__(self):
        self.session = None

    async def connect(self):
        params = StdioServerParameters(
            command="membrain",  # Membrain MCP server command
            args=[]
        )

        self.session = await ClientSession.create(params)

    async def add_memory(self, content: str):
        result = await self.session.call_tool(
            "membrain_add",
            {"content": content}
        )
        return result

    async def search_memory(self, query: str):
        result = await self.session.call_tool(
            "membrain_search",
            {"query": query}
        )
        return result