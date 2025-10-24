// FinGenius 台股分析平台前端邏輯

class FinGeniusApp {
    constructor() {
        this.currentStock = null;
        this.analysisResults = null;
        this.websocket = null;
        this.charts = {};

        this.init();
    }

    init() {
        this.bindEvents();
        this.setupWebSocket();
        this.showWelcomeMessage();
    }

    bindEvents() {
        // 表單提交
        document.getElementById('analysisForm').addEventListener('submit', (e) => {
            e.preventDefault();
            this.startAnalysis();
        });

        // 股票代碼驗證
        document.getElementById('validateBtn').addEventListener('click', () => {
            this.validateStockCode();
        });

        // 股票代碼輸入驗證
        document.getElementById('stockCode').addEventListener('input', (e) => {
            this.validateInput(e.target.value);
        });

        // 股票代碼輸入框獲得焦點時清除錯誤
        document.getElementById('stockCode').addEventListener('focus', () => {
            this.clearValidationError();
        });
    }

    setupWebSocket() {
        // 建立 WebSocket 連接
        const clientId = `client_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
        const wsUrl = `ws://${window.location.hostname}:8000/ws/${clientId}`;

        try {
            this.websocket = new WebSocket(wsUrl);

            this.websocket.onopen = () => {
                console.log('WebSocket 連接已建立');
                this.showToast('已連接到分析服務器', 'success');
            };

            this.websocket.onmessage = (event) => {
                this.handleWebSocketMessage(JSON.parse(event.data));
            };

            this.websocket.onerror = (error) => {
                console.error('WebSocket 錯誤:', error);
                this.showToast('連接服務器失敗，使用模擬模式', 'warning');
                this.websocket = null; // 使用模擬模式
            };

            this.websocket.onclose = () => {
                console.log('WebSocket 連接已關閉');
                this.websocket = null;
            };
        } catch (error) {
            console.error('無法建立 WebSocket 連接:', error);
            this.websocket = null; // 使用模擬模式
        }
    }

    handleWebSocketMessage(message) {
        console.log('收到 WebSocket 消息:', message);

        switch (message.type) {
            case 'validation_result':
                this.handleValidationResult(message);
                break;
            case 'analysis_started':
                this.handleAnalysisStarted(message);
                break;
            case 'phase_started':
                this.handlePhaseStarted(message);
                break;
            case 'phase_completed':
                this.handlePhaseCompleted(message);
                break;
            case 'agent_progress':
                this.handleAgentProgress(message);
                break;
            case 'battle_started':
                this.handleBattleStarted(message);
                break;
            case 'battle_results':
                this.handleBattleResults(message);
                break;
            case 'analysis_complete':
                this.handleAnalysisComplete(message);
                break;
            case 'error':
                this.showToast(message.message || '發生錯誤', 'danger');
                break;
            default:
                console.log('未知消息類型:', message.type);
        }
    }

    handleValidationResult(message) {
        if (message.valid && message.stock_info) {
            const info = message.stock_info;
            document.getElementById('stockInfo').innerHTML =
                `<strong>${info.name}</strong> (${this.currentStock}) - ${info.industry}`;
            this.showValidationSuccess(message.message || '股票驗證成功');
        } else {
            this.showValidationError(message.message || '找不到該股票代碼');
        }
    }

    handleAnalysisStarted(message) {
        console.log('分析已開始:', message);
    }

    handleAgentProgress(message) {
        const { agent, status, message: progressMessage } = message;

        if (agent === 'all') {
            document.getElementById('progressText').textContent = progressMessage;
            return;
        }

        const statusElement = document.getElementById(`agent-status-${agent}`);
        const iconElement = document.getElementById(`agent-icon-${agent}`);
        const agentCard = document.getElementById(`agent-${agent}`);

        if (!statusElement || !iconElement || !agentCard) return;

        if (status === 'started') {
            agentCard.classList.add('active');
            statusElement.textContent = '分析中...';
            iconElement.innerHTML = '<div class="loading-spinner"></div>';
        } else if (status === 'completed') {
            agentCard.classList.remove('active');
            agentCard.classList.add('completed');
            statusElement.textContent = '完成';
            iconElement.innerHTML = '<i class="fas fa-check success-icon"></i>';
        }
    }

