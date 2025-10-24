from typing import Any, List, Optional
from pydantic import Field

from src.agent.mcp import MCPAgent
from src.logger import logger
from src.prompt.big_deal_analysis import BIG_DEAL_SYSTEM_PROMPT
from src.prompt.mcp import NEXT_STEP_PROMPT_ZN
from src.schema import Message
from src.tool import Terminate, ToolCollection
from src.tool.big_deal_analysis import BigDealAnalysisTool


class BigDealAnalysisAgent(MCPAgent):
    """大单异动分析 Agent"""

    name: str = "big_deal_analysis_agent"
    description: str = "分析市场及个股大单资金异动，为投资决策提供依据。"

    system_prompt: str = BIG_DEAL_SYSTEM_PROMPT
    next_step_prompt: str = NEXT_STEP_PROMPT_ZN

    available_tools: ToolCollection = Field(
        default_factory=lambda: ToolCollection(
            BigDealAnalysisTool(),
            Terminate(),
        )
    )
    # 限制单次观察字符，防止内存过大导致 LLM 无法响应
    max_observe: int = 10000
    special_tool_names: List[str] = Field(default_factory=lambda: [Terminate().name])

    async def run(
        self,
        request: Optional[str] = None,
        stock_code: Optional[str] = None,
    ) -> Any:
        """Run big deal analysis"""
        if stock_code and not request:
            self.memory.add_message(
                Message.system_message(
                    f"你正在分析股票 {stock_code} 的大单资金流向，请综合资金异动与价格走势给出结论。"
                )
            )
            request = f"请对 {stock_code} 进行大单异动深度分析，并生成投资建议。"

        result = await super().run(request)

        # Force generate summary if no analysis found in result
        if result and isinstance(result, str):
            # Check if result contains actual analysis or just tool outputs
            if "Observed output of cmd" in result and not any(keyword in result for keyword in ["大單", "大单", "資金", "资金", "分析", "建議", "建议"]):
                logger.info(f"⚠️ {self.name} finished without generating analysis, forcing summary generation...")

                # Add a forced prompt to generate summary
                summary_prompt = """
                基於你剛才獲取的大單交易數據，請立即提供完整的大單異動分析報告，包括：
                1. 大單交易概況（大單成交筆數、金額、占比）
                2. 主力資金流向（主力買入賣出、淨流入流出）
                3. 大單交易時機（集中交易時段、價格位置）
                4. 資金異動分析（異常資金流入、突發大單分析）
                5. 主力操作意圖（吸籌、出貨、洗盤、拉升判斷）
                6. 價格走勢關聯（大單與價格關係、成交量配合）
                7. 操作建議（基於大單異動的交易策略、跟隨或迴避建議）

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