"""
Realtime Logic Module - Xử lý dữ liệu real-time cho VPD Analysis Tool
Tạm thời dùng số liệu ngẫu nhiên mô phỏng cảm biến thật
"""

import random
import math
from datetime import datetime
import pandas as pd


# ============================================================================
# CẤU HÌNH MÔ PHỎNG CẢM BIẾN
# ============================================================================

SENSOR_T_MIN  = 18.0
SENSOR_T_MAX  = 35.0
SENSOR_RH_MIN = 30.0
SENSOR_RH_MAX = 95.0

# Biến động mỗi lần đọc — nhỏ để số liệu mượt
SENSOR_T_DRIFT  = 0.4   # °C
SENSOR_RH_DRIFT = 1.2   # %

# Tần suất cập nhật (giây) — đổi sang 10 giây
UPDATE_INTERVAL = 10

# Ngưỡng tối ưu để sinh số liệu thiên về "tốt"
# VPD tối ưu 0.8-1.2 kPa ứng với T~24°C, RH~65%
TARGET_T  = 24.0   # °C — nhiệt độ mục tiêu
TARGET_RH = 65.0   # %  — độ ẩm mục tiêu

# Xác suất để "kéo" về vùng tối ưu sau khi lệch
PULL_PROB = 0.6    # 60% lần sẽ kéo về gần target


# ============================================================================
# HÀM SINH DỮ LIỆU CẢM BIẾN
# ============================================================================

def _pull_toward_target(value, target, drift, pull_prob=PULL_PROB):
    """
    Sinh giá trị mới:
    - Với xác suất pull_prob: kéo nhẹ về phía target (mô phỏng môi trường
      tự điều chỉnh hoặc người dùng can thiệp)
    - Còn lại: dao động ngẫu nhiên bình thường
    """
    if random.random() < pull_prob:
        # Kéo về target: bước nhảy hướng về target, tối đa 1 drift
        direction = 1 if target > value else -1
        step = random.uniform(0, drift) * direction
    else:
        step = random.uniform(-drift, drift)
    return value + step


def generate_sensor_reading(prev_T=None, prev_RH=None):
    """
    Sinh một bản ghi cảm biến mô phỏng.

    Chiến lược sinh số liệu:
    - Lần đầu: chọn gần vùng tối ưu (±3°C, ±10% RH quanh target)
      để không bắt đầu từ trạng thái cực xấu
    - Các lần sau: dao động nhỏ với xác suất cao kéo về target
      → kết quả hầu hết ở mức trung bình đến tối ưu

    Returns:
        dict với keys: timestamp, temperature, humidity
    """
    if prev_T is None:
        # Lần đầu: bắt đầu gần target thay vì random toàn khoảng
        T  = round(random.gauss(TARGET_T,  2.0), 1)   # gauss quanh 24°C, std=2
        RH = round(random.gauss(TARGET_RH, 6.0), 1)   # gauss quanh 65%, std=6
        # Clamp trong khoảng hợp lệ
        T  = max(SENSOR_T_MIN,  min(SENSOR_T_MAX,  T))
        RH = max(SENSOR_RH_MIN, min(SENSOR_RH_MAX, RH))
    else:
        # Các lần sau: kéo về target với xác suất PULL_PROB
        T  = _pull_toward_target(prev_T,  TARGET_T,  SENSOR_T_DRIFT)
        RH = _pull_toward_target(prev_RH, TARGET_RH, SENSOR_RH_DRIFT)
        T  = round(max(SENSOR_T_MIN,  min(SENSOR_T_MAX,  T)),  1)
        RH = round(max(SENSOR_RH_MIN, min(SENSOR_RH_MAX, RH)), 1)

    return {
        "timestamp":   datetime.now(),
        "temperature": T,
        "humidity":    RH
    }


# ============================================================================
# QUẢN LÝ LỊCH SỬ DỮ LIỆU REAL-TIME (SESSION)
# ============================================================================

def init_realtime_session(session_state):
    """Khởi tạo các biến session cho real-time. Gọi 1 lần khi app khởi động."""
    if 'rt_running'     not in session_state:
        session_state.rt_running     = False
    if 'rt_history'     not in session_state:
        session_state.rt_history     = []
    if 'rt_last_T'      not in session_state:
        session_state.rt_last_T      = None
    if 'rt_last_RH'     not in session_state:
        session_state.rt_last_RH     = None
    if 'rt_last_update' not in session_state:
        session_state.rt_last_update = None


