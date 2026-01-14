# 止损管理功能使用指南

## 概述

IBKR Toolkit 提供**追踪止损 (Trailing Stop)** 订单管理功能，可以直接在 IBKR 系统中为你的持仓下追踪止损单，实现自动止损保护。

## 功能特性

- **追踪止损卖出**: 股价下跌触发止损，保护已实现利润
- **追踪止损买入**: 股价反弹触发买入，实现逢低买入策略
- **IBKR 原生支持**: 订单直接提交到 IBKR 系统，24/7 自动监控
- **批量下单**: 支持为账户的所有持仓或指定股票批量下单
- **订单管理**: 查看、取消活跃订单

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
   - 设置 "Socket port" (Paper: 4002, Live: 4001)
   - 勾选 "Allow connections from localhost only"

### 2. 配置环境变量

在 `.env` 文件中添加以下配置:

```bash
# IBKR Gateway 连接配置
IBKR_GATEWAY_HOST=127.0.0.1
IBKR_GATEWAY_PORT=4002  # Paper Trading, Live 使用 4001
IBKR_CLIENT_ID=1
```

## 使用方法

### 可用命令

```bash
# 为账户所有持仓下追踪止损卖出单
ibkr-toolkit stop-loss place U12345678 --percent 5.0

# 为特定股票下追踪止损卖出单
ibkr-toolkit stop-loss place U12345678 --percent 5.0 --symbols AAPL TSLA

# 为特定股票下追踪止损买入单（逢低买入策略）
ibkr-toolkit stop-loss place-buy U12345678 --percent 5.0 --symbols AAPL TSLA

# 查看所有活跃订单
ibkr-toolkit stop-loss orders

# 查看指定账户的活跃订单
ibkr-toolkit stop-loss orders --account U12345678

# 取消特定订单（通过订单ID）
ibkr-toolkit stop-loss cancel 15 12 6

# 取消指定账户的所有追踪止损单
ibkr-toolkit stop-loss cancel --account U12345678

# 取消指定账户特定股票的订单
ibkr-toolkit stop-loss cancel --account U12345678 --symbols AAPL TSLA
```

### 典型工作流程

#### 1. 为持仓下追踪止损单

使用 `place` 命令直接在IB系统中为指定账户下Trailing Stop订单：

```bash
# 为账户（U12345678）的所有持仓下5%追踪止损单
ibkr-toolkit stop-loss place U12345678 --percent 5.0

# 只为指定股票下单
ibkr-toolkit stop-loss place U12345678 --percent 5.0 --symbols AAPL TSLA NVDA

# 查看下单结果
ibkr-toolkit stop-loss orders --account U12345678
```

**优势：**

- ✅ 订单提交到IB系统，24/7自动监控
- ✅ 不需要本地程序运行
- ✅ 可在TWS/IB Gateway中可视化管理
- ✅ 账户特定，支持多账户管理

**注意事项：**

- 必须指定账户ID（如 U12345678）
- 订单会立即提交到IB系统
- 可以在TWS/IB Gateway中随时取消或修改订单

#### 2. 取消止损订单

```bash
# 方式1：查看订单获取ID
ibkr-toolkit stop-loss orders --account U12345678

# 输出示例：
# 订单ID  股票    动作   数量   类型    止损%
# 15      AAPL    SELL   100    TRAIL   5.0%
# 12      TSLA    SELL   50     TRAIL   5.0%

# 方式2：通过订单ID取消
ibkr-toolkit stop-loss cancel 15 12

# 方式3：取消账户所有追踪止损单
ibkr-toolkit stop-loss cancel --account U12345678

# 方式4：只取消特定股票的订单
ibkr-toolkit stop-loss cancel --account U12345678 --symbols SNDK NVDA
```

**使用场景：**

- 股价已经上涨，想调整止损百分比
- 决定不再使用止损保护
- 需要重新设置止损策略

#### 3. 使用追踪止损买入（逢低买入策略）

**追踪止损买入 (Trailing Stop Buy)** 是一种自动逢低买入的策略：

**工作原理：**

```
假设想买入 AAPL，设置 5% 追踪止损买入

1. 当前价格：$150
   触发买入价：$157.5（150 × 1.05，上浮5%）

2. 价格下跌时（追踪下移）：
   新价格：$140
   触发价自动下调：$147（140 × 1.05）
   继续等待更低价格

3. 价格上涨时（触发买入）：
   价格从 $140 回升到 $147+
   → 自动以市价买入
```

**使用命令：**

```bash
# 为 AAPL 和 TSLA 设置 5% 追踪止损买入
# 价格下跌时，买入触发价会跟随下降
# 价格回升超过 5% 时，自动买入
ibkr-toolkit stop-loss place-buy U12345678 --percent 5.0 --symbols AAPL TSLA

# 查看订单状态
ibkr-toolkit stop-loss orders --account U12345678
```

**适用场景：**

- ✅ **逢低买入**：等待价格充分回调后自动买入
- ✅ **趋势反转捕捉**：价格下跌后反弹时自动入场
- ✅ **避免追高**：不在高位买入，等待回调

**注意事项：**

- 默认下单数量为 1 股（可在 TWS/IB Gateway 中修改）
- 必须指定具体股票（`--symbols` 参数必填）
- 订单类型为 BUY + TRAIL，与 SELL + TRAIL 相反
- 适合有明确买入意向但想等待更好价格的场景

