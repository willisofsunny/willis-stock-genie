from typing import Any, List, Optional

from pydantic import Field

from src.agent.mcp import MCPAgent
from src.logger import logger
from src.prompt.mcp import NEXT_STEP_PROMPT_ZN
from src.prompt.risk_control import RISK_SYSTEM_PROMPT
from src.schema import Message
from src.tool import Terminate, ToolCollection
from src.tool.risk_control import RiskControlTool


class RiskControlAgent(MCPAgent):
    """Risk analysis agent focused on identifying and quantifying investment risks."""

    name: str = "risk_control_agent"
    description: str = "Analyzes financial risks and proposes risk control strategies for stock investments."
    system_prompt: str = RISK_SYSTEM_PROMPT
    next_step_prompt: str = NEXT_STEP_PROMPT_ZN

    # Initialize with FinGenius tools with proper type annotation
    available_tools: ToolCollection = Field(
        default_factory=lambda: ToolCollection(
            RiskControlTool(),
            Terminate(),
        )
    )
    special_tool_names: List[str] = Field(default_factory=lambda: [Terminate().name])

    async def run(
        self, request: Optional[str] = None, stock_code: Optional[str] = None
    ) -> Any:
        """Run risk analysis on the given stock.

        Args:
            request: Optional initial request to process. If provided, overrides stock_code parameter.
            stock_code: The stock code/ticker to analyze

        Returns:
            Dictionary containing comprehensive risk analysis
        """
        # If stock_code is provided but request is not, create request from stock_code
        if stock_code and not request:
            # Set up system message about the stock being analyzed
            self.memory.add_message(
                Message.system_message(
                    f"你正在分析股票 {stock_code} 的风险因素。请收集相关财务数据并进行全面风险评估。"
                )
            )
            request = f"请对 {stock_code} 进行全面的风险分析。"

        # Call parent implementation with the request
        result = await super().run(request)

        # Force generate summary if no analysis found in result
        if result and isinstance(result, str):
            # Check if result contains actual analysis or just tool outputs
            if "Observed output of cmd" in result and not any(keyword in result for keyword in ["風險", "风险", "分析", "建議", "建议", "評估", "评估"]):
                logger.info(f"⚠️ {self.name} finished without generating analysis, forcing summary generation...")

                # Add a forced prompt to generate summary
                summary_prompt = """
                基於你剛才獲取的風險數據，請立即提供完整的風險評估報告，包括：
                1. 財務風險分析（負債率、現金流、財務健康度）
                2. 市場風險評估（行業風險、市場波動、系統性風險）
                3. 營運風險分析（公司治理、經營風險、產業競爭）
                4. 技術風險評估（技術面風險、支撐壓力風險）
                5. 流動性風險（成交量、換手率、流動性評估）
                6. 綜合風險評級（整體風險等級、風險因子權重）
                7. 風險控制建議（止損建議、倉位控制、對沖策略）

                請直接輸出分析內容，不要再調用工具。
                """

                self.memory.add_message(Message.user_message(summary_prompt))

                # Generate summary without tools
                summary_response = await self.llm.ask(
                    messages=self.messages,
                    system_msgs=[Message.system_message(self.system_prompt)] if self.system_prompt else None
                )

                if summary_response:
                    logger.info(f"✅ Generated forced summary for {self.name}")
                    result += f"\n\n{summary_response}"

        return result
