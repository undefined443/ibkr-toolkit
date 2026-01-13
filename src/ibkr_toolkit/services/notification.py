"""
Notification service for sending alerts

Supports email notifications for stop-loss triggers
"""

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Dict, List

from ..exceptions import ConfigurationError
from ..utils.logging import setup_logger

logger = setup_logger(__name__)


class EmailNotifier:
    """Email notification service"""

    def __init__(
        self,
        smtp_host: str,
        smtp_port: int,
        smtp_user: str,
        smtp_password: str,
        from_email: str,
        to_emails: List[str],
        use_tls: bool = True,
    ):
        """
        Initialize email notifier

        Args:
            smtp_host: SMTP server host
            smtp_port: SMTP server port
            smtp_user: SMTP username
            smtp_password: SMTP password
            from_email: Sender email address
            to_emails: List of recipient email addresses
            use_tls: Whether to use TLS encryption
        """
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.smtp_user = smtp_user
        self.smtp_password = smtp_password
        self.from_email = from_email
        self.to_emails = to_emails
        self.use_tls = use_tls

        # Validate configuration
        if not all([smtp_host, smtp_port, smtp_user, smtp_password, from_email, to_emails]):
            raise ConfigurationError("邮件通知配置不完整")

    def send_stop_loss_alert(self, results: List[Dict]) -> None:
        """
        Send stop-loss alert email

        Args:
            results: List of check results from StopLossChecker
        """
        # Filter triggered positions
        triggered = [r for r in results if r.get("triggered")]

        if not triggered:
            logger.info("没有触发止损的持仓，无需发送通知")
            return

        # Build email content
        subject = f"⚠️ 止损提醒: {len(triggered)} 个持仓触发止损条件"
        html_content = self._build_html_content(triggered, results)

        try:
            self._send_email(subject, html_content)
            logger.info(f"已发送止损提醒邮件到 {', '.join(self.to_emails)}")
        except Exception as e:
            logger.error(f"发送邮件失败: {e}")

    def _build_html_content(self, triggered_results: List[Dict], all_results: List[Dict]) -> str:
        """Build HTML email content"""
        html = """
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; }}
                table {{ border-collapse: collapse; width: 100%; margin: 20px 0; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background-color: #4CAF50; color: white; }}
                .triggered {{ background-color: #ffebee; }}
                .profit {{ color: green; }}
                .loss {{ color: red; }}
                .summary {{ background-color: #f5f5f5; padding: 15px; margin: 10px 0; }}
            </style>
        </head>
        <body>
            <h2>⚠️ 止损提醒</h2>
            <div class="summary">
                <p><strong>检查时间:</strong> {timestamp}</p>
                <p><strong>总持仓数:</strong> {total_positions}</p>
                <p><strong>触发止损:</strong> {triggered_count} 个</p>
            </div>
        """.format(
            timestamp=self._get_timestamp(),
            total_positions=len(all_results),
            triggered_count=len(triggered_results),
        )

        # Triggered positions table
        html += """
            <h3>🚨 触发止损的持仓</h3>
            <table class="triggered">
                <tr>
                    <th>代码</th>
                    <th>数量</th>
                    <th>成本价</th>
                    <th>当前价</th>
                    <th>止损价</th>
                    <th>未实现盈亏</th>
                    <th>盈亏比例</th>
                    <th>操作</th>
                </tr>
        """

        for r in triggered_results:
            pnl_class = "profit" if r["unrealized_pnl"] > 0 else "loss"
            html += f"""
                <tr>
                    <td><strong>{r["symbol"]}</strong></td>
                    <td>{r["quantity"]}</td>
                    <td>${r["avg_cost"]:.2f}</td>
                    <td>${r["current_price"]:.2f}</td>
                    <td>${r["stop_price"]:.2f}</td>
                    <td class="{pnl_class}">${r["unrealized_pnl"]:+.2f}</td>
                    <td class="{pnl_class}">{r["pnl_percent"]:+.2f}%</td>
                    <td>{r.get("action_taken", "建议手动下单")}</td>
                </tr>
            """

        html += "</table>"

        # All positions summary
        html += """
            <h3>📊 所有持仓概况</h3>
            <table>
                <tr>
                    <th>代码</th>
                    <th>当前价</th>
                    <th>止损价</th>
                    <th>未实现盈亏</th>
                    <th>状态</th>
                </tr>
        """

        for r in all_results:
            status = "🚨 触发止损" if r["triggered"] else "✅ 正常"
            pnl_class = "profit" if r["unrealized_pnl"] > 0 else "loss"
            html += f"""
                <tr>
                    <td>{r["symbol"]}</td>
                    <td>${r["current_price"]:.2f}</td>
                    <td>${r["stop_price"]:.2f}</td>
                    <td class="{pnl_class}">${r["unrealized_pnl"]:+.2f}</td>
                    <td>{status}</td>
                </tr>
            """

        html += """
            </table>
            <hr>
            <p><em>此邮件由 IBKR Tax Tool 自动发送</em></p>
        </body>
        </html>
        """

        return html

    def _send_email(self, subject: str, html_content: str) -> None:
        """Send email via SMTP"""
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = self.from_email
        msg["To"] = ", ".join(self.to_emails)

        # Attach HTML content
        html_part = MIMEText(html_content, "html", "utf-8")
        msg.attach(html_part)

        # Send email
        with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
            if self.use_tls:
                server.starttls()
            server.login(self.smtp_user, self.smtp_password)
            server.send_message(msg)

    @staticmethod
    def _get_timestamp() -> str:
        """Get current timestamp in readable format"""
        from datetime import datetime

        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
