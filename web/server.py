#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Willis Stock Genie WebSocket 服務器
提供前端與後端 AI 分析的即時通信
"""

import asyncio
import json
import logging
import os
import sys
from datetime import datetime
from typing import Dict, Any, Optional

# 添加專案根目錄到路徑
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from src.environment.research import ResearchEnvironment
    from src.environment.battle import BattleEnvironment
    from src.schema import AgentState
    from src.agent.report import ReportAgent
    from src.utils.report_manager import report_manager
    from src.logger import logger
except ImportError as e:
    print(f"Import error: {e}")
    logger = logging.getLogger(__name__)

try:
    import websockets
    HAS_WEBSOCKETS = True
except ImportError:
    HAS_WEBSOCKETS = False
    print("警告：未安裝 websockets 庫，WebSocket 服務器功能將不可用")

try:
    from fastapi import FastAPI, WebSocket, WebSocketDisconnect
    from fastapi.staticfiles import StaticFiles
    from fastapi.responses import HTMLResponse
    HAS_FASTAPI = True
except ImportError:
    HAS_FASTAPI = False
    print("警告：未安裝 fastapi 庫，Web 服務器功能將不可用")


class WillisStockGenieWebServer:
    """Willis Stock Genie Web 服務器"""

    def __init__(self, host: str = "localhost", port: int = 8000):
        self.host = host
        self.port = port
        self.connected_clients: Dict[str, WebSocket] = {}
        self.research_env: Optional[ResearchEnvironment] = None

        # 設置日誌
        self.logger = logging.getLogger(__name__)

        if not HAS_FASTAPI:
            raise ImportError("需要安裝 fastapi 和 uvicorn: pip install fastapi uvicorn")

    async def initialize(self):
        """初始化服務器"""
        try:
            # 創建研究環境
            self.research_env = await ResearchEnvironment.create()
            self.logger.info("Willis Stock Genie Web 服務器初始化完成")
        except Exception as e:
            self.logger.error(f"服務器初始化失敗: {e}")
            raise

    async def handle_websocket(self, websocket: WebSocket, client_id: str):
        """處理 WebSocket 連接"""
        await websocket.accept()
        self.connected_clients[client_id] = websocket

        self.logger.info(f"客戶端 {client_id} 已連接")

        try:
            while True:
                # 接收前端消息
                data = await websocket.receive_text()
                message = json.loads(data)

                self.logger.info(f"收到來自 {client_id} 的消息: {message.get('type', 'unknown')}")

                # 處理不同類型的消息
                if message.get('type') == 'start_analysis':
                    await self.handle_analysis_request(websocket, message)
                elif message.get('type') == 'validate_stock':
                    await self.handle_validation_request(websocket, message)
                elif message.get('type') == 'configure_api':
                    await self.handle_api_config_request(websocket, message)
                elif message.get('type') == 'test_api':
                    await self.handle_api_test_request(websocket, message)
                else:
                    await websocket.send_json({
                        'type': 'error',
                        'message': '未知的消息類型'
                    })

        except WebSocketDisconnect:
            self.logger.info(f"客戶端 {client_id} 已斷開連接")
        except Exception as e:
            self.logger.error(f"WebSocket 處理錯誤: {e}")
        finally:
            if client_id in self.connected_clients:
                del self.connected_clients[client_id]

    async def handle_analysis_request(self, websocket: WebSocket, message: Dict[str, Any]):
        """處理完整分析請求（Research + Battle + 報告）"""
        stock_code = message.get('stock_code', '')
        max_steps = message.get('max_steps', 5)  # Increased from 3 to 5 to allow for tool call + analysis generation
        debate_rounds = message.get('debate_rounds', 2)

        if not stock_code:
            await websocket.send_json({
                'type': 'error',
                'message': '缺少股票代碼'
            })
            return

        try:
            # 發送分析開始訊息
            await websocket.send_json({
                'type': 'analysis_started',
                'stock_code': stock_code,
                'timestamp': datetime.now().isoformat()
            })

            # ========== Research 階段 ==========
            self.logger.info(f"開始 Research 階段: {stock_code}")
            await websocket.send_json({
                'type': 'phase_started',
                'phase': 'research',
                'message': '開始研究階段'
            })

            research_results = await self._run_research_phase(
                websocket, stock_code, max_steps
            )

            if not research_results:
                await websocket.send_json({
                    'type': 'error',
                    'message': '研究階段失敗'
                })
                return

            await websocket.send_json({
                'type': 'phase_completed',
                'phase': 'research',
                'message': '研究階段完成'
            })

            # ========== Battle 階段 ==========
            self.logger.info(f"開始 Battle 階段: {stock_code}")
            await websocket.send_json({
                'type': 'phase_started',
                'phase': 'battle',
                'message': '開始辯論階段'
            })

            battle_results = await self._run_battle_phase(
                websocket, research_results, max_steps, debate_rounds
            )

            await websocket.send_json({
                'type': 'phase_completed',
                'phase': 'battle',
                'message': '辯論階段完成'
            })

            # ========== 報告生成 ==========
            self.logger.info(f"生成報告: {stock_code}")
            await websocket.send_json({
                'type': 'phase_started',
                'phase': 'report',
                'message': '生成分析報告'
            })

            report_paths = await self._generate_reports(
                stock_code, research_results, battle_results
            )

            self.logger.info(f"📋 報告生成完成，準備發送 phase_completed 消息")

            # Check WebSocket connection before sending
            try:
                await websocket.send_json({
                    'type': 'phase_completed',
                    'phase': 'report',
                    'message': '報告生成完成'
                })
                self.logger.info(f"✅ phase_completed 消息已發送")
            except Exception as e:
                self.logger.error(f"發送 phase_completed 失敗: {e}")
                # Continue anyway, try to send final results

            # ========== 發送最終結果 ==========
            # Log what we're about to send
            self.logger.info(f"📤 準備發送最終結果，研究結果包含的鍵：{list(research_results.keys())}")
            for key, value in research_results.items():
                if key != 'stock_code' and key != 'basic_info':
                    if isinstance(value, dict):
                        self.logger.info(f"  - {key}: 對象 (包含 {list(value.keys())})")
                    else:
                        self.logger.info(f"  - {key}: {type(value).__name__}")

            final_results = {
                'stock_code': stock_code,
                'research': research_results,
                'battle': battle_results,
                'reports': report_paths
            }

            # Convert any non-JSON-serializable objects
            import json
            try:
                # Try to JSON serialize to check for issues
                json.dumps(final_results, default=str)
            except Exception as e:
                self.logger.warning(f"⚠️ 序列化最終結果時出現問題: {e}，正在進行轉換")
                # Convert all values to string if needed
                final_results = json.loads(json.dumps(final_results, default=str))

            # Send final results with error handling
            try:
                self.logger.info(f"🚀 開始發送 analysis_complete 消息")
                await websocket.send_json({
                    'type': 'analysis_complete',
                    'stock_code': stock_code,
                    'results': final_results,
                    'timestamp': datetime.now().isoformat()
                })
                self.logger.info(f"✅ 完整分析完成並成功發送: {stock_code}")
            except Exception as e:
                self.logger.error(f"❌ 發送 analysis_complete 失敗: {e}")
                # Even if WebSocket fails, log the completion
                self.logger.info(f"⚠️ 分析已完成但 WebSocket 發送失敗: {stock_code}")

        except Exception as e:
            self.logger.error(f"分析請求處理錯誤: {e}")
            await websocket.send_json({
                'type': 'error',
                'message': f'分析失敗: {str(e)}'
            })

    async def handle_validation_request(self, websocket: WebSocket, message: Dict[str, Any]):
        """處理股票驗證請求"""
        stock_code = message.get('stock_code', '')

        if not stock_code:
            await websocket.send_json({
                'type': 'validation_result',
                'valid': False,
                'message': '缺少股票代碼'
            })
            return

        # 簡單的股票代碼驗證邏輯
        is_valid = self.validate_stock_code(stock_code)

        if is_valid:
            # 獲取股票基本資訊 (模擬)
            stock_info = self.get_stock_info(stock_code)
            await websocket.send_json({
                'type': 'validation_result',
                'valid': True,
                'stock_info': stock_info,
                'message': '股票驗證成功'
            })
        else:
            await websocket.send_json({
                'type': 'validation_result',
                'valid': False,
                'message': '無效的股票代碼'
            })

    async def handle_api_config_request(self, websocket: WebSocket, message: Dict[str, Any]):
        """處理 API 配置請求"""
        try:
            config = message.get('config', {})
            provider = config.get('provider', 'deepseek')
            api_key = config.get('api_key', '')
            model = config.get('model', 'deepseek-chat')
            temperature = config.get('temperature', 0.7)

            if not api_key:
                await websocket.send_json({
                    'type': 'api_config_result',
                    'success': False,
                    'message': '缺少 API KEY'
                })
                return

            # 更新全局 LLM 配置
            from src.config import Config
            config_instance = Config.get_instance()
            config_instance.update_llm_config(
                provider=provider,
                api_key=api_key,
                model=model,
                temperature=temperature,
                base_url=self._get_base_url(provider)
            )

            self.logger.info(f"API 配置已更新: provider={provider}, model={model}")

            await websocket.send_json({
                'type': 'api_config_result',
                'success': True,
                'message': f'API 配置已更新: {provider}/{model}',
                'provider': provider,
                'model': model
            })
        except Exception as e:
            self.logger.error(f"API 配置更新失敗: {e}")
            await websocket.send_json({
                'type': 'api_config_result',
                'success': False,
                'message': f'API 配置更新失敗: {str(e)}'
            })

    async def handle_api_test_request(self, websocket: WebSocket, message: Dict[str, Any]):
        """測試 API KEY 是否有效"""
        try:
            config = message.get('config', {})
            provider = config.get('provider', 'deepseek')
            api_key = config.get('api_key', '')
            model = config.get('model', 'deepseek-chat')
            temperature = config.get('temperature', 0.7)

            if not api_key:
                await websocket.send_json({
                    'type': 'api_test_result',
                    'success': False,
                    'message': '缺少 API KEY'
                })
                return

            # 使用 Config 更新配置，然後測試
            from src.config import Config
            from src.llm import LLM

            try:
                # 首先更新配置
                config_instance = Config.get_instance()
                config_instance.update_llm_config(
                    provider=provider,
                    api_key=api_key,
                    model=model,
                    temperature=temperature,
                    base_url=self._get_base_url(provider)
                )

                # 清除 LLM 單例快取以使用新配置
                LLM._instances = {}

                # 創建新的 LLM 實例進行測試
                test_llm = LLM(config_name='default')

                # 簡單的測試請求（ask 方法期望 messages 是一個列表）
                test_message = "你好，請簡短回應一個字"
                messages = [{"role": "user", "content": test_message}]
                response = await test_llm.ask(messages)

                await websocket.send_json({
                    'type': 'api_test_result',
                    'success': True,
                    'message': f'API KEY 驗證成功！',
                    'response_preview': response[:100] if response else 'N/A'
                })
                self.logger.info(f"API 測試成功: {provider}/{model}")
            except Exception as test_error:
                await websocket.send_json({
                    'type': 'api_test_result',
                    'success': False,
                    'message': f'API 測試失敗: {str(test_error)}'
                })
                self.logger.error(f"API 測試失敗: {test_error}")

        except Exception as e:
            self.logger.error(f"API 測試請求處理錯誤: {e}")
            await websocket.send_json({
                'type': 'api_test_result',
                'success': False,
                'message': f'測試過程出錯: {str(e)}'
            })

    def _get_base_url(self, provider: str) -> str:
        """根據提供商返回對應的 base_url"""
        urls = {
            'deepseek': 'https://api.deepseek.com/v1',
            'gemini': 'https://generativelanguage.googleapis.com/v1beta/openai/',
            'openai': 'https://api.openai.com/v1',
        }
        return urls.get(provider, 'https://api.deepseek.com/v1')

    async def _run_research_phase(
        self,
        websocket: WebSocket,
        stock_code: str,
        max_steps: int
    ) -> Dict[str, Any]:
        """執行 Research 階段"""
        try:
            # Create a progress callback that sends WebSocket messages
            async def progress_callback(message: Dict[str, Any]):
                """Send progress updates to frontend via WebSocket"""
                try:
                    await websocket.send_json(message)
                    self.logger.info(f"Sent progress update: {message.get('agent')} - {message.get('status')}")
                except Exception as e:
                    self.logger.error(f"Failed to send progress update: {e}")

            # 創建研究環境並傳入進度回調
            research_env = await ResearchEnvironment.create(
                max_steps=max_steps,
                progress_callback=progress_callback
            )

            # 執行分析 (progress updates will be sent automatically by research_env)
            results = await research_env.run(stock_code)

            await research_env.cleanup()
            return results

        except Exception as e:
            self.logger.error(f"Research 階段錯誤: {e}")
            return {}

    async def _run_battle_phase(
        self,
        websocket: WebSocket,
        research_results: Dict[str, Any],
        max_steps: int,
        debate_rounds: int
    ) -> Dict[str, Any]:
        """執行 Battle 辯論階段"""
        try:
            # 創建辯論環境
            battle_env = await BattleEnvironment.create(
                max_steps=max_steps,
                debate_rounds=debate_rounds
            )

            # 註冊辯論 Agents
            research_env = await ResearchEnvironment.create(max_steps=max_steps)
            agent_names = [
                "sentiment_agent",
                "risk_control_agent",
                "institutional_investor_agent",
                "technical_analysis_agent",
                "chip_analysis_agent",
                "big_deal_analysis_agent",
            ]

            for name in agent_names:
                agent = research_env.get_agent(name)
                if agent:
                    agent.current_step = 0
                    agent.state = AgentState.IDLE
                    battle_env.register_agent(agent)

            # 發送辯論開始訊息
            await websocket.send_json({
                'type': 'battle_started',
                'message': f'開始 {debate_rounds} 輪辯論'
            })

            # 執行辯論
            results = await battle_env.run(research_results)

            # 發送辯論結果
            await websocket.send_json({
                'type': 'battle_results',
                'final_decision': results.get('final_decision'),
                'vote_count': results.get('vote_count'),
                'debate_rounds': results.get('debate_rounds')
            })

            await research_env.cleanup()
            await battle_env.cleanup()
            return results

        except Exception as e:
            self.logger.error(f"Battle 階段錯誤: {e}")
            return {}

    async def _generate_reports(
        self,
        stock_code: str,
        research_results: Dict[str, Any],
        battle_results: Dict[str, Any]
    ) -> Dict[str, str]:
        """生成 HTML 和 JSON 報告"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_paths = {}

        # ========== 生成 HTML 報告 (可選，允許失敗) ==========
        try:
            report_agent = await ReportAgent.create(max_steps=3)

            # 計算投票百分比
            bull_cnt = battle_results.get('vote_count', {}).get('bullish', 0)
            bear_cnt = battle_results.get('vote_count', {}).get('bearish', 0)
            total_votes = bull_cnt + bear_cnt
            bull_pct = round(bull_cnt / total_votes * 100, 1) if total_votes else 0
            bear_pct = round(bear_cnt / total_votes * 100, 1) if total_votes else 0

            html_filename = f"report_{stock_code}_{timestamp}.html"
            html_path = f"report/{html_filename}"

            html_request = f"""
            基於股票 {stock_code} 的綜合分析，生成一份美觀的 HTML 報告。

            請包含以下模塊：
            1. 標題及股票基本信息
            2. 博弈結果與投票統計
               • 最終結論：{battle_results.get('final_decision', '未知')}
               • 看漲票數：{bull_cnt}（{bull_pct}%）
               • 看跌票數：{bear_cnt}（{bear_pct}%）
            3. 研究分析結果
            4. 辯論對話過程
            5. 圖表可視化

            底部保留 AI 免責聲明。
            """

            if report_agent and report_agent.available_tools:
                await report_agent.available_tools.execute(
                    name="create_html",
                    tool_input={
                        "request": html_request,
                        "output_path": html_path,
                        "data": {
                            "stock_code": stock_code,
                            "research_results": research_results,
                            "battle_results": battle_results,
                            "timestamp": timestamp
                        }
                    }
                )
                report_paths['html'] = html_path
                self.logger.info(f"✅ HTML 報告生成成功: {html_path}")
        except Exception as e:
            self.logger.warning(f"⚠️ 生成 HTML 報告失敗（可能是 API 餘額不足）: {e}")
            self.logger.warning(f"⚠️ 將繼續生成 JSON 報告...")

        # ========== 保存 JSON 報告 (必須成功) ==========
        try:
            # 保存辯論 JSON
            debate_data = {
                "stock_code": stock_code,
                "timestamp": timestamp,
                "debate_rounds": battle_results.get("debate_rounds", 0),
                "agent_order": battle_results.get("agent_order", []),
                "debate_history": battle_results.get("debate_history", []),
                "battle_highlights": battle_results.get("battle_highlights", [])
            }

            debate_json_path = report_manager.save_debate_report(
                stock_code=stock_code,
                debate_data=debate_data,
                metadata={
                    "type": "debate_dialog",
                    "debate_rounds": battle_results.get("debate_rounds", 0),
                    "participants": len(battle_results.get("agent_order", []))
                }
            )
            report_paths['debate_json'] = str(debate_json_path) if debate_json_path else None

            # 計算 total_votes (如果 HTML 生成失敗，這裡需要重新計算)
            bull_cnt = battle_results.get('vote_count', {}).get('bullish', 0)
            bear_cnt = battle_results.get('vote_count', {}).get('bearish', 0)
            total_votes = bull_cnt + bear_cnt

            # 保存投票 JSON
            vote_data = {
                "stock_code": stock_code,
                "timestamp": timestamp,
                "final_decision": battle_results.get("final_decision", "No decision"),
                "vote_count": battle_results.get("vote_count", {}),
                "agent_order": battle_results.get("agent_order", []),
            }

            vote_json_path = report_manager.save_vote_report(
                stock_code=stock_code,
                vote_data=vote_data,
                metadata={
                    "type": "vote_results",
                    "final_decision": battle_results.get("final_decision", "No decision"),
                    "total_votes": total_votes
                }
            )
            report_paths['vote_json'] = str(vote_json_path) if vote_json_path else None

            self.logger.info(f"🎯 _generate_reports 準備返回，report_paths: {report_paths}")
            return report_paths

        except Exception as e:
            self.logger.error(f"生成 JSON 報告失敗: {e}")
            import traceback
            self.logger.error(f"完整錯誤追蹤: {traceback.format_exc()}")
            return report_paths  # 即使 JSON 失敗，也返回可能已生成的 HTML

    async def simulate_analysis_progress(self, websocket: WebSocket, stock_code: str):
        """模擬分析進度 (用於演示)"""
        agents = [
            {'id': 'sentiment', 'name': '輿情分析', 'duration': 3},
            {'id': 'risk', 'name': '風險評估', 'duration': 2},
            {'id': 'institutional_investor', 'name': '三大法人', 'duration': 4},
            {'id': 'technical', 'name': '技術分析', 'duration': 3},
            {'id': 'chip_analysis', 'name': '籌碼分析', 'duration': 3},
            {'id': 'big_deal', 'name': '大額交易', 'duration': 2}
        ]

        for agent in agents:
            # 發送 Agent 開始訊息
            await websocket.send_json({
                'type': 'agent_progress',
                'agent': agent['id'],
                'status': 'started',
                'message': f'正在分析 {agent["name"]}...'
            })

            # 模擬分析時間
            await asyncio.sleep(agent['duration'])

            # 發送 Agent 完成訊息
            await websocket.send_json({
                'type': 'agent_progress',
                'agent': agent['id'],
                'status': 'completed',
                'message': f'{agent["name"]} 分析完成'
            })

    def validate_stock_code(self, stock_code: str) -> bool:
        """驗證股票代碼格式"""
        # 台股代碼規則：4-6位數字
        import re
        return bool(re.match(r'^\d{4,6}$', stock_code))

    def get_stock_info(self, stock_code: str) -> Dict[str, Any]:
        """獲取股票基本資訊"""
        try:
            # 嘗試從真實 API 獲取數據
            from src.tool.taiwan_stock_data import get_stock_basic_info

            stock_info = get_stock_basic_info(stock_code)
            if stock_info and 'name' in stock_info:
                return {
                    'name': stock_info.get('name', '未知'),
                    'industry': stock_info.get('industry', '未知'),
                    'code': stock_code
                }
        except Exception as e:
            self.logger.warning(f"無法從 API 獲取股票資訊: {e}，使用模擬數據")

        # 備用模擬數據
        mock_stocks = {
            '2330': {'name': '台積電', 'industry': '半導體業'},
            '2317': {'name': '鴻海', 'industry': '電子零組件業'},
            '2454': {'name': '聯發科', 'industry': '半導體業'},
            '3008': {'name': '大立光', 'industry': '光學鏡頭業'},
            '2881': {'name': '富邦金', 'industry': '金融保險業'},
            '2882': {'name': '國泰金', 'industry': '金融保險業'},
            '2412': {'name': '中華電', 'industry': '通信網路業'},
            '2308': {'name': '台達電', 'industry': '電源供應器'},
            '2303': {'name': '聯電', 'industry': '半導體業'},
            '1301': {'name': '台塑', 'industry': '塑膠工業'}
        }

        stock_data = mock_stocks.get(stock_code, None)
        if stock_data:
            stock_data['code'] = stock_code
            return stock_data

        return {'name': '未知', 'industry': '未知', 'code': stock_code}

    async def broadcast(self, message: Dict[str, Any]):
        """廣播訊息給所有連接的客戶端"""
        disconnected_clients = []

        for client_id, websocket in self.connected_clients.items():
            try:
                await websocket.send_json(message)
            except Exception as e:
                self.logger.error(f"廣播訊息失敗 {client_id}: {e}")
                disconnected_clients.append(client_id)

        # 清理斷開的連接
        for client_id in disconnected_clients:
            if client_id in self.connected_clients:
                del self.connected_clients[client_id]

    async def shutdown(self):
        """關閉服務器"""
        self.logger.info("正在關閉 Willis Stock Genie Web 服務器...")

        # 關閉所有 WebSocket 連接
        for client_id, websocket in self.connected_clients.items():
            try:
                await websocket.close()
            except Exception as e:
                self.logger.error(f"關閉客戶端 {client_id} 連接失敗: {e}")

        self.connected_clients.clear()

        # 清理研究環境
        if self.research_env:
            await self.research_env.cleanup()

        self.logger.info("Willis Stock Genie Web 服務器已關閉")