    handlePhaseStarted(message) {
        const { phase, message: phaseMessage } = message;
        document.getElementById('progressText').textContent = phaseMessage;

        // 顯示當前階段
        const phaseNames = {
            'research': '研究階段',
            'battle': '辯論階段',
            'report': '報告生成'
        };

        this.showToast(`開始${phaseNames[phase]}`, 'info');
    }

    handlePhaseCompleted(message) {
        const { phase, message: phaseMessage } = message;
        console.log(`階段完成: ${phase}`, phaseMessage);
    }

    handleBattleStarted(message) {
        // 顯示辯論開始
        document.getElementById('progressText').textContent = '正在進行多輪辯論投票...';
        this.showToast('AI 專家辯論階段開始', 'info');

        // 如果有辯論卡片，顯示它
        const battleCard = document.getElementById('battleCard');
        if (battleCard) {
            battleCard.style.display = 'block';
        }
    }

    handleBattleResults(message) {
        const { final_decision, vote_count } = message;

        // 儲存辯論結果
        if (!this.analysisResults) {
            this.analysisResults = {};
        }
        this.analysisResults.battle = {
            final_decision,
            vote_count
        };

        // 顯示辯論結果
        this.showToast(`辯論完成：${final_decision}`, 'success');
    }

    handleAnalysisComplete(message) {
        this.analysisResults = message.results;

        // 檢查結果是否有效
        if (!this.analysisResults || Object.keys(this.analysisResults).length === 0) {
            this.showToast('分析完成，但未獲取到有效數據', 'warning');
            // 使用模擬數據
            this.loadMockResults();
        } else {
            this.showAnalysisResults();
            this.showToast('分析完成！', 'success');
        }
    }

    // 添加重試機制
    retryAnalysis() {
        if (this.currentStock) {
            this.showToast('正在重新分析...', 'info');
            this.startAnalysis();
        }
    }

    // 添加取消分析功能
    cancelAnalysis() {
        if (this.websocket && this.websocket.readyState === WebSocket.OPEN) {
            try {
                this.websocket.send(JSON.stringify({
                    type: 'cancel_analysis',
                    stock_code: this.currentStock
                }));
            } catch (error) {
                console.error('發送取消請求失敗:', error);
            }
        }

        document.getElementById('progressCard').style.display = 'none';
        this.showToast('已取消分析', 'info');
    }

    showWelcomeMessage() {
        // 延遲顯示歡迎訊息，避免與 WebSocket 連接訊息衝突
        setTimeout(() => {
            this.showToast('歡迎使用 FinGenius 台股分析平台', 'info');
        }, 500);
    }

    validateInput(value) {
        const stockCode = value.trim();

        // 清除之前的驗證狀態
        this.clearValidationError();

        if (stockCode === '') {
            return;
        }

        // 台股代碼驗證規則：4-6位數字
        const isValidFormat = /^\d{4,6}$/.test(stockCode);

        if (!isValidFormat) {
            this.showValidationError('台股代碼格式錯誤，應為4-6位數字');
            return;
        }

        // 顯示驗證成功狀態
        this.showValidationSuccess('代碼格式正確');
    }

    validateStockCode() {
        const stockCode = document.getElementById('stockCode').value.trim();

        if (!stockCode) {
            this.showValidationError('請輸入股票代碼');
            return;
        }

        this.showValidationSuccess('正在驗證股票代碼...');

        // 如果有 WebSocket 連接，使用真實 API 驗證
        if (this.websocket && this.websocket.readyState === WebSocket.OPEN) {
            try {
                this.websocket.send(JSON.stringify({
                    type: 'validate_stock',
                    stock_code: stockCode
                }));
            } catch (error) {
                console.error('發送驗證請求失敗:', error);
                this.useMockValidation(stockCode);
            }
        } else {
            // 否則使用模擬驗證
            this.useMockValidation(stockCode);
        }
    }

