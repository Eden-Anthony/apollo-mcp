"""MCP STDIO JSON-RPC 2.0 server for Apollo.io."""

import json
import sys
import logging
import traceback
from typing import Any, Dict, Optional, Union

from .api import ApolloClient, ApolloAPIError
from .tools import ApolloTools, get_tool_schemas


class MCPServer:
    """STDIO JSON-RPC 2.0 server implementing the Model Context Protocol."""

    def __init__(self, debug: bool = False):
        self.debug = debug
        self.initialized = False
        self.client: Optional[ApolloClient] = None
        self.tools: Optional[ApolloTools] = None
        self.logger = self._setup_logging()

        self.server_info = {
            "name": "apollo-mcp",
            "version": "0.1.0",
        }

    def _setup_logging(self) -> logging.Logger:
        logger = logging.getLogger("apollo_mcp")
        if self.debug:
            logger.setLevel(logging.DEBUG)
            handler = logging.StreamHandler(sys.stderr)
            handler.setFormatter(
                logging.Formatter("%(asctime)s %(name)s %(levelname)s %(message)s")
            )
            logger.addHandler(handler)
        else:
            logger.setLevel(logging.WARNING)
        return logger

    # ---- transport ----

    def _send(self, response: Dict[str, Any]) -> None:
        try:
            out = json.dumps(response, separators=(",", ":"))
            print(out, flush=True)
            self.logger.debug(f">>> {out}")
        except Exception as e:
            self.logger.error(f"Send error: {e}")

    def _send_error(
        self,
        request_id: Optional[Union[str, int]],
        code: int,
        message: str,
        data: Optional[Any] = None,
    ) -> None:
        err: Dict[str, Any] = {"code": code, "message": message}
        if data is not None:
            err["data"] = data
        self._send({"jsonrpc": "2.0", "id": request_id, "error": err})

    # ---- handlers ----

    def _handle_initialize(self, request: Dict[str, Any]) -> None:
        try:
            self.client = ApolloClient()
            self.tools = ApolloTools(self.client)
            self.initialized = True

            self._send(
                {
                    "jsonrpc": "2.0",
                    "id": request.get("id"),
                    "result": {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {"tools": {"listChanged": False}},
                        "serverInfo": self.server_info,
                    },
                }
            )
            self.logger.info("Initialized successfully")
        except ApolloAPIError as e:
            self._send_error(request.get("id"), -32603, f"Initialization failed: {e}")
        except Exception as e:
            self.logger.error(f"Init error: {e}")
            self._send_error(request.get("id"), -32603, f"Initialization failed: {e}")

    def _handle_tools_list(self, request: Dict[str, Any]) -> None:
        if not self.initialized:
            self._send_error(request.get("id"), -32002, "Server not initialized")
            return
        self._send(
            {
                "jsonrpc": "2.0",
                "id": request.get("id"),
                "result": {"tools": get_tool_schemas()},
            }
        )

    def _handle_tools_call(self, request: Dict[str, Any]) -> None:
        if not self.initialized or not self.tools:
            self._send_error(request.get("id"), -32002, "Server not initialized")
            return

        params = request.get("params", {})
        tool_name = params.get("name")
        tool_args = params.get("arguments", {})

        if not tool_name:
            self._send_error(request.get("id"), -32602, "Missing tool name")
            return

        try:
            result = self.tools.execute_tool(tool_name, tool_args)
            self._send(
                {
                    "jsonrpc": "2.0",
                    "id": request.get("id"),
                    "result": {
                        "content": [
                            {"type": "text", "text": json.dumps(result, indent=2)}
                        ]
                    },
                }
            )
        except ApolloAPIError as e:
            # API errors go back as tool results with isError so the LLM can see them
            self._send(
                {
                    "jsonrpc": "2.0",
                    "id": request.get("id"),
                    "result": {
                        "content": [{"type": "text", "text": str(e)}],
                        "isError": True,
                    },
                }
            )
        except ValueError as e:
            self._send_error(request.get("id"), -32602, str(e))
        except Exception as e:
            self.logger.error(f"Tool error: {e}")
            if self.debug:
                self.logger.error(traceback.format_exc())
            self._send(
                {
                    "jsonrpc": "2.0",
                    "id": request.get("id"),
                    "result": {
                        "content": [{"type": "text", "text": f"Internal error: {e}"}],
                        "isError": True,
                    },
                }
            )

    def _handle_ping(self, request: Dict[str, Any]) -> None:
        self._send({"jsonrpc": "2.0", "id": request.get("id"), "result": {}})

    # ---- dispatch ----

    def _handle_notification(self, notification: Dict[str, Any]) -> None:
        method = notification.get("method")
        if method == "notifications/initialized":
            self.logger.info("Client initialization completed")
        else:
            self.logger.debug(f"Notification: {method}")

    def _handle_request(self, request: Dict[str, Any]) -> None:
        method = request.get("method")

        if method == "initialize":
            self._handle_initialize(request)
        elif method == "tools/list":
            self._handle_tools_list(request)
        elif method == "tools/call":
            self._handle_tools_call(request)
        elif method == "ping":
            self._handle_ping(request)
        else:
            self._send_error(request.get("id"), -32601, f"Unknown method: {method}")

    # ---- main loop ----

    def run(self) -> None:
        self.logger.info("Starting Apollo MCP server...")

        try:
            for line in sys.stdin:
                line = line.strip()
                if not line:
                    continue

                try:
                    message = json.loads(line)
                    self.logger.debug(f"<<< {message}")

                    if "id" in message:
                        self._handle_request(message)
                    else:
                        self._handle_notification(message)
                except json.JSONDecodeError:
                    self._send_error(None, -32700, "Invalid JSON")
                except Exception as e:
                    self.logger.error(f"Request error: {e}")
                    if self.debug:
                        self.logger.error(traceback.format_exc())
                    self._send_error(None, -32603, f"Internal error: {e}")

        except KeyboardInterrupt:
            self.logger.info("Interrupted")
        except Exception as e:
            self.logger.error(f"Server error: {e}")
            if self.debug:
                self.logger.error(traceback.format_exc())
        finally:
            self.logger.info("Shutting down")
