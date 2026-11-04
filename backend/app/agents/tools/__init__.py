from app.agents.tools.base import BaseDiagnosticTool, ToolExecutionResult
from app.agents.tools.registry import DiagnosticToolRegistry, tool_registry
from app.agents.tools.log_analyzer import LogAnalysisTool, LogAnalysisInput, LogAnalysisOutput
from app.agents.tools.source_inspector import (
    SourceInspectionTool,
    SourceInspectionInput,
    SourceInspectionOutput,
)

# Register core diagnostic tools into default registry
tool_registry.register(LogAnalysisTool())
tool_registry.register(SourceInspectionTool())

__all__ = [
    "BaseDiagnosticTool",
    "ToolExecutionResult",
    "DiagnosticToolRegistry",
    "tool_registry",
    "LogAnalysisTool",
    "LogAnalysisInput",
    "LogAnalysisOutput",
    "SourceInspectionTool",
    "SourceInspectionInput",
    "SourceInspectionOutput",
]

