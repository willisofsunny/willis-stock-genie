from typing import Any, Dict
import pandas as pd
from datetime import datetime, timedelta

from src.logger import logger
from src.tool.base import BaseTool, ToolResult

try:
    from FinMind.data import DataLoader
    HAS_FINMIND = True
except ImportError:
    HAS_FINMIND = False


class BigDealAnalysisTool(BaseTool):
    """Tool for analysing big deal transactions using FinMind interfaces for Taiwan stocks."""

    name: str = "big_deal_analysis_tool"
    description: str = (
        "獲取台股市場及個股大額交易數據，並返回綜合分析結果。"
        "使用 FinMind 的大額交易與三大法人數據。"
    )
    parameters: dict = {
        "type": "object",
        "properties": {
            "stock_code": {
                "type": "string",
                "description": "股票代碼，如 '2330'，若為空代表全市場分析",
                "default": "",
            },
            "top_n": {
                "type": "integer",
                "description": "排行前 N 名股票的數據",
                "default": 10,
            },
            "days": {
                "type": "integer",
                "description": "查詢最近天數",
                "default": 5,
            },
            "finmind_token": {
                "type": "string",
                "description": "FinMind API Token (選用)",
                "default": "",
            },
        },
    }

    async def execute(
        self,
        stock_code: str = "",
        top_n: int = 10,
        days: int = 5,
        finmind_token: str = "",
        **kwargs,
    ) -> ToolResult:
        """Fetch big deal transaction data and return structured result."""
        if not HAS_FINMIND:
            return ToolResult(error="FinMind library not installed")

        try:
            result: Dict[str, Any] = {}
            dl = DataLoader()
            if finmind_token:
                dl.login_by_token(api_token=finmind_token)

            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            date_str_start = start_date.strftime("%Y-%m-%d")
            date_str_end = end_date.strftime("%Y-%m-%d")

            if stock_code:
                df_institutional = dl.taiwan_stock_institutional_investors(
                    stock_id=stock_code,
                    start_date=date_str_start,
                    end_date=date_str_end
                )

                if df_institutional is not None and not df_institutional.empty:
                    foreign_buy = df_institutional[df_institutional["name"] == "Foreign_Investor"]["buy"].sum()
                    foreign_sell = df_institutional[df_institutional["name"] == "Foreign_Investor"]["sell"].sum()
                    trust_buy = df_institutional[df_institutional["name"] == "Investment_Trust"]["buy"].sum()
                    trust_sell = df_institutional[df_institutional["name"] == "Investment_Trust"]["sell"].sum()
                    dealer_buy = df_institutional[df_institutional["name"] == "Dealer"]["buy"].sum()
                    dealer_sell = df_institutional[df_institutional["name"] == "Dealer"]["sell"].sum()

                    total_buy = foreign_buy + trust_buy + dealer_buy
                    total_sell = foreign_sell + trust_sell + dealer_sell

                    result["stock_institutional_summary"] = {
                        "stock_code": stock_code,
                        "period_days": days,
                        "total_buy_shares": int(total_buy),
                        "total_sell_shares": int(total_sell),
                        "net_buy_shares": int(total_buy - total_sell),
                        "foreign_net": int(foreign_buy - foreign_sell),
                        "trust_net": int(trust_buy - trust_sell),
                        "dealer_net": int(dealer_buy - dealer_sell),
                    }
                    result["stock_institutional_details"] = df_institutional.to_dict(orient="records")
                else:
                    result["stock_institutional_summary"] = {}
                    result["stock_institutional_details"] = []

                try:
                    df_price = dl.taiwan_stock_daily(
                        stock_id=stock_code,
                        start_date=date_str_start,
                        end_date=date_str_end
                    )
                    if df_price is not None and not df_price.empty:
                        result["stock_price_hist"] = df_price.tail(60).to_dict(orient="records")
                    else:
                        result["stock_price_hist"] = []
                except Exception as e:
                    logger.warning(f"Failed to fetch price data: {e}")
                    result["stock_price_hist"] = []

            else:
                all_stocks = ["2330", "2317", "2454", "3008", "2881", "2882", "2886", "2412", "2891", "6505"]
                
                market_summary = []
                for stock_id in all_stocks:
                    try:
                        df_inst = dl.taiwan_stock_institutional_investors(
                            stock_id=stock_id,
                            start_date=date_str_start,
                            end_date=date_str_end
                        )
                        if df_inst is not None and not df_inst.empty:
                            foreign_net = (
                                df_inst[df_inst["name"] == "Foreign_Investor"]["buy"].sum() -
                                df_inst[df_inst["name"] == "Foreign_Investor"]["sell"].sum()
                            )
                            trust_net = (
                                df_inst[df_inst["name"] == "Investment_Trust"]["buy"].sum() -
                                df_inst[df_inst["name"] == "Investment_Trust"]["sell"].sum()
                            )
                            dealer_net = (
                                df_inst[df_inst["name"] == "Dealer"]["buy"].sum() -
                                df_inst[df_inst["name"] == "Dealer"]["sell"].sum()
                            )
                            total_net = foreign_net + trust_net + dealer_net

                            market_summary.append({
                                "stock_code": stock_id,
                                "total_net_buy": int(total_net),
                                "foreign_net": int(foreign_net),
                                "trust_net": int(trust_net),
                                "dealer_net": int(dealer_net),
                            })
                    except Exception as e:
                        logger.warning(f"Failed to fetch data for {stock_id}: {e}")
                        continue

                market_df = pd.DataFrame(market_summary)
                if not market_df.empty:
                    top_inflow = market_df.nlargest(top_n, "total_net_buy")
                    top_outflow = market_df.nsmallest(top_n, "total_net_buy")

                    result["market_summary"] = {
                        "period_days": days,
                        "total_stocks_analyzed": len(market_summary),
                    }
                    result["top_net_buy"] = top_inflow.to_dict(orient="records")
                    result["top_net_sell"] = top_outflow.to_dict(orient="records")
                else:
                    result["market_summary"] = {"period_days": days, "total_stocks_analyzed": 0}
                    result["top_net_buy"] = []
                    result["top_net_sell"] = []

            return ToolResult(output=result)
        except Exception as e:
            logger.error(f"BigDealAnalysisTool error: {e}")
            return ToolResult(error=str(e))
