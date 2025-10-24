# Willis Stock Genie 部署指南

本指南將幫助你將 Willis Stock Genie 部署到線上服務器。我們使用：
- **後端**: GitHub + Render（免費方案）
- **前端**: Cloudflare Pages（免費方案）

## 📋 前置準備

### 1. 需要的帳號
- ✅ GitHub 帳號
- ✅ Render 帳號 (https://render.com)
- ✅ Cloudflare 帳號 (https://cloudflare.com)
- ✅ DeepSeek API Key (https://platform.deepseek.com)

### 2. 本地環境檢查
```bash
# 確認 Git 已初始化
git status

# 如果尚未初始化 Git
git init
git add .
git commit -m "Initial commit: Willis Stock Genie"
```

---

## 🚀 部署步驟

### 步驟 1: 推送代碼到 GitHub

#### 1.1 創建 GitHub 倉庫
1. 登入 GitHub
2. 點擊右上角 `+` → `New repository`
3. 倉庫名稱: `willis-stock-genie`
4. 選擇 `Public` 或 `Private`
5. **不要**初始化 README、.gitignore 或 license
6. 點擊 `Create repository`

#### 1.2 推送代碼
```bash
# 添加遠程倉庫（替換為你的 GitHub 用戶名）
git remote add origin https://github.com/YOUR_USERNAME/willis-stock-genie.git

# 推送代碼
git branch -M main
git push -u origin main
```

---

### 步驟 2: 部署後端到 Render

#### 2.1 連接 GitHub 倉庫
1. 登入 [Render Dashboard](https://dashboard.render.com/)
2. 點擊 `New +` → `Web Service`
3. 選擇 `Connect GitHub` 並授權
4. 選擇 `willis-stock-genie` 倉庫

#### 2.2 配置服務
填寫以下配置：

| 欄位 | 值 |
|-----|-----|
| **Name** | `willis-stock-genie-api` |
| **Region** | `Singapore` (或離你最近的區域) |
| **Branch** | `main` |
| **Root Directory** | (留空) |
| **Environment** | `Python 3` |
| **Build Command** | `pip install --upgrade pip && pip install -r requirements.txt` |
| **Start Command** | `python -m uvicorn web.server:app --host 0.0.0.0 --port $PORT` |
| **Plan** | `Free` |

#### 2.3 設置環境變量
點擊 `Advanced` → `Add Environment Variable`，添加以下變量：

```bash
DEEPSEEK_API_KEY=sk-your-actual-deepseek-key
ENVIRONMENT=production
LOG_LEVEL=INFO
PYTHON_VERSION=3.12
CORS_ORIGINS=https://willis-stock-genie.pages.dev
```

**重要提示**:
- `DEEPSEEK_API_KEY`: 必須填入你的真實 API Key
- `CORS_ORIGINS`: 部署後需要更新為你的 Cloudflare Pages 實際域名

#### 2.4 部署
1. 點擊 `Create Web Service`
2. Render 會自動開始構建和部署
3. 等待 5-10 分鐘直到狀態變為 `Live`
4. 記下你的 API 地址，格式為：`https://willis-stock-genie-api.onrender.com`

---

### 步驟 3: 部署前端到 Cloudflare Pages

#### 3.1 更新前端配置
在部署前，需要更新 `web/config.js` 中的 API 地址：

```javascript
// 修改 web/config.js 第 13-14 行
return 'https://willis-stock-genie-api.onrender.com';  // 替換為你的實際 Render API 地址
```

提交更改：
```bash
git add web/config.js
git commit -m "Update API endpoint for production"
git push
```

#### 3.2 連接 GitHub 倉庫
1. 登入 [Cloudflare Dashboard](https://dash.cloudflare.com/)
2. 進入 `Workers & Pages` → `Pages`
3. 點擊 `Create a project` → `Connect to Git`
4. 選擇你的 GitHub 帳號並授權
5. 選擇 `willis-stock-genie` 倉庫

#### 3.3 配置構建設置
填寫以下配置：

| 欄位 | 值 |
|-----|-----|
| **Project name** | `willis-stock-genie` |
| **Production branch** | `main` |
| **Build command** | (留空，因為是靜態網站) |
| **Build output directory** | `web` |
| **Root directory** | (留空) |

#### 3.4 部署
1. 點擊 `Save and Deploy`
2. Cloudflare 會自動開始部署
3. 等待 2-3 分鐘直到部署完成
4. 你的網站將可在以下地址訪問：
   - `https://willis-stock-genie.pages.dev`
   - 或你設置的自定義域名

#### 3.5 更新後端 CORS 設置
部署完成後，需要回到 Render 更新 CORS 設置：

1. 進入 Render Dashboard → 你的服務
2. 點擊 `Environment` 標籤
3. 更新 `CORS_ORIGINS` 環境變量為：
   ```
   https://willis-stock-genie.pages.dev
   ```
4. 保存後服務會自動重啟

---

## ✅ 驗證部署

### 1. 測試後端 API
訪問你的 Render API 地址：
```
https://willis-stock-genie-api.onrender.com/
```

應該看到類似的響應：
```html
<h1>Willis Stock Genie</h1>
```

### 2. 測試前端
訪問你的 Cloudflare Pages 地址：
```
https://willis-stock-genie.pages.dev
```

應該看到完整的 Willis Stock Genie 界面。

### 3. 測試完整功能
1. 在前端輸入股票代碼（如 `2330`）
2. 點擊「開始分析」
3. 檢查連接狀態是否顯示「已連接」
4. 等待分析結果

---

## 🔧 常見問題

### 問題 1: 後端部署失敗
**原因**: Python 版本或依賴問題

**解決方案**:
1. 檢查 `render.yaml` 中的 Python 版本設置
2. 確認 `requirements.txt` 中所有依賴版本正確
3. 查看 Render 構建日誌，找出具體錯誤

### 問題 2: WebSocket 連接失敗
**原因**: CORS 設置不正確或 API 地址錯誤

**解決方案**:
1. 確認 `web/config.js` 中的 API 地址正確
2. 確認 Render 環境變量中 `CORS_ORIGINS` 包含你的 Cloudflare Pages 域名
3. 打開瀏覽器開發者工具 → Network 標籤，檢查 WebSocket 連接錯誤訊息

### 問題 3: 前端顯示但無法連接後端
**原因**: 前端配置中的 API 地址錯誤

**解決方案**:
1. 檢查 `web/config.js` 文件
2. 確認 API 地址與 Render 提供的地址一致
3. 確保使用 `https://` 而非 `http://`

### 問題 4: Render 服務進入睡眠狀態
**原因**: Render 免費方案在 15 分鐘無活動後會進入睡眠

**解決方案**:
- 這是正常行為，首次訪問會需要 30-60 秒喚醒
- 考慮升級到付費方案以保持服務始終運行
- 或使用外部監控服務定期 ping 你的 API

---

## 🔄 更新部署

### 更新代碼
```bash
# 修改代碼後
git add .
git commit -m "Update: description of changes"
git push
```

- **Render**: 會自動檢測推送並重新部署
- **Cloudflare Pages**: 會自動檢測推送並重新部署

### 手動觸發部署
- **Render**: Dashboard → 你的服務 → Manual Deploy → Deploy latest commit
- **Cloudflare Pages**: Dashboard → 你的項目 → Deployments → Retry deployment

---

## 📊 監控和日誌

### Render 日誌
1. 進入 Render Dashboard → 你的服務
2. 點擊 `Logs` 標籤
3. 可以看到實時日誌輸出

### Cloudflare Pages 部署狀態
1. 進入 Cloudflare Dashboard → Pages → 你的項目
2. 點擊 `Deployments` 查看部署歷史
3. 點擊特定部署查看詳細日誌

---

## 🌐 自定義域名（可選）

### 為 Cloudflare Pages 添加自定義域名
1. 進入你的 Cloudflare Pages 項目
2. 點擊 `Custom domains` 標籤
3. 點擊 `Set up a custom domain`
4. 輸入你的域名（如 `stock.yourdomain.com`）
5. 按照指示添加 DNS 記錄
6. 等待 DNS 生效（通常 5-10 分鐘）

### 更新 Render CORS 設置
添加自定義域名後，記得在 Render 環境變量中更新 `CORS_ORIGINS`:
```
https://willis-stock-genie.pages.dev,https://stock.yourdomain.com
```

---

## 💡 優化建議

### 1. 效能優化
- 考慮使用 CDN 加速靜態資源
- 啟用 Cloudflare 的壓縮和快取功能
- 優化圖片和資源大小

### 2. 安全性
- 定期更新依賴包版本
- 使用環境變量管理敏感信息
- 啟用 Cloudflare 的安全功能（WAF、DDoS 防護）

### 3. 監控
- 設置 Sentry 或其他錯誤追蹤服務
- 使用 UptimeRobot 監控服務可用性
- 定期檢查日誌

---

## 📞 需要幫助？

如果遇到問題：
1. 檢查本文檔的「常見問題」部分
2. 查看 Render 和 Cloudflare 的官方文檔
3. 檢查 GitHub Issues

---

## 📝 部署檢查清單

部署前請確認：

- [ ] GitHub 倉庫已創建並推送代碼
- [ ] 已獲取 DeepSeek API Key
- [ ] Render 服務已創建並配置環境變量
- [ ] Cloudflare Pages 項目已創建
- [ ] `web/config.js` 中的 API 地址已更新
- [ ] Render 中的 CORS_ORIGINS 已更新
- [ ] 後端 API 可以正常訪問
- [ ] 前端可以正常訪問
- [ ] WebSocket 連接正常
- [ ] 股票分析功能正常

祝部署順利！ 🎉
