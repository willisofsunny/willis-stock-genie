"""
台股數據統一接口層
功能：統一封裝多個數據源，提供容錯和降級機制
作者：FinGenius Team
版本：v1.0
"""

from typing import Dict, Any, Optional, List
import pandas as pd
from datetime import datetime, timedelta
import asyncio

try:
    from FinMind.data import DataLoader
    FINMIND_AVAILABLE = True
except ImportError:
    FINMIND_AVAILABLE = False
    print("⚠️ FinMind 未安裝，部分功能將受限")

try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
except ImportError:
    YFINANCE_AVAILABLE = False
    print("⚠️ yfinance 未安裝，將無法使用備用數據源")

try:
    import twstock
    TWSTOCK_AVAILABLE = True
except ImportError:
    TWSTOCK_AVAILABLE = False


class TaiwanStockDataProvider:
    """台股數據提供者 - 統一接口"""

    def __init__(self, api_token: Optional[str] = None):
        """
        初始化台股數據提供者
        
        Args:
            api_token: FinMind API Token (可選，免費版無需)
        """
        self.primary_source = "FinMind" if FINMIND_AVAILABLE else "yfinance"
        self.api_token = api_token
        
        if FINMIND_AVAILABLE:
            self.finmind = DataLoader()
            if api_token:
                self.finmind.login_by_token(api_token=api_token)
        else:
            self.finmind = None

    def get_stock_info(self, stock_code: str) -> Dict[str, Any]:
        """
        獲取股票基本資訊
        
        Args:
            stock_code: 台股代碼 (4位數字)
            
        Returns:
            包含股票基本資訊的字典
        """
        # 驗證股票代碼格式
        if not self._validate_stock_code(stock_code):
            return {"error": f"無效的股票代碼: {stock_code}，台股代碼應為4位數字"}

        # 優先使用 FinMind
        if FINMIND_AVAILABLE and self.finmind:
            try:
                data = self.finmind.taiwan_stock_info()
                if not data.empty:
                    stock_data = data[data['stock_id'] == stock_code]
                    if not stock_data.empty:
                        return self._format_finmind_stock_info(stock_data)
            except Exception as e:
                print(f"FinMind 獲取股票資訊失敗: {e}")

        # 降級到 yfinance
        if YFINANCE_AVAILABLE:
            try:
                ticker = yf.Ticker(f"{stock_code}.TW")
                info = ticker.info
                if info and 'symbol' in info:
                    return self._format_yfinance_stock_info(info, stock_code)
            except Exception as e:
                print(f"yfinance 獲取股票資訊失敗: {e}")

        # 返回錯誤信息
        return {"error": f"無法獲取股票 {stock_code} 的基本資訊"}

    def get_institutional_investors(
        self, 
        stock_code: str, 
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> pd.DataFrame:
        """
        獲取三大法人買賣超數據
        
        Args:
            stock_code: 台股代碼
            start_date: 起始日期 (YYYY-MM-DD)
            end_date: 結束日期 (YYYY-MM-DD)
            
        Returns:
            三大法人買賣超數據的 DataFrame
        """
        if not start_date:
            start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
        if not end_date:
            end_date = datetime.now().strftime("%Y-%m-%d")

        if not FINMIND_AVAILABLE or not self.finmind:
            print("⚠️ FinMind 不可用，無法獲取三大法人數據")
            return pd.DataFrame()

        try:
            data = self.finmind.taiwan_stock_institutional_investors(
                stock_id=stock_code,
                start_date=start_date,
                end_date=end_date
            )
            return data
        except Exception as e:
            print(f"獲取三大法人數據失敗: {e}")
            return pd.DataFrame()

    def get_margin_trading(
        self,
        stock_code: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> pd.DataFrame:
        """
        獲取融資融券數據
        
        Args:
            stock_code: 台股代碼
            start_date: 起始日期
            end_date: 結束日期
            
        Returns:
            融資融券數據的 DataFrame
        """
        if not start_date:
            start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
        if not end_date:
            end_date = datetime.now().strftime("%Y-%m-%d")

        if not FINMIND_AVAILABLE or not self.finmind:
            print("⚠️ FinMind 不可用，無法獲取融資融券數據")
            return pd.DataFrame()

        try:
            data = self.finmind.taiwan_stock_margin_purchase_short_sale(
                stock_id=stock_code,
                start_date=start_date,
                end_date=end_date
            )
            return data
        except Exception as e:
            print(f"獲取融資融券數據失敗: {e}")
            return pd.DataFrame()

    def get_daily_price(
        self,
        stock_code: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> pd.DataFrame:
        """
        獲取每日股價數據
        
        Args:
            stock_code: 台股代碼
            start_date: 起始日期
            end_date: 結束日期
            
        Returns:
            每日股價數據的 DataFrame
        """
        if not start_date:
            start_date = (datetime.now() - timedelta(days=90)).strftime("%Y-%m-%d")
        if not end_date:
            end_date = datetime.now().strftime("%Y-%m-%d")

        # 優先使用 FinMind
        if FINMIND_AVAILABLE and self.finmind:
            try:
                data = self.finmind.taiwan_stock_daily(
                    stock_id=stock_code,
                    start_date=start_date,
                    end_date=end_date
                )
                if not data.empty:
                    return data
            except Exception as e:
                print(f"FinMind 獲取股價數據失敗: {e}")

        # 降級到 yfinance
        if YFINANCE_AVAILABLE:
            try:
                ticker = yf.Ticker(f"{stock_code}.TW")
                data = ticker.history(start=start_date, end=end_date)
                if not data.empty:
                    return self._format_yfinance_price_data(data, stock_code)
            except Exception as e:
                print(f"yfinance 獲取股價數據失敗: {e}")

        return pd.DataFrame()

    def get_monthly_revenue(
        self,
        stock_code: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> pd.DataFrame:
        """
        獲取月營收數據 (台股特色)
        
        Args:
            stock_code: 台股代碼
            start_date: 起始日期
            end_date: 結束日期
            
        Returns:
            月營收數據的 DataFrame
        """
        if not start_date:
            start_date = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")
        if not end_date:
            end_date = datetime.now().strftime("%Y-%m-%d")

        if not FINMIND_AVAILABLE or not self.finmind:
            print("⚠️ FinMind 不可用，無法獲取月營收數據")
            return pd.DataFrame()

        try:
            data = self.finmind.taiwan_stock_month_revenue(
                stock_id=stock_code,
                start_date=start_date,
                end_date=end_date
            )
            return data
        except Exception as e:
            print(f"獲取月營收數據失敗: {e}")
            return pd.DataFrame()

    @staticmethod
    def _validate_stock_code(code: str) -> bool:
        """驗證台股代碼格式"""
        return code.isdigit() and len(code) == 4

    @staticmethod
    def get_market(code: str) -> str:
        """判斷股票市場 (上市/上櫃)"""
        if not TaiwanStockDataProvider._validate_stock_code(code):
            return "無效代碼"

        first_digit = int(code[0])
        if first_digit in [1, 2, 3, 5, 9]:
            return "上市 (TWSE)"
        elif first_digit in [4, 6, 7, 8]:
            return "上櫃 (OTC)"
        return "未知市場"

    def _format_finmind_stock_info(self, data: pd.DataFrame) -> Dict[str, Any]:
        """格式化 FinMind 股票資訊"""
        if data.empty:
            return {}

        row = data.iloc[0]
        return {
            "股票代碼": row.get("stock_id", ""),
            "股票名稱": row.get("stock_name", ""),
            "市場別": self.get_market(row.get("stock_id", "")),
            "產業別": row.get("industry_category", ""),
            "上市日期": row.get("date", ""),
            "資料來源": "FinMind"
        }

    def _format_yfinance_stock_info(self, info: Dict[str, Any], stock_code: str) -> Dict[str, Any]:
        """格式化 yfinance 股票資訊"""
        return {
            "股票代碼": stock_code,
            "股票名稱": info.get("longName", info.get("shortName", "")),
            "市場別": self.get_market(stock_code),
            "產業別": info.get("industry", ""),
            "市價": info.get("currentPrice", info.get("regularMarketPrice", 0)),
            "市值": info.get("marketCap", 0),
            "資料來源": "yfinance"
        }

    def _format_yfinance_price_data(self, data: pd.DataFrame, stock_code: str) -> pd.DataFrame:
        """格式化 yfinance 股價數據為 FinMind 格式"""
        formatted = pd.DataFrame()
        formatted['date'] = data.index.strftime('%Y-%m-%d')
        formatted['stock_id'] = stock_code
        formatted['open'] = data['Open'].values
        formatted['high'] = data['High'].values
        formatted['low'] = data['Low'].values
        formatted['close'] = data['Close'].values
        formatted['volume'] = data['Volume'].values
        return formatted


# 全局實例
_global_provider = None

def get_taiwan_stock_provider(api_token: Optional[str] = None) -> TaiwanStockDataProvider:
    """獲取全局台股數據提供者實例"""
    global _global_provider
    if _global_provider is None:
        _global_provider = TaiwanStockDataProvider(api_token=api_token)
    return _global_provider
