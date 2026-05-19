"""
Cảnh báo VPD Logic Module - Gửi cảnh báo VPD qua Gmail
"""
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from typing import Optional, Dict


def send_vpd_alert(
    recipient_email: str,
    vpd_value: float,
    temperature: float,
    humidity: float,
    assessment: Dict,
    app_url: str = "https://tool-thuc-tapvpd-edrzk6mjbtzfg5hkbqlsvb.streamlit.app",
    sender_email: str = "your_gmail@gmail.com",
    sender_password: str = "your_app_password"
) -> tuple[bool, str]:
    """
    Gửi cảnh báo VPD qua Gmail
    
    Args:
        recipient_email: Email người nhận
        vpd_value: Giá trị VPD (kPa)
        temperature: Nhiệt độ (°C)
        humidity: Độ ẩm (%)
        assessment: Dict chứa status, description, recommendation
        app_url: Link đến ứng dụng
        sender_email: Email Gmail của người gửi
        sender_password: Mật khẩu ứng dụng Gmail
        
    Returns:
        (success: bool, message: str)
    """
    try:
        # Xác định icon trạng thái
        status_icons = {
            'too_low': '🔵',
            'low': '🟡',
            'optimal': '🟢',
            'high': '🟡',
            'too_high': '🔴'
        }
        
        status_icon = status_icons.get(assessment['status'], '⚠️')
        
        # Tạo nội dung email HTML
        current_time = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
        
        html_content = f"""
        <html>
            <body style="font-family: Arial, sans-serif; background-color: #f5f5f5; padding: 20px;">
                <div style="max-width: 600px; margin: 0 auto; background-color: white; border-radius: 10px; padding: 30px; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
                    
                    <!-- Header -->
                    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; text-align: center;">
                        <h1 style="margin: 0; font-size: 24px;">🌱 Cảnh báo VPD</h1>
                        <p style="margin: 5px 0 0 0; font-size: 14px;">Nhà kính - Hệ thống theo dõi</p>
                    </div>
                    
                    <!-- Thời gian -->
                    <div style="background-color: #f9f9f9; padding: 12px; border-radius: 5px; margin-bottom: 15px; border-left: 4px solid #667eea;">
                        <p style="margin: 0; color: #666; font-size: 14px;">
                            <strong>⏰ Thời gian:</strong> {current_time}
                        </p>
                    </div>
                    
                    <!-- Trạng thái VPD -->
                    <div style="background-color: #fff3cd; border-left: 4px solid #ffc107; padding: 15px; border-radius: 5px; margin-bottom: 20px;">
                        <h2 style="margin: 0 0 10px 0; font-size: 18px;">
                            {status_icon} {assessment['description']}
                        </h2>
                        <p style="margin: 0; color: #856404; font-size: 14px;">
                            <strong>VPD:</strong> {vpd_value:.2f} kPa
                        </p>
                    </div>
                    
                    <!-- Dữ liệu chi tiết -->
                    <div style="background-color: #f0f4ff; padding: 15px; border-radius: 5px; margin-bottom: 20px;">
                        <h3 style="margin: 0 0 10px 0; font-size: 16px; color: #084298;">📊 Dữ liệu hiện tại:</h3>
                        <table style="width: 100%; font-size: 14px; color: #333;">
                            <tr style="border-bottom: 1px solid #ddd;">
                                <td style="padding: 8px; font-weight: bold;">🌡️ Nhiệt độ</td>
                                <td style="padding: 8px; text-align: right;">{temperature:.2f}°C</td>
                            </tr>
                            <tr style="border-bottom: 1px solid #ddd;">
                                <td style="padding: 8px; font-weight: bold;">💧 Độ ẩm</td>
                                <td style="padding: 8px; text-align: right;">{humidity:.2f}%</td>
                            </tr>
                            <tr>
                                <td style="padding: 8px; font-weight: bold;">📈 VPD</td>
                                <td style="padding: 8px; text-align: right;">{vpd_value:.2f} kPa</td>
                            </tr>
                        </table>
                    </div>
                    
                    <!-- Khuyến cáo -->
                    <div style="background-color: #fff8dc; padding: 15px; border-radius: 5px; border-left: 4px solid #ff6b6b; margin-bottom: 20px;">
                        <h3 style="margin: 0 0 10px 0; font-size: 16px; color: #721c24;">💡 Hướng giải quyết:</h3>
                        <p style="margin: 0; color: #666; font-size: 14px; line-height: 1.6;">
                            {assessment['recommendation']}
                        </p>
                    </div>
                    
                    <!-- Ghi chú -->
                    <div style="background-color: #f0f8ff; padding: 12px; border-radius: 5px; margin-bottom: 20px; border-left: 4px solid #0d6efd;">
                        <p style="margin: 0; font-size: 12px; color: #084298;">
                            <strong>ℹ️ Lưu ý:</strong><br>
                            • VPD tối ưu: <strong>0.8 - 1.2 kPa</strong><br>
                            • VPD quá thấp: Độ ẩm cao, tăng nguy cơ bệnh nấm<br>
                            • VPD quá cao: Cây mất nước nhanh, cần tưới nhiều hơn
                        </p>
                    </div>
                    
                    <!-- Nút xem chi tiết -->
                    <div style="text-align: center; margin-bottom: 20px;">
                        <a href="{app_url}" style="background-color: #667eea; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; font-weight: bold; display: inline-block; font-size: 14px;">
                            📱 Xem chi tiết chỉ số
                        </a>
                    </div>
                    
                    <!-- Footer -->
                    <div style="text-align: center; padding-top: 20px; border-top: 1px solid #ddd; color: #999; font-size: 12px;">
                        <p style="margin: 5px 0;">VPD Analysis Tool - Công cụ phân tích VPD cho cây trồng trong nhà kính</p>
                        <p style="margin: 5px 0;">© 2026 - Hệ thống theo dõi tự động</p>
                    </div>
                </div>
            </body>
        </html>
        """
        
        # Tạo email
        msg = MIMEMultipart('alternative')
        msg['Subject'] = f"🚨 Cảnh báo VPD - {assessment['description']}"
        msg['From'] = sender_email
        msg['To'] = recipient_email
        
        # Thêm nội dung HTML
        msg.attach(MIMEText(html_content, 'html'))
        
        # Gửi email qua Gmail SMTP
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, recipient_email, msg.as_string())
        
        return True, f"✅ Gửi cảnh báo thành công đến {recipient_email}"
    
    except smtplib.SMTPAuthenticationError:
        return False, "❌ Lỗi xác thực Gmail - Kiểm tra email và mật khẩu ứng dụng"
    except smtplib.SMTPException as e:
        return False, f"❌ Lỗi SMTP: {str(e)}"
    except Exception as e:
        return False, f"❌ Lỗi: {str(e)}"


