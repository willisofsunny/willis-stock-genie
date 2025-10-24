// Willis Stock Genie 前端配置
const CONFIG = {
    // API 配置
    API: {
        // 根據環境自動選擇 API 地址
        getBaseUrl() {
            // 如果是 localhost，使用本地開發環境
            if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
                return 'http://localhost:8000';
            }
            // 生產環境 - 使用 Render 部署的後端
            return 'https://willis-stock-genie-api.onrender.com';
        },

        // 獲取 WebSocket URL
        getWebSocketUrl() {
            const baseUrl = this.getBaseUrl();
            // 將 http/https 替換為 ws/wss
            const wsProtocol = baseUrl.startsWith('https') ? 'wss' : 'ws';
            const wsHost = baseUrl.replace(/^https?:\/\//, '');
            return `${wsProtocol}://${wsHost}`;
        }
    },

    // WebSocket 配置
    WEBSOCKET: {
        // 心跳間隔（毫秒）
        HEARTBEAT_INTERVAL: 30000,

        // 重連配置
        RECONNECT: {
            MAX_RETRIES: 5,
            INITIAL_DELAY: 1000,
            MAX_DELAY: 30000,
            BACKOFF_MULTIPLIER: 2
        }
    },

    // UI 配置
    UI: {
        // Toast 通知持續時間（毫秒）
        TOAST_DURATION: 3000,

        // 分析超時時間（毫秒）
        ANALYSIS_TIMEOUT: 300000  // 5 分鐘
    },

    // Render 預熱配置 - 防止自由層進程睡眠
    KEEPALIVE: {
        // 是否啟用預熱機制
        ENABLED: true,
        // 預熱間隔（毫秒） - 每 10 分鐘預熱一次
        INTERVAL: 600000,
        // 預熱端點
        ENDPOINT: '/health'
    }
};

// 導出配置
window.CONFIG = CONFIG;
