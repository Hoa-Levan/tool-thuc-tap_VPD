import streamlit as st
import pandas as pd
from datetime import datetime
import json
import math
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from docfile_logic import (
    parse_json_file, prepare_dataframe, filter_data_by_period,
    format_date_range_display, calculate_statistics
)
from vpd_logic import calculate_vpd, get_vpd_assessment, categorize_vpd_status
from canhbao_logic import send_vpd_alert, validate_email
from zalo_logic import send_zalo_alert, validate_phone_number, validate_zalo_token
from realtime_logic import (
    init_realtime_session, reset_realtime_session,
    should_update, push_new_reading,
    get_realtime_dataframe, get_realtime_stats,
    get_realtime_table,
    UPDATE_INTERVAL
)

# ============================================================================
# CẤU HÌNH STREAMLIT
# ============================================================================

st.set_page_config(
    page_title="Xem chỉ số của VPD",
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
        padding: 15px;
        border-radius: 8px;
        border-left: 5px solid #28a745;
        margin: 10px 0;
    }
    .warning {
        background-color: #fff3cd;
        color: #856404;
        padding: 15px;
        border-radius: 8px;
        border-left: 5px solid #ffc107;
        margin: 10px 0;
    }
    .danger {
        background-color: #f8d7da;
        color: #721c24;
        padding: 15px;
        border-radius: 8px;
        border-left: 5px solid #dc3545;
        margin: 10px 0;
    }
    .info-box {
        background-color: #cfe2ff;
        color: #084298;
        padding: 12px;
        border-radius: 5px;
        border-left: 4px solid #0d6efd;
        margin: 8px 0;
    }
    .alert-box {
        background-color: #f0f4ff;
        padding: 15px;
        border-radius: 8px;
        border: 2px solid #667eea;
        margin: 15px 0;
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
if 'selected_period' not in st.session_state:
    st.session_state.selected_period = 'day'
if 'reference_date' not in st.session_state:
    st.session_state.reference_date = datetime.now()

# Khởi tạo session real-time
init_realtime_session(st.session_state)

# ============================================================================
# HEADER
# ============================================================================

st.title("🌱 VPD Analysis Tool")
st.markdown("""
    Công cụ phân tích **VPD (Vapor Pressure Deficit)** dành cho cây trồng trong nhà kính
    - Nạp dữ liệu JSON từ máy
    - Tính toán VPD dựa trên nhiệt độ và độ ẩm
    - Đánh giá điều kiện và đưa ra khuyến cáo
    - Gửi cảnh báo VPD qua Gmail hoặc Zalo
""")

st.divider()

# ============================================================================
# SIDEBAR - NẠP FILE VÀ CÀI ĐẶT
# ============================================================================

with st.sidebar:
    st.header("⚙️ Cài đặt")

    # [MỚI] Sidebar chia 2 tab: Nạp file | Real-time
    tab_file, tab_rt = st.tabs(["📁 Nạp file", "📡 Real-time"])

    # -----------------------------------------------------------------------
    # TAB 1: NẠP FILE (giữ nguyên logic cũ, chỉ thụt vào trong with tab_file)
    # -----------------------------------------------------------------------
    with tab_file:
        st.subheader("📁 Nạp file JSON")
        uploaded_file = st.file_uploader(
            "Chọn file JSON chứa dữ liệu",
            type=['json'],
            help="File JSON phải chứa thời gian, nhiệt độ, độ ẩm"
        )

        if uploaded_file is not None:
            try:
                file_content = uploaded_file.getvalue()
                records = parse_json_file(file_content)

                if records:
                    df = prepare_dataframe(records)

                    if df is not None and not df.empty:
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

            min_date = st.session_state.df['datetime'].min().date()
            max_date = st.session_state.df['datetime'].max().date()

            reference_date = st.date_input(
                "Chọn ngày tham chiếu:",
                value=min(datetime.now().date(), max_date),
                min_value=min_date,
                max_value=max_date
            )
            from datetime import timedelta

            if period == 'day':
                st.caption(f"🔍 Đang xem dữ liệu ngày: **{reference_date.strftime('%d/%m/%Y')}**")
            elif period == 'week':
                start_of_week = reference_date - timedelta(days=reference_date.weekday())
                end_of_week = start_of_week + timedelta(days=6)
                st.info(f"📆 **Tuần được chọn:**\nTừ **{start_of_week.strftime('%d/%m/%Y')}** đến **{end_of_week.strftime('%d/%m/%Y')}**")
            elif period == 'month':
                st.info(f"📊 **Tháng được chọn:**\nToàn bộ tháng **{reference_date.strftime('%m/%Y')}**")
            elif period == 'quarter':
                quarter = (reference_date.month - 1) // 3 + 1
                st.info(f"📈 **Quý được chọn:**\nQuý **{quarter}** năm **{reference_date.year}**")
            elif period == 'six_months':
                half = "Đầu" if reference_date.month <= 6 else "Cuối"
                st.info(f"📉 **Kỳ 6 tháng được chọn:**\n6 tháng **{half}** năm **{reference_date.year}**")
            elif period == 'year':
                st.info(f"📋 **Năm được chọn:**\nToàn bộ năm **{reference_date.year}**")

            st.session_state.selected_period = period
            st.session_state.reference_date = datetime.combine(reference_date, datetime.min.time())
        else:
            st.warning("⚠️ Vui lòng nạp file JSON trước")

    # -----------------------------------------------------------------------
    # [MỚI] TAB 2: REAL-TIME
    # -----------------------------------------------------------------------
    with tab_rt:
        st.subheader("📡 Chế độ Real-time")
        st.caption("Dữ liệu mô phỏng cảm biến, cập nhật mỗi 1 phút")

        rt_col1, rt_col2 = st.columns(2)
        with rt_col1:
            if not st.session_state.rt_running:
                if st.button("▶️ Bắt đầu", use_container_width=True, type="primary", key="btn_rt_start"):
                    st.session_state.rt_running = True
                    st.rerun()
            else:
                if st.button("⏹️ Dừng", use_container_width=True, key="btn_rt_stop"):
                    st.session_state.rt_running = False
                    st.rerun()
        with rt_col2:
            if st.button("🗑️ Xóa dữ liệu", use_container_width=True, key="btn_rt_clear"):
                reset_realtime_session(st.session_state)
                st.rerun()

        if st.session_state.rt_running:
            st.success("🟢 Đang chạy")
            count = len(st.session_state.rt_history)
            st.caption(f"Đã thu thập: {count} điểm dữ liệu")
        else:
            st.warning("⚫ Chưa chạy")


# ============================================================================
# MAIN CONTENT - 2 TAB NGANG
# ============================================================================

tab_vpd, tab_realtime = st.tabs(["📊 Dữ liệu VPD", "📡 Real-time"])

# ============================================================================
# TAB 1: DỮ LIỆU VPD (từ file)
# ============================================================================
with tab_vpd:
    if not st.session_state.file_uploaded:
        st.info("👈 Vui lòng nạp file JSON từ sidebar để bắt đầu")
    else:
        filtered_df, (actual_start, actual_end), has_full_period = filter_data_by_period(
            st.session_state.df,
            st.session_state.selected_period,
            st.session_state.reference_date
        )

        if filtered_df is None or filtered_df.empty:
            st.error(f"❌ Không có dữ liệu cho kỳ này")
        else:
            if not has_full_period:
                st.markdown(f"""
                    <div class="info-box">
                    ⚠️ <strong>Dữ liệu không đầy đủ cho kỳ này.</strong> Chỉ có chỉ số từ <strong>{actual_start.strftime('%d/%m/%Y')}</strong> đến <strong>{actual_end.strftime('%d/%m/%Y')}</strong>
                    </div>
                    """, unsafe_allow_html=True)

            date_range_display = format_date_range_display(actual_start, actual_end, st.session_state.selected_period)
            st.subheader(f"📊 Dữ liệu VPD: {date_range_display}")

            # ================================================================
            # THỐNG KÊ
            # ================================================================
            st.markdown("### 📈 Thống kê VPD")
            stats = calculate_statistics(filtered_df)
            if stats:
                col1, col2, col3, col4, col5 = st.columns(5)
                with col1:
                    st.metric(label="Trung bình", value=f"{stats['mean']:.2f} kPa")
                with col2:
                    st.metric(label="Tối thiểu",  value=f"{stats['min']:.2f} kPa")
                with col3:
                    st.metric(label="Tối đa",     value=f"{stats['max']:.2f} kPa")
                with col4:
                    st.metric(label="Trung vị",   value=f"{stats['median']:.2f} kPa")
                with col5:
                    st.metric(label="Số liệu",    value=f"{stats['count']}")

            st.divider()

            # ================================================================
            # ĐÁNH GIÁ TRẠNG THÁI
            # ================================================================
            st.markdown("### 💡 Đánh giá trạng thái (Dựa trên VPD trung bình)")
            vpd_values = filtered_df['vpd'].dropna()
            valid_vpd = vpd_values[~vpd_values.apply(lambda x: math.isnan(x) or math.isinf(x))]

            if len(valid_vpd) > 0:
                avg_vpd = valid_vpd.mean()
                avg_T   = filtered_df['temperature'].dropna().mean()
                avg_RH  = filtered_df['humidity'].dropna().mean()
                latest_assessment = get_vpd_assessment(avg_vpd, T=avg_T, RH=avg_RH)

                if latest_assessment['status'] == 'optimal':
                    st.markdown(
                        f"""<div class="optimal">
                            <h4>✅ {latest_assessment['description']}</h4>
                            <p>{latest_assessment['recommendation']}</p>
                        </div>""", unsafe_allow_html=True)
                elif latest_assessment['status'] in ['low', 'high']:
                    cause_text = f"<p>🔍 <strong>Nguyên nhân:</strong> {latest_assessment['cause']}</p>" if latest_assessment['cause'] else ""
                    st.markdown(
                        f"""<div class="warning">
                            <h4>⚠️ {latest_assessment['description']}</h4>
                            {cause_text}
                            <p>{latest_assessment['recommendation']}</p>
                        </div>""", unsafe_allow_html=True)
                else:
                    st.markdown(
                        f"""<div class="danger">
                            <h4>❌ {latest_assessment['description']}</h4>
                            <p>{latest_assessment['recommendation']}</p>
                        </div>""", unsafe_allow_html=True)
            else:
                st.error("❌ Không có dữ liệu VPD hợp lệ để đánh giá")

            st.divider()

            # ================================================================
            # BỐ CỤC 2 CỘT: BIỂU ĐỒ (TRÁI) & CẢNH BÁO (PHẢI)
            # ================================================================
            col_left, col_right = st.columns([1.1, 0.9])

            with col_left:
                st.markdown("### 📉 Biểu đồ dữ liệu")
                chart_df = filtered_df.copy()
                chart_df['datetime'] = pd.to_datetime(chart_df['datetime'])
                chart_df = chart_df.sort_values('datetime', ascending=True)
                vn_weekdays = {0: 'Thứ 2', 1: 'Thứ 3', 2: 'Thứ 4', 3: 'Thứ 5', 4: 'Thứ 6', 5: 'Thứ 7', 6: 'CN'}

                if st.session_state.selected_period in ['day', 'week']:
                    chart_df['Thời gian hiển thị'] = chart_df['datetime'].apply(
                        lambda x: f"{vn_weekdays[x.weekday()]} {x.strftime('%d/%m %H:%M')}")
                else:
                    chart_df['Thời gian hiển thị'] = chart_df['datetime'].apply(
                        lambda x: f"{vn_weekdays[x.weekday()]} {x.strftime('%d/%m')}")
                chart_df = chart_df.set_index('Thời gian hiển thị')

                st.markdown("#### VPD theo thời gian")
                vpd_chart_data = chart_df[['vpd']].rename(columns={'vpd': 'VPD (kPa)'}).dropna()
                if not vpd_chart_data.empty:
                    fig_vpd = go.Figure()
                    vpd_zones = [
                        (0,   0.4, 'rgba(220,53,69,0.15)',  'Quá thấp'),
                        (0.4, 0.8, 'rgba(255,193,7,0.18)',  'Thấp'),
                        (0.8, 1.2, 'rgba(40,167,69,0.18)',  'Tối ưu'),
                        (1.2, 1.5, 'rgba(255,193,7,0.18)',  'Cao'),
                        (1.5, 3.0, 'rgba(220,53,69,0.15)',  'Quá cao'),
                    ]
                    for y0, y1, color, label in vpd_zones:
                        fig_vpd.add_hrect(y0=y0, y1=y1, fillcolor=color, line_width=0,
                                         annotation_text=label, annotation_position='left',
                                         annotation=dict(font_size=10, font_color='rgba(255,255,255,0.45)'))
                    fig_vpd.add_trace(go.Scatter(
                        x=vpd_chart_data.index, y=vpd_chart_data['VPD (kPa)'],
                        name='VPD (kPa)', line=dict(color='#00BFFF', width=2)))
                    fig_vpd.update_layout(
                        plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
                        font=dict(color='white'),
                        yaxis=dict(title='VPD (kPa)',
                                   range=[0, max(3.0, vpd_chart_data['VPD (kPa)'].max() * 1.1)],
                                   gridcolor='rgba(255,255,255,0.1)'),
                        xaxis=dict(gridcolor='rgba(255,255,255,0.05)'),
                        hovermode='x unified', height=300,
                        margin=dict(l=0, r=0, t=10, b=0), showlegend=False)
                    st.plotly_chart(fig_vpd, use_container_width=True)
                else:
                    st.warning("⚠️ Không có dữ liệu VPD hợp lệ để hiển thị")

                chart_col1, chart_col2, chart_col3 = st.columns(3)
                with chart_col1:
                    st.markdown("**Khoảng tối ưu:** 0.8 - 1.2 kPa  \n*Điều kiện lý tưởng cho cây*")
                with chart_col2:
                    st.markdown("**VPD thấp:** < 0.8 kPa  \n*Độ ẩm cao - Tăng thông thoáng*")
                with chart_col3:
                    st.markdown("**VPD cao:** > 1.2 kPa  \n*Độ ẩm thấp - Tăng tưới nước*")

                st.markdown("#### Nhiệt độ & Độ ẩm theo thời gian")
                fig_th = make_subplots(specs=[[{"secondary_y": True}]])
                fig_th.add_trace(go.Scatter(x=chart_df.index, y=chart_df['temperature'],
                                            name='Nhiệt độ (°C)', line=dict(color='#FF6B6B', width=2)),
                                 secondary_y=False)
                fig_th.add_trace(go.Scatter(x=chart_df.index, y=chart_df['humidity'],
                                            name='Độ ẩm (%)', line=dict(color='#4ECDC4', width=2)),
                                 secondary_y=True)
                fig_th.update_layout(
                    plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
                    font=dict(color='white'), legend=dict(orientation='h', y=1.12),
                    hovermode='x unified', height=280, margin=dict(l=0, r=0, t=30, b=0))
                fig_th.update_yaxes(title_text='Nhiệt độ (°C)', secondary_y=False,
                                    color='#FF6B6B', gridcolor='rgba(255,255,255,0.1)')
                fig_th.update_yaxes(title_text='Độ ẩm (%)', secondary_y=True,
                                    color='#4ECDC4', gridcolor='rgba(255,255,255,0.1)')
                fig_th.update_xaxes(gridcolor='rgba(255,255,255,0.05)')
                st.plotly_chart(fig_th, use_container_width=True)

            with col_right:
                st.markdown("### 📧 Gửi cảnh báo VPD")
                alert_tab1, alert_tab2 = st.tabs(["📧 Gmail", "💬 Zalo"])

                with alert_tab1:
                    with st.expander("⚙️ Cài đặt gửi cảnh báo Gmail", expanded=True):
                        alert_col1, alert_col2 = st.columns(2)
                        with alert_col1:
                            recipient_email = st.text_input(
                                "📧 Email nhận cảnh báo", placeholder="your.email@gmail.com",
                                help="Email sẽ nhận cảnh báo VPD", key="alert_rec_email")
                        with alert_col2:
                            st.markdown("**ℹ️ Mốc thời gian gửi:**")
                            alert_interval = st.selectbox(
                                "Chọn mốc gửi",
                                options=['1 giờ', '2 giờ', '3 giờ', '6 giờ', '12 giờ', '1 ngày'],
                                label_visibility="collapsed", key="alert_interval_select")
                        alert_col3, alert_col4 = st.columns(2)
                        with alert_col3:
                            sender_email = st.text_input(
                                "📨 Email Gmail (người gửi)", placeholder="your.gmail@gmail.com",
                                help="Email Gmail của bạn", type="default", key="alert_send_email")
                        with alert_col4:
                            sender_password = st.text_input(
                                "🔑 Mật khẩu ứng dụng Gmail", placeholder="xxxx xxxx xxxx xxxx",
                                help="Tạo mật khẩu ứng dụng tại myaccount.google.com",
                                type="password", key="alert_send_pwd")
                        st.info("""
                        💡 **Hướng dẫn lấy mật khẩu ứng dụng Gmail:**
                        1. Truy cập [myaccount.google.com](https://myaccount.google.com)
                        2. Chọn **Security** → **App passwords**
                        3. Chọn **Mail** và **Windows Computer**
                        4. Copy mật khẩu 16 ký tự
                        """)
                        btn_col1, btn_col2, btn_col3 = st.columns([1.5, 1, 1.5])
                        with btn_col1:
                            send_alert = st.button("✉️ Xác nhận gửi cảnh báo", type="primary",
                                                   use_container_width=True, key="btn_send_alert")
                        if send_alert:
                            if not recipient_email:
                                st.error("❌ Vui lòng nhập email nhận cảnh báo")
                            elif not validate_email(recipient_email):
                                st.error("❌ Email không hợp lệ")
                            elif not sender_email or not sender_password:
                                st.error("❌ Vui lòng nhập email Gmail và mật khẩu ứng dụng")
                            elif len(valid_vpd) == 0:
                                st.error("❌ Không có dữ liệu VPD hợp lệ để gửi cảnh báo")
                            else:
                                latest_row = filtered_df[filtered_df['vpd'].notna()].iloc[-1]
                                latest_vpd_val  = latest_row['vpd']
                                latest_temp     = latest_row['temperature']
                                latest_humidity = latest_row['humidity']
                                latest_assessment_send = get_vpd_assessment(latest_vpd_val)
                                with st.spinner("📤 Đang gửi cảnh báo..."):
                                    success, message = send_vpd_alert(
                                        recipient_email=recipient_email,
                                        vpd_value=latest_vpd_val,
                                        temperature=latest_temp,
                                        humidity=latest_humidity,
                                        assessment=latest_assessment_send,
                                        sender_email=sender_email,
                                        sender_password=sender_password)
                                if success:
                                    st.success(message)
                                    st.markdown(f"""
                                    <div class="alert-box">
                                    <h4>✅ Cảnh báo đã gửi thành công!</h4>
                                    <p>📧 Gửi đến: <strong>{recipient_email}</strong></p>
                                    <p>📊 Giá trị VPD: <strong>{latest_vpd_val:.2f} kPa</strong></p>
                                    <p>🌡️ Nhiệt độ: <strong>{latest_temp:.2f}°C</strong></p>
                                    <p>💧 Độ ẩm: <strong>{latest_humidity:.2f}%</strong></p>
                                    <p>📌 Mốc gửi: <strong>Mỗi {alert_interval}</strong></p>
                                    </div>""", unsafe_allow_html=True)
                                else:
                                    st.error(message)

                with alert_tab2:
                    with st.expander("⚙️ Cài đặt gửi cảnh báo Zalo", expanded=True):
                        st.info("""
                        💡 **Hướng dẫn thiết lập Zalo Official Account:**
                        1. Truy cập [Zalo Official Account](https://oa.zalo.me)
                        2. Tạo hoặc đăng nhập vào Zalo OA
                        3. Vào **Cài đặt** → **Kết nối API** để lấy OA ID và Access Token
                        4. Nhập thông tin vào form dưới đây
                        """)
                        zalo_col1, zalo_col2 = st.columns(2)
                        with zalo_col1:
                            zalo_oa_id = st.text_input("🆔 Zalo OA ID", placeholder="123456789",
                                                       help="ID của Zalo Official Account", key="zalo_oa_id")
                        with zalo_col2:
                            zalo_access_token = st.text_input("🔑 Zalo Access Token",
                                                              placeholder="Nhập access token...",
                                                              help="Access Token từ Zalo API",
                                                              type="password", key="zalo_access_token")
                        btn_verify_zalo = st.button("✅ Kiểm tra kết nối Zalo",
                                                    use_container_width=True, key="btn_verify_zalo")
                        if btn_verify_zalo:
                            if not zalo_oa_id or not zalo_access_token:
                                st.error("❌ Vui lòng nhập Zalo OA ID và Access Token")
                            else:
                                with st.spinner("⏳ Đang kiểm tra..."):
                                    is_valid, verify_msg = validate_zalo_token(zalo_oa_id, zalo_access_token)
                                if is_valid:
                                    st.success(verify_msg)
                                else:
                                    st.error(verify_msg)
                        st.divider()
                        recipient_phone = st.text_input(
                            "📱 Số điện thoại Zalo nhận cảnh báo",
                            placeholder="0901234567 hoặc +84901234567",
                            help="Số điện thoại người nhận (định dạng VN)", key="zalo_recipient_phone")
                        zalo_interval = st.selectbox(
                            "ℹ️ Mốc thời gian gửi",
                            options=['1 giờ', '2 giờ', '3 giờ', '6 giờ', '12 giờ', '1 ngày'],
                            key="zalo_interval")
                        btn_zalo1, btn_zalo2, btn_zalo3 = st.columns([1.5, 1, 1.5])
                        with btn_zalo1:
                            send_zalo_alert_btn = st.button("💬 Gửi cảnh báo Zalo", type="primary",
                                                            use_container_width=True, key="btn_send_zalo")
                        if send_zalo_alert_btn:
                            if not recipient_phone:
                                st.error("❌ Vui lòng nhập số điện thoại Zalo")
                            elif not validate_phone_number(recipient_phone):
                                st.error("❌ Số điện thoại không hợp lệ")
                            elif not zalo_oa_id or not zalo_access_token:
                                st.error("❌ Vui lòng nhập Zalo OA ID và Access Token")
                            elif len(valid_vpd) == 0:
                                st.error("❌ Không có dữ liệu VPD hợp lệ để gửi cảnh báo")
                            else:
                                latest_row = filtered_df[filtered_df['vpd'].notna()].iloc[-1]
                                latest_vpd_val  = latest_row['vpd']
                                latest_temp     = latest_row['temperature']
                                latest_humidity = latest_row['humidity']
                                latest_assessment_send = get_vpd_assessment(latest_vpd_val)
                                with st.spinner("📤 Đang gửi cảnh báo Zalo..."):
                                    success, message = send_zalo_alert(
                                        recipient_phone=recipient_phone,
                                        vpd_value=latest_vpd_val,
                                        temperature=latest_temp,
                                        humidity=latest_humidity,
                                        assessment=latest_assessment_send,
                                        zalo_oa_id=zalo_oa_id,
                                        zalo_access_token=zalo_access_token)
                                if success:
                                    st.success(message)
                                    st.markdown(f"""
                                    <div class="alert-box">
                                    <h4>✅ Cảnh báo Zalo đã gửi thành công!</h4>
                                    <p>📱 Gửi đến: <strong>{recipient_phone}</strong></p>
                                    <p>📊 Giá trị VPD: <strong>{latest_vpd_val:.2f} kPa</strong></p>
                                    <p>🌡️ Nhiệt độ: <strong>{latest_temp:.2f}°C</strong></p>
                                    <p>💧 Độ ẩm: <strong>{latest_humidity:.2f}%</strong></p>
                                    <p>📌 Mốc gửi: <strong>Mỗi {zalo_interval}</strong></p>
                                    </div>""", unsafe_allow_html=True)
                                else:
                                    st.error(message)

            st.divider()

            # ================================================================
            # BẢNG DỮ LIỆU
            # ================================================================
            st.markdown("### 📋 Bảng dữ liệu")
            display_df = filtered_df.copy()
            display_df['datetime'] = display_df['datetime'].dt.strftime('%d/%m/%Y %H:%M')
            display_df = display_df[['datetime', 'temperature', 'humidity', 'vpd', 'vpd_status']]
            display_df.columns = ['Thời gian', 'Nhiệt độ (°C)', 'Độ ẩm (%)', 'VPD (kPa)', 'Trạng thái']
            display_df['Nhiệt độ (°C)'] = display_df['Nhiệt độ (°C)'].apply(lambda x: f"{x:.2f}" if pd.notna(x) else "N/A")
            display_df['Độ ẩm (%)']     = display_df['Độ ẩm (%)'].apply(lambda x: f"{x:.2f}" if pd.notna(x) else "N/A")
            display_df['VPD (kPa)']     = display_df['VPD (kPa)'].apply(
                lambda x: f"{x:.2f}" if pd.notna(x) and not math.isinf(x) else "N/A")
            status_map = {'optimal': '✅ Tối ưu', 'warning': '⚠️ Cảnh báo',
                          'danger': '❌ Nguy hiểm', 'unknown': '❓ Không xác định'}
            display_df['Trạng thái'] = display_df['Trạng thái'].map(status_map)
            st.dataframe(display_df, use_container_width=True, hide_index=True)
            csv = display_df.to_csv(index=False, encoding='utf-8-sig')
            st.download_button(label="📥 Tải xuống CSV", data=csv,
                               file_name=f"vpd_analysis_{actual_start.strftime('%Y%m%d')}.csv",
                               mime="text/csv")

# ============================================================================
# TAB 2: REAL-TIME
# ============================================================================
with tab_realtime:
    if st.session_state.rt_running:
        if should_update(st.session_state, UPDATE_INTERVAL):
            push_new_reading(st.session_state, calculate_vpd)

    rt_df    = get_realtime_dataframe(st.session_state)
    rt_stats = get_realtime_stats(st.session_state)

    if not st.session_state.rt_running and not st.session_state.rt_history:
        st.info("👈 Bấm **▶️ Bắt đầu** trong sidebar để bắt đầu thu thập dữ liệu real-time")
    elif rt_df is not None and not rt_df.empty:
        latest     = rt_df.iloc[-1]
        latest_vpd = latest['vpd']
        latest_T   = latest['temperature']
        latest_RH  = latest['humidity']
        rt_assessment = get_vpd_assessment(latest_vpd, T=latest_T, RH=latest_RH)

        rc1, rc2, rc3 = st.columns(3)
        with rc1:
            st.metric("🌡️ Nhiệt độ", f"{latest_T:.1f} °C")
        with rc2:
            st.metric("💧 Độ ẩm",    f"{latest_RH:.1f} %")
        with rc3:
            st.metric("🌿 VPD",      f"{latest_vpd:.2f} kPa")

        if rt_stats:
            st.markdown("#### 📈 Thống kê phiên")
            rs1, rs2, rs3, rs4, rs5 = st.columns(5)
            rs1.metric("Trung bình", f"{rt_stats['mean']:.2f} kPa")
            rs2.metric("Tối thiểu",  f"{rt_stats['min']:.2f} kPa")
            rs3.metric("Tối đa",     f"{rt_stats['max']:.2f} kPa")
            rs4.metric("Trung vị",   f"{rt_stats['median']:.2f} kPa")
            rs5.metric("Số liệu",    f"{rt_stats['count']}")

        st.markdown("#### 💡 Đánh giá trạng thái")
        if rt_assessment['status'] == 'optimal':
            st.markdown(f"""<div class="optimal">
                <h4>✅ {rt_assessment['description']}</h4>
                <p>{rt_assessment['recommendation']}</p>
            </div>""", unsafe_allow_html=True)
        elif rt_assessment['status'] in ['low', 'high']:
            cause_text = f"<p>🔍 <strong>Nguyên nhân:</strong> {rt_assessment['cause']}</p>" if rt_assessment['cause'] else ""
            st.markdown(f"""<div class="warning">
                <h4>⚠️ {rt_assessment['description']}</h4>
                {cause_text}
                <p>{rt_assessment['recommendation']}</p>
            </div>""", unsafe_allow_html=True)
        else:
            st.markdown(f"""<div class="danger">
                <h4>❌ {rt_assessment['description']}</h4>
                <p>{rt_assessment['recommendation']}</p>
            </div>""", unsafe_allow_html=True)

        st.markdown("#### 📉 Biểu đồ VPD Real-time")
        fig_rt = go.Figure()
        vpd_zones = [
            (0,   0.4, 'rgba(220,53,69,0.15)',  'Quá thấp'),
            (0.4, 0.8, 'rgba(255,193,7,0.18)',  'Thấp'),
            (0.8, 1.2, 'rgba(40,167,69,0.18)',  'Tối ưu'),
            (1.2, 1.5, 'rgba(255,193,7,0.18)',  'Cao'),
            (1.5, 3.0, 'rgba(220,53,69,0.15)',  'Quá cao'),
        ]
        for y0, y1, color, label in vpd_zones:
            fig_rt.add_hrect(y0=y0, y1=y1, fillcolor=color, line_width=0,
                             annotation_text=label, annotation_position='left',
                             annotation=dict(font_size=10, font_color='rgba(255,255,255,0.45)'))
        fig_rt.add_trace(go.Scatter(
            x=rt_df['timestamp'], y=rt_df['vpd'],
            mode='lines+markers', name='VPD (kPa)',
            line=dict(color='#00BFFF', width=2),
            marker=dict(size=6, color='#00BFFF')))
        fig_rt.update_layout(
            plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
            font=dict(color='white'),
            yaxis=dict(title='VPD (kPa)', range=[0, 3.0], gridcolor='rgba(255,255,255,0.1)'),
            xaxis=dict(gridcolor='rgba(255,255,255,0.05)'),
            hovermode='x unified', height=300,
            margin=dict(l=0, r=0, t=10, b=0), showlegend=False)
        st.plotly_chart(fig_rt, use_container_width=True)
        # Bảng số liệu ghi nhận
        st.markdown("#### 📋 Bảng số liệu ghi nhận")
        rt_table = get_realtime_table(st.session_state)
        if rt_table is not None:
            st.dataframe(rt_table, use_container_width=True)
            st.caption(f"Tổng cộng {len(rt_table)} bản ghi — mới nhất hiển thị trên đầu")
    else:
        st.info("⏳ Đang chờ dữ liệu đầu tiên...")

    # Auto-refresh chỉ khi đang chạy
    if st.session_state.rt_running:
        import time
        time.sleep(UPDATE_INTERVAL)
        st.rerun()

# ============================================================================
# FOOTER
# ============================================================================

st.divider()
st.markdown("""
    **VPD Analysis Tool** | Công cụ phân tích VPD cho cây trồng trong nhà kính

    💡 **Ghi chú:**
    - VPD tối ưu: 0.8 - 1.2 kPa
    - VPD quá thấp (< 0.8 kPa): Độ ẩm cao, tăng nguy cơ bệnh nấm
    - VPD quá cao (> 1.2 kPa): Khô quá, cây mất nước nhanh
    - **Đánh giá dựa trên VPD trung bình** của kỳ được chọn

    📧 Liên hệ: [GitHub Repository](https://github.com/Hoa-Levan/tool-thuc-tap_VPD)
""")
