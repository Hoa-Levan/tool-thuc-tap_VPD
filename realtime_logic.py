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

# Khoảng giá trị ngẫu nhiên mô phỏng thực tế nhà kính
SENSOR_T_MIN  = 18.0   # °C
SENSOR_T_MAX  = 35.0   # °C
SENSOR_RH_MIN = 30.0   # %
SENSOR_RH_MAX = 95.0   # %

# Biến động tối đa mỗi lần đọc (để số liệu trông tự nhiên, không nhảy đột ngột)
SENSOR_T_DRIFT  = 0.5  # °C
SENSOR_RH_DRIFT = 1.5  # %

# Tần suất cập nhật (giây)
UPDATE_INTERVAL = 60  # 1 phút


# ============================================================================
# HÀM SINH DỮ LIỆU CẢM BIẾN
# ============================================================================

def generate_sensor_reading(prev_T=None, prev_RH=None):
    """
    Sinh một bản ghi cảm biến mô phỏng.
    Nếu có giá trị trước (prev_T, prev_RH), số mới sẽ dao động nhẹ quanh đó
    để mô phỏng cảm biến thật (không nhảy đột ngột).

    Args:
        prev_T  : float | None — Nhiệt độ lần đọc trước
        prev_RH : float | None — Độ ẩm lần đọc trước

    Returns:
        dict với keys: timestamp, temperature, humidity
    """
    if prev_T is None:
        # Lần đầu: chọn ngẫu nhiên trong toàn khoảng
        T  = round(random.uniform(SENSOR_T_MIN, SENSOR_T_MAX), 1)
    else:
        # Các lần sau: dao động quanh giá trị trước
        delta_T = random.uniform(-SENSOR_T_DRIFT, SENSOR_T_DRIFT)
        T = round(max(SENSOR_T_MIN, min(SENSOR_T_MAX, prev_T + delta_T)), 1)

    if prev_RH is None:
        RH = round(random.uniform(SENSOR_RH_MIN, SENSOR_RH_MAX), 1)
    else:
        delta_RH = random.uniform(-SENSOR_RH_DRIFT, SENSOR_RH_DRIFT)
        RH = round(max(SENSOR_RH_MIN, min(SENSOR_RH_MAX, prev_RH + delta_RH)), 1)

    return {
        "timestamp": datetime.now(),
        "temperature": T,
        "humidity": RH
    }


# ============================================================================
# QUẢN LÝ LỊCH SỬ DỮ LIỆU REAL-TIME (SESSION)
# ============================================================================

def init_realtime_session(session_state):
    """
    Khởi tạo các biến session cần thiết cho chế độ real-time.
    Gọi 1 lần khi app khởi động.
    """
    if 'rt_running' not in session_state:
        session_state.rt_running = False          # Đang chạy hay không
    if 'rt_history' not in session_state:
        session_state.rt_history = []             # Danh sách bản ghi [{timestamp, T, RH, VPD}]
    if 'rt_last_T' not in session_state:
        session_state.rt_last_T = None            # Nhiệt độ lần đọc trước
    if 'rt_last_RH' not in session_state:
        session_state.rt_last_RH = None           # Độ ẩm lần đọc trước
    if 'rt_last_update' not in session_state:
        session_state.rt_last_update = None       # Thời điểm cập nhật gần nhất


def reset_realtime_session(session_state):
    """
    Xóa toàn bộ lịch sử và reset session real-time.
    Gọi khi người dùng bấm 'Dừng' hoặc 'Xóa dữ liệu'.
    """
    session_state.rt_running    = False
    session_state.rt_history    = []
    session_state.rt_last_T     = None
    session_state.rt_last_RH    = None
    session_state.rt_last_update = None


def should_update(session_state, interval_seconds=UPDATE_INTERVAL):
    """
    Kiểm tra xem đã đến lúc cập nhật dữ liệu chưa.

    Returns:
        bool — True nếu cần cập nhật
    """
    if session_state.rt_last_update is None:
        return True
    elapsed = (datetime.now() - session_state.rt_last_update).total_seconds()
    return elapsed >= interval_seconds


def push_new_reading(session_state, vpd_calculator, max_points=120):
    """
    Sinh bản ghi mới, tính VPD, lưu vào lịch sử session.

    Args:
        session_state  : st.session_state
        vpd_calculator : hàm calculate_vpd(T, RH) từ vpd_logic
        max_points     : số điểm tối đa lưu trong session (mặc định 120 = 2 giờ)

    Returns:
        dict — bản ghi vừa thêm {timestamp, temperature, humidity, vpd}
    """
    reading = generate_sensor_reading(
        prev_T=session_state.rt_last_T,
        prev_RH=session_state.rt_last_RH
    )

    vpd = vpd_calculator(reading['temperature'], reading['humidity'])
    reading['vpd'] = vpd

    # Lưu vào lịch sử, giới hạn số điểm
    session_state.rt_history.append(reading)
    if len(session_state.rt_history) > max_points:
        session_state.rt_history = session_state.rt_history[-max_points:]

    # Cập nhật trạng thái session
    session_state.rt_last_T      = reading['temperature']
    session_state.rt_last_RH     = reading['humidity']
    session_state.rt_last_update = reading['timestamp']

    return reading


def get_realtime_dataframe(session_state):
    """
    Chuyển lịch sử real-time sang DataFrame để vẽ biểu đồ.

    Returns:
        pd.DataFrame với columns: timestamp, temperature, humidity, vpd
        hoặc None nếu chưa có dữ liệu
    """
    if not session_state.rt_history:
        return None

    df = pd.DataFrame(session_state.rt_history)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df = df.sort_values('timestamp').reset_index(drop=True)
    return df


def get_realtime_stats(session_state):
    """
    Tính thống kê cơ bản từ lịch sử real-time.

    Returns:
        dict với mean, min, max, median, count của VPD
        hoặc None nếu chưa có dữ liệu
    """
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
