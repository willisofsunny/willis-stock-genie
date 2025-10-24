from src.mcp.server import MCPServer
from src.tool import Terminate
from src.tool.chip_analysis import ChipAnalysisTool


class ChipAnalysisServer(MCPServer):
    def __init__(self, name: str = "ChipAnalysisServer"):
        super().__init__(name)

    def _initialize_standard_tools(self) -> None:
        self.tools.update(
            {
                "chip_analysis_tool": ChipAnalysisTool(),
                "terminate": Terminate(),
            }
        )
