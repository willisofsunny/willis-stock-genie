import asyncio
from typing import Any, Dict

from pydantic import Field

from src.agent.chip_analysis import ChipAnalysisAgent
from src.agent.institutional_investor import InstitutionalInvestorAgent
from src.agent.risk_control import RiskControlAgent
from src.agent.sentiment import SentimentAgent
from src.agent.technical_analysis import TechnicalAnalysisAgent
from src.agent.big_deal_analysis import BigDealAnalysisAgent
from src.environment.base import BaseEnvironment
from src.logger import logger
from src.schema import Message
from src.tool.stock_info_request import StockInfoRequest
from src.utils.report_manager import report_manager


class ResearchEnvironment(BaseEnvironment):
    """Environment for stock research using multiple specialized agents."""

    name: str = Field(default="research_environment")
    description: str = Field(default="Environment for comprehensive stock research")
    results: Dict[str, Any] = Field(default_factory=dict)
    max_steps: int = Field(default=3, description="Maximum steps for each agent")
    progress_callback: Any = Field(default=None, description="Callback function for progress updates")

    # Analysis mapping for agent roles
    analysis_mapping: Dict[str, str] = Field(
        default={
            "sentiment_agent": "sentiment",
            "risk_control_agent": "risk",
            "institutional_investor_agent": "institutional_investor",
            "technical_analysis_agent": "technical",
            "chip_analysis_agent": "chip_analysis",
            "big_deal_analysis_agent": "big_deal",
        }
    )

    async def initialize(self) -> None:
        """Initialize the research environment with specialized agents."""
        await super().initialize()

        # Create specialized analysis agents
        specialized_agents = {
            "sentiment_agent": await SentimentAgent.create(max_steps=self.max_steps),
            "risk_control_agent": await RiskControlAgent.create(max_steps=self.max_steps),
            "institutional_investor_agent": await InstitutionalInvestorAgent.create(max_steps=self.max_steps),
            "technical_analysis_agent": await TechnicalAnalysisAgent.create(max_steps=self.max_steps),
            "chip_analysis_agent": await ChipAnalysisAgent.create(max_steps=self.max_steps),
            "big_deal_analysis_agent": await BigDealAnalysisAgent.create(max_steps=self.max_steps),
        }

        # Register all agents
        for agent in specialized_agents.values():
            self.register_agent(agent)

        logger.info(f"Research environment initialized with 6 specialist agents (max_steps={self.max_steps})")

    async def run(self, stock_code: str) -> Dict[str, Any]:
        """Run research on the given stock code using all specialist agents."""
        logger.info(f"Running research on stock {stock_code}")

        try:
            # 獲取股票基本資訊
            basic_info_tool = StockInfoRequest()
            basic_info_result = await basic_info_tool.execute(stock_code=stock_code)

            if basic_info_result.error:
                logger.error(f"Error getting basic info: {basic_info_result.error}")
            else:
                # 將基本資訊添加到每個agent的上下文中
                stock_info_message = f"""
                股票代碼: {stock_code}
                當前交易日: {basic_info_result.output.get('current_trading_day', '未知')}
                基本資訊: {basic_info_result.output.get('basic_info', '{}')}
                """

                for agent_key in self.analysis_mapping.keys():
                    agent = self.get_agent(agent_key)
                    if agent and hasattr(agent, "memory"):
                        agent.memory.add_message(
                            Message.system_message(stock_info_message)
                        )
                        logger.info(f"Added basic stock info to {agent_key}'s context")

            # Run analysis tasks sequentially with 3-second intervals
            results = {}
            agent_count = 0
            total_agents = len([k for k in self.analysis_mapping.keys() if k in self.agents])
            
            # Import visualizer for progress display
            try:
                from src.console import visualizer
                show_visual = True
            except:
                show_visual = False
            
            for agent_key, result_key in self.analysis_mapping.items():
                if agent_key not in self.agents:
                    continue

                agent_count += 1
                logger.info(f"🔄 Starting analysis with {agent_key} ({agent_count}/{total_agents})")

                # Show agent starting in terminal
                if show_visual:
                    visualizer.show_agent_starting(agent_key, agent_count, total_agents)

                # Send WebSocket progress update - agent started
                if self.progress_callback:
                    try:
                        await self.progress_callback({
                            'type': 'agent_progress',
                            'agent': result_key,
                            'status': 'started',
                            'message': f'{result_key} 分析中...',
                            'progress': int((agent_count - 1) / total_agents * 70)  # Research phase is 0-70%
                        })
                    except Exception as e:
                        logger.warning(f"Failed to send progress callback: {e}")

                try:
                    # Run individual agent
                    result = await self.agents[agent_key].run(stock_code)

                    # Extract tool output data if available
                    agent = self.agents[agent_key]
                    tool_data = None

                    # Try to get the last tool result from agent's memory
                    if hasattr(agent, 'memory') and hasattr(agent.memory, 'messages'):
                        for msg in reversed(agent.memory.messages):
                            if hasattr(msg, 'tool_call_results') and msg.tool_call_results:
                                for tool_result in msg.tool_call_results:
                                    if tool_result.output:
                                        tool_data = tool_result.output
                                        break
                                if tool_data:
                                    break

                    # Extract clean AI analysis from result
                    clean_analysis = self._extract_ai_analysis(result)

                    # Store as consistent object format (always object, never just string)
                    results[result_key] = {
                        'agent_output': clean_analysis,
                        'raw_output': result,
                        'tool_data': tool_data
                    }

                    logger.info(f"✅ Completed analysis with {agent_key}")

                    # Show agent completion in terminal
                    if show_visual:
                        visualizer.show_agent_completed(agent_key, agent_count, total_agents)

                    # Send WebSocket progress update - agent completed
                    if self.progress_callback:
                        try:
                            await self.progress_callback({
                                'type': 'agent_progress',
                                'agent': result_key,
                                'status': 'completed',
                                'message': f'{result_key} 分析完成',
                                'progress': int(agent_count / total_agents * 70)  # Research phase is 0-70%
                            })
                        except Exception as e:
                            logger.warning(f"Failed to send progress callback: {e}")

                    # Wait 3 seconds before next agent (except for the last one)
                    if agent_count < total_agents:
                        logger.info(f"⏳ Waiting 3 seconds before next agent...")
                        if show_visual:
                            visualizer.show_waiting_next_agent(3)
                        await asyncio.sleep(3)

                except Exception as e:
                    logger.error(f"❌ Error with {agent_key}: {str(e)}")
                    results[result_key] = f"Error: {str(e)}"

                    # Send WebSocket progress update - agent error
                    if self.progress_callback:
                        try:
                            await self.progress_callback({
                                'type': 'agent_progress',
                                'agent': result_key,
                                'status': 'error',
                                'message': f'{result_key} 分析錯誤: {str(e)}',
                                'progress': int(agent_count / total_agents * 70)
                            })
                        except Exception as e:
                            logger.warning(f"Failed to send progress callback: {e}")

            if not results:
                return {
                    "error": "No specialist agents completed successfully",
                    "stock_code": stock_code,
                }

            # 添加基本資訊到結果中
            if not basic_info_result.error:
                results["basic_info"] = basic_info_result.output

            # Store and return complete results (without generating report here)
            self.results = {**results, "stock_code": stock_code}
            return self.results

        except Exception as e:
            logger.error(f"Error in research: {str(e)}")
            return {"error": str(e), "stock_code": stock_code}

    def _extract_ai_analysis(self, agent_output: str) -> str:
        """Extract clean AI analysis from agent output, removing tool call details.

        Args:
            agent_output: Raw agent output containing steps and tool calls

        Returns:
            Cleaned AI analysis text
        """
        import re

        if not agent_output or not isinstance(agent_output, str):
            return agent_output

        # Method 1: Find Chinese markdown content (most reliable for AI analysis)
        # Look for markdown headers (##, ###) followed by Chinese or mixed content with at least some content after
        chinese_markdown_pattern = r'#{2,}\s*[^\n]*[\u4e00-\u9fa5][^\n]*\n[\s\S]{200,}'
        chinese_match = re.search(chinese_markdown_pattern, agent_output)

        if chinese_match:
            # Extract from the start of Chinese markdown to the end or next "Step"
            content = chinese_match.group(0)
            # Remove any trailing step indicators
            content = re.split(r'\n(?=Step \d+:)', content)[0].strip()
            logger.info(f"Extracted Chinese markdown analysis ({len(content)} chars)")
            return content

        # Method 2: Remove tool call blocks and extract remaining analysis
        cleaned = agent_output

        # Remove "Step X: Observed output of cmd..." blocks
        cleaned = re.sub(
            r'Step \d+:\s*Observed output of cmd[^:]*?executed:\s*(\{[\s\S]*?\}|Error:[\s\S]*?)(?=\n\s*Step \d+:|\n\s*$)',
            '',
            cleaned
        )

        # Remove "Step X: Calling tool..." blocks
        cleaned = re.sub(
            r'Step \d+:\s*Calling tool[^:]*?with[\s\S]*?(?=\n\s*Step \d+:|\n\s*$)',
            '',
            cleaned
        )

        # Remove remaining "Step X:" prefixes
        cleaned = re.sub(r'Step \d+:\s*', '\n', cleaned)

        # Clean up multiple newlines
        cleaned = re.sub(r'\n{3,}', '\n\n', cleaned).strip()

        # Accept cleaned content even if shorter (lowered threshold from 100 to 30)
        if len(cleaned) >= 30:
            logger.info(f"Extracted cleaned analysis ({len(cleaned)} chars)")
            return cleaned

        # If cleaning resulted in very short content, check if it's just tool output
        # Check for common patterns that indicate only tool output (no AI analysis)
        tool_only_patterns = [
            'Observed output of cmd',
            'Step 1:',
            'Step 2:',
            'Calling tool'
        ]
        has_only_tool_output = any(pattern in agent_output for pattern in tool_only_patterns)
        has_no_chinese = not re.search(r'[\u4e00-\u9fa5]', agent_output)  # No Chinese characters

        if len(cleaned) < 30 and has_only_tool_output and (has_no_chinese or len(agent_output) > 500):
            logger.warning(f"Agent output contains only tool calls, no AI analysis generated")
            return ""

        # Fallback: return original if cleaning resulted in too little content
        logger.warning(f"Cleaning resulted in short content ({len(cleaned)} chars), returning original")
        return agent_output

    async def cleanup(self) -> None:
        """Clean up all agent resources."""
        cleanup_tasks = [
            agent.cleanup()
            for agent in self.agents.values()
            if hasattr(agent, "cleanup")
        ]

        if cleanup_tasks:
            await asyncio.gather(*cleanup_tasks)

        await super().cleanup()
