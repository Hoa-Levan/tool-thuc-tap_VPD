"""
Document File Logic Module - Xử lý file JSON và dữ liệu
"""
import json
from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Optional
import pandas as pd


def parse_json_file(file_content):
    """
    Phân tích file JSON
    
    Args:
        file_content: Nội dung file JSON (bytes hoặc string)
        
    Returns:
        List các bản ghi hoặc None nếu lỗi
    """
    try:
        if isinstance(file_content, bytes):
            data = json.loads(file_content.decode('utf-8'))
        else:
            data = json.loads(file_content)
        
        # Nếu là list, trả về trực tiếp
        if isinstance(data, list):
            return data
        # Nếu là dict, check có key 'data' hoặc 'records' không
        elif isinstance(data, dict):
            if 'data' in data:
                return data['data']
            elif 'records' in data:
                return data['records']
            # Nếu dict có chứa "_id", coi đó là một bản ghi đơn
            elif '_id' in data:
                return [data]
            else:
                return [data]
        
        return None
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        raise Exception(f"Lỗi đọc file JSON: {str(e)}")


def parse_datetime(datetime_str):
    """
    Phân tích chuỗi thời gian với nhiều định dạng khác nhau
    
    Args:
        datetime_str: Chuỗi thời gian
        
    Returns:
        datetime object hoặc None
    """
    if not datetime_str:
        return None
    
    datetime_str = str(datetime_str).strip()
    
    # Danh sách các định dạng để thử
    formats = [
        "%Y-%m-%d %H-%M-%S",      # 2025-03-25 12-34-44
        "%Y-%m-%d %H:%M:%S",      # 2025-03-25 12:34:44
        "%Y-%m-%d %H-%M",         # 2025-03-25 12-34
        "%Y-%m-%d %H:%M",         # 2025-03-25 12:34
        "%d-%m-%Y %H-%M-%S",      # 25-03-2025 12-34-44
        "%d-%m-%Y %H:%M:%S",      # 25-03-2025 12:34:44
        "%Y-%m-%d",               # 2025-03-25
        "%d-%m-%Y",               # 25-03-2025
        "%Y/%m/%d %H:%M:%S",      # 2025/03/25 12:34:44
    ]
    
    for fmt in formats:
        try:
            return datetime.strptime(datetime_str, fmt)
        except ValueError:
            continue
    
    return None


def extract_temperature_humidity(record: Dict) -> Tuple[Optional[float], Optional[float]]:
    """
    Trích xuất nhiệt độ và độ ẩm từ bản ghi
    Hỗ trợ các tên cột khác nhau
    
    Returns:
        (temperature, humidity) hoặc (None, None)
    """
    temp = None
    humidity = None
    
    # Các tên có thể cho nhiệt độ
    temp_keys = ['Nhiệt Độ', 'Nhiệt độ', 'nhiệt độ', 'TempKK', 'tempkk', 'Temperature', 'temperature', 'T']
    
    # Các tên có thể cho độ ẩm
    humidity_keys = ['Độ ẩm', 'độ ẩm', 'HumiKK', 'humikk', 'Humidity', 'humidity', 'RH', 'H']
    
    for key in temp_keys:
        if key in record:
            try:
                temp_value = float(record[key])
                # Kiểm tra xem có phải Kelvin không (thường > 100)
                if temp_value > 100:
                    temp = temp_value - 273.15  # Chuyển K sang C
                else:
                    temp = temp_value
                break
            except (ValueError, TypeError):
                continue
    
    for key in humidity_keys:
        if key in record:
            try:
                humidity = float(record[key])
                break
            except (ValueError, TypeError):
                continue
    
    return temp, humidity


def prepare_dataframe(records: List[Dict]) -> pd.DataFrame:
    """
    Chuẩn bị DataFrame từ danh sách bản ghi
    Thêm cột thời gian chuẩn hóa, nhiệt độ, độ ẩm
    
    Args:
        records: Danh sách bản ghi từ JSON
        
    Returns:
        DataFrame hoặc None nếu không có dữ liệu hợp lệ
    """
    if not records:
        return None
    
    processed_records = []
    
    for record in records:
        # Tìm cột thời gian
        datetime_str = None
        datetime_keys = ['Thời gian', 'thời gian', 'Ngày giờ', 'ngày giờ', 'Timestamp', 'timestamp', 'datetime']
        
        for key in datetime_keys:
            if key in record:
                datetime_str = record[key]
                break
        
        if not datetime_str:
            continue
        
        dt = parse_datetime(datetime_str)
        if not dt:
            continue
        
        temp, humidity = extract_temperature_humidity(record)
        
        # Chỉ thêm nếu có cả nhiệt độ và độ ẩm
        if temp is not None and humidity is not None:
            processed_records.append({
                'datetime': dt,
                'temperature': temp,
                'humidity': humidity,
                'original_record': record
            })
    
    if not processed_records:
        return None
    
    df = pd.DataFrame(processed_records)
    df = df.sort_values('datetime').reset_index(drop=True)
    
    return df


