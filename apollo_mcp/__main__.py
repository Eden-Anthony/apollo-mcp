"""Entry point: python -m apollo_mcp [--debug]"""

import argparse
from .server import MCPServer


def main() -> None:
    parser = argparse.ArgumentParser(description="Apollo.io MCP Server")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging to stderr")
    args = parser.parse_args()

    server = MCPServer(debug=args.debug)
    server.run()


if __name__ == "__main__":
    main()
