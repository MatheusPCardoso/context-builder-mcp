"""Servidor MCP — entry point principal."""

import argparse
import sys
import anyio
from mcp.server.stdio import stdio_server

from . import tools  # noqa: F401 — registra os decoradores
from .context import mcp


def run_stdio() -> None:
    """Roda o servidor via stdio (padrão para uso com Claude Desktop, Kiro, etc.)."""
    async def _run() -> None:
        async with stdio_server() as streams:
            await mcp._mcp_server.run(
                streams[0],
                streams[1],
                mcp._mcp_server.create_initialization_options(),
            )
    anyio.run(_run)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="context-builder: Ferramentas para contexto com IA")
    parser.add_argument(
        "--transport",
        choices=["stdio"],
        default="stdio",
        help="Tipo de transporte (padrão: stdio)",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        if args.transport == "stdio":
            run_stdio()
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"Erro: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