**示例对比：**

| 订单类型     | 命令        | 用途             | 触发条件        |
| ------------ | ----------- | ---------------- | --------------- |
| 追踪止损卖出 | `place`     | 保护已有持仓利润 | 价格下跌超过 X% |
| 追踪止损买入 | `place-buy` | 逢低买入新仓位   | 价格反弹超过 X% |

## 追踪止损工作原理

### 追踪止损卖出示例

假设你持有 AAPL 股票，设置 5% 追踪止损：

```
初始状态:
- 持仓成本: $100
- 当前价格: $150
- 止损价格: $142.5 (150 × 0.95)

场景1: 股价上涨
- 新价格: $160
- 止损价自动上调: $152 (160 × 0.95)
- 锁定更多利润 ✓

场景2: 股价小幅回落
- 新价格: $155
- 止损价保持: $152 (峰值 $160 × 0.95)
- 仍然安全 ✓

场景3: 触发止损
- 价格跌至: $151
- 触发止损: $151 < $152
- 自动以市价卖出 ⚠️
```

### 追踪止损买入示例

假设你想买入 TSLA，设置 5% 追踪止损买入：

```
初始状态:
- 当前价格: $200
- 触发买入价: $210 (200 × 1.05)

场景1: 股价下跌
- 新价格: $180
- 触发价自动下调: $189 (180 × 1.05)
- 等待更低价格 ✓

场景2: 股价持续下跌
- 新价格: $160
- 触发价继续下调: $168 (160 × 1.05)
- 继续等待 ✓

场景3: 触发买入
- 价格反弹至: $169
- 触发买入: $169 > $168
- 自动以市价买入 ⚠️
```

## 订单类型说明

### SELL + TRAIL (追踪止损卖出)

- **用途**: 保护已有持仓的利润
- **触发**: 价格从峰值下跌超过设定百分比
- **下单数量**: 自动获取持仓数量
- **适用**: 持有股票，想设置止损保护

### BUY + TRAIL (追踪止损买入)

- **用途**: 逢低买入新仓位
- **触发**: 价格从低点反弹超过设定百分比
- **下单数量**: 默认 1 股（需手动调整）
- **适用**: 想买入股票，但等待更好价格

## 常见问题

### 1. 订单在哪里执行？

订单直接提交到 IBKR 系统，由 IBKR 服务器 24/7 监控和执行，不需要本地程序运行。

### 2. 如何查看订单状态？

可以通过以下方式查看：

- 使用 `ibkr-toolkit stop-loss orders` 命令
- 在 TWS 或 IB Gateway 中查看活跃订单

### 3. 如何修改订单？

- 方式1：在 TWS/IB Gateway 中直接修改
- 方式2：取消原订单，重新下单

### 4. 止损触发后会自动卖出吗？

是的，订单提交到 IBKR 系统后，触发条件满足时会自动执行。

### 5. 可以为多个账户下单吗？

可以，每次下单时指定不同的账户ID即可。

### 6. 订单有效期是多久？

默认为 GTC (Good Till Cancelled)，除非手动取消否则一直有效。

## 最佳实践

### 1. 选择合适的止损百分比

- **保守策略**: 3-5%，适合波动较小的大盘股
- **平衡策略**: 5-8%，适合中等波动的股票
- **激进策略**: 8-12%，适合高波动的成长股

### 2. 定期检查订单

建议每周检查一次活跃订单：

```bash
ibkr-toolkit stop-loss orders --account U12345678
```

### 3. 根据市场调整

- 牛市：可适当放宽止损百分比（6-8%）
- 熊市：收紧止损百分比（3-5%）
- 高波动期：暂停使用或放宽百分比

### 4. 避免过度交易

- 不要频繁修改止损订单
- 给市场一定的波动空间
- 避免在短期波动中被止损出局

## 注意事项

⚠️ **重要提醒**:

1. **Paper Trading 测试**: 建议先在模拟账户测试，熟悉后再在实盘使用
2. **市场波动**: 高波动市场可能导致频繁触发止损
3. **盘后交易**: 确认订单是否允许盘后交易
4. **账户权限**: 确保账户有交易权限
5. **网络连接**: 下单时需要 IBKR Gateway 在线

## 故障排查

### 连接失败

```
Error: Not connected to IBKR Gateway
```

**解决方法**:

1. 确认 TWS/IB Gateway 正在运行
2. 检查端口配置 (Paper: 4002, Live: 4001)
3. 确认 API 设置已启用
4. 检查防火墙设置

### 下单失败

```
Error: Order rejected
```

**可能原因**:

1. 账户没有持仓（place 命令需要有持仓）
2. 账户权限不足
3. 股票不支持追踪止损订单
4. 数量超过持仓量

### 无法取消订单

```
Error: Order not found
```

**解决方法**:

1. 使用 `orders` 命令确认订单ID
2. 订单可能已经执行
3. 在 TWS/IB Gateway 中手动取消

## 参考资源

- [IBKR API 文档](https://interactivebrokers.github.io/tws-api/)
- [追踪止损订单说明](https://www.interactivebrokers.com/en/trading/orders/trailing-stop.php)
- [IB Gateway 下载](https://www.interactivebrokers.com/en/trading/ibgateway-stable.php)
