import logging
from typing import Any, Dict, List, Optional
from app.agents.tools.base import BaseDiagnosticTool, ToolExecutionResult

logger = logging.getLogger("nexops.agents.tools.registry")


class DiagnosticToolRegistry:
    """Registry maintaining authorized diagnostic tools with permission boundaries."""

    def __init__(self) -> None:
        self._tools: Dict[str, BaseDiagnosticTool] = {}

    def register(self, tool: BaseDiagnosticTool) -> None:
        """Register a diagnostic tool into the runtime."""
        if not tool.name or not isinstance(tool.name, str):
            raise ValueError("Tool name must be a non-empty string")
        self._tools[tool.name] = tool
        logger.info("Registered diagnostic tool: %s", tool.name)

    def get(self, name: str) -> Optional[BaseDiagnosticTool]:
        """Retrieve tool by name."""
        return self._tools.get(name)

    def list_tools(self) -> List[Dict[str, Any]]:
        """List registered tools with metadata and parameter specifications."""
        return [
            {
                "name": t.name,
                "description": t.description,
                "input_schema": t.input_schema.model_json_schema(),
                "output_schema": t.output_schema.model_json_schema(),
            }
            for t in self._tools.values()
        ]

    def execute(self, tool_name: str, **kwargs: Any) -> ToolExecutionResult:
        """Execute a registered tool safely."""
        tool = self.get(tool_name)
        if tool is None:
            return ToolExecutionResult(
                tool_name=tool_name,
                success=False,
                error=f"Tool '{tool_name}' is not registered in NexOps diagnostic registry",
            )
        return tool.safe_execute(**kwargs)


# Global singleton registry
tool_registry = DiagnosticToolRegistry()

