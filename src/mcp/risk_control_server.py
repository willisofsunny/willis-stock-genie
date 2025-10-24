from src.mcp.server import MCPServer
from src.tool import Terminate
from src.tool.risk_control import RiskControlTool


class RiskControlServer(MCPServer):
    def __init__(self, name: str = "RiskControlServer"):
        super().__init__(name)

    def _initialize_standard_tools(self) -> None:
        self.tools.update(
            {
                "risk_control_tool": RiskControlTool(),
                "terminate": Terminate(),
            }
        )
