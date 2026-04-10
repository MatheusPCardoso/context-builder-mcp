"""MCP server instance — separado para evitar imports circulares."""

from mcp.server.fastmcp import FastMCP

mcp = FastMCP(
    "context-builder",
    description="Ferramentas para construir contexto otimizado para IA",
    version="0.1.0",
)

__all__ = ["mcp"]