def reset_realtime_session(session_state):
    """Xóa toàn bộ lịch sử và reset session. Gọi khi bấm 'Xóa dữ liệu'."""
    session_state.rt_running     = False
    session_state.rt_history     = []
    session_state.rt_last_T      = None
    session_state.rt_last_RH     = None
    session_state.rt_last_update = None


def should_update(session_state, interval_seconds=UPDATE_INTERVAL):
    """Kiểm tra xem đã đến lúc cập nhật chưa."""
    if session_state.rt_last_update is None:
        return True
    elapsed = (datetime.now() - session_state.rt_last_update).total_seconds()
    return elapsed >= interval_seconds


def push_new_reading(session_state, vpd_calculator, max_points=360):
    """
    Sinh bản ghi mới, tính VPD, lưu vào lịch sử session.
    max_points=360 tương đương 1 giờ với interval 10 giây.
    """
    reading = generate_sensor_reading(
        prev_T=session_state.rt_last_T,
        prev_RH=session_state.rt_last_RH
    )
    vpd = vpd_calculator(reading['temperature'], reading['humidity'])
    reading['vpd'] = vpd

    session_state.rt_history.append(reading)
    if len(session_state.rt_history) > max_points:
        session_state.rt_history = session_state.rt_history[-max_points:]

    session_state.rt_last_T      = reading['temperature']
    session_state.rt_last_RH     = reading['humidity']
    session_state.rt_last_update = reading['timestamp']
    return reading


def get_realtime_dataframe(session_state):
    """Chuyển lịch sử sang DataFrame. Trả về None nếu chưa có dữ liệu."""
    if not session_state.rt_history:
        return None
    df = pd.DataFrame(session_state.rt_history)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df = df.sort_values('timestamp').reset_index(drop=True)
    return df


def get_realtime_stats(session_state):
    """Tính thống kê VPD từ lịch sử. Trả về None nếu chưa có dữ liệu."""
    df = get_realtime_dataframe(session_state)
    if df is None or df.empty:
        return None
    vpd_series = df['vpd'].dropna()
    vpd_series = vpd_series[vpd_series.apply(lambda x: not (math.isnan(x) or math.isinf(x)))]
    if vpd_series.empty:
        return None
    return {
        'mean':   vpd_series.mean(),
        'min':    vpd_series.min(),
        'max':    vpd_series.max(),
        'median': vpd_series.median(),
        'count':  len(vpd_series)
    }


def get_realtime_table(session_state):
    """
    Trả về DataFrame đã định dạng để hiển thị bảng số liệu real-time.
    Cột: STT | Thời gian | Nhiệt độ (°C) | Độ ẩm (%) | VPD (kPa) | Trạng thái
    Sắp xếp mới nhất lên đầu.
    """
    df = get_realtime_dataframe(session_state)
    if df is None or df.empty:
        return None

    table = df.copy()
    table = table.iloc[::-1].reset_index(drop=True)  # Đảo ngược: mới nhất trên đầu
    table.index = table.index + 1                     # STT bắt đầu từ 1

    # Định dạng cột
    table['Thời gian']     = table['timestamp'].dt.strftime('%H:%M:%S')
    table['Nhiệt độ (°C)'] = table['temperature'].apply(lambda x: f"{x:.1f}")
    table['Độ ẩm (%)']     = table['humidity'].apply(lambda x: f"{x:.1f}")
    table['VPD (kPa)']     = table['vpd'].apply(
        lambda x: f"{x:.3f}" if pd.notna(x) and not math.isinf(x) else "N/A")

    # Trạng thái VPD
    def vpd_status_label(vpd):
        if pd.isna(vpd) or math.isinf(vpd):
            return "❓"
        if vpd < 0.4:   return "❌ Quá thấp"
        if vpd < 0.8:   return "⚠️ Thấp"
        if vpd <= 1.2:  return "✅ Tối ưu"
        if vpd <= 1.5:  return "⚠️ Cao"
        return "❌ Quá cao"

    table['Trạng thái'] = table['vpd'].apply(vpd_status_label)

    return table[['Thời gian', 'Nhiệt độ (°C)', 'Độ ẩm (%)', 'VPD (kPa)', 'Trạng thái']]
