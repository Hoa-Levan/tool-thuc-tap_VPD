"""
VPD Logic Module - Tính toán chỉ số VPD (Vapor Pressure Deficit)
"""
import math
from datetime import datetime

# Ngưỡng tối ưu tham chiếu cho phân tích nguyên nhân
OPTIMAL_T_MIN = 22.0   # °C
OPTIMAL_T_MAX = 26.0   # °C
OPTIMAL_RH_MIN = 60.0  # %
OPTIMAL_RH_MAX = 75.0  # %


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
    """
    try:
        T = float(temperature_celsius)
        svp_hpa = 0.6108 * math.exp((17.27 * T) / (T + 237.7))
        svp_kpa = svp_hpa / 10
        return svp_kpa
    except (ValueError, TypeError):
        return None


def calculate_actual_vapor_pressure(temperature_celsius, relative_humidity):
    """
    Tính áp suất hơi thực tế (AVP)
    AVP = SVP * (RH / 100)
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


def _analyze_cause(status, T, RH):
    if status == "high":
        t_deviation  = max(0, T - OPTIMAL_T_MAX) / OPTIMAL_T_MAX * 100
        rh_deviation = max(0, OPTIMAL_RH_MIN - RH) / OPTIMAL_RH_MIN * 100
        if t_deviation == 0 and rh_deviation == 0:
            return "Cả nhiệt độ và độ ẩm đều gần ngưỡng tối ưu nhưng VPD vẫn cao"
        if t_deviation >= rh_deviation:
            return f"Nhiệt độ quá cao (T={T:.1f}°C, vượt ngưỡng {OPTIMAL_T_MAX}°C khoảng {T - OPTIMAL_T_MAX:.1f}°C)"
        else:
            return f"Độ ẩm không khí quá thấp (RH={RH:.1f}%, thấp hơn ngưỡng {OPTIMAL_RH_MIN}% khoảng {OPTIMAL_RH_MIN - RH:.1f}%)"

    elif status == "low":
        rh_deviation = max(0, RH - OPTIMAL_RH_MAX) / OPTIMAL_RH_MAX * 100
        t_deviation  = max(0, OPTIMAL_T_MIN - T) / OPTIMAL_T_MIN * 100
        if t_deviation == 0 and rh_deviation == 0:
            return "Cả nhiệt độ và độ ẩm đều gần ngưỡng tối ưu nhưng VPD vẫn thấp"
        if rh_deviation >= t_deviation:
            return f"Độ ẩm không khí quá cao (RH={RH:.1f}%, vượt ngưỡng {OPTIMAL_RH_MAX}% khoảng {RH - OPTIMAL_RH_MAX:.1f}%)"
        else:
            return f"Nhiệt độ quá thấp (T={T:.1f}°C, thấp hơn ngưỡng {OPTIMAL_T_MIN}°C khoảng {OPTIMAL_T_MIN - T:.1f}°C)"

    return ""


def get_vpd_assessment(vpd_value, T=None, RH=None):
    """
    Đánh giá chất lượng VPD cho cây trồng
    Khoảng tối ưu: 0.8 - 1.2 kPa

    Args:
        vpd_value : float — Giá trị VPD (kPa)
        T         : float — Nhiệt độ (°C), tùy chọn
        RH        : float — Độ ẩm tương đối (%), tùy chọn

    Returns:
        Dict chứa: status, description, cause, recommendation
    """
    if vpd_value is None:
        return {
            "status": "error",
            "description": "Không thể tính VPD",
            "cause": "",
            "recommendation": "Kiểm tra lại dữ liệu nhiệt độ và độ ẩm"
        }

    vpd = float(vpd_value)

    if vpd < 0.4:
        status = "too_low"
        description = f"VPD quá thấp ({vpd:.2f} kPa)"
        recommendation = "⚠️ Độ ẩm quá cao - Tăng thông thoáng, giảm tưới nước, hạ độ ẩm để tránh bệnh nấm"
    elif vpd < 0.8:
        status = "low"
        description = f"VPD thấp ({vpd:.2f} kPa)"
        recommendation = "✓ Điều kiện chưa tối ưu - Tăng thông thoáng nhẹ"
    elif vpd <= 1.2:
        status = "optimal"
        description = f"VPD tối ưu ({vpd:.2f} kPa)"
        recommendation = "✅ Điều kiện lý tưởng - Duy trì điều kiện hiện tại"
    elif vpd <= 1.5:
        status = "high"
        description = f"VPD cao ({vpd:.2f} kPa)"
        recommendation = "⚠️ Độ ẩm thấp - Tăng tưới nước, phun sương, tăng độ ẩm"
    else:
        status = "too_high"
        description = f"VPD quá cao ({vpd:.2f} kPa)"
        recommendation = "❌ Điều kiện khô quá - Tăng mạnh độ ẩm, phun sương thường xuyên, giảm nhiệt độ"

    cause = ""
    if T is not None and RH is not None and status in ("low", "high"):
        cause = _analyze_cause(status, float(T), float(RH))

    return {
        "status": status,
        "description": description,
        "cause": cause,
        "recommendation": recommendation
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
