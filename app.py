"""
VPD Analysis Tool - Ứng dụng Streamlit để phân tích VPD cho cây trồng trong nhà kính
Main Application File
"""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import plotly.graph_objects as go
import plotly.express as px

from docfile_logic import (
    parse_json_file, prepare_dataframe, filter_data_by_period,
    format_date_range_display, get_data_completeness_message,
    calculate_statistics
)
from vpd_logic import calculate_vpd, get_vpd_assessment, categorize_vpd_status


# ============================================================================
# CẤU HÌNH STREAMLIT
# ============================================================================

st.set_page_config(
    page_title="VPD Analysis Tool",
    page_icon="🌱",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS tùy chỉnh
st.markdown("""
    <style>
    .metric-card {
        background-color: #f0f2f6;
        padding: 20px;
        border-radius: 10px;
        margin: 10px 0;
    }
    .optimal {
        background-color: #d4edda;
        color: #155724;
        padding: 10px;
        border-radius: 5px;
        border-left: 5px solid #28a745;
    }
    .warning {
        background-color: #fff3cd;
        color: #856404;
        padding: 10px;
        border-radius: 5px;
        border-left: 5px solid #ffc107;
    }
    .danger {
        background-color: #f8d7da;
        color: #721c24;
        padding: 10px;
        border-radius: 5px;
        border-left: 5px solid #dc3545;
    }
    </style>
    """, unsafe_allow_html=True)


# ============================================================================
# KHỞI TẠO SESSION STATE
# ============================================================================

if 'df' not in st.session_state:
    st.session_state.df = None
if 'original_df' not in st.session_state:
    st.session_state.original_df = None
if 'file_uploaded' not in st.session_state:
    st.session_state.file_uploaded = False


# ============================================================================
# HEADER
# ============================================================================

st.title("🌱 VPD Analysis Tool")
st.markdown("""
    Công cụ phân tích **VPD (Vapor Pressure Deficit)** dành cho cây trồng trong nhà kính
    - Nạp dữ liệu JSON
    - Tính toán VPD dựa trên nhiệt độ và độ ẩm
    - Đánh giá điều kiện và đưa ra khuyến cáo
""")

st.divider()


# ============================================================================
# SIDEBAR - NẠP FILE VÀ CÀI ĐẶT
# ============================================================================

with st.sidebar:
    st.header("⚙️ Cài đặt")
    
    # Nạp file
    st.subheader("📁 Nạp file JSON")
    uploaded_file = st.file_uploader(
        "Chọn file JSON chứa dữ liệu",
        type=['json'],
        help="File JSON phải chứa thời gian, nhiệt độ, độ ẩm"
    )
    
    if uploaded_file is not None:
        try:
            # Đọc file
            file_content = uploaded_file.getvalue()
            records = parse_json_file(file_content)
            
            if records:
                # Chuẩn bị DataFrame
                df = prepare_dataframe(records)
                
                if df is not None and not df.empty:
                    # Tính VPD cho tất cả bản ghi
                    df['vpd'] = df.apply(
                        lambda row: calculate_vpd(row['temperature'], row['humidity']),
                        axis=1
                    )
                    df['vpd_status'] = df['vpd'].apply(categorize_vpd_status)
                    
                    st.session_state.df = df
                    st.session_state.original_df = df.copy()
                    st.session_state.file_uploaded = True
                    
                    st.success(f"✅ Nạp thành công! {len(df)} bản ghi")
                    st.info(f"📅 Dữ liệu từ: {df['datetime'].min().strftime('%d/%m/%Y %H:%M')} đến {df['datetime'].max().strftime('%d/%m/%Y %H:%M')}")
                else:
                    st.error("❌ Không tìm thấy dữ liệu hợp lệ trong file")
            else:
                st.error("❌ Không thể phân tích file JSON")
        except Exception as e:
            st.error(f"❌ Lỗi: {str(e)}")
    
    st.divider()
    
    # Lựa chọn kỳ
    if st.session_state.file_uploaded:
        st.subheader("📊 Lựa chọn kỳ")
        
        period = st.radio(
            "Chọn kỳ xem dữ liệu:",
            options=['day', 'week', 'month', 'quarter', 'six_months', 'year'],
            format_func=lambda x: {
                'day': '📅 Ngày',
                'week': '📆 Tuần',
                'month': '📊 Tháng',
                'quarter': '📈 Quý',
                'six_months': '📉 6 tháng',
                'year': '📋 Năm'
            }[x]
        )
        
        # Lựa chọn ngày tham chiếu (mặc định là hôm nay)
        min_date = st.session_state.df['datetime'].min().date()
        max_date = st.session_state.df['datetime'].max().date()
        
        reference_date = st.date_input(
            "Chọn ngày tham chiếu:",
            value=min(datetime.now().date(), max_date),
            min_value=min_date,
            max_value=max_date
        )
        
        st.session_state.selected_period = period
        st.session_state.reference_date = datetime.combine(reference_date, datetime.min.time())
    else:
        st.warning("⚠️ Vui lòng nạp file JSON trước")


# ============================================================================
# MAIN CONTENT
# ============================================================================

if not st.session_state.file_uploaded:
    st.info("👈 Vui lòng nạp file JSON từ sidebar để bắt đầu")
else:
    # Lọc dữ liệu theo kỳ
    filtered_df, (actual_start, actual_end), has_full_period = filter_data_by_period(
        st.session_state.df,
        st.session_state.selected_period,
        st.session_state.reference_date
    )
    
    if filtered_df is None or filtered_df.empty:
        st.error(f"❌ Không có dữ liệu cho kỳ này")
    else:
        # Thông báo tính đầy đủ dữ liệu
        if not has_full_period:
            st.warning(
                f"⚠️ Dữ liệu không đầy đủ cho kỳ này. "
                f"Chỉ có chỉ số từ {actual_start.strftime('%d/%m/%Y')} "
                f"đến {actual_end.strftime('%d/%m/%Y')}"
            )
        
        # Tiêu đề với khoảng ngày
        date_range_display = format_date_range_display(actual_start, actual_end, st.session_state.selected_period)
        st.subheader(f"📊 Dữ liệu VPD: {date_range_display}")
        
        # ====================================================================
        # THỐNG KÊ
        # ====================================================================
        
        st.markdown("### 📈 Thống kê VPD")
        
        stats = calculate_statistics(filtered_df)
        
        if stats:
            col1, col2, col3, col4, col5 = st.columns(5)
            
            with col1:
                st.metric(
                    label="Trung bình",
                    value=f"{stats['mean']:.2f} kPa",
                    delta=None
                )
            
            with col2:
                st.metric(
                    label="Tối thiểu",
                    value=f"{stats['min']:.2f} kPa"
                )
            
            with col3:
                st.metric(
                    label="Tối đa",
                    value=f"{stats['max']:.2f} kPa"
                )
            
            with col4:
                st.metric(
                    label="Trung vị",
                    value=f"{stats['median']:.2f} kPa"
                )
            
            with col5:
                st.metric(
                    label="Số liệu",
                    value=f"{stats['count']}"
                )
        
        st.divider()
        
        # ====================================================================
        # ĐÁNH GIÁ TRẠNG THÁI
        # ====================================================================
        
        st.markdown("### 💡 Đánh giá trạng thái")
        
        # Tính toán trạng thái hiện tại (dữ liệu gần nhất)
        latest_row = filtered_df.iloc[-1]
        latest_vpd = latest_row['vpd']
        latest_assessment = get_vpd_assessment(latest_vpd)
        
        # Hiển thị đánh giá
        if latest_assessment['status'] == 'optimal':
            st.markdown(
                f"""
                <div class="optimal">
                    <h4>✅ {latest_assessment['description']}</h4>
                    <p>{latest_assessment['recommendation']}</p>
                </div>
                """,
                unsafe_allow_html=True
            )
        elif latest_assessment['status'] in ['low', 'high']:
            st.markdown(
                f"""
                <div class="warning">
                    <h4>⚠️ {latest_assessment['description']}</h4>
                    <p>{latest_assessment['recommendation']}</p>
                </div>
                """,
                unsafe_allow_html=True
            )
        else:
            st.markdown(
                f"""
                <div class="danger">
                    <h4>❌ {latest_assessment['description']}</h4>
                    <p>{latest_assessment['recommendation']}</p>
                </div>
                """,
                unsafe_allow_html=True
            )
        
        st.divider()
        
        # ====================================================================
        # BIỂU ĐỒ
        # ====================================================================
        
        st.markdown("### 📉 Biểu đồ dữ liệu")
        
        # Biểu đồ VPD
        fig_vpd = go.Figure()
        
        fig_vpd.add_trace(go.Scatter(
            x=filtered_df['datetime'],
            y=filtered_df['vpd'],
            mode='lines+markers',
            name='VPD',
            line=dict(color='#1f77b4', width=2),
            marker=dict(size=4)
        ))
        
        # Thêm vùng tối ưu
        fig_vpd.add_hrect(
            y0=0.8, y1=1.2,
            fillcolor="green", opacity=0.1,
            layer="below", line_width=0,
            annotation_text="Khoảng tối ưu (0.8-1.2 kPa)",
            annotation_position="right"
        )
        
        fig_vpd.update_layout(
            title="VPD theo thời gian",
            xaxis_title="Thời gian",
            yaxis_title="VPD (kPa)",
            hovermode="x unified",
            height=400,
            template="plotly_white"
        )
        
        st.plotly_chart(fig_vpd, use_container_width=True)
        
        # Biểu đồ nhiệt độ và độ ẩm
        fig_temp_humidity = make_subplots(
            rows=2, cols=1,
            subplot_titles=("Nhiệt độ", "Độ ẩm"),
            shared_xaxes=True,
            vertical_spacing=0.1
        )
        
        from plotly.subplots import make_subplots
        
        fig_temp_humidity = make_subplots(
            rows=2, cols=1,
            subplot_titles=("Nhiệt độ", "Độ ẩm"),
            shared_xaxes=True,
            vertical_spacing=0.1
        )
        
        fig_temp_humidity.add_trace(
            go.Scatter(
                x=filtered_df['datetime'],
                y=filtered_df['temperature'],
                mode='lines',
                name='Nhiệt độ',
                line=dict(color='red', width=2)
            ),
            row=1, col=1
        )
        
        fig_temp_humidity.add_trace(
            go.Scatter(
                x=filtered_df['datetime'],
                y=filtered_df['humidity'],
                mode='lines',
                name='Độ ẩm',
                line=dict(color='blue', width=2)
            ),
            row=2, col=1
        )
        
        fig_temp_humidity.update_yaxes(title_text="Nhiệt độ (°C)", row=1, col=1)
        fig_temp_humidity.update_yaxes(title_text="Độ ẩm (%)", row=2, col=1)
        fig_temp_humidity.update_xaxes(title_text="Thời gian", row=2, col=1)
        
        fig_temp_humidity.update_layout(
            height=500,
            hovermode="x unified",
            template="plotly_white"
        )
        
        st.plotly_chart(fig_temp_humidity, use_container_width=True)
        
        st.divider()
        
        # ====================================================================
        # BẢNG DỮ LIỆU
        # ====================================================================
        
        st.markdown("### 📋 Bảng dữ liệu")
        
        # Hiển thị bảng
        display_df = filtered_df.copy()
        display_df['datetime'] = display_df['datetime'].dt.strftime('%d/%m/%Y %H:%M')
        display_df = display_df[['datetime', 'temperature', 'humidity', 'vpd', 'vpd_status']]
        display_df.columns = ['Thời gian', 'Nhiệt độ (°C)', 'Độ ẩm (%)', 'VPD (kPa)', 'Trạng thái']
        
        # Định dạng số
        display_df['Nhiệt độ (°C)'] = display_df['Nhiệt độ (°C)'].apply(lambda x: f"{x:.2f}")
        display_df['Độ ẩm (%)'] = display_df['Độ ẩm (%)'].apply(lambda x: f"{x:.2f}")
        display_df['VPD (kPa)'] = display_df['VPD (kPa)'].apply(lambda x: f"{x:.2f}")
        
        # Ánh xạ trạng thái
        status_map = {
            'optimal': '✅ Tối ưu',
            'warning': '⚠️ Cảnh báo',
            'danger': '❌ Nguy hiểm',
            'unknown': '❓ Không xác định'
        }
        display_df['Trạng thái'] = display_df['Trạng thái'].map(status_map)
        
        st.dataframe(display_df, use_container_width=True, hide_index=True)
        
        # Tùy chọn tải xuống
        csv = display_df.to_csv(index=False, encoding='utf-8-sig')
        st.download_button(
            label="📥 Tải xuống CSV",
            data=csv,
            file_name=f"vpd_analysis_{actual_start.strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )

st.divider()

# Footer
st.markdown("""
    ---
    **VPD Analysis Tool** | Công cụ phân tích VPD cho cây trồng trong nhà kính
    
    💡 **Ghi chú:**
    - VPD tối ưu: 0.8 - 1.2 kPa
    - VPD quá thấp (< 0.8 kPa): Độ ẩm cao, tăng nguy cơ bệnh nấm
    - VPD quá cao (> 1.2 kPa): Khô quá, cây mất nước nhanh
    
    📧 Liên hệ: [GitHub Repository](https://github.com/Hoa-Levan/tool-thuc-tap_VPD)
""")
