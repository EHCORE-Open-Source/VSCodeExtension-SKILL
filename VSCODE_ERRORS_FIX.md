# ⚠️ 看到 VSCode 錯誤？請閱讀這裡！

## 🔴 如果您在 VSCode 中看到很多 TypeScript 錯誤...

**請執行以下步驟：**

### 🔄 步驟 1：重新載入 VSCode

1. 按 `Ctrl+Shift+P`（Mac: `Cmd+Shift+P`）
2. 輸入：`reload`
3. 選擇：**Developer: Reload Window**

### ✅ 步驟 2：驗證

- 錯誤應該會消失或大幅減少
- 如果仍有問題，請參考：[VSCode TypeScript 設定指南](docs/VSCODE_TYPESCRIPT_SETUP.md)

## 📝 為什麼會這樣？

VSCode 需要重新載入才能正確使用新的 TypeScript 配置。

## 🚀 快速開始

### 開發擴充套件

```bash
# 最簡單的方式：按 F5 鍵
# 或使用命令：
npm run watch
```

### 執行測試

```bash
npm test
```

### 編譯

```bash
npm run compile
```

---

**詳細文件**:
- [VSCode TypeScript 設定](docs/VSCODE_TYPESCRIPT_SETUP.md)
- [TypeScript 配置說明](docs/TYPESCRIPT_CONFIG.md)
- [完整修復總結](TYPESCRIPT_FIX_SUMMARY.md)
