"""
台股三大法人分析工具
替代原有的 hot_money.py (游資分析)
"""

import asyncio
import json
from datetime import datetime, timedelta
from typing import Optional

from pydantic import Field

from src.logger import logger
from src.tool.base import BaseTool, ToolResult, get_recent_trading_day
from src.tool.taiwan_stock_data import get_taiwan_stock_provider


_INSTITUTIONAL_INVESTOR_DESCRIPTION = """
獲取台股三大法人（外資、投信、自營商）買賣超數據與分析工具。

該工具提供以下精確數據服務：
1. 外資買賣超：外資券商在台股的買賣動向與持股變化
2. 投信買賣超：國內投信基金的買賣行為與作帳特徵
3. 自營商買賣超：證券自營商的避險與套利操作
4. 三大法人合計：總體法人資金流向與市場態度
5. 歷史趨勢：近期法人買賣持續性與轉折點分析

結果以結構化JSON格式返回，包含完整的法人動態、金額統計和趨勢分析。
"""


class InstitutionalInvestorTool(BaseTool):
    """Tool for retrieving Taiwan institutional investor (三大法人) trading data."""

    name: str = "institutional_investor_tool"
    description: str = _INSTITUTIONAL_INVESTOR_DESCRIPTION
    parameters: dict = {
        "type": "object",
        "properties": {
            "stock_code": {
                "type": "string",
                "description": "台股代碼（4位數字），如'2330'（台積電）、'2454'（聯發科）等",
            },
            "days": {
                "type": "integer",
                "description": "查詢天數，預設30天",
                "default": 30,
            },
            "max_retry": {
                "type": "integer",
                "description": "數據獲取最大重試次數，範圍1-5",
                "default": 3,
            },
            "sleep_seconds": {
                "type": "integer",
                "description": "重試間隔秒數，範圍1-10",
                "default": 1,
            },
        },
        "required": ["stock_code"],
    }

    lock: asyncio.Lock = Field(default_factory=asyncio.Lock)

    async def execute(
        self,
        stock_code: str,
        days: int = 30,
        max_retry: int = 3,
        sleep_seconds: int = 1,
        **kwargs,
    ) -> ToolResult:
        """
        Execute the institutional investor data retrieval operation.

        Args:
            stock_code: Taiwan stock code, e.g. "2330"
            days: Number of days to query, default 30
            max_retry: Maximum retry attempts, default 3
            sleep_seconds: Seconds to wait between retries, default 1
            **kwargs: Additional parameters

        Returns:
            ToolResult: Unified JSON format containing institutional investor data
        """
        async with self.lock:
            try:
                # Calculate date range
                end_date = datetime.now()
                start_date = end_date - timedelta(days=days)
                start_date_str = start_date.strftime("%Y-%m-%d")
                end_date_str = end_date.strftime("%Y-%m-%d")

                result = {
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "stock_code": stock_code,
                    "date_range": {
                        "start": start_date_str,
                        "end": end_date_str,
                        "days": days
                    },
                }

                # Get institutional investor data with retry mechanism
                institutional_data = await self._get_data_with_retry(
                    lambda: self._fetch_institutional_data(stock_code, start_date_str, end_date_str),
                    "institutional_investors",
                    max_retry,
                    sleep_seconds
                )

                if institutional_data is not None and not institutional_data.empty:
                    result["institutional_investors"] = self._analyze_institutional_data(
                        institutional_data
                    )
                else:
                    result["institutional_investors"] = {"error": "無法獲取三大法人數據"}

                # Get margin trading data (optional, provides additional context)
                margin_data = await self._get_data_with_retry(
                    lambda: self._fetch_margin_data(stock_code, start_date_str, end_date_str),
                    "margin_trading",
                    max_retry,
                    sleep_seconds
                )

                if margin_data is not None and not margin_data.empty:
                    result["margin_trading"] = self._analyze_margin_data(margin_data)
                else:
                    result["margin_trading"] = {"note": "融資融券數據暫無"}

                return ToolResult(output=result)

            except Exception as e:
                error_msg = f"Failed to get institutional investor data: {str(e)}"
                logger.error(error_msg)
                return ToolResult(error=error_msg)

    def _fetch_institutional_data(self, stock_code: str, start_date: str, end_date: str):
        """Fetch institutional investor data"""
        provider = get_taiwan_stock_provider()
        return provider.get_institutional_investors(stock_code, start_date, end_date)

    def _fetch_margin_data(self, stock_code: str, start_date: str, end_date: str):
        """Fetch margin trading data"""
        provider = get_taiwan_stock_provider()
        return provider.get_margin_trading(stock_code, start_date, end_date)

    def _analyze_institutional_data(self, data) -> dict:
        """Analyze institutional investor data"""
        try:
            # Convert to dict
            data_dict = data.to_dict(orient="records")
            
            # Calculate summary statistics
            if len(data_dict) > 0:
                # Get latest data
                latest = data_dict[-1] if data_dict else {}
                
                # Calculate totals for recent period
                recent_5days = data_dict[-5:] if len(data_dict) >= 5 else data_dict
                recent_20days = data_dict[-20:] if len(data_dict) >= 20 else data_dict
                
                summary = {
                    "latest_date": latest.get("date", ""),
                    "latest_data": {
                        "外資買賣超": latest.get("Foreign_Investor_BuySell", 0),
                        "投信買賣超": latest.get("Investment_Trust_BuySell", 0),
                        "自營商買賣超": latest.get("Dealer_BuySell", 0),
                        "三大法人合計": (
                            latest.get("Foreign_Investor_BuySell", 0) +
                            latest.get("Investment_Trust_BuySell", 0) +
                            latest.get("Dealer_BuySell", 0)
                        )
                    },
                    "recent_5days_total": {
                        "外資": sum(d.get("Foreign_Investor_BuySell", 0) for d in recent_5days),
                        "投信": sum(d.get("Investment_Trust_BuySell", 0) for d in recent_5days),
                        "自營商": sum(d.get("Dealer_BuySell", 0) for d in recent_5days),
                    },
                    "recent_20days_total": {
                        "外資": sum(d.get("Foreign_Investor_BuySell", 0) for d in recent_20days),
                        "投信": sum(d.get("Investment_Trust_BuySell", 0) for d in recent_20days),
                        "自營商": sum(d.get("Dealer_BuySell", 0) for d in recent_20days),
                    },
                    "historical_data": data_dict
                }
                
                return summary
            else:
                return {"error": "無數據"}
                
        except Exception as e:
            logger.error(f"Error analyzing institutional data: {e}")
            return {"error": str(e)}

    def _analyze_margin_data(self, data) -> dict:
        """Analyze margin trading data"""
        try:
            data_dict = data.to_dict(orient="records")
            
            if len(data_dict) > 0:
                latest = data_dict[-1]
                
                return {
                    "latest_date": latest.get("date", ""),
                    "融資餘額": latest.get("MarginPurchaseTodayBalance", 0),
                    "融券餘額": latest.get("ShortSaleTodayBalance", 0),
                    "券資比": self._calculate_margin_ratio(latest),
                    "趨勢": self._analyze_margin_trend(data_dict)
                }
            else:
                return {"note": "無融資融券數據"}
                
        except Exception as e:
            logger.error(f"Error analyzing margin data: {e}")
            return {"error": str(e)}

    @staticmethod
    def _calculate_margin_ratio(latest_data: dict) -> float:
        """Calculate margin ratio (券資比)"""
        try:
            margin = latest_data.get("MarginPurchaseTodayBalance", 0)
            short = latest_data.get("ShortSaleTodayBalance", 0)
            if margin > 0:
                return round((short / margin) * 100, 2)
            return 0.0
        except:
            return 0.0

    @staticmethod
    def _analyze_margin_trend(data_list: list) -> str:
        """Analyze margin trading trend"""
        try:
            if len(data_list) < 2:
                return "數據不足"
            
            recent_margin = [d.get("MarginPurchaseTodayBalance", 0) for d in data_list[-5:]]
            if recent_margin[-1] > recent_margin[0]:
                return "融資增加"
            elif recent_margin[-1] < recent_margin[0]:
                return "融資減少"
            else:
                return "持平"
        except:
            return "分析失敗"

    @staticmethod
    async def _get_data_with_retry(func, data_name, max_retry=3, sleep_seconds=1):
        """
        Get data with retry mechanism.

        Args:
            func: Function to call
            data_name: Data name (for logging)
            max_retry: Maximum retry attempts
            sleep_seconds: Seconds to wait between retries

        Returns:
            Function return data or None
        """
        last_error = None
        for attempt in range(1, max_retry + 1):
            try:
                # Use asyncio.to_thread for synchronous operations
                data = await asyncio.to_thread(func)
                
                if data is not None:
                    logger.info(f"[{data_name}] Data retrieved successfully")
                    return data

            except Exception as e:
                last_error = str(e)
                logger.warning(f"[{data_name}][Attempt {attempt}] Failed: {e}")

                if attempt < max_retry:
                    await asyncio.sleep(sleep_seconds)
                    logger.info(f"[{data_name}] Preparing attempt {attempt+1}...")

        logger.error(
            f"[{data_name}] Max retries ({max_retry}) reached, failed: {last_error}"
        )
        return None


if __name__ == "__main__":
    import sys

    code = sys.argv[1] if len(sys.argv) > 1 else "2330"

    async def run_tool():
        tool = InstitutionalInvestorTool()
        result = await tool.execute(stock_code=code, days=30)

        if result.error:
            print(f"Failed: {result.error}")
        else:
            data = result.output
            print(f"Success! Timestamp: {data['timestamp']}")
            print(f"Stock Code: {data['stock_code']}")
            
            if "institutional_investors" in data:
                status = "Success" if "error" not in data["institutional_investors"] else "Failed"
                print(f"- Institutional Investors: {status}")
            
            if "margin_trading" in data:
                status = "Success" if "error" not in data["margin_trading"] else "Note"
                print(f"- Margin Trading: {status}")

            filename = f"institutional_data_{code}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f"\nComplete results saved to: {filename}")

    asyncio.run(run_tool())
