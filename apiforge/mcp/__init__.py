"""MCP (Model Context Protocol) integration.

This module defines the contract for MCP adapters and generators.
The actual protocol implementation is a Phase 4 deliverable; the
abstractions are stable enough that first-party plugins can already
ship adapters.
"""

from apiforge.mcp.adapter import BaseMCPAdapter
from apiforge.mcp.generator import MCPGenerator

__all__ = ["BaseMCPAdapter", "MCPGenerator"]