    useMockValidation(stockCode) {
        setTimeout(() => {
            const mockStockInfo = this.getMockStockInfo(stockCode);
            if (mockStockInfo) {
                document.getElementById('stockInfo').innerHTML =
                    `<strong>${mockStockInfo.name}</strong> (${mockStockInfo.code}) - ${mockStockInfo.industry}`;
                this.showValidationSuccess('股票驗證成功（模擬模式）');
            } else {
                this.showValidationError('找不到該股票代碼');
            }
        }, 1000);
    }

    startAnalysis() {
        const stockCode = document.getElementById('stockCode').value.trim();

        if (!stockCode) {
            this.showValidationError('請輸入股票代碼');
            return;
        }

        // 驗證格式
        if (!/^\d{4,6}$/.test(stockCode)) {
            this.showValidationError('台股代碼格式錯誤，應為4-6位數字');
            return;
        }

        this.currentStock = stockCode;

        // 隱藏輸入區域，顯示進度區域
        document.getElementById('progressCard').style.display = 'block';
        document.getElementById('resultCard').style.display = 'none';

        // 重置進度
        this.resetProgress();

        // 如果有 WebSocket 連接，使用真實 API
        if (this.websocket && this.websocket.readyState === WebSocket.OPEN) {
            try {
                this.websocket.send(JSON.stringify({
                    type: 'start_analysis',
                    stock_code: stockCode
                }));
                this.showToast(`開始分析 ${stockCode}`, 'info');
            } catch (error) {
                console.error('發送分析請求失敗:', error);
                this.showToast('發送請求失敗，使用模擬模式', 'warning');
                this.simulateAnalysis();
            }
        } else {
            // 否則使用模擬分析
            this.showToast('使用模擬模式分析', 'info');
            this.simulateAnalysis();
        }
    }

    resetProgress() {
        document.getElementById('progressBar').style.width = '0%';
        document.getElementById('progressText').textContent = '準備開始分析...';

        // 創建 Agent 進度卡片
        const agents = [
            { id: 'sentiment', name: '輿情分析', icon: 'fas fa-comments' },
            { id: 'risk', name: '風險評估', icon: 'fas fa-shield-alt' },
            { id: 'institutional', name: '三大法人', icon: 'fas fa-users' },
            { id: 'technical', name: '技術分析', icon: 'fas fa-chart-line' },
            { id: 'chip', name: '籌碼分析', icon: 'fas fa-layer-group' },
            { id: 'big_deal', name: '大額交易', icon: 'fas fa-dollar-sign' }
        ];

        const agentProgressContainer = document.getElementById('agentProgress');
        agentProgressContainer.innerHTML = '';

        agents.forEach(agent => {
            const agentCard = document.createElement('div');
            agentCard.className = 'col-md-6 agent-card';
            agentCard.id = `agent-${agent.id}`;
            agentCard.innerHTML = `
                <div class="d-flex align-items-center">
                    <div class="agent-icon ${agent.id}">
                        <i class="${agent.icon}"></i>
                    </div>
                    <div class="flex-grow-1">
                        <div class="fw-bold">${agent.name}</div>
                        <div class="small text-muted" id="agent-status-${agent.id}">等待中</div>
                    </div>
                    <div id="agent-icon-${agent.id}">
                        <i class="fas fa-clock text-muted"></i>
                    </div>
                </div>
            `;
            agentProgressContainer.appendChild(agentCard);
        });
    }

