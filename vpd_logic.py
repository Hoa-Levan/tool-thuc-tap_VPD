"""
VPD Logic Module - Tính toán chỉ số VPD (Vapor Pressure Deficit)
"""
import math
from datetime import datetime


def celsius_to_kelvin(celsius):
    """Chuyển đổi từ Celsius sang Kelvin"""
    return float(celsius) + 273.15


def kelvin_to_celsius(kelvin):
    """Chuyển đổi từ Kelvin sang Celsius"""
    return float(kelvin) - 273.15


def calculate_saturation_vapor_pressure(temperature_celsius):
    """
    Tính áp suất hơi bão hòa (SVP) bằng công thức Magnus
    Đơn vị: kPa
    
    Args:
        temperature_celsius: Nhiệt độ tính bằng Celsius
        
    Returns:
        Áp suất hơi bão hòa (kPa)
    """
    try:
        T = float(temperature_celsius)
        
        # Công thức Magnus: SVP = 0.6108 * exp((17.27 * T) / (T + 237.7))
        # Kết quả đơn vị: hPa (hectoPascal)
        svp_hpa = 0.6108 * math.exp((17.27 * T) / (T + 237.7))
        
        # Chuyển sang kPa (1 kPa = 10 hPa)
        svp_kpa = svp_hpa / 10
        
        return svp_kpa
    except (ValueError, TypeError):
        return None


def calculate_actual_vapor_pressure(temperature_celsius, relative_humidity):
    """
    Tính áp suất hơi thực tế (AVP)
    AVP = SVP * (RH / 100)
    
    Args:
        temperature_celsius: Nhiệt độ tính bằng Celsius
        relative_humidity: Độ ẩm tương đối (%)
        
    Returns:
        Áp suất hơi thực tế (kPa)
    """
    try:
        T = float(temperature_celsius)
        RH = float(relative_humidity)
        
        if RH < 0 or RH > 100:
            return None
            
        svp = calculate_saturation_vapor_pressure(T)
        avp = svp * (RH / 100)
        
        return avp
    except (ValueError, TypeError):
        return None


def calculate_vpd(temperature_celsius, relative_humidity):
    """
    Tính VPD (Vapor Pressure Deficit)
    VPD = SVP - AVP
    
    Args:
        temperature_celsius: Nhiệt độ tính bằng Celsius
        relative_humidity: Độ ẩm tương đối (%)
        
    Returns:
        VPD (kPa) hoặc None nếu dữ liệu không hợp lệ
    """
    try:
        T = float(temperature_celsius)
        RH = float(relative_humidity)
        
        if RH < 0 or RH > 100 or T < -50 or T > 60:
            return None
            
        svp = calculate_saturation_vapor_pressure(T)
        avp = calculate_actual_vapor_pressure(T, RH)
        
        if svp is None or avp is None:
            return None
            
        vpd = svp - avp
        
        return vpd
    except (ValueError, TypeError):
        return None


def get_vpd_assessment(vpd_value):
    """
    Đánh giá chất lượng VPD cho cây trồng
    Khoảng tối ưu: 0.8 - 1.2 kPa
    
    Args:
        vpd_value: Giá trị VPD (kPa)
        
    Returns:
        Dict chứa: status, description, recommendation
    """
    if vpd_value is None:
        return {
            "status": "error",
            "description": "Không thể tính VPD",
            "recommendation": "Kiểm tra lại dữ liệu nhiệt độ và độ ẩm"
        }
    
    vpd = float(vpd_value)
    
    if vpd < 0.4:
        return {
            "status": "too_low",
            "description": f"VPD quá thấp ({vpd:.2f} kPa)",
            "recommendation": "⚠️ Độ ẩm quá cao - Tăng thông thoáng, giảm tưới nước, hạ độ ẩm để tránh bệnh nấm"
        }
    elif vpd < 0.8:
        return {
            "status": "low",
            "description": f"VPD thấp ({vpd:.2f} kPa)",
            "recommendation": "✓ Điều kiện chưa tối ưu - Tăng thông thoáng nhẹ nhàng"
        }
    elif vpd <= 1.2:
        return {
            "status": "optimal",
            "description": f"VPD tối ưu ({vpd:.2f} kPa)",
            "recommendation": "✅ Điều kiện lý tưởng - Duy trì điều kiện hiện tại"
        }
    elif vpd <= 1.5:
        return {
            "status": "high",
            "description": f"VPD cao ({vpd:.2f} kPa)",
            "recommendation": "⚠️ Độ ẩm thấp - Tăng tưới nước, phun sương, tăng độ ẩm"
        }
    else:
        return {
            "status": "too_high",
            "description": f"VPD quá cao ({vpd:.2f} kPa)",
            "recommendation": "❌ Điều kiện khô quá - Tăng độ ẩm quyết liệt, phun sương thường xuyên, giảm nhiệt độ"
        }


def categorize_vpd_status(vpd_value):
    """
    Phân loại trạng thái VPD để hiển thị màu sắc
    
    Returns: 'optimal', 'warning', 'danger'
    """
    if vpd_value is None:
        return 'unknown'
    
    vpd = float(vpd_value)
    
    if 0.8 <= vpd <= 1.2:
        return 'optimal'
    elif 0.4 <= vpd < 0.8 or 1.2 < vpd <= 1.5:
        return 'warning'
    else:
        return 'danger'
