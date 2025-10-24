import asyncio
import json
import sys
import time
from typing import Any, Dict
from datetime import datetime, timedelta

from src.logger import logger
from src.tool.base import BaseTool, ToolResult
from src.tool.taiwan_stock_data import get_taiwan_stock_provider


class TechnicalAnalysisTool(BaseTool):
    """Tool for retrieving technical data for Taiwan stocks."""

    name: str = "technical_analysis_tool"
    description: str = "獲取台股技術面數據，包括即時行情、日K線、歷史數據和籌碼資訊。支持最大重試機制，適合大模型自動調用。返回結構化字典。"
    parameters: dict = {
        "type": "object",
        "properties": {
            "stock_code": {
                "type": "string",
                "description": "台股代碼（4位數字，必填），如'2330'（台積電）、'2454'（聯發科）、'2603'（長榮）、'2891'（中信金）等",
            },
            "need_realtime": {
                "type": "boolean",
                "description": "是否獲取即時行情數據，包括最新價、漲跌幅、成交量等核心指標",
                "default": True,
            },
            "need_daily_kline": {
                "type": "boolean",
                "description": "是否獲取日K線歷史數據，包括開盤價、最高價、最低價、收盤價等OHLC數據",
                "default": True,
            },
            "need_institutional": {
                "type": "boolean",
                "description": "是否獲取三大法人買賣超數據，展示外資、投信、自營商資金動向",
                "default": True,
            },
            "need_margin_trading": {
                "type": "boolean",
                "description": "是否獲取融資融券數據，包括融資餘額、融券餘額、券資比等",
                "default": True,
            },
            "kline_days": {
                "type": "integer",
                "description": "K線數據獲取天數，範圍10-90，控制歷史數據回溯深度",
                "default": 30,
            },
            "max_retry": {
                "type": "integer",
                "description": "數據獲取最大重試次數，範圍1-5，用於處理網絡波動情況",
                "default": 3,
            },
        },
        "required": ["stock_code"],
    }

    async def execute(
        self,
        stock_code: str,
        need_realtime: bool = True,
        need_daily_kline: bool = True,
        need_institutional: bool = True,
        need_margin_trading: bool = True,
        kline_days: int = 30,
        max_retry: int = 3,
        sleep_seconds: int = 1,
        **kwargs,
    ) -> ToolResult:
        """
        Get technical data for a Taiwan stock with retry mechanism.

        Args:
            stock_code: Taiwan stock code (4 digits)
            need_realtime: Whether to get real-time quotes
            need_daily_kline: Whether to get daily K-line data
            need_institutional: Whether to get institutional investor data
            need_margin_trading: Whether to get margin trading data
            kline_days: Number of days of K-line data to retrieve
            max_retry: Maximum retry attempts
            sleep_seconds: Seconds to wait between retries
            **kwargs: Additional parameters

        Returns:
            ToolResult: Result containing technical data
        """
        try:
            # Execute synchronous operation in thread pool to avoid blocking event loop
            result = await asyncio.to_thread(
                self._get_tech_data,
                stock_code=stock_code,
                need_realtime=need_realtime,
                need_daily_kline=need_daily_kline,
                need_institutional=need_institutional,
                need_margin_trading=need_margin_trading,
                kline_days=kline_days,
                max_retry=max_retry,
                sleep_seconds=sleep_seconds,
            )

            # Check if result contains error
            if "error" in result:
                return ToolResult(error=result["error"])

            # Return success result
            return ToolResult(output=result)

        except Exception as e:
            error_msg = f"獲取技術面數據失敗: {str(e)}"
            logger.error(error_msg)
            return ToolResult(error=error_msg)

    def _get_tech_data(
        self,
        stock_code: str,
        need_realtime: bool = True,
        need_daily_kline: bool = True,
        need_institutional: bool = True,
        need_margin_trading: bool = True,
        kline_days: int = 30,
        max_retry: int = 3,
        sleep_seconds: int = 1,
    ):
        """
        Get technical data including real-time quotes, K-line data, institutional data and margin trading.
        Supports maximum retry mechanism.
        """
        for attempt in range(1, max_retry + 1):
            try:
                # Build result dictionary
                result = {
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "stock_code": stock_code,
                }

                # Get data provider
                provider = get_taiwan_stock_provider()

                # Calculate date range
                end_date = datetime.now()
                start_date = end_date - timedelta(days=kline_days)
                start_date_str = start_date.strftime("%Y-%m-%d")
                end_date_str = end_date.strftime("%Y-%m-%d")

                # 1. Get real-time quotes (from stock info)
                if need_realtime:
                    realtime_data = self._get_realtime_quotes(provider, stock_code)
                    result["realtime_quotes"] = realtime_data
                    logger.info(
                        f"[Attempt {attempt}] Retrieved real-time quotes for {stock_code}"
                    )

                # 2. Get daily K-line data
                if need_daily_kline:
                    daily_kline = self._get_daily_kline(
                        provider, stock_code, start_date_str, end_date_str
                    )
                    result["daily_kline"] = daily_kline
                    logger.info(
                        f"[Attempt {attempt}] Retrieved daily K-line data for {stock_code}"
                    )

                # 3. Get institutional investor data (台股特色)
                if need_institutional:
                    institutional_data = self._get_institutional_data(
                        provider, stock_code, start_date_str, end_date_str
                    )
                    result["institutional_investors"] = institutional_data
                    logger.info(
                        f"[Attempt {attempt}] Retrieved institutional data for {stock_code}"
                    )

                # 4. Get margin trading data (台股特色)
                if need_margin_trading:
                    margin_data = self._get_margin_trading(
                        provider, stock_code, start_date_str, end_date_str
                    )
                    result["margin_trading"] = margin_data
                    logger.info(
                        f"[Attempt {attempt}] Retrieved margin trading data for {stock_code}"
                    )

                return result

            except Exception as e:
                logger.warning(
                    f"[Attempt {attempt}] Failed to get technical data for {stock_code}: {e}"
                )
                if attempt < max_retry:
                    logger.info(f"Waiting {sleep_seconds} seconds before retry...")
                    time.sleep(sleep_seconds)
                else:
                    logger.error(f"Max retries ({max_retry}) reached, failed")
                    return {"error": f"獲取技術面數據失敗: {str(e)}"}

    @staticmethod
    def _get_realtime_quotes(provider, stock_code: str) -> Dict[str, Any]:
        """Get real-time quotes data from stock info"""
        try:
            stock_info = provider.get_stock_info(stock_code)
            if "error" in stock_info:
                return {"error": stock_info["error"]}
            return stock_info
        except Exception as e:
            logger.error(f"Failed to get real-time quotes: {e}")
            return {"error": str(e)}

    @staticmethod
    def _get_daily_kline(provider, stock_code: str, start_date: str, end_date: str) -> list:
        """Get daily K-line data"""
        try:
            kline_df = provider.get_daily_price(stock_code, start_date, end_date)

            if kline_df is not None and not kline_df.empty:
                # Convert to list of dictionaries
                return kline_df.to_dict(orient="records")
            return []
        except Exception as e:
            logger.error(f"Failed to get daily K-line data: {e}")
            return []

    @staticmethod
    def _get_institutional_data(provider, stock_code: str, start_date: str, end_date: str) -> Dict[str, Any]:
        """Get institutional investor data (三大法人)"""
        try:
            inst_df = provider.get_institutional_investors(stock_code, start_date, end_date)

            if inst_df is not None and not inst_df.empty:
                # Get latest and calculate summary
                latest = inst_df.iloc[-1] if len(inst_df) > 0 else {}
                recent_5days = inst_df.tail(5) if len(inst_df) >= 5 else inst_df

                return {
                    "latest_date": latest.get("date", ""),
                    "latest": {
                        "外資買賣超": latest.get("Foreign_Investor_BuySell", 0),
                        "投信買賣超": latest.get("Investment_Trust_BuySell", 0),
                        "自營商買賣超": latest.get("Dealer_BuySell", 0),
                    },
                    "recent_5days_total": {
                        "外資": recent_5days["Foreign_Investor_BuySell"].sum() if "Foreign_Investor_BuySell" in recent_5days else 0,
                        "投信": recent_5days["Investment_Trust_BuySell"].sum() if "Investment_Trust_BuySell" in recent_5days else 0,
                        "自營商": recent_5days["Dealer_BuySell"].sum() if "Dealer_BuySell" in recent_5days else 0,
                    },
                    "historical_data": inst_df.to_dict(orient="records")
                }
            return {"note": "無三大法人數據"}
        except Exception as e:
            logger.error(f"Failed to get institutional data: {e}")
            return {"error": str(e)}

    @staticmethod
    def _get_margin_trading(provider, stock_code: str, start_date: str, end_date: str) -> Dict[str, Any]:
        """Get margin trading data (融資融券)"""
        try:
            margin_df = provider.get_margin_trading(stock_code, start_date, end_date)

            if margin_df is not None and not margin_df.empty:
                latest = margin_df.iloc[-1] if len(margin_df) > 0 else {}

                return {
                    "latest_date": latest.get("date", ""),
                    "融資餘額": latest.get("MarginPurchaseTodayBalance", 0),
                    "融券餘額": latest.get("ShortSaleTodayBalance", 0),
                    "融資增減": latest.get("MarginPurchaseChange", 0),
                    "融券增減": latest.get("ShortSaleChange", 0),
                    "券資比": TechnicalAnalysisTool._calculate_margin_ratio(latest),
                    "historical_data": margin_df.to_dict(orient="records")
                }
            return {"note": "無融資融券數據"}
        except Exception as e:
            logger.error(f"Failed to get margin trading data: {e}")
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


if __name__ == "__main__":
    # Direct tool testing
    code = sys.argv[1] if len(sys.argv) > 1 else "2330"

    # Get technical data
    tool = TechnicalAnalysisTool()
    result = asyncio.run(tool.execute(stock_code=code))

    # Output results
    if result.error:
        print(f"Failed: {result.error}")
    else:
        output = result.output
        print(f"Success! Timestamp: {output['timestamp']}")
        print(f"Stock Code: {output['stock_code']}")

        # Check if each data item was successfully retrieved
        for key in ["realtime_quotes", "daily_kline", "institutional_investors", "margin_trading"]:
            if key in output:
                item_count = 0
                if isinstance(output[key], list):
                    item_count = len(output[key])
                    status = f"Retrieved ({item_count} items)"
                else:
                    status = "Retrieved" if output[key] else "Not Retrieved"
                print(f"- {key}: {status}")

        # Save complete results to JSON file
        filename = f"tech_data_{code}_{time.strftime('%Y%m%d_%H%M%S')}.json"
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(output, f, ensure_ascii=False, indent=2)
        print(f"\nComplete results saved to: {filename}")