    simulateAnalysis() {
        const agents = ['sentiment', 'risk', 'institutional', 'technical', 'chip', 'big_deal'];
        let currentIndex = 0;
        let progress = 0;

        const processNextAgent = () => {
            if (currentIndex >= agents.length) {
                // 分析完成
                this.showAnalysisResults();
                return;
            }

            const agentId = agents[currentIndex];
            const agentCard = document.getElementById(`agent-${agentId}`);
            const statusElement = document.getElementById(`agent-status-${agentId}`);
            const iconElement = document.getElementById(`agent-icon-${agentId}`);

            // 標記為活躍狀態
            agentCard.classList.add('active');
            statusElement.textContent = '分析中...';
            iconElement.innerHTML = '<div class="loading-spinner"></div>';

            // 更新總進度
            progress = (currentIndex / agents.length) * 100;
            document.getElementById('progressBar').style.width = `${progress}%`;
            document.getElementById('progressText').textContent =
                `正在分析 ${agentCard.querySelector('.fw-bold').textContent}...`;

            // 模擬分析時間 (2-4秒)
            const analysisTime = 2000 + Math.random() * 2000;

            setTimeout(() => {
                // 標記為完成狀態
                agentCard.classList.remove('active');
                agentCard.classList.add('completed');
                statusElement.textContent = '完成';
                iconElement.innerHTML = '<i class="fas fa-check success-icon"></i>';

                currentIndex++;
                processNextAgent();
            }, analysisTime);
        };

        // 開始處理第一個 Agent
        processNextAgent();
    }

    showAnalysisResults() {
        // 更新進度為完成
        document.getElementById('progressBar').style.width = '100%';
        document.getElementById('progressText').textContent = '分析完成！';

        // 隱藏進度區域，顯示結果區域
        setTimeout(() => {
            document.getElementById('progressCard').style.display = 'none';
            document.getElementById('resultCard').style.display = 'block';
            document.getElementById('resultCard').classList.add('fade-in');

            // 載入模擬數據
            this.loadMockResults();
        }, 1000);
    }

    loadMockResults() {
        // 載入模擬的分析結果
        const mockResults = this.getMockAnalysisResults();

        // 填充基本資訊
        document.getElementById('stockBasicInfo').innerHTML = mockResults.basicInfo;

        // 填充 AI 總結
        document.getElementById('aiSummary').innerHTML = mockResults.aiSummary;

        // 填充各分析模組
        document.getElementById('technicalAnalysis').innerHTML = mockResults.technical;
        document.getElementById('institutionalAnalysis').innerHTML = mockResults.institutional;
        document.getElementById('chipAnalysis').innerHTML = mockResults.chip;
        document.getElementById('sentimentAnalysis').innerHTML = mockResults.sentiment;
        document.getElementById('riskAnalysis').innerHTML = mockResults.risk;

        // 如果有辯論結果，顯示它
        if (this.analysisResults && this.analysisResults.battle) {
            this.displayBattleResults(this.analysisResults.battle);
        }

        // 創建圖表
        this.createCharts(mockResults.charts);

        this.showToast('分析結果載入完成', 'success');
    }

    displayBattleResults(battleData) {
        const battleContainer = document.getElementById('battleResults');
        const noBattleResults = document.getElementById('noBattleResults');

        if (!battleContainer) return;

        const { final_decision, vote_count } = battleData;

        // 創建辯論結果 HTML
        const battleHTML = `
            <div class="analysis-content">
                <h5 class="mb-3">
                    <i class="fas fa-gavel me-2"></i>AI 專家辯論結果
                </h5>
                <div class="alert alert-${final_decision === '看多' ? 'success' : final_decision === '看空' ? 'danger' : 'warning'}">
                    <h6 class="alert-heading">
                        <i class="fas fa-chart-line me-2"></i>最終決策：${final_decision}
                    </h6>
                </div>
                ${vote_count ? `
                    <h6 class="mt-4 mb-3">投票結果</h6>
                    <div class="row">
                        ${Object.entries(vote_count).map(([option, count]) => `
                            <div class="col-md-4 mb-3">
                                <div class="card text-center">
                                    <div class="card-body">
                                        <h3 class="text-primary">${count}</h3>
                                        <p class="mb-0">${option}</p>
                                    </div>
                                </div>
                            </div>
                        `).join('')}
                    </div>
                ` : ''}
            </div>
        `;

        battleContainer.innerHTML = battleHTML;
        battleContainer.style.display = 'block';

        // 隱藏 "無辯論結果" 訊息
        if (noBattleResults) {
            noBattleResults.style.display = 'none';
        }
    }

