import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import database as db
import plotly.express as px
import plotly.graph_objects as go

# إعدادات الصفحة - تركنا السايد بار في مكانه الطبيعي (اليسار) لحل مشكلة التداخل
st.set_page_config(page_title="لاڤار للمنظفات - نظام الإدارة", layout="wide", initial_sidebar_state="auto")

# حقن CSS لضمان محاذاة النصوص لليمين (RTL) مع بقاء السايد بار يساراً
st.markdown("""
    <style>
    /* جعل المحتوى الرئيسي يبدأ من اليمين */
    .stApp { text-align: right; direction: rtl; }
    
    /* التأكد من أن النصوص داخل القائمة الجانبية (التي تظهر يساراً) محاذية لليمين أيضاً */
    [data-testid="stSidebar"] { text-align: right; direction: rtl; }
    
    /* إصلاح ظهور النصوص بشكل عمودي عبر إعطاء مساحة كافية */
    [data-testid="stSidebarContent"] {
        padding-top: 2rem;
    }
    
    /* تحسين مظهر التبويبات في الجوال */
    @media (max-width: 768px) {
        .stTabs [data-baseweb="tab-list"] {
            gap: 10px;
        }
        .stTabs [data-baseweb="tab"] {
            font-size: 0.9rem !important;
            padding: 10px !important;
        }
        /* تصغير العناوين لتناسب عرض الجوال */
        h1 { font-size: 1.6rem !important; }
        .stMarkdown p { font-size: 1rem !important; }
    }
    
    /* تنسيق البطاقات */
    .metric-card {
        background: white;
        padding: 20px;
        border-radius: 12px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        border: 1px solid #f0f0f0;
        margin-bottom: 15px;
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
                st.error("بيانات الدخول غير صحيحة")

if not st.session_state.logged_in:
    login()
    st.stop()

# القائمة الجانبية (ستظهر في اليسار تلقائياً وهو الحل الأفضل تقنياً)
with st.sidebar:
    st.image("https://img.icons8.com/fluency/96/factory.png", width=70)
    st.title("لاڤار للمنظفات")
    st.markdown(f"👤 مرحباً: **{st.session_state.role}**")
    st.divider()
    
    if st.button("🚪 تسجيل الخروج", use_container_width=True):
        st.session_state.logged_in = False
        st.rerun()

# واجهة المندوب
if st.session_state.role == "sales":
    st.title("📋 واجهة المندوب")
    tab1, tab2 = st.tabs(["🛒 إدارة الطلبات", "📍 الزيارات الميدانية"])
    
    with tab1:
        st.subheader("➕ إنشاء طلب جديد")
        with st.form("order_form", clear_on_submit=True):
            client_name = st.text_input("اسم العميل")
            cr_number = st.text_input("رقم السجل التجاري")
            vat_number = st.text_input("الرقم الضريبي")
            qty = st.number_input("الكمية (علبة)", min_value=1, value=100)
            if st.form_submit_button("حفظ الطلب بنجاح", use_container_width=True):
                if client_name:
                    db.add_order(client_name, cr_number, vat_number, qty, 11)
                    st.success(f"تم تسجيل طلب {client_name} بنجاح")
                else:
                    st.error("يرجى إدخال اسم العميل")

    with tab2:
        st.subheader("📍 تسجيل زيارة ميدانية")
        with st.form("visit_form", clear_on_submit=True):
            v_client = st.text_input("اسم العميل")
            v_notes = st.text_area("ملاحظات الزيارة")
            v_conf = st.slider("مستوى الثقة (%)", 0, 100, 50)
            if st.form_submit_button("حفظ الزيارة", use_container_width=True):
                db.add_visit(v_client, "ميدانية", v_notes, v_conf)
                st.success("تم تسجيل الزيارة")

# واجهة المحاسب
elif st.session_state.role == "acc":
    st.title("💰 واجهة المحاسب")
    orders = db.get_orders()
    st.dataframe(orders, use_container_width=True)

# واجهة المدير
elif st.session_state.role == "admin":
    st.title("🚀 لوحة تحكم المدير")
    st.info("مرحباً بك في مركز القيادة الذكي")
    
    # إحصائيات سريعة
    orders = db.get_orders()
    total_sales = orders['total_price'].sum() if not orders.empty else 0
    visits_count = len(db.get_visits())
    
    c1, c2 = st.columns(2)
    with c1:
        st.metric("إجمالي المبيعات", f"{total_sales:,.0f} ريال")
    with c2:
        st.metric("إجمالي الزيارات", visits_count)
