from typing import Any, List, Optional

from pydantic import Field

from src.agent.mcp import MCPAgent
from src.logger import logger
from src.prompt.mcp import NEXT_STEP_PROMPT_ZN
from src.prompt.technical_analysis import TECHNICAL_ANALYSIS_SYSTEM_PROMPT
from src.schema import Message
from src.tool import Terminate, ToolCollection
from src.tool.technical_analysis import TechnicalAnalysisTool


class TechnicalAnalysisAgent(MCPAgent):
    """Technical analysis agent applying technical indicators to stock analysis."""

    name: str = "technical_analysis_agent"
    description: str = (
        "Applies technical analysis and chart patterns to stock market analysis."
    )

    system_prompt: str = TECHNICAL_ANALYSIS_SYSTEM_PROMPT
    next_step_prompt: str = NEXT_STEP_PROMPT_ZN

    # Initialize with FinGenius tools with proper type annotation
    available_tools: ToolCollection = Field(
        default_factory=lambda: ToolCollection(
            TechnicalAnalysisTool(),
            Terminate(),
        )
    )
    special_tool_names: List[str] = Field(default_factory=lambda: [Terminate().name])

    async def run(
        self, request: Optional[str] = None, stock_code: Optional[str] = None
    ) -> Any:
        """Run technical analysis on the given stock using technical indicators.

        Args:
            request: Optional initial request to process. If provided, overrides stock_code parameter.
            stock_code: The stock code/ticker to analyze

        Returns:
            Dictionary containing technical analysis insights
        """
        # If stock_code is provided but request is not, create request from stock_code
        if stock_code and not request:
            # Set up system message about the stock being analyzed
            self.memory.add_message(
                Message.system_message(
                    f"你正在对股票 {stock_code} 进行技术面分析。请评估价格走势、图表形态和关键技术指标，形成短中期交易策略。"
                )
            )
            request = f"请分析 {stock_code} 的技术指标和图表形态。"

        # Call parent implementation with the request
        result = await super().run(request)

        # Force generate summary if no analysis found in result
        if result and isinstance(result, str):
            # Check if result contains actual analysis or just tool outputs
            if "Observed output of cmd" in result and ("趨勢" not in result and "分析" not in result and "建議" not in result):
                logger.info(f"⚠️ {self.name} finished without generating analysis, forcing summary generation...")

                # Add a强制 prompt to generate summary
                summary_prompt = """
                基於你剛才獲取的技術數據，請立即提供完整的技術分析報告，包括：
                1. 技術概述（當前技術面整體狀況）
                2. 趨勢分析（主要趨勢方向和強度）
                3. 關鍵位點（支撐位、阻力位）
                4. 技術指標解讀（RSI、MACD等）
                5. 成交量分析
                6. 籌碼面配合（三大法人、融資融券）
                7. 技術訊號總結（買賣訊號和操作提示）

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
