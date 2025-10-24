from src.mcp.server import MCPServer
from src.tool import Terminate
from src.tool.big_deal_analysis import BigDealAnalysisTool


class BigDealAnalysisServer(MCPServer):
    def __init__(self, name: str = "BigDealAnalysisServer"):
        super().__init__(name)

    def _initialize_standard_tools(self) -> None:
        self.tools.update(
            {
                "big_deal_analysis_tool": BigDealAnalysisTool(),
                "terminate": Terminate(),
            }
        )
