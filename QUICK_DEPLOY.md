# 🚀 Willis Stock Genie 快速部署指南

## 📋 準備工作（5 分鐘）

1. **註冊帳號**
   - [ ] GitHub: https://github.com/signup
   - [ ] Render: https://render.com/register
   - [ ] Cloudflare: https://dash.cloudflare.com/sign-up
   - [ ] DeepSeek API: https://platform.deepseek.com

2. **獲取 API Key**
   - [ ] 登入 DeepSeek Platform
   - [ ] 點擊右上角頭像 → API Keys
   - [ ] 點擊「Create API Key」
   - [ ] 複製並保存 API Key（格式：`sk-xxxxxx`）

---

## 🔧 部署步驟（15 分鐘）

### 步驟 1: 推送到 GitHub（3 分鐘）

```bash
# 1. 創建 GitHub 倉庫
# 前往 https://github.com/new
# 倉庫名稱: willis-stock-genie
# 類型: Public
# 不要勾選任何初始化選項

# 2. 在本地執行
git add .
git commit -m "Initial commit: Willis Stock Genie"
git remote add origin https://github.com/YOUR_USERNAME/willis-stock-genie.git
git branch -M main
git push -u origin main
```

### 步驟 2: 部署後端到 Render（7 分鐘）

1. **連接倉庫**
   - 前往 https://dashboard.render.com/
   - 點擊 `New +` → `Web Service`
   - 連接 GitHub 並選擇 `willis-stock-genie` 倉庫

2. **配置服務**
   ```
   Name: willis-stock-genie-api
   Region: Singapore
   Branch: main
   Build Command: pip install --upgrade pip && pip install -r requirements.txt
   Start Command: python -m uvicorn web.server:app --host 0.0.0.0 --port $PORT
   Plan: Free
   ```

3. **設置環境變量**
   點擊 `Advanced` → 添加以下環境變量：
   ```
   DEEPSEEK_API_KEY=你的_DeepSeek_API_Key
   ENVIRONMENT=production
   LOG_LEVEL=INFO
   ```

4. **部署**
   - 點擊 `Create Web Service`
   - 等待 5-10 分鐘
   - **重要**: 複製你的 API 地址（如：`https://willis-stock-genie-api.onrender.com`）

### 步驟 3: 更新前端配置（2 分鐘）

編輯 `web/config.js` 文件：

```javascript
// 第 13 行，替換為你的 Render API 地址
return 'https://willis-stock-genie-api.onrender.com';
```

提交更改：
```bash
git add web/config.js
git commit -m "Update API endpoint"
git push
```

### 步驟 4: 部署前端到 Cloudflare Pages（3 分鐘）

1. **創建項目**
   - 前往 https://dash.cloudflare.com/
   - 進入 `Workers & Pages` → `Pages`
   - 點擊 `Create a project` → `Connect to Git`
   - 選擇 `willis-stock-genie` 倉庫

2. **配置構建**
   ```
   Project name: willis-stock-genie
   Production branch: main
   Build command: (留空)
   Build output directory: web
   ```

3. **部署**
   - 點擊 `Save and Deploy`
   - 等待 2-3 分鐘
   - **重要**: 複製你的網站地址（如：`https://willis-stock-genie.pages.dev`）

### 步驟 5: 更新 CORS 設置（1 分鐘）

1. 回到 Render Dashboard
2. 進入你的服務 → `Environment` 標籤
3. 添加/更新環境變量：
   ```
   CORS_ORIGINS=https://willis-stock-genie.pages.dev
   ```
4. 保存（服務會自動重啟）

---

## ✅ 測試部署

1. **訪問前端**
   ```
   https://willis-stock-genie.pages.dev
   ```

2. **測試功能**
   - 輸入股票代碼：`2330`
   - 點擊「開始分析」
   - 檢查連接狀態：應顯示「已連接」
   - 等待分析結果（約 2-3 分鐘）

3. **驗證成功標誌**
   - ✅ 前端頁面正常加載
   - ✅ WebSocket 連接成功（綠色圓點）
   - ✅ 股票分析正常運行
   - ✅ 6 個分析模塊都有 AI 生成的總結

---

## ⚠️ 常見問題快速修復

### 問題 1: 前端無法連接後端
**原因**: `web/config.js` 中的 API 地址錯誤

**解決**:
```javascript
// 確認 web/config.js 第 13 行
return 'https://你的實際Render地址.onrender.com';  // 注意使用 https
```

### 問題 2: WebSocket 連接失敗
**原因**: CORS 設置不正確

**解決**:
1. 確認 Render 環境變量 `CORS_ORIGINS` 包含你的 Cloudflare 地址
2. 確保沒有多餘的空格或斜線
3. 保存後等待服務重啟（約 1 分鐘）

### 問題 3: 後端首次訪問很慢
**原因**: Render 免費方案會在 15 分鐘無活動後睡眠

**說明**: 這是正常行為，首次訪問需要 30-60 秒喚醒服務

---

## 📞 需要幫助？

- 詳細文檔: `DEPLOYMENT.md`
- 檢查 Render 日誌: Dashboard → 你的服務 → Logs
- 檢查瀏覽器控制台: F12 → Console

---

## 🎉 部署完成！

恭喜！你的 Willis Stock Genie 現在已經部署到線上了！

**你的網站**: `https://willis-stock-genie.pages.dev`

記得分享給朋友們使用！📈✨
