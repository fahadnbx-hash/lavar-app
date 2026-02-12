import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import database as db
import plotly.express as px
import plotly.graph_objects as go
import base64

# إعدادات الصفحة
st.set_page_config(page_title="لاڤار للمنظفات - نظام الإدارة", layout="wide", initial_sidebar_state="auto")

# تهيئة قاعدة البيانات
db.init_db()

# حقن CSS لإصلاح مشاكل الجوال والـ RTL بشكل آمن
st.markdown("""
    <style>
    /* التنسيقات الأساسية للـ RTL */
    .stApp { text-align: right; direction: rtl; }
    [data-testid="stSidebar"] { text-align: right; direction: rtl; }
    
    /* حل مشكلة التداخل في الجوال عبر السماح للقائمة بالالتفاف */
    @media (max-width: 768px) {
        [data-testid="stSidebar"] {
            min-width: 250px !important;
        }
        /* منع النصوص من التداخل عبر السماح لها بالنزول لسطر جديد */
        .stMarkdown, .stText, label, p {
            white-space: normal !important;
            word-wrap: break-word !important;
        }
    }
    
    /* تنسيق البطاقات الإحصائية */
    .metric-card {
        background: white;
        padding: 20px;
        border-radius: 12px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        border: 1px solid #f0f0f0;
        margin-bottom: 15px;
        text-align: center;
    }
    .metric-value { font-size: 1.8rem; font-weight: bold; color: #2E7D32; }
    .metric-label { font-size: 1rem; color: #666; }
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
                st.error("بيانات الدخول غير صحيحة")

if not st.session_state.logged_in:
    login()
    st.stop()

# القائمة الجانبية
with st.sidebar:
    st.title("لاڤار للمنظفات")
    st.markdown(f"👤 مرحباً: **{st.session_state.role}**")
    st.divider()
    
    if st.button("🚪 تسجيل الخروج", use_container_width=True):
        st.session_state.logged_in = False
        st.rerun()

# --- واجهة المندوب ---
if st.session_state.role == "sales":
    st.title("📋 واجهة المندوب")
    tab1, tab2 = st.tabs(["🛒 إدارة الطلبات", "📍 الزيارات الميدانية"])
    
    with tab1:
        st.subheader("➕ إنشاء طلب جديد")
        with st.form("order_form", clear_on_submit=True):
            c1, c2 = st.columns(2)
            name = c1.text_input("اسم العميل")
            cr = c2.text_input("رقم السجل التجاري")
            tax = c1.text_input("الرقم الضريبي")
            address = c2.text_input("العنوان")
            phone = c1.text_input("رقم الجوال")
            prod = c2.selectbox("المنتج", ["صابون لآفار 3 لتر"])
            qty = c1.number_input("الكمية", min_value=1, value=100)
            days = c2.number_input("مدة السداد (يوم)", min_value=1, value=30)
            price = st.number_input("سعر الوحدة", value=11.0)
            
            if st.form_submit_button("حفظ الطلب", use_container_width=True):
                if name:
                    db.add_order(name, cr, tax, address, phone, prod, qty, days, price)
                    st.success(f"تم تسجيل طلب {name} بنجاح")
                else:
                    st.error("يرجى إدخال اسم العميل")

    with tab2:
        st.subheader("📍 تسجيل زيارة ميدانية")
        with st.form("visit_form", clear_on_submit=True):
            customer = st.text_input("اسم العميل")
            pot_qty = st.number_input("الكمية المتوقعة", min_value=0)
            pot_date = st.date_input("التاريخ المتوقع للطلب")
            notes = st.text_area("ملاحظات")
            if st.form_submit_button("حفظ الزيارة", use_container_width=True):
                db.add_visit(st.session_state.role, customer, pot_qty, pot_date.strftime("%Y-%m-%d"), notes)
                st.success("تم تسجيل الزيارة")

# --- واجهة المحاسب ---
elif st.session_state.role == "acc":
    st.title("💰 واجهة المحاسب")
    orders = db.get_orders()
    if not orders.empty:
        st.subheader("📦 الطلبات المسجلة")
        for index, row in orders.iterrows():
            with st.expander(f"طلب: {row['Customer Name']} - {row['Order ID']}"):
                st.write(f"الكمية: {row['Quantity']} | الإجمالي: {row['Total Amount']} ريال")
                st.write(f"الحالة: {row['Status']}")
                if st.button("تأكيد الطلب", key=f"conf_{row['Order ID']}"):
                    db.update_order_status(row['Order ID'], "Confirmed")
                    st.rerun()
    else:
        st.info("لا توجد طلبات حالياً")

# --- واجهة المدير ---
elif st.session_state.role == "admin":
    st.title("🚀 مركز القيادة الذكي")
    
    orders = db.get_orders()
    total_sales = orders['Total Amount'].sum() if not orders.empty else 0
    target = db.get_annual_target()
    
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(f'<div class="metric-card"><div class="metric-label">إجمالي المبيعات</div><div class="metric-value">{total_sales:,.0f}</div></div>', unsafe_allow_html=True)
    with c2:
        st.markdown(f'<div class="metric-card"><div class="metric-label">الهدف السنوي</div><div class="metric-value">{target:,.0f}</div></div>', unsafe_allow_html=True)
    with c3:
        progress = (total_sales / target * 100) if target > 0 else 0
        st.markdown(f'<div class="metric-card"><div class="metric-label">نسبة الإنجاز</div><div class="metric-value">{progress:.1f}%</div></div>', unsafe_allow_html=True)
    
    st.divider()
    st.subheader("📊 تحليل البيانات")
    if not orders.empty:
        fig = px.bar(orders, x='Customer Name', y='Total Amount', title="المبيعات حسب العميل")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("لا توجد بيانات كافية للتحليل")
