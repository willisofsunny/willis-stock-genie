import asyncio
import sys
import time
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

import pandas as pd

from src.logger import logger
from src.tool.base import BaseTool, ToolResult, get_recent_trading_day
from src.tool.taiwan_stock_data import get_taiwan_stock_provider


class ChipAnalysisTool(BaseTool):
    """台股籌碼分析工具，分析融資融券與主力動向"""

    name: str = "chip_analysis_tool"
    description: str = "獲取台股籌碼分布數據並進行分析，包括融資融券、主力進出、籌碼集中度等。專注台股特色籌碼分析，返回結構化分析結果。"
    parameters: dict = {
        "type": "object",
        "properties": {
            "stock_code": {
                "type": "string",
                "description": "台股代碼（必填），4位數字格式，如'2330'（台積電）、'2454'（聯發科）、'2603'（長榮）等",
            },
            "analysis_days": {
                "type": "integer",
                "description": "分析天數，用於計算籌碼變化趨勢，建議30-60天",
                "default": 30,
            },
        },
        "required": ["stock_code"],
    }

    async def execute(
        self,
        stock_code: str,
        analysis_days: int = 30,
        **kwargs,
    ) -> ToolResult:
        """執行台股籌碼分析"""
        try:
            logger.info(f"開始台股籌碼分析: {stock_code}")
            
            # 計算日期範圍
            end_date = datetime.now()
            start_date = end_date - timedelta(days=analysis_days)
            start_date_str = start_date.strftime("%Y-%m-%d")
            end_date_str = end_date.strftime("%Y-%m-%d")
            
            # 獲取台股數據
            provider = get_taiwan_stock_provider()
            
            # 獲取融資融券數據
            margin_data = await self._get_margin_trading_data(
                provider, stock_code, start_date_str, end_date_str
            )
            
            # 獲取三大法人數據
            institutional_data = await self._get_institutional_data(
                provider, stock_code, start_date_str, end_date_str
            )
            
            # 獲取股票基本資訊
            stock_info = provider.get_stock_info(stock_code)
            
            # 進行籌碼分析
            analysis_result = await self._analyze_chip_data(
                margin_data, institutional_data, stock_info, analysis_days
            )
            
            result = {
                "stock_code": stock_code,
                "analysis_timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "stock_info": stock_info,
                "margin_trading": margin_data,
                "institutional_investors": institutional_data,
                "analysis": analysis_result,
            }
            
            logger.info(f"台股籌碼分析完成: {stock_code}")
            return ToolResult(output=result)
            
        except Exception as e:
            error_msg = f"籌碼分析錯誤: {str(e)}"
            logger.error(error_msg)
            return ToolResult(error=error_msg)

    async def _get_margin_trading_data(
        self, provider, stock_code: str, start_date: str, end_date: str
    ) -> Dict:
        """獲取融資融券數據"""
        try:
            df = await asyncio.to_thread(
                provider.get_margin_trading, stock_code, start_date, end_date
            )
            
            if df is not None and not df.empty:
                latest = df.iloc[-1] if len(df) > 0 else {}
                
                return {
                    "latest_date": latest.get("date", ""),
                    "latest": {
                        "融資餘額": latest.get("MarginPurchaseTodayBalance", 0),
                        "融券餘額": latest.get("ShortSaleTodayBalance", 0),
                        "融資增減": latest.get("MarginPurchaseChange", 0),
                        "融券增減": latest.get("ShortSaleChange", 0),
                        "券資比": self._calculate_margin_ratio(latest),
                    },
                    "historical_data": df.to_dict(orient="records"),
                    "data_count": len(df),
                }
            return {"note": "無融資融券數據"}
            
        except Exception as e:
            logger.error(f"獲取融資融券數據失敗: {e}")
            return {"error": str(e)}

    async def _get_institutional_data(
        self, provider, stock_code: str, start_date: str, end_date: str
    ) -> Dict:
        """獲取三大法人數據"""
        try:
            df = await asyncio.to_thread(
                provider.get_institutional_investors, stock_code, start_date, end_date
            )
            
            if df is not None and not df.empty:
                latest = df.iloc[-1] if len(df) > 0 else {}
                recent_5days = df.tail(5) if len(df) >= 5 else df
                
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
                    "historical_data": df.to_dict(orient="records"),
                    "data_count": len(df),
                }
            return {"note": "無三大法人數據"}
            
        except Exception as e:
            logger.error(f"獲取三大法人數據失敗: {e}")
            return {"error": str(e)}

    async def _analyze_chip_data(
        self, margin_data: Dict, institutional_data: Dict, stock_info: Dict, analysis_days: int
    ) -> Dict:
        """分析台股籌碼數據"""
        try:
            current_price = stock_info.get("市價", 0)
            
            # 融資融券分析
            margin_analysis = self._analyze_margin_trading(margin_data, current_price)
            
            # 三大法人分析
            institutional_analysis = self._analyze_institutional(institutional_data)
            
            # 籌碼集中度分析
            concentration_analysis = self._analyze_concentration(
                margin_data, institutional_data
            )
            
            # 台股特色分析
            taiwan_special = self._taiwan_stock_special_analysis(
                margin_data, institutional_data
            )
            
            # 交易信號
            trading_signals = self._generate_trading_signals(
                margin_analysis, institutional_analysis, concentration_analysis
            )
            
            return {
                "margin_analysis": margin_analysis,
                "institutional_analysis": institutional_analysis,
                "concentration_analysis": concentration_analysis,
                "taiwan_special": taiwan_special,
                "trading_signals": trading_signals,
            }
            
        except Exception as e:
            logger.error(f"籌碼分析失敗: {e}")
            return {"error": str(e)}

    def _analyze_margin_trading(self, margin_data: Dict, current_price: float) -> Dict:
        """分析融資融券"""
        try:
            if "error" in margin_data or "note" in margin_data:
                return {"note": "融資融券數據不足"}
            
            latest = margin_data.get("latest", {})
            margin_balance = latest.get("融資餘額", 0)
            short_balance = latest.get("融券餘額", 0)
            margin_change = latest.get("融資增減", 0)
            ratio = latest.get("券資比", 0)
            
            # 分析融資使用率與風險
            analysis = []
            if ratio > 50:
                analysis.append("券資比偏高，市場看空氣氛濃厚")
            elif ratio < 20:
                analysis.append("券資比偏低，市場看多氣氛較強")
            
            if margin_change > 0:
                analysis.append("融資增加，散戶追高跡象")
            elif margin_change < 0:
                analysis.append("融資減少，散戶獲利了結或停損")
            
            return {
                "融資餘額": margin_balance,
                "融券餘額": short_balance,
                "券資比": ratio,
                "融資趨勢": "增加" if margin_change > 0 else "減少",
                "風險評估": self._evaluate_margin_risk(ratio, margin_balance),
                "analysis": " | ".join(analysis) if analysis else "籌碼中性",
            }
            
        except Exception as e:
            logger.error(f"融資融券分析失敗: {e}")
            return {"error": str(e)}

    def _analyze_institutional(self, institutional_data: Dict) -> Dict:
        """分析三大法人"""
        try:
            if "error" in institutional_data or "note" in institutional_data:
                return {"note": "三大法人數據不足"}
            
            latest = institutional_data.get("latest", {})
            recent_5days = institutional_data.get("recent_5days_total", {})
            
            foreign = latest.get("外資買賣超", 0)
            trust = latest.get("投信買賣超", 0)
            dealer = latest.get("自營商買賣超", 0)
            total = foreign + trust + dealer
            
            # 分析法人態度
            analysis = []
            if foreign > 0:
                analysis.append("外資買超，國際資金看好")
            elif foreign < 0:
                analysis.append("外資賣超，需注意資金外流")
            
            if trust > 0:
                analysis.append("投信買超，本土法人看好")
            
            if total > 0:
                analysis.append("三大法人合計買超，籌碼偏多")
            elif total < 0:
                analysis.append("三大法人合計賣超，籌碼偏空")
            
            return {
                "外資態度": "買超" if foreign > 0 else "賣超",
                "投信態度": "買超" if trust > 0 else "賣超",
                "自營商態度": "買超" if dealer > 0 else "賣超",
                "三大法人合計": total,
                "近5日累計": recent_5days,
                "法人共識": self._evaluate_institutional_consensus(foreign, trust, dealer),
                "analysis": " | ".join(analysis) if analysis else "法人態度中性",
            }
            
        except Exception as e:
            logger.error(f"三大法人分析失敗: {e}")
            return {"error": str(e)}

    def _analyze_concentration(self, margin_data: Dict, institutional_data: Dict) -> Dict:
        """分析籌碼集中度"""
        try:
            # 根據融資融券和法人動向評估籌碼集中度
            margin_ratio = margin_data.get("latest", {}).get("券資比", 0)
            inst_total = institutional_data.get("latest", {})
            
            if inst_total:
                foreign = inst_total.get("外資買賣超", 0)
                trust = inst_total.get("投信買賣超", 0)
                
                # 簡單評估
                if abs(foreign) > 1000 or abs(trust) > 500:
                    level = "主力高度介入"
                elif abs(foreign) > 500 or abs(trust) > 200:
                    level = "主力中度介入"
                else:
                    level = "籌碼分散"
            else:
                level = "無法評估"
            
            return {
                "concentration_level": level,
                "main_participation": "積極" if abs(foreign) > 1000 else "觀望",
                "analysis": f"籌碼狀態：{level}",
            }
            
        except Exception as e:
            logger.error(f"籌碼集中度分析失敗: {e}")
            return {"error": str(e)}

    def _taiwan_stock_special_analysis(
        self, margin_data: Dict, institutional_data: Dict
    ) -> Dict:
        """台股特色分析"""
        try:
            features = []
            
            # 外資影響力
            foreign = institutional_data.get("latest", {}).get("外資買賣超", 0)
            if abs(foreign) > 1000:
                features.append("外資主導明顯")
            
            # 融資風險
            margin_ratio = margin_data.get("latest", {}).get("券資比", 0)
            if margin_ratio > 60:
                features.append("高券資比，軋空風險")
            
            # 投信作帳
            trust = institutional_data.get("latest", {}).get("投信買賣超", 0)
            current_month = datetime.now().month
            if current_month in [3, 6, 9, 12] and trust > 500:
                features.append("季底投信作帳跡象")
            
            return {
                "features": features,
                "external_influence": "高" if abs(foreign) > 1000 else "中",
                "margin_risk": "高" if margin_ratio > 60 else "低",
                "analysis": " | ".join(features) if features else "無明顯特徵",
            }
            
        except Exception as e:
            logger.error(f"台股特色分析失敗: {e}")
            return {"error": str(e)}

    def _generate_trading_signals(
        self, margin: Dict, institutional: Dict, concentration: Dict
    ) -> Dict:
        """生成交易信號"""
        try:
            signals = {
                "buy_signals": [],
                "sell_signals": [],
                "risk_warnings": [],
            }
            
            # 買入信號
            inst_total = institutional.get("三大法人合計", 0)
            if inst_total > 500:
                signals["buy_signals"].append("三大法人大幅買超")
            
            margin_ratio = margin.get("券資比", 0)
            if margin_ratio > 60:
                signals["buy_signals"].append("高券資比，潛在軋空行情")
            
            # 賣出信號
            if inst_total < -500:
                signals["sell_signals"].append("三大法人大幅賣超")
            
            margin_balance = margin.get("融資餘額", 0)
            if margin_balance > 0 and margin.get("融資趨勢") == "增加":
                signals["sell_signals"].append("融資持續增加，散戶追高")
            
            # 風險警示
            if margin_ratio > 70:
                signals["risk_warnings"].append("券資比過高，注意軋空風險")
            
            if inst_total < -1000:
                signals["risk_warnings"].append("法人大幅賣超，資金外流風險")
            
            return signals
            
        except Exception as e:
            logger.error(f"交易信號生成失敗: {e}")
            return {"error": str(e)}

    @staticmethod
    def _calculate_margin_ratio(latest_data: dict) -> float:
        """計算券資比"""
        try:
            margin = latest_data.get("MarginPurchaseTodayBalance", 0)
            short = latest_data.get("ShortSaleTodayBalance", 0)
            if margin > 0:
                return round((short / margin) * 100, 2)
            return 0.0
        except:
            return 0.0

    @staticmethod
    def _evaluate_margin_risk(ratio: float, balance: float) -> str:
        """評估融資風險"""
        if ratio > 60:
            return "高風險（軋空可能）"
        elif ratio > 40:
            return "中度風險"
        else:
            return "低風險"

    @staticmethod
    def _evaluate_institutional_consensus(foreign: float, trust: float, dealer: float) -> str:
        """評估法人共識"""
        buy_count = sum([1 for x in [foreign, trust, dealer] if x > 0])
        sell_count = sum([1 for x in [foreign, trust, dealer] if x < 0])
        
        if buy_count >= 2:
            return "買超共識"
        elif sell_count >= 2:
            return "賣超共識"
        else:
            return "法人分歧"


if __name__ == "__main__":
    # 測試工具
    code = sys.argv[1] if len(sys.argv) > 1 else "2330"

    async def run_tool():
        tool = ChipAnalysisTool()
        result = await tool.execute(stock_code=code, analysis_days=30)

        if result.error:
            print(f"失敗: {result.error}")
        else:
            import json
            print(json.dumps(result.output, ensure_ascii=False, indent=2))

    asyncio.run(run_tool())