    createCharts(chartData) {
        // 技術分析圖表
        const technicalCtx = document.getElementById('technicalChart').getContext('2d');
        this.charts.technical = new Chart(technicalCtx, {
            type: 'line',
            data: chartData.technical,
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    title: {
                        display: true,
                        text: '技術指標走勢圖'
                    }
                }
            }
        });

        // 三大法人圖表
        const institutionalCtx = document.getElementById('institutionalChart').getContext('2d');
        this.charts.institutional = new Chart(institutionalCtx, {
            type: 'bar',
            data: chartData.institutional,
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    title: {
                        display: true,
                        text: '三大法人買賣超統計'
                    }
                }
            }
        });

        // 籌碼分析圖表
        const chipCtx = document.getElementById('chipChart').getContext('2d');
        this.charts.chip = new Chart(chipCtx, {
            type: 'doughnut',
            data: chartData.chip,
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    title: {
                        display: true,
                        text: '籌碼集中度分析'
                    }
                }
            }
        });
    }

    showValidationError(message) {
        const stockInfo = document.getElementById('stockInfo');
        stockInfo.innerHTML = `<span class="text-danger"><i class="fas fa-exclamation-triangle me-1"></i>${message}</span>`;
        document.getElementById('stockCode').classList.add('is-invalid');
    }

    showValidationSuccess(message) {
        const stockInfo = document.getElementById('stockInfo');
        stockInfo.innerHTML = `<span class="text-success"><i class="fas fa-check-circle me-1"></i>${message}</span>`;
        document.getElementById('stockCode').classList.remove('is-invalid');
        document.getElementById('stockCode').classList.add('is-valid');
    }

    clearValidationError() {
        document.getElementById('stockInfo').innerHTML = '';
        document.getElementById('stockCode').classList.remove('is-invalid', 'is-valid');
    }

    showToast(message, type = 'info') {
        // 簡單的 toast 實現
        const toast = document.createElement('div');
        toast.className = `alert alert-${type} position-fixed`;
        toast.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px;';
        toast.innerHTML = `
            <i class="fas fa-info-circle me-2"></i>${message}
            <button type="button" class="btn-close" onclick="this.parentElement.remove()"></button>
        `;
        document.body.appendChild(toast);

        // 3秒後自動移除
        setTimeout(() => {
            if (toast.parentElement) {
                toast.remove();
            }
        }, 3000);
    }

    getMockStockInfo(stockCode) {
        // 模擬股票資訊
        const mockStocks = {
            '2330': { code: '2330', name: '台積電', industry: '半導體' },
            '2317': { code: '2317', name: '鴻海', industry: '電子零件' },
            '2454': { code: '2454', name: '聯發科', industry: '半導體' },
            '3008': { code: '3008', name: '大立光', industry: '光學鏡頭' },
            '2881': { code: '2881', name: '富邦金', industry: '金融保險' },
            '2882': { code: '2882', name: '國泰金', industry: '金融保險' }
        };

        return mockStocks[stockCode] || null;
    }

    getMockAnalysisResults() {
        return {
            basicInfo: `
                <div class="analysis-content">
                    <p><strong>股票代碼：</strong>${this.currentStock}</p>
                    <p><strong>公司名稱：</strong>台積電</p>
                    <p><strong>產業別：</strong>半導體</p>
                    <p><strong>最新價：</strong>650.00 元</p>
                    <p><strong>漲跌幅：</strong><span class="metric positive">+2.5%</span></p>
                    <p><strong>成交量：</strong>25,680 張</p>
                </div>
            `,
            aiSummary: `
                <div class="analysis-content">
                    <h6>AI 綜合評估</h6>
                    <p><span class="metric positive">看漲</span> 綜合評分：78/100</p>
                    <p><strong>主要利多：</strong></p>
                    <ul>
                        <li>三大法人連續買超，外資持有比例穩定</li>
                        <li>技術面呈多頭排列，均線系統向上</li>
                        <li>籌碼面健康，散戶套牢比例不高</li>
                    </ul>
                    <p><strong>注意風險：</strong></p>
                    <ul>
                        <li>國際半導體景氣波動</li>
                        <li>美中科技貿易戰影響</li>
                    </ul>
                </div>
            `,
            technical: `
                <div class="analysis-content">
                    <h6>技術分析總結</h6>
                    <p><strong>趨勢評估：</strong><span class="metric positive">多頭</span></p>
                    <p><strong>關鍵支撐：</strong>620, 600 元</p>
                    <p><strong>關鍵壓力：</strong>680, 700 元</p>
                    <p><strong>技術指標：</strong></p>
                    <ul>
                        <li>RSI: 65 (中性偏多)</li>
                        <li>MACD: 金叉向上</li>
                        <li>布林通道: 價格在中上軌</li>
                    </ul>
                </div>
            `,
            institutional: `
                <div class="analysis-content">
                    <h6>三大法人動向</h6>
                    <p><strong>近5日買賣超：</strong></p>
                    <ul>
                        <li>外資：+15,230 張</li>
                        <li>投信：+2,450 張</li>
                        <li>自營商：-1,890 張</li>
                        <li><strong>合計：</strong><span class="metric positive">+15,790 張</span></li>
                    </ul>
                    <p><strong>外資持股比例：</strong>78.5%</p>
                </div>
            `,
            chip: `
                <div class="analysis-content">
                    <h6>籌碼分析總結</h6>
                    <p><strong>籌碼集中度：</strong>70% 以上集中度為 15%</p>
                    <p><strong>籌碼穩定性：</strong><span class="metric positive">良好</span></p>
                    <p><strong>獲利比例：</strong>25% (健康)</p>
                    <p><strong>分析結論：</strong>籌碼面健康，主力控盤積極</p>
                </div>
            `,
            sentiment: `
                <div class="analysis-content">
                    <h6>輿情分析總結</h6>
                    <p><strong>整體情感：</strong><span class="metric positive">正面</span></p>
                    <p><strong>熱度評級：</strong>高</p>
                    <p><strong>關鍵話題：</strong></p>
                    <ul>
                        <li>先進製程技術領先</li>
                        <li>客戶訂單能見度高</li>
                        <li>資本支出計劃積極</li>
                    </ul>
                </div>
            `,
            risk: `
                <div class="analysis-content">
                    <h6>風險評估總結</h6>
                    <p><strong>風險等級：</strong><span class="metric neutral">中性</span></p>
                    <p><strong>主要風險：</strong></p>
                    <ul>
                        <li>地緣政治風險</li>
                        <li>供應鏈波動</li>
                        <li>技術轉換成本</li>
                    </ul>
                    <p><strong>風險控制建議：</strong>適度分散投資，關注國際政經情勢</p>
                </div>
            `,
            charts: {
                technical: {
                    labels: ['Day 1', 'Day 2', 'Day 3', 'Day 4', 'Day 5'],
                    datasets: [{
                        label: '股價',
                        data: [620, 635, 645, 650, 655],
                        borderColor: '#667eea',
                        backgroundColor: 'rgba(102, 126, 234, 0.1)',
                        tension: 0.4
                    }, {
                        label: '5日均線',
                        data: [615, 625, 635, 640, 645],
                        borderColor: '#28a745',
                        backgroundColor: 'rgba(40, 167, 69, 0.1)',
                        tension: 0.4
                    }]
                },
                institutional: {
                    labels: ['外資', '投信', '自營商'],
                    datasets: [{
                        label: '買賣超 (張)',
                        data: [15230, 2450, -1890],
                        backgroundColor: [
                            'rgba(102, 126, 234, 0.8)',
                            'rgba(40, 167, 69, 0.8)',
                            'rgba(255, 193, 7, 0.8)'
                        ],
                        borderWidth: 1
                    }]
                },
                chip: {
                    labels: ['散戶持有', '主力持有', '法人持有'],
                    datasets: [{
                        data: [25, 35, 40],
                        backgroundColor: [
                            'rgba(220, 53, 69, 0.8)',
                            'rgba(255, 193, 7, 0.8)',
                            'rgba(40, 167, 69, 0.8)'
                        ],
                        borderWidth: 1
                    }]
                }
            }
        };
    }
}

// 應用程式初始化
let app;
document.addEventListener('DOMContentLoaded', () => {
    app = new FinGeniusApp();

    // 將 app 設為全局，方便 HTML 中的按鈕調用
    window.app = app;
});