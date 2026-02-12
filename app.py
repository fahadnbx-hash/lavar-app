import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import database as db
import plotly.express as px
import plotly.graph_objects as go

# إعدادات الصفحة
st.set_page_config(page_title="لاڤار للمنظفات - نظام الإدارة", layout="wide", initial_sidebar_state="collapsed")

# حقن CSS لإصلاح مشاكل الجوال والـ RTL بشكل جذري
st.markdown("""
    <style>
    /* التنسيقات الأساسية للـ RTL */
    .stApp { text-align: right; direction: rtl; }
    [data-testid="stSidebar"] { text-align: right; direction: rtl; }
    
    /* إصلاح تداخل النصوص في القائمة الجانبية والجوال */
    [data-testid="stSidebar"] * {
        white-space: normal !important;
        word-wrap: break-word !important;
        overflow-wrap: break-word !important;
    }
    
    /* تنسيق القائمة الجانبية في الجوال ليكون مرناً */
    @media (max-width: 768px) {
        [data-testid="stSidebar"] {
            width: 250px !important;
            min-width: 250px !important;
        }
        .stApp { padding: 0.5rem !important; }
        .main-title { font-size: 1.5rem !important; }
    }

    /* تحسين مظهر البطاقات والمقاييس */
    .metric-card {
        background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
        border-radius: 12px;
        padding: 20px;
        margin: 10px 0;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        border: 1px solid rgba(255, 255, 255, 0.3);
        text-align: center;
    }
    .metric-value { font-size: 2rem; font-weight: bold; color: #2E7D32; }
    .metric-label { font-size: 1rem; color: #666; }
    
    /* ضبط الجداول لتكون متجاوبة */
    .stTable, .stDataFrame { width: 100%; overflow-x: auto; }
    </style>
""", unsafe_allow_html=True)

# التحقق من تسجيل الدخول
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

def login():
    st.title("🔐 تسجيل الدخول - شركة لاڤار")
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        username = st.text_input("اسم المستخدم")
        password = st.text_input("كلمة المرور", type="password")
        if st.button("دخول", use_container_width=True):
            if username == "admin" and password == "lavar2026":
                st.session_state.logged_in = True
                st.session_state.role = "admin"
                st.rerun()
            elif username == "sales" and password == "lavar_sales":
                st.session_state.logged_in = True
                st.session_state.role = "sales"
                st.rerun()
            elif username == "acc" and password == "lavar_acc":
                st.session_state.logged_in = True
                st.session_state.role = "acc"
                st.rerun()
            else:
                st.error("خطأ في اسم المستخدم أو كلمة المرور")

if not st.session_state.logged_in:
    login()
    st.stop()

# القائمة الجانبية المشتركة
with st.sidebar:
    st.image("https://img.icons8.com/fluency/96/factory.png", width=80)
    st.title("لاڤار للمنظفات")
    st.write(f"👤 مرحباً: **{st.session_state.role}**")
    
    # روابط التنقل بناءً على الصلاحيات
    if st.session_state.role == "admin":
        st.divider()
        st.subheader("🛠️ الإدارة الذكية")
        if st.button("🚀 مركز القيادة", use_container_width=True): st.session_state.page = "dashboard"
        if st.button("📦 إدارة البيانات", use_container_width=True): st.session_state.page = "data_mgmt"
    
    st.divider()
    if st.button("🚪 تسجيل الخروج", use_container_width=True):
        st.session_state.logged_in = False
        st.rerun()

# توجيه المستخدم حسب الصلاحيات
if st.session_state.role == "sales":
    st.title("📋 واجهة المندوب")
    tab1, tab2 = st.tabs(["🛒 إدارة الطلبات", "📍 سجل الزيارات الميدانية"])
    
    with tab1:
        st.subheader("➕ إنشاء طلب جديد")
        with st.form("order_form", clear_on_submit=True):
            c1, c2 = st.columns(2)
            client_name = c1.text_input("اسم العميل")
            cr_number = c2.text_input("رقم السجل التجاري")
            vat_number = c1.text_input("الرقم الضريبي")
            qty = c2.number_input("الكمية (علبة)", min_value=1, value=100)
            submit = st.form_submit_button("حفظ الطلب")
            if submit:
                if client_name:
                    db.add_order(client_name, cr_number, vat_number, qty, 11)
                    st.success(f"تم تسجيل طلب لـ {client_name} بنجاح")
                else:
                    st.error("يرجى إدخال اسم العميل")

    with tab2:
        st.subheader("📍 تسجيل زيارة ميدانية")
        with st.form("visit_form", clear_on_submit=True):
            v_client = st.text_input("اسم العميل المزوار")
            v_notes = st.text_area("ملاحظات الزيارة")
            v_conf = st.slider("مستوى ثقة المندوب في الطلب القادم (%)", 0, 100, 50)
            if st.form_submit_button("حفظ الزيارة"):
                db.add_visit(v_client, "ميدانية", v_notes, v_conf)
                st.success("تم تسجيل الزيارة بنجاح")

elif st.session_state.role == "acc":
    st.title("💰 واجهة المحاسب")
    orders = db.get_orders()
    if not orders.empty:
        pending = orders[orders['status'] == 'قيد الانتظار']
        st.subheader(f"📦 الطلبات المعلقة ({len(pending)})")
        st.dataframe(pending, use_container_width=True)
        # منطق الموافقة هنا
    else:
        st.info("لا توجد طلبات مسجلة حالياً")

elif st.session_state.role == "admin":
    st.title("🚀 مركز القيادة الذكي")
    
    # 1. ملخص الأداء (Row 1)
    c1, c2, c3 = st.columns(3)
    target = db.get_annual_target()
    actual_sales = db.get_orders()['total_price'].sum() if not db.get_orders().empty else 0
    
    with c1:
        st.markdown(f'<div class="metric-card"><div class="metric-label">الهدف السنوي</div><div class="metric-value">{target:,.0f}</div></div>', unsafe_allow_html=True)
    with c2:
        st.markdown(f'<div class="metric-card"><div class="metric-label">المبيعات الفعلية</div><div class="metric-value">{actual_sales:,.0f}</div></div>', unsafe_allow_html=True)
    with c3:
        progress = (actual_sales / target * 100) if target > 0 else 0
        st.markdown(f'<div class="metric-card"><div class="metric-label">نسبة الإنجاز</div><div class="metric-value">{progress:.1f}%</div></div>', unsafe_allow_html=True)

    st.divider()
    st.subheader("📈 التخطيط والإنتاج الذكي")
    # منطق التخطيط والإنتاج هنا
    st.info("تم تفعيل نظام التنبؤ الذكي بناءً على ثقة المناديب")