def validate_email(email: str) -> bool:
    """
    Kiểm tra email có hợp lệ không
    
    Args:
        email: Email cần kiểm tra
        
    Returns:
        bool
    """
    import re
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


def format_alert_message(
    vpd_value: float,
    temperature: float,
    humidity: float,
    assessment: Dict
) -> str:
    """
    Tạo nội dung cảnh báo dạng text thuần
    
    Args:
        vpd_value: Giá trị VPD (kPa)
        temperature: Nhiệt độ (°C)
        humidity: Độ ẩm (%)
        assessment: Dict chứa status, description, recommendation
        
    Returns:
        Chuỗi nội dung cảnh báo
    """
    current_time = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
    
    message = f"""
╔══════════════════════════════════════════╗
║        🌱 CẢNH BÁO VPD - NHÀ KÍNH       ║
╚══════════════════════════════════════════╝

⏰ Thời gian: {current_time}

📊 TRẠNG THÁI VPD:
{assessment['description']}

📈 DỮ LIỆU CHI TIẾT:
  • 🌡️  Nhiệt độ: {temperature:.2f}°C
  • 💧 Độ ẩm: {humidity:.2f}%
  • 📊 VPD: {vpd_value:.2f} kPa

💡 HƯỚNG GIẢI QUYẾT:
{assessment['recommendation']}

ℹ️  GHI CHÚ:
  • VPD tối ưu: 0.8 - 1.2 kPa
  • VPD quá thấp (<0.8 kPa): Độ ẩm cao
  • VPD quá cao (>1.2 kPa): Khô quá

═════════════════════════════════════════════
VPD Analysis Tool - Công cụ phân tích VPD
"""
    return message