def get_date_range_by_period(period: str, reference_date: Optional[datetime] = None) -> Tuple[datetime, datetime]:
    """
    Lấy khoảng ngày theo kỳ (ngày, tuần, tháng, quý, 6 tháng, năm)
    
    Args:
        period: 'day', 'week', 'month', 'quarter', 'six_months', 'year'
        reference_date: Ngày tham chiếu (mặc định là hôm nay)
        
    Returns:
        (start_date, end_date)
    """
    if reference_date is None:
        reference_date = datetime.now()
    
    if period == 'day':
        start = reference_date.replace(hour=0, minute=0, second=0, microsecond=0)
        end = start + timedelta(days=1)
    
    elif period == 'week':
        # Bắt đầu từ thứ Hai (weekday=0)
        days_since_monday = reference_date.weekday()
        start = (reference_date - timedelta(days=days_since_monday)).replace(hour=0, minute=0, second=0, microsecond=0)
        end = start + timedelta(days=7)
    
    elif period == 'month':
        # Bắt đầu từ ngày 1 tháng hiện tại
        start = reference_date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        # Tháng sau
        if reference_date.month == 12:
            end = start.replace(year=start.year + 1, month=1)
        else:
            end = start.replace(month=start.month + 1)
    
    elif period == 'quarter':
        # Quý: 1 (1-3), 2 (4-6), 3 (7-9), 4 (10-12)
        quarter = (reference_date.month - 1) // 3 + 1
        start_month = (quarter - 1) * 3 + 1
        start = reference_date.replace(month=start_month, day=1, hour=0, minute=0, second=0, microsecond=0)
        end = start + timedelta(days=92)  # ~3 tháng
    
    elif period == 'six_months':
        start = reference_date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        end = start + timedelta(days=183)  # ~6 tháng
    
    elif period == 'year':
        start = reference_date.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        end = start.replace(year=start.year + 1)
    
    else:
        raise ValueError(f"Kỳ không hợp lệ: {period}")
    
    return start, end


def filter_data_by_period(df: pd.DataFrame, period: str, reference_date: Optional[datetime] = None) -> Tuple[pd.DataFrame, Tuple[datetime, datetime], bool]:
    """
    Lọc dữ liệu theo kỳ
    
    Args:
        df: DataFrame chứa dữ liệu
        period: Kỳ ('day', 'week', 'month', 'quarter', 'six_months', 'year')
        reference_date: Ngày tham chiếu
        
    Returns:
        (filtered_df, (actual_start, actual_end), has_full_period)
        has_full_period: True nếu dữ liệu đầy đủ cho kỳ đó
    """
    start, end = get_date_range_by_period(period, reference_date)
    
    # Lọc dữ liệu
    filtered_df = df[(df['datetime'] >= start) & (df['datetime'] < end)]
    
    if filtered_df.empty:
        return None, (start, end), False
    
    # Kiểm tra xem dữ liệu có đầy đủ không
    actual_start = filtered_df['datetime'].min()
    actual_end = filtered_df['datetime'].max()
    
    # Kiểm tra xem ngày bắt đầu có khớp không
    has_full_start = actual_start.date() == start.date()
    # Kiểm tra xem ngày kết thúc có khớp không (không quan tâm giờ)
    has_full_end = actual_end.date() == (end - timedelta(days=1)).date()
    
    has_full_period = has_full_start and has_full_end
    
    return filtered_df, (actual_start, actual_end), has_full_period


def format_date_range_display(start_date: datetime, end_date: datetime, period: str) -> str:
    """
    Định dạng chuỗi hiển thị khoảng ngày theo yêu cầu
    
    Format: "DD/MM-DD/MM" (ví dụ: "25/03-31/03")
    
    Args:
        start_date: Ngày bắt đầu
        end_date: Ngày kết thúc (không bao gồm)
        period: Kỳ
        
    Returns:
        Chuỗi định dạng
    """
    # Điều chỉnh end_date để không bao gồm
    end_date_adj = end_date - timedelta(days=1)
    
    if start_date.month == end_date_adj.month:
        # Cùng tháng
        return f"{start_date.strftime('%d/%m')}-{end_date_adj.strftime('%d/%m')}"
    else:
        # Khác tháng
        return f"{start_date.strftime('%d/%m')}-{end_date_adj.strftime('%d/%m')}"


def get_data_completeness_message(filtered_df: pd.DataFrame, actual_start: datetime, actual_end: datetime, period: str) -> str:
    """
    Tạo thông báo về tính đầy đủ dữ liệu
    
    Args:
        filtered_df: DataFrame đã lọc
        actual_start: Ngày bắt đầu dữ liệu thực tế
        actual_end: Ngày kết thúc dữ liệu thực tế
        period: Kỳ
        
    Returns:
        Thông báo
    """
    if filtered_df is None or filtered_df.empty:
        return f"⚠️ Không có dữ liệu cho {period}"
    
    start_str = f"{actual_start.strftime('%d/%m/%Y')}"
    end_str = f"{actual_end.strftime('%d/%m/%Y')}"
    
    return f"📊 Dữ liệu từ {start_str} đến {end_str}"


def calculate_statistics(df: pd.DataFrame) -> Dict:
    """
    Tính toán các chỉ số thống kê cho dữ liệu
    
    Args:
        df: DataFrame chứa cột 'vpd'
        
    Returns:
        Dict chứa các thống kê
    """
    if df is None or df.empty:
        return None
    
    if 'vpd' not in df.columns:
        return None
    
    vpd_values = df['vpd'].dropna()
    
    if vpd_values.empty:
        return None
    
    return {
        'mean': vpd_values.mean(),
        'min': vpd_values.min(),
        'max': vpd_values.max(),
        'median': vpd_values.median(),
        'std': vpd_values.std(),
        'count': len(vpd_values)
    }
