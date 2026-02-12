import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import database as db
import plotly.express as px
import plotly.graph_objects as go

# إعدادات الصفحة - جعل القائمة الجانبية مخفية افتراضياً
st.set_page_config(page_title="لاڤار للمنظفات - نظام الإدارة", layout="wide", initial_sidebar_state="collapsed")

# حقن CSS لإصلاح مشاكل الجوال والـ RTL بشكل نهائي
st.markdown("""
    <style>
    /* التنسيقات الأساسية للـ RTL */
    .stApp { text-align: right; direction: rtl; }
    [data-testid="stSidebar"] { text-align: right; direction: rtl; }
    
    /* حل مشكلة التداخل في الجوال بشكل جذري */
    @media (max-width: 768px) {
        /* إخفاء القائمة الجانبية تماماً لتوفير مساحة للمحتوى */
        [data-testid="stSidebar"] {
            display: none;
        }
        /* توسيع المحتوى الرئيسي ليملأ الشاشة */
        .main .block-container {
            padding: 1rem !important;
            max-width: 100% !important;
        }
        /* منع ظهور النصوص بشكل عمودي */
        * {
            white-space: normal !important;
        }
        /* تصغير العناوين لتناسب الشاشة */
        h1 { font-size: 1.4rem !important; }
        h2 { font-size: 1.2rem !important; }
        
        /* تحسين مظهر أزرار التبويبات */
        .stTabs [data-baseweb="tab-list"] {
            display: flex;
            flex-wrap: wrap;
            gap: 5px;
        }
        .stTabs [data-baseweb="tab"] {
            flex: 1 1 auto;
            text-align: center;
            padding: 10px 5px !important;
            font-size: 0.8rem !important;
        }
    }
    
    /* تنسيق البطاقات */
    .metric-card {
        background: white;
        padding: 15px;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        border: 1px solid #eee;
        margin-bottom: 10px;
    }
    </style>
""", unsafe_allow_html=True)

# التحقق من تسجيل الدخول
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

def login():
    st.title("🔐 تسجيل الدخول")
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
                st.error("خطأ في البيانات")

if not st.session_state.logged_in:
    login()
    st.stop()

# القائمة الجانبية (ستكون مخفية في الجوال لتوفير المساحة)
with st.sidebar:
    st.image("https://img.icons8.com/fluency/96/factory.png", width=60)
    st.title("لاڤار")
    st.write(f"👤: **{st.session_state.role}**")
    if st.button("🚪 خروج", use_container_width=True):
        st.session_state.logged_in = False
        st.rerun()

# واجهة المندوب
if st.session_state.role == "sales":
    st.title("📋 واجهة المندوب")
    tab1, tab2 = st.tabs(["🛒 الطلبات", "📍 الزيارات"])
    
    with tab1:
        st.subheader("🛒 إنشاء طلب")
        with st.form("order_form", clear_on_submit=True):
            client_name = st.text_input("اسم العميل")
            cr_number = st.text_input("السجل التجاري")
            vat_number = st.text_input("الرقم الضريبي")
            qty = st.number_input("الكمية", min_value=1, value=100)
            if st.form_submit_button("حفظ الطلب", use_container_width=True):
                if client_name:
                    db.add_order(client_name, cr_number, vat_number, qty, 11)
                    st.success(f"تم الحفظ لـ {client_name}")
                else:
                    st.error("أدخل الاسم")

    with tab2:
        st.subheader("📍 تسجيل زيارة")
        with st.form("visit_form", clear_on_submit=True):
            v_client = st.text_input("اسم العميل")
            v_notes = st.text_area("الملاحظات")
            v_conf = st.slider("الثقة (%)", 0, 100, 50)
            if st.form_submit_button("حفظ الزيارة", use_container_width=True):
                db.add_visit(v_client, "ميدانية", v_notes, v_conf)
                st.success("تم التسجيل")

# واجهة المحاسب
elif st.session_state.role == "acc":
    st.title("💰 واجهة المحاسب")
    orders = db.get_orders()
    st.dataframe(orders, use_container_width=True)

# واجهة المدير
elif st.session_state.role == "admin":
    st.title("🚀 لوحة الإدارة")
    orders = db.get_orders()
    total = orders['total_price'].sum() if not orders.empty else 0
    st.metric("إجمالي المبيعات", f"{total:,.0f} ريال")
    st.info("مرحباً بك في لوحة الإدارة")
