"""
Zalo Alert Logic Module - Gửi cảnh báo VPD qua Zalo Official Account (OA)
"""
import requests
from datetime import datetime
from typing import Dict, Optional, Tuple


def send_zalo_alert(
    recipient_phone: str,
    vpd_value: float,
    temperature: float,
    humidity: float,
    assessment: Dict,
    zalo_oa_id: str,
    zalo_access_token: str
) -> Tuple[bool, str]:
    """
    Gửi cảnh báo VPD qua Zalo Official Account
    
    Args:
        recipient_phone: Số điện thoại người nhận (định dạng: 0901234567 hoặc +84901234567)
        vpd_value: Giá trị VPD (kPa)
        temperature: Nhiệt độ (°C)
        humidity: Độ ẩm (%)
        assessment: Dict chứa status, description, recommendation
        zalo_oa_id: ID của Zalo Official Account
        zalo_access_token: Access Token từ Zalo API
        
    Returns:
        (success: bool, message: str)
    """
    try:
        # Chuẩn hóa số điện thoại
        phone = normalize_phone_number(recipient_phone)
        
        # Tạo nội dung tin nhắn
        message_content = format_zalo_message(
            vpd_value=vpd_value,
            temperature=temperature,
            humidity=humidity,
            assessment=assessment
        )
        
        # Gọi Zalo API
        headers = {
            'access_token': zalo_access_token,
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        
        data = {
            'phone': phone,
            'message': message_content
        }
        
        url = f"https://openapi.zalo.me/v2.0/oa/{zalo_oa_id}/message"
        
        response = requests.post(url, headers=headers, data=data, timeout=10)
        
        if response.status_code == 200:
            result = response.json()
            if result.get('error') == 0:
                return True, f"✅ Gửi cảnh báo Zalo thành công đến {phone}"
            else:
                error_msg = result.get('message', 'Lỗi không xác định')
                return False, f"❌ Zalo API lỗi: {error_msg}"
        else:
            return False, f"❌ Lỗi kết nối Zalo: HTTP {response.status_code}"
    
    except requests.exceptions.Timeout:
        return False, "❌ Hết thời gian kết nối Zalo API"
    except requests.exceptions.ConnectionError:
        return False, "❌ Không thể kết nối đến Zalo API"
    except Exception as e:
        return False, f"❌ Lỗi: {str(e)}"


def format_zalo_message(
    vpd_value: float,
    temperature: float,
    humidity: float,
    assessment: Dict
) -> str:
    """
    Tạo nội dung tin nhắn Zalo
    
    Args:
        vpd_value: Giá trị VPD (kPa)
        temperature: Nhiệt độ (°C)
        humidity: Độ ẩm (%)
        assessment: Dict chứa status, description, recommendation
        
    Returns:
        Nội dung tin nhắn text
    """
    current_time = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
    
    status_emoji = {
        'optimal': '✅',
        'low': '⚠️',
        'high': '⚠️',
        'too_low': '🔵',
        'too_high': '🔴'
    }
    
    emoji = status_emoji.get(assessment['status'], '⚠️')
    
    message = f"""🌱 CẢNH BÁO VPD - NHÀ KÍNH

⏰ {current_time}

{emoji} {assessment['description']}

📊 DỮ LIỆU:
• 🌡️  Nhiệt độ: {temperature:.2f}°C
• 💧 Độ ẩm: {humidity:.2f}%
• 📈 VPD: {vpd_value:.2f} kPa

💡 HƯỚNG GIẢI QUYẾT:
{assessment['recommendation']}

ℹ️  KHOẢNG TỐI ƯU: 0.8 - 1.2 kPa"""
    
    return message


def normalize_phone_number(phone: str) -> str:
    """
    Chuẩn hóa số điện thoại Việt Nam
    
    Args:
        phone: Số điện thoại (có thể là 0901234567 hoặc +84901234567)
        
    Returns:
        Số điện thoại dạng chuẩn 84901234567
    """
    # Loại bỏ khoảng trắng
    phone = phone.strip()
    
    # Nếu bắt đầu bằng +, loại bỏ nó
    if phone.startswith('+'):
        phone = phone[1:]
    
    # Nếu bắt đầu bằng 0, thay thế bằng 84
    if phone.startswith('0'):
        phone = '84' + phone[1:]
    
    return phone


def validate_zalo_token(zalo_oa_id: str, zalo_access_token: str) -> Tuple[bool, str]:
    """
    Kiểm tra xem Zalo token có hợp lệ không
    
    Args:
        zalo_oa_id: ID của Zalo Official Account
        zalo_access_token: Access Token từ Zalo API
        
    Returns:
        (is_valid: bool, message: str)
    """
    try:
        headers = {
            'access_token': zalo_access_token
        }
        
        url = f"https://openapi.zalo.me/v2.0/oa/{zalo_oa_id}/getprofile"
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            result = response.json()
            if result.get('error') == 0:
                oa_name = result.get('data', {}).get('name', 'Unknown')
                return True, f"✅ Token hợp lệ - Tài khoản: {oa_name}"
            else:
                return False, f"❌ Token không hợp lệ: {result.get('message')}"
        else:
            return False, f"❌ Lỗi kết nối: HTTP {response.status_code}"
    
    except Exception as e:
        return False, f"❌ Lỗi kiểm tra token: {str(e)}"


def validate_phone_number(phone: str) -> bool:
    """
    Kiểm tra số điện thoại Việt Nam có hợp lệ không
    
    Args:
        phone: Số điện thoại cần kiểm tra
        
    Returns:
        bool
    """
    import re
    # Loại bỏ khoảng trắng
    phone = phone.strip()
    
    # Kiểm tra định dạng 0901234567 hoặc +84901234567 hoặc 84901234567
    pattern = r'^(\+84|84|0)[0-9]{9}$'
    
    return re.match(pattern, phone) is not None