# FastAPI 應用程式
if HAS_FASTAPI:
    import os

    app = FastAPI(title="Willis Stock Genie", version="1.0.0")

    # 獲取當前目錄的絕對路徑
    current_dir = os.path.dirname(os.path.abspath(__file__))

    # 掛載靜態文件（直接掛載在根路徑下的各個文件）
    # 注意：FastAPI 會優先匹配具體的路由，所以這不會影響其他端點
    from fastapi.responses import FileResponse

    @app.get("/styles.css")
    async def get_styles():
        """提供 CSS 文件"""
        return FileResponse(os.path.join(current_dir, "styles.css"))

    @app.get("/app.js")
    async def get_app_js():
        """提供原始 JS 文件"""
        return FileResponse(os.path.join(current_dir, "app.js"))

    @app.get("/app-improved.js")
    async def get_app_improved_js():
        """提供改進的 JS 文件"""
        return FileResponse(os.path.join(current_dir, "app-improved.js"))

    # 全域 WebSocket 管理器
    websocket_manager = None

    @app.on_event("startup")
    async def startup_event():
        global websocket_manager
        websocket_manager = WillisStockGenieWebServer()
        await websocket_manager.initialize()

    @app.on_event("shutdown")
    async def shutdown_event():
        global websocket_manager
        if websocket_manager:
            await websocket_manager.shutdown()

    @app.get("/", response_class=HTMLResponse)
    async def get_home():
        """提供主頁面"""
        try:
            # 獲取當前目錄
            current_dir = os.path.dirname(os.path.abspath(__file__))
            index_path = os.path.join(current_dir, "index.html")
            with open(index_path, "r", encoding="utf-8") as f:
                return f.read()
        except FileNotFoundError:
            return HTMLResponse(content="<h1>Willis Stock Genie</h1><p>前端文件未找到</p>", status_code=404)

    @app.websocket("/ws/{client_id}")
    async def websocket_endpoint(websocket: WebSocket, client_id: str):
        """WebSocket 端點"""
        global websocket_manager
        if websocket_manager:
            await websocket_manager.handle_websocket(websocket, client_id)
        else:
            await websocket.close(code=1011)  # 服務器錯誤

    @app.get("/api/health")
    async def health_check():
        """健康檢查"""
        return {"status": "healthy", "timestamp": datetime.now().isoformat()}


def main():
    """主函數"""
    import uvicorn

    if not HAS_FASTAPI:
        print("錯誤：需要安裝 fastapi 和 uvicorn")
        print("請執行: pip install fastapi uvicorn")
        return

    print("🚀 啟動 Willis Stock Genie Web 服務器")
    print(f"📱 前端訪問地址: http://localhost:8000")
    print(f"🔌 WebSocket 端點: ws://localhost:8000/ws/{{client_id}}")
    print("按 Ctrl+C 停止服務器")

    try:
        uvicorn.run(
            "server:app",
            host="localhost",
            port=8000,
            reload=True,
            log_level="info"
        )
    except KeyboardInterrupt:
        print("\n👋 服務器已停止")


if __name__ == "__main__":
    main()