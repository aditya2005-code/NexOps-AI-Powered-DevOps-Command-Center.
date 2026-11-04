import time
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Type
from pydantic import BaseModel, Field


class ToolExecutionResult(BaseModel):
    """Encapsulates the standard outcome of any diagnostic tool execution."""
    tool_name: str
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    execution_time_seconds: float = Field(default=0.0)
    warnings: list[str] = Field(default_factory=list)


class BaseDiagnosticTool(ABC):
    """Abstract base class for all bounded, read-only diagnostic tools."""

    name: str
    description: str
    input_schema: Type[BaseModel]
    output_schema: Type[BaseModel]

    @abstractmethod
    def execute(self, **kwargs: Any) -> BaseModel:
        """Execute the diagnostic logic synchronously."""
        raise NotImplementedError

    def safe_execute(self, **kwargs: Any) -> ToolExecutionResult:
        """Safely execute the tool with validation and complete error encapsulation."""
        start = time.perf_counter()
        try:
            validated_input = self.input_schema.model_validate(kwargs)
            result_model = self.execute(**validated_input.model_dump())
            elapsed = round(time.perf_counter() - start, 4)
            return ToolExecutionResult(
                tool_name=self.name,
                success=True,
                data=result_model.model_dump(),
                execution_time_seconds=elapsed,
            )
        except Exception as exc:
            elapsed = round(time.perf_counter() - start, 4)
            return ToolExecutionResult(
                tool_name=self.name,
                success=False,
                error=f"{type(exc).__name__}: {str(exc)}",
                execution_time_seconds=elapsed,
            )

