import re
from typing import Any, List, Optional

from pydantic import Field

from src.agent.mcp import MCPAgent
from src.logger import logger
from src.prompt.institutional_investor import INSTITUTIONAL_INVESTOR_SYSTEM_PROMPT
from src.prompt.mcp import NEXT_STEP_PROMPT_ZN
from src.schema import Message
from src.tool import Terminate, ToolCollection
from src.tool.institutional_investor import InstitutionalInvestorTool


class InstitutionalInvestorAgent(MCPAgent):
    """Institutional investor analysis agent focused on foreign/trust/dealer trading patterns."""

    name: str = "institutional_investor_agent"
    description: str = (
        "分析三大法人（外資、投信、自營商）交易模式、持股變動與資金流向。"
    )

    system_prompt: str = INSTITUTIONAL_INVESTOR_SYSTEM_PROMPT
    next_step_prompt: str = NEXT_STEP_PROMPT_ZN

    available_tools: ToolCollection = Field(
        default_factory=lambda: ToolCollection(
            InstitutionalInvestorTool(),
            Terminate(),
        )
    )
    special_tool_names: List[str] = Field(default_factory=lambda: [Terminate().name])

    async def run(
        self, request: Optional[str] = None, stock_code: Optional[str] = None
    ) -> Any:
        """Run institutional investor analysis on the given stock.

        Args:
            request: Optional initial request to process. If provided, overrides stock_code parameter.
            stock_code: The stock code/ticker to analyze

        Returns:
            Dictionary containing institutional investor analysis
        """
        if stock_code and not request:
            self.memory.add_message(
                Message.system_message(
                    f"你正在分析股票 {stock_code} 的三大法人交易行為。請識別外資、投信、自營商的持股變動，並分析資金流向與交易模式。"
                )
            )
            request = f"請分析 {stock_code} 的三大法人交易與資金流向情況。"

        # Call parent implementation with the request
        result = await super().run(request)

        # Force generate summary if no analysis found in result
        if result and isinstance(result, str):
            # Check if result contains actual analysis or just tool outputs
            # Look for Chinese markdown headers (## 法人, ## 分析, etc.) which indicate AI analysis
            has_chinese_analysis = bool(re.search(r'##\s*[\u4e00-\u9fa5]', result))
            if "Observed output of cmd" in result and not has_chinese_analysis:
                logger.info(f"⚠️ {self.name} finished without generating analysis, forcing summary generation...")

                # Add a forced prompt to generate summary
                summary_prompt = """
                基於你剛才獲取的三大法人數據，請立即提供完整的三大法人分析報告，包括：
                1. 法人操作概況（整體法人動向總結）
                2. 外資分析（外資買賣超、持股比例、操作特徵）
                3. 投信分析（投信買賣超、作帳行為、操作特徵）
                4. 自營商分析（自營商買賣超、避險操作、操作特徵）
                5. 融資融券分析（融資餘額、融券餘額、券資比）
                6. 法人籌碼總結（三大法人同步性、市場情緒）
                7. 操作建議（基於法人動向的交易建議與風險提示）

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
