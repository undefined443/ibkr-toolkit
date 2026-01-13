# 止损管理功能使用指南

## 概述

IBKR Toolkit 现在支持**移动止损 (Trailing Stop Loss)** 功能，可以自动监控你的持仓并在触发止损条件时发送提醒或自动下单。

## 功能特性

- **移动止损策略**: 止损价随股价上涨自动上移，保护已实现利润
- **手动触发检查**: 按需检查持仓，不需要常驻后台
- **邮件通知**: 触发止损时自动发送邮件提醒
- **灵活配置**: 每个股票可设置不同的止损百分比
- **持久化存储**: 止损配置自动保存，重启后仍然有效

## 前置准备

### 1. 启动 TWS 或 IB Gateway

止损功能需要连接到 IBKR 的 TWS (Trader Workstation) 或 IB Gateway。

**推荐使用 IB Gateway** (更轻量，无 GUI):

1. 下载并安装 [IB Gateway](https://www.interactivebrokers.com/en/trading/ibgateway-stable.php)
2. 启动 IB Gateway
3. 登录你的账户 (Paper Trading 或 Live)
4. 在设置中启用 API 连接:
   - 点击 "Configure" → "Settings" → "API" → "Settings"
   - 勾选 "Enable ActiveX and Socket Clients"
   - 勾选 "Read-Only API" (如果只是查询，不自动下单)
   - 设置 "Socket port" (Paper: 4002, Live: 4001)
   - 勾选 "Allow connections from localhost only"

### 2. 配置环境变量

在 `.env` 文件中添加以下配置:

```bash
# IBKR Gateway 连接配置
IBKR_GATEWAY_HOST=127.0.0.1
IBKR_GATEWAY_PORT=4002  # Paper Trading, Live 使用 4001
IBKR_CLIENT_ID=1

# 默认止损百分比
DEFAULT_TRAILING_STOP_PERCENT=5.0

# 邮件通知配置 (可选)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your_email@gmail.com
SMTP_PASSWORD=your_app_password
EMAIL_FROM=your_email@gmail.com
EMAIL_TO=recipient@example.com
SMTP_USE_TLS=true
```

**注意**: 如果使用 Gmail，需要生成[应用专用密码](https://support.google.com/accounts/answer/185833)。

## 使用方法

### 基本命令

止损功能通过 `ibkr-toolkit stop-loss` 命令使用:

```bash
# 查看帮助
ibkr-toolkit stop-loss --help

# 检查所有持仓的止损条件
ibkr-toolkit stop-loss check

# 检查并发送邮件通知
ibkr-toolkit stop-loss check --email

# 检查并自动执行止损订单 (谨慎使用!)
ibkr-toolkit stop-loss check --auto-execute

# 为特定股票设置止损配置（仅监控，不下单）
ibkr-toolkit stop-loss set AAPL --percent 5.0

# 查看所有止损配置
ibkr-toolkit stop-loss list

# 🆕 在IB系统中为指定账户下追踪止损单
ibkr-toolkit stop-loss place U13900978 --percent 5.0

# 🆕 为指定账户的特定股票下追踪止损单
ibkr-toolkit stop-loss place U13900978 --percent 5.0 --symbols AAPL TSLA

# 🆕 查看所有活跃订单
ibkr-toolkit stop-loss orders

# 🆕 查看指定账户的活跃订单
ibkr-toolkit stop-loss orders --account U13900978
```

### 典型工作流程

#### 1. 首次使用: 为持仓设置止损

```bash
# 启动 IB Gateway
# ...

# 为 AAPL 设置 5% 移动止损
ibkr-toolkit stop-loss set AAPL --percent 5.0

# 为 TSLA 设置 8% 移动止损 (更高风险容忍度)
ibkr-toolkit stop-loss set TSLA --percent 8.0
```

#### 2. 定期检查止损条件

```bash
# 手动检查 (每天执行一次或多次)
ibkr-toolkit stop-loss check --email
```

**推荐做法**: 使用 cron 定时任务每天自动检查:

```bash
# 编辑 crontab
crontab -e

# 添加定时任务: 每天 9:30 和 15:30 检查 (美股开盘和收盘前)
30 9,15 * * 1-5 cd /path/to/ibkr-toolkit && uv run ibkr-toolkit stop-loss check --email
```

#### 3. 查看当前配置

```bash
# 查看所有股票的止损配置
ibkr-toolkit stop-loss list
```

#### 4. 🆕 在IB系统中下追踪止损单（推荐）

使用 `place` 命令直接在IB系统中为指定账户下Trailing Stop订单：

```bash
# 为 first 账户（U13900978）的所有持仓下5%追踪止损单
ibkr-toolkit stop-loss place U13900978 --percent 5.0

# 只为指定股票下单
ibkr-toolkit stop-loss place U13900978 --percent 5.0 --symbols AAPL TSLA NVDA

# 查看下单结果
ibkr-toolkit stop-loss orders --account U13900978
```

**优势：**

- ✅ IB系统原生支持，24小时自动监控和执行
- ✅ 可以精确指定账户，避免误操作
- ✅ 不需要本地程序常驻或定时任务
- ✅ 在TWS/IB Gateway中可以查看和管理订单

**注意事项：**

- 必须指定账户ID（如 U13900978）
- 订单会立即提交到IB系统
- 可以在TWS/IB Gateway中随时取消或修改订单

## 两种止损方式对比

IBKR Toolkit 提供了两种止损管理方式：

### 方式一：监控模式（set + check）

**使用命令：**

```bash
ibkr-toolkit stop-loss set AAPL --percent 5.0
ibkr-toolkit stop-loss check --email
```

**特点：**

- 本地监控，需要定期执行 `check` 命令
- 支持邮件通知
- 可以使用 `--auto-execute` 自动下单，但不建议
- 适合多账户统一管理和监控

**局限性：**

- ❌ 无法区分账户（按股票代码管理）
- ❌ 需要定时任务或手动执行
- ❌ 不是24小时监控（除非自己搭建服务）

### 方式二：IB系统订单（place）🆕 推荐

**使用命令：**

```bash
ibkr-toolkit stop-loss place U13900978 --percent 5.0
ibkr-toolkit stop-loss orders --account U13900978
```

**特点：**

- 直接在IB系统中下Trailing Stop订单
- IB系统24小时自动监控和执行
- 可以精确指定账户
- 在TWS/IB Gateway中可视化管理

**优势：**

- ✅ 可以按账户下单，避免混淆
- ✅ IB原生功能，更可靠
- ✅ 24小时自动监控，无需本地程序
- ✅ 市场开盘时订单自动激活

**推荐使用场景：**

- 有多个账户需要区分管理
- 需要24小时自动监控
- 希望在IB系统中统一管理订单

## 移动止损工作原理

### 示例

假设你持有 AAPL，设置 5% 移动止损:

1. **初始状态**:
   - 当前价格: $150
   - 止损价格: $142.5 (150 × 0.95)

2. **价格上涨**:
   - 新价格: $160
   - 止损价格自动上移: $152 (160 × 0.95)
   - 保护了 $10 的利润

3. **价格下跌**:
   - 新价格: $155
   - 止损价格保持: $152 (不会下移)
   - 当价格跌破 $152 时触发止损

4. **触发止损**:
   - 价格跌至 $151
   - 工具检测到触发条件
   - 发送邮件通知 (如果配置了 `--email`)
   - 自动下单 (如果使用了 `--auto-execute`)

## 配置说明

### 止损配置文件

止损配置自动保存在 `data/cache/stop_loss_config.json`:

```json
{
  "AAPL": {
    "symbol": "AAPL",
    "trailing_percent": 5.0,
    "peak_price": 160.0,
    "stop_price": 152.0,
    "last_updated": "2025-01-13T10:30:00"
  },
  "TSLA": {
    "symbol": "TSLA",
    "trailing_percent": 8.0,
    "peak_price": 250.0,
    "stop_price": 230.0,
    "last_updated": "2025-01-13T10:30:00"
  }
}
```

### 邮件通知

触发止损时会收到包含以下信息的邮件:

- 触发止损的持仓列表
- 当前价格、止损价格、未实现盈亏
- 所有持仓的概况
- 建议操作

## 安全建议

### ⚠️ 重要提示

1. **谨慎使用 `--auto-execute`**:
   - 自动下单有风险，建议先使用邮件通知模式
   - 确保在 Paper Trading 环境中充分测试
   - 生产环境建议人工确认后再下单

2. **API 权限**:
   - 如果只是检查持仓，启用 IB Gateway 的 "Read-Only API"
   - 自动下单前，确保 API 有交易权限

3. **网络稳定性**:
   - 确保 IB Gateway 稳定运行
   - 网络中断可能导致检查失败

4. **定时任务**:
   - 设置合理的检查频率 (建议每天 1-2 次)
   - 避免过于频繁的 API 调用

## 常见问题

### Q: 如何修改已设置的止损百分比?

A: 重新运行 `set` 命令即可覆盖:

```bash
ibkr-toolkit stop-loss set AAPL --percent 8.0
```

### Q: 如何删除某个股票的止损配置?

A: 目前需要手动编辑 `data/cache/stop_loss_config.json` 文件删除对应条目，或卖出该股票后系统会自动忽略。

### Q: 止损配置会过期吗?

A: 不会。配置会一直保存，直到手动删除或重新设置。

### Q: 可以为所有持仓一次性设置止损吗?

A: 目前需要逐个设置。未来版本可能会添加批量设置功能。

### Q: 连接 IB Gateway 失败怎么办?

A: 检查以下几点:

1. IB Gateway 是否已启动并登录
2. API 设置是否已启用
3. 端口号是否正确 (.env 中的 `IBKR_GATEWAY_PORT`)
4. 防火墙是否阻止了连接

### Q: 邮件发送失败怎么办?

A: 检查:

1. SMTP 配置是否正确
2. Gmail 用户需使用应用专用密码，不是账户密码
3. 是否启用了 TLS (`SMTP_USE_TLS=true`)

## 技术细节

### 架构

```
止损管理系统
├── TradingClient (交易客户端)
│   ├── 连接 IB Gateway
│   ├── 获取持仓信息
│   ├── 获取实时价格
│   └── 下达止损订单
├── StopLossManager (止损配置管理)
│   ├── 保存/加载配置
│   ├── 更新峰值价格
│   └── 计算止损价格
├── StopLossChecker (止损检查器)
│   ├── 遍历所有持仓
│   ├── 检查触发条件
│   └── 执行操作
└── EmailNotifier (邮件通知)
    └── 发送HTML格式提醒邮件
```

### 依赖

- `ib_async`: 与 IBKR API 交互
- `smtplib`: 发送邮件通知

## 下一步计划

未来可能添加的功能:

- [ ] 批量设置止损
- [ ] 支持不同的止损策略 (固定价格、时间止损等)
- [ ] 可视化界面
- [ ] 回测功能
- [ ] 微信/钉钉通知

## 参考资料

- [IB Gateway 用户指南](https://www.interactivebrokers.com/en/trading/ibgateway-stable.php)
- [IBKR API 文档](https://interactivebrokers.github.io/)
- [ib_async 文档](https://github.com/ib-api-reloaded/ib_async)
