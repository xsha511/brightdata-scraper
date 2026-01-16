# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Temu 商品数据采集系统，包含两个主要部分：
1. **BrightData SDK 爬虫**：使用 BrightData 官方 SDK 从 Amazon/Temu 爬取商品数据
2. **Chrome 插件 + FastAPI 服务端**：通过 Chrome 插件从 Temu 页面提取数据，上报到 FastAPI 服务端存储

## Commands

### 服务端
```bash
# 启动 FastAPI 服务端 (端口 8001)
python server.py

# 或直接使用 uvicorn
uvicorn src.api.main:app --host 0.0.0.0 --port 8001 --reload
```

### 测试
```bash
# 运行所有测试
pytest

# 运行单个测试文件
pytest tests/test_temu_models.py -v

# 运行特定测试
pytest tests/test_temu_service.py::test_save_product_new -v
```

### 代码检查
```bash
# 检查 Chrome 插件 JavaScript 语法
node --check extension/background/service-worker.js
```

### Chrome 插件
1. 打开 `chrome://extensions/`
2. 启用"开发者模式"
3. 点击"加载已解压的扩展程序"
4. 选择 `extension/` 目录
5. 修改代码后在扩展页面点击刷新按钮

## Architecture

### 服务端 (Python FastAPI)
```
src/
├── api/
│   ├── main.py              # FastAPI 入口，配置 CORS 和路由
│   └── routers/
│       ├── collect.py       # POST /api/collect/product, /api/collect/batch
│       ├── products.py      # GET /api/products, /api/products/{id}
│       └── debug.py         # POST /api/debug/log (插件调试日志)
├── temu/
│   ├── models.py            # Pydantic + SQLAlchemy 模型
│   └── service.py           # 商品 CRUD 业务逻辑
└── database.py              # SQLite + SQLAlchemy async 配置
```

### Chrome 插件 (Manifest V3)
```
extension/
├── manifest.json            # 权限：storage, activeTab, scripting, alarms, debugger
├── background/
│   └── service-worker.js    # 核心：批量上报、Chrome Debugger API 提取选品助手数据
├── content/
│   ├── main.js              # 商品详情页数据提取入口
│   ├── page-bridge.js       # 注入页面上下文读取 window.rawData
│   └── early-injector.js    # document_start 时注入的 hook
└── utils/
    ├── storage.js           # DataQueue 类，本地队列
    └── api.js               # 服务端通信
```

### 数据流
1. 用户访问 Temu 商品页
2. `content/main.js` 检测页面类型，注入 `page-bridge.js` 读取 `window.rawData`
3. 提取商品数据，通过 `chrome.runtime.sendMessage` 发送给 service worker
4. service worker 将数据加入队列，每分钟批量上报到服务端
5. 8秒后触发 `EXTRACT_XUANPIN`，使用 Chrome Debugger API 提取选品助手面板数据

### 选品助手数据提取 (Chrome Debugger API)
- 通过 `DOM.performSearch` + `includeUserAgentShadowDOM: true` 穿透 Shadow DOM
- 使用 `Input.dispatchMouseEvent` 模拟鼠标移动获取图表 tooltip
- 解析选品助手 HTML 获取销量、销售额、店铺信息等

## Key Files

- `extension/background/service-worker.js` - 插件核心逻辑，包含 `extractXuanpinViaDebugger()` 函数
- `extension/manifest.json` - 插件版本号在此更新
- `src/api/routers/debug.py` - 查看插件发送的调试日志
- `config/extension-config.json` - 插件配置，包含服务端 URL

## Database

SQLite 数据库位于 `data/temu.db`，主要表：
- `products` - 商品信息
- `price_history` - 价格历史记录
- `collect_logs` - 采集日志

## Version Control

修改插件后记得更新 `extension/manifest.json` 中的 `version` 字段，便于在 chrome://extensions 确认刷新成功。
