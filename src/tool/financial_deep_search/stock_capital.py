#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
獲取台股三大法人資金流向數據（台股版）
使用 FinMind 獲取外資、投信、自營商買賣超數據
"""

import json
import time
import traceback
from datetime import datetime, timedelta

try:
    from FinMind.data import DataLoader
    HAS_FINMIND = True
except ImportError:
    HAS_FINMIND = False


def fetch_institutional_capital_flow(
    stock_code=None, days=5, finmind_token="", max_retries=3, retry_delay=2
):
    """
    獲取三大法人資金流向數據（台股版）

    參數:
        stock_code: 股票代碼，如"2330"，若為 None 則獲取多檔標的
        days: 查詢最近天數
        finmind_token: FinMind API Token
        max_retries: 最大重試次數
        retry_delay: 重試延迟時間(秒)

    返回:
        dict: 包含三大法人資金流向數據的字典
    """
    if not HAS_FINMIND:
        return {"success": False, "message": "未安裝 FinMind 庫", "data": {}}

    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    date_str_start = start_date.strftime("%Y-%m-%d")
    date_str_end = end_date.strftime("%Y-%m-%d")

    for attempt in range(1, max_retries + 1):
        try:
            dl = DataLoader()
            if finmind_token:
                dl.login_by_token(api_token=finmind_token)

            if stock_code:
                df = dl.taiwan_stock_institutional_investors(
                    stock_id=stock_code,
                    start_date=date_str_start,
                    end_date=date_str_end
                )

                if df is None or df.empty:
                    if attempt < max_retries:
                        time.sleep(retry_delay)
                        continue
                    return {
                        "success": False,
                        "message": f"未獲取到 {stock_code} 的三大法人數據",
                        "data": {}
                    }

                foreign_buy = df[df["name"] == "Foreign_Investor"]["buy"].sum()
                foreign_sell = df[df["name"] == "Foreign_Investor"]["sell"].sum()
                trust_buy = df[df["name"] == "Investment_Trust"]["buy"].sum()
                trust_sell = df[df["name"] == "Investment_Trust"]["sell"].sum()
                dealer_buy = df[df["name"] == "Dealer"]["buy"].sum()
                dealer_sell = df[df["name"] == "Dealer"]["sell"].sum()

                result_data = {
                    "股票代碼": stock_code,
                    "查詢期間": f"{date_str_start} ~ {date_str_end}",
                    "外資買超張數": int(foreign_buy - foreign_sell),
                    "投信買超張數": int(trust_buy - trust_sell),
                    "自營商買超張數": int(dealer_buy - dealer_sell),
                    "三大法人合計買超": int((foreign_buy + trust_buy + dealer_buy) - (foreign_sell + trust_sell + dealer_sell)),
                    "明細": df.to_dict(orient="records")
                }

                return {
                    "success": True,
                    "message": f"成功獲取 {stock_code} 的三大法人資金流向數據",
                    "last_updated": datetime.now().isoformat(),
                    "data": result_data
                }

            else:
                top_stocks = ["2330", "2317", "2454", "3008", "2881", "2882", "2886", "2412", "2891", "6505"]
                
                stock_list = []
                for stock_id in top_stocks:
                    try:
                        df = dl.taiwan_stock_institutional_investors(
                            stock_id=stock_id,
                            start_date=date_str_start,
                            end_date=date_str_end
                        )
                        
                        if df is not None and not df.empty:
                            foreign_net = (
                                df[df["name"] == "Foreign_Investor"]["buy"].sum() -
                                df[df["name"] == "Foreign_Investor"]["sell"].sum()
                            )
                            trust_net = (
                                df[df["name"] == "Investment_Trust"]["buy"].sum() -
                                df[df["name"] == "Investment_Trust"]["sell"].sum()
                            )
                            dealer_net = (
                                df[df["name"] == "Dealer"]["buy"].sum() -
                                df[df["name"] == "Dealer"]["sell"].sum()
                            )
                            total_net = foreign_net + trust_net + dealer_net

                            stock_list.append({
                                "股票代碼": stock_id,
                                "三大法人合計買超": int(total_net),
                                "外資買超": int(foreign_net),
                                "投信買超": int(trust_net),
                                "自營商買超": int(dealer_net),
                            })
                    except Exception as e:
                        print(f"獲取 {stock_id} 數據失敗: {e}")
                        continue

                if not stock_list:
                    if attempt < max_retries:
                        time.sleep(retry_delay)
                        continue
                    return {
                        "success": False,
                        "message": "未能獲取任何股票的三大法人數據",
                        "data": {}
                    }

                stock_list.sort(key=lambda x: x["三大法人合計買超"], reverse=True)

                result_data = {
                    "查詢期間": f"{date_str_start} ~ {date_str_end}",
                    "股票列表": stock_list,
                    "總數": len(stock_list),
                    "更新時間": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }

                return {
                    "success": True,
                    "message": f"成功獲取 {len(stock_list)} 檔股票的三大法人資金流向數據",
                    "last_updated": datetime.now().isoformat(),
                    "data": result_data
                }

        except Exception as e:
            print(f"獲取三大法人資金流向數據失敗: {e} (第{attempt}次嘗試)")
            if attempt < max_retries:
                time.sleep(retry_delay)
            else:
                return {
                    "success": False,
                    "message": f"獲取失敗: {str(e)}",
                    "data": {}
                }


def get_stock_capital_flow(stock_code=None, days=5, finmind_token=""):
    """
    獲取股票三大法人資金流向數據，支持獲取列表或單只股票數據

    參數:
        stock_code: 股票代碼，如果指定，則返回單只股票數據，否則返回列表
        days: 查詢最近天數
        finmind_token: FinMind API Token

    返回:
        dict: 包含資金流向數據的字典
    """
    try:
        result = fetch_institutional_capital_flow(
            stock_code=stock_code,
            days=days,
            finmind_token=finmind_token
        )
        return result
    except Exception as e:
        error_msg = f"獲取三大法人資金流向數據時出錯: {str(e)}"
        print(error_msg)
        print(traceback.format_exc())
        return {
            "success": False,
            "message": error_msg,
            "error": traceback.format_exc(),
            "data": {},
        }


def main():
    """命令行調用入口函數"""
    import argparse

    parser = argparse.ArgumentParser(description="獲取台股三大法人資金流向數據")
    parser.add_argument("--code", type=str, help="股票代碼，不指定則獲取列表")
    parser.add_argument("--days", type=int, default=5, help="查詢最近天數，默認5")
    parser.add_argument("--token", type=str, default="", help="FinMind API Token")
    args = parser.parse_args()

    result = get_stock_capital_flow(
        stock_code=args.code,
        days=args.days,
        finmind_token=args.token
    )

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
