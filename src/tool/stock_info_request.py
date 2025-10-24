import asyncio
import datetime
from typing import Any, Dict

from pydantic import Field

from src.tool.base import BaseTool, ToolResult, get_recent_trading_day
from src.tool.taiwan_stock_data import get_taiwan_stock_provider


class StockInfoResponse(ToolResult):
    """Response model for stock information, extending ToolResult."""

    output: Dict[str, Any] = Field(default_factory=dict)

    @property
    def current_trading_day(self) -> str:
        """Get the current trading day from the output."""
        return self.output.get("current_trading_day", "")

    @property
    def basic_info(self) -> Dict[str, Any]:
        """Get the basic stock information from the output."""
        return self.output.get("basic_info", {})


class StockInfoRequest(BaseTool):
    """Tool to fetch basic information about a Taiwan stock with the current trading date."""

    name: str = "stock_info_request"
    description: str = "獲取台股股票基礎資訊和當前交易日，返回JSON格式的結果。"
    parameters: Dict[str, Any] = {
        "type": "object",
        "properties": {"stock_code": {"type": "string", "description": "台股代碼（4位數字，如2330代表台積電）"}},
        "required": ["stock_code"],
    }

    MAX_RETRIES: int = 3
    RETRY_DELAY: int = 1  # seconds

    async def execute(self, stock_code: str, **kwargs) -> StockInfoResponse | None:
        """
        Execute the tool to fetch Taiwan stock information.

        Args:
            stock_code: The Taiwan stock code to query (4 digits)

        Returns:
            StockInfoResponse containing stock information and current trading date
        """
        for attempt in range(1, self.MAX_RETRIES + 1):
            try:
                # Get current trading day
                trading_day = get_recent_trading_day()

                # Fetch stock information using Taiwan stock provider
                provider = get_taiwan_stock_provider()
                basic_info = provider.get_stock_info(stock_code)
                
                # Check if there was an error
                if "error" in basic_info:
                    if attempt < self.MAX_RETRIES:
                        await asyncio.sleep(float(self.RETRY_DELAY))
                        continue
                    return StockInfoResponse(
                        error=f"獲取股票資訊失敗 ({self.MAX_RETRIES}次嘗試): {basic_info['error']}"
                    )

                # Create and return the response
                return StockInfoResponse(
                    output={
                        "current_trading_day": trading_day,
                        "basic_info": basic_info,
                    }
                )

            except Exception as e:
                if attempt < self.MAX_RETRIES:
                    await asyncio.sleep(float(self.RETRY_DELAY))
                else:
                    return StockInfoResponse(
                        error=f"獲取股票資訊失敗 ({self.MAX_RETRIES}次嘗試): {str(e)}"
                    )
        
        return None


if __name__ == "__main__":
    import json
    import sys

    # Use default stock code "2330" (TSMC) if not provided
    code = sys.argv[1] if len(sys.argv) > 1 else "2330"

    # Create and run the tool
    tool = StockInfoRequest()
    result = asyncio.run(tool.execute(code))

    # Print the result
    if result and result.error:
        print(f"Error: {result.error}")
    elif result:
        print(json.dumps(result.output, ensure_ascii=False, indent=2))
    else:
        print("No result returned")
