#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
風控數據獲取工具（台股版）
用於獲取並保存公司公告和財務相關數據
使用 FinMind 提供台股財報數據
"""

import os
import time
import traceback
from datetime import datetime

import pandas as pd

try:
    from FinMind.data import DataLoader
    HAS_FINMIND = True
except ImportError:
    HAS_FINMIND = False
    print("警告：未安裝 FinMind 庫，財務數據獲取功能將不可用")

STOCK_NAME_CACHE = {}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Referer": "https://mops.twse.com.tw/",
    "Accept": "application/json, text/javascript, */*; q=0.01",
}

import requests


def get_twse_announcements(stock_code, max_count=10, max_retries=3, retry_delay=2):
    """獲取公開資訊觀測站公告（簡化版）"""
    url = "https://mops.twse.com.tw/mops/web/ajax_t05st01"
    
    for attempt in range(1, max_retries + 1):
        try:
            params = {
                "encodeURIComponent": "1",
                "step": "1",
                "firstin": "1",
                "off": "1",
                "keyword4": stock_code,
                "code1": "",
                "TYPEK2": "",
                "checkbtn": "",
                "queryName": "co_id",
                "inpuType": "co_id",
                "TYPEK": "all",
            }
            
            resp = requests.post(url, data=params, headers=HEADERS, timeout=15)
            resp.raise_for_status()
            
            result = []
            if resp.text and len(resp.text) > 100:
                result.append({
                    "title": f"{stock_code} 公告摘要（公開資訊觀測站）",
                    "date": datetime.now().strftime("%Y-%m-%d"),
                    "content": resp.text[:1000],
                })
            
            return result[:max_count]

        except Exception as e:
            print(f"獲取公告失敗: {e} (第{attempt}次嘗試)")
            if attempt < max_retries:
                time.sleep(retry_delay)
            else:
                return []


def get_announcements_with_detail(stock_code, max_count=10):
    """獲取指定股票公告"""
    max_count = min(max_count, 10)
    
    try:
        anns = get_twse_announcements(stock_code, max_count)
        return anns
    except Exception as e:
        print(f"獲取公告標題失敗: {e}")
        print(traceback.format_exc())
        return []


def get_balance_sheet(stock_code, finmind_token=""):
    """獲取資產負債表（使用 FinMind）"""
    if not HAS_FINMIND:
        print("未安裝 FinMind 庫，無法獲取資產負債表數據")
        return pd.DataFrame()

    try:
        dl = DataLoader()
        if finmind_token:
            dl.login_by_token(api_token=finmind_token)
        
        df = dl.taiwan_stock_balance_sheet(stock_id=stock_code)
        if isinstance(df, pd.DataFrame) and not df.empty:
            return df.head(5)
        return df
    except Exception as e:
        print(f"獲取資產負債表失敗: {e}")
        return pd.DataFrame()


def get_income_statement(stock_code, finmind_token=""):
    """獲取利潤表（使用 FinMind）"""
    if not HAS_FINMIND:
        print("未安裝 FinMind 庫，無法獲取利潤表數據")
        return pd.DataFrame()

    try:
        dl = DataLoader()
        if finmind_token:
            dl.login_by_token(api_token=finmind_token)
        
        df = dl.taiwan_stock_financial_statement(stock_id=stock_code)
        if isinstance(df, pd.DataFrame) and not df.empty:
            return df.head(5)
        return df
    except Exception as e:
        print(f"獲取利潤表失敗: {e}")
        return pd.DataFrame()


def get_cash_flow(stock_code, finmind_token=""):
    """獲取現金流量表（使用 FinMind）"""
    if not HAS_FINMIND:
        print("未安裝 FinMind 庫，無法獲取現金流量表數據")
        return pd.DataFrame()

    try:
        dl = DataLoader()
        if finmind_token:
            dl.login_by_token(api_token=finmind_token)
        
        df = dl.taiwan_stock_cash_flows_statement(stock_id=stock_code)
        if isinstance(df, pd.DataFrame) and not df.empty:
            return df.head(5)
        return df
    except Exception as e:
        print(f"獲取現金流量表失敗: {e}")
        return pd.DataFrame()


def get_financial_reports(stock_code, finmind_token=""):
    """獲取財務報表數據（資產負債表、利潤表、現金流量表）"""
    if not HAS_FINMIND:
        return {"error": "未安裝 FinMind 庫，無法獲取財務報表數據"}

    try:
        print(f"獲取 {stock_code} 的財務報表數據...")
        balance_sheet = get_balance_sheet(stock_code, finmind_token)
        income_statement = get_income_statement(stock_code, finmind_token)
        cash_flow = get_cash_flow(stock_code, finmind_token)

        if (
            (isinstance(balance_sheet, pd.DataFrame) and balance_sheet.empty)
            and (isinstance(income_statement, pd.DataFrame) and income_statement.empty)
            and (isinstance(cash_flow, pd.DataFrame) and cash_flow.empty)
        ):
            return {"error": f"未能獲取到 {stock_code} 的任何財務報表數據"}

        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        financial_reports = {
            "元數據": {
                "股票代碼": stock_code,
                "數據來源": "FinMind",
                "數據獲取時間": current_time,
                "報表類型": ["資產負債表", "綜合損益表", "現金流量表"],
                "報表條目數": {
                    "資產負債表": len(balance_sheet)
                    if isinstance(balance_sheet, pd.DataFrame)
                    else 0,
                    "綜合損益表": len(income_statement)
                    if isinstance(income_statement, pd.DataFrame)
                    else 0,
                    "現金流量表": len(cash_flow)
                    if isinstance(cash_flow, pd.DataFrame)
                    else 0,
                },
            },
            "資產負債表": balance_sheet.to_dict(orient="records")
            if isinstance(balance_sheet, pd.DataFrame) and not balance_sheet.empty
            else [],
            "綜合損益表": income_statement.to_dict(orient="records")
            if isinstance(income_statement, pd.DataFrame) and not income_statement.empty
            else [],
            "現金流量表": cash_flow.to_dict(orient="records")
            if isinstance(cash_flow, pd.DataFrame) and not cash_flow.empty
            else [],
        }

        print(f"成功獲取 {stock_code} 的財務報表數據")
        return financial_reports

    except Exception as e:
        print(f"獲取財務報表數據失敗: {str(e)}")
        return {"error": f"獲取財務報表數據失敗: {str(e)}"}


def get_company_name_for_stock(stock_code, csv_path=None):
    """從CSV文件或緩存中獲取股票對應的公司名稱"""
    global STOCK_NAME_CACHE

    if stock_code in STOCK_NAME_CACHE:
        return STOCK_NAME_CACHE[stock_code]

    if csv_path is None:
        csv_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "stocks.csv"
        )
        if not os.path.exists(csv_path):
            csv_path = os.path.join(
                os.path.dirname(
                    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                ),
                "utils",
                "stocks.csv",
            )

    if not os.path.exists(csv_path):
        print(f"股票列表文件不存在: {csv_path}，將使用股票代碼作為公司名稱")
        STOCK_NAME_CACHE[stock_code] = stock_code
        return stock_code

    try:
        df = pd.read_csv(csv_path, dtype=str)

        if "股票代碼" not in df.columns or "股票名稱" not in df.columns:
            print(f"CSV文件缺少必要的列: 股票代碼, 股票名稱，將使用股票代碼作為公司名稱")
            STOCK_NAME_CACHE[stock_code] = stock_code
            return stock_code

        matched = df[df["股票代碼"] == stock_code]
        if not matched.empty:
            company_name = matched.iloc[0]["股票名稱"]
            STOCK_NAME_CACHE[stock_code] = company_name
            return company_name
        else:
            print(f"未找到股票代碼 {stock_code} 對應的公司名稱，將使用股票代碼作為公司名稱")
            STOCK_NAME_CACHE[stock_code] = stock_code
            return stock_code

    except Exception as e:
        print(f"讀取股票列表文件出錯: {e}，將使用股票代碼作為公司名稱")
        STOCK_NAME_CACHE[stock_code] = stock_code
        return stock_code


def get_all_stock_codes(csv_path=None):
    """從CSV文件獲取所有股票代碼和名稱"""
    if csv_path is None:
        csv_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "stocks.csv"
        )
        if not os.path.exists(csv_path):
            csv_path = os.path.join(
                os.path.dirname(
                    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                ),
                "utils",
                "stocks.csv",
            )

    if not os.path.exists(csv_path):
        print(f"股票列表文件不存在: {csv_path}")
        return []

    try:
        df = pd.read_csv(csv_path, dtype=str)

        if "股票代碼" not in df.columns or "股票名稱" not in df.columns:
            print(f"CSV文件缺少必要的列: 股票代碼, 股票名稱")
            return []

        stocks = []
        for _, row in df.iterrows():
            stocks.append((row["股票代碼"], row["股票名稱"]))

        print(f"從CSV文件讀取到 {len(stocks)} 只股票")
        return stocks

    except Exception as e:
        print(f"讀取股票列表文件失敗: {e}")
        return []


def get_risk_control_data(
    stock_code,
    max_count=10,
    finmind_token="",
    include_announcements=True,
    include_financial=True,
    max_retry=3,
    sleep_seconds=1,
):
    """
    獲取單只股票的風控數據（財務數據和法務公告），台股版。

    Args:
        stock_code (str): 股票代碼，如"2330"
        max_count (int, optional): 最多獲取的公告數量. Defaults to 10.
        finmind_token (str, optional): FinMind API Token. Defaults to "".
        include_announcements (bool, optional): 是否包含公告數據. Defaults to True.
        include_financial (bool, optional): 是否包含財務數據. Defaults to True.
        max_retry (int, optional): 最大重試次數. Defaults to 3.
        sleep_seconds (int, optional): 重試前等待的秒數. Defaults to 1.

    Returns:
        dict: 包含財務數據和公告數據的字典
    """
    last_exception = None
    for attempt in range(1, max_retry + 1):
        try:
            legal_data = None
            if include_announcements:
                legal_data = get_announcements_with_detail(stock_code, max_count)
            
            financial_data = None
            if include_financial:
                financial_data = get_financial_reports(stock_code, finmind_token)
            
            financial_meta = (
                financial_data.get("元數據", {}) if isinstance(financial_data, dict) else {}
            )
            return {"legal": legal_data, "financial_meta": financial_meta}
        except Exception as e:
            last_exception = str(e)
            print(f"[第{attempt}次] 獲取風控數據失敗: {e}")
            if attempt < max_retry:
                time.sleep(sleep_seconds)
                print(f"正在嘗試第{attempt + 1}次獲取...")

    print(f"獲取風控數據達到最大重試次數 {max_retry}，獲取失敗")
    return {"financial": None, "legal": None, "error": f"獲取風控數據失敗，原因: {last_exception}"}
