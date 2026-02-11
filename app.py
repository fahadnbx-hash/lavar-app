import streamlit as st
import pandas as pd
from database import init_db, get_orders, add_order, update_order_status, get_stock, upload_to_github, delete_order, update_stock_quantity
from datetime import datetime, date, timedelta
import plotly.express as px

# إعداد الصفحة
st.set_page_config(page_title="نظام لآفار الذكي", layout="wide")
init_db()

# --- نظام تسجيل الدخول ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.title("🔐 تسجيل الدخول - لآفار")
    user = st.text_input("اسم المستخدم")
    password = st.text_input("كلمة المرور", type="password")
    if st.button("دخول"):
        # يمكنك تغيير كلمات المرور هنا
        if user == "admin" and password == "lavar2026":
            st.session_state.logged_in = True
            st.session_state.role = "admin"
            st.rerun()
        elif user == "acc" and password == "lavar_acc":
            st.session_state.logged_in = True
            st.session_state.role = "accountant"
            st.rerun()
        elif user == "sales" and password == "lavar_sales":
            st.session_state.logged_in = True
            st.session_state.role = "sales"
            st.rerun()
        else:
            st.error("بيانات الدخول غير صحيحة")
    st.stop()

# القائمة الجانبية بناءً على الصلاحيات
st.sidebar.title(f"👤 مرحباً: {st.session_state.role}")
if st.sidebar.button("تسجيل الخروج"):
    st.session_state.logged_in = False
    st.rerun()

available_pages = []
if st.session_state.role == "admin":
    available_pages = ["واجهة المندوب", "واجهة المحاسب", "واجهة الإدارة"]
elif st.session_state.role == "accountant":
    available_pages = ["واجهة المحاسب"]
elif st.session_state.role == "sales":
    available_pages = ["واجهة المندوب"]

page = st.sidebar.radio("الانتقال إلى:", available_pages)

# --- واجهة المندوب ---
if page == "واجهة المندوب":
    st.header("📋 واجهة المندوب")
    orders = get_orders()
    stock_df = get_stock()
    
    with st.expander("➕ إضافة طلب جديد", expanded=True):
        c1, c2 = st.columns(2)
        with c1:
            name = st.text_input("اسم العميل")
            cr = st.text_input("السجل التجاري")
            tax = st.text_input("الرقم الضريبي")
            address = st.text_input("العنوان")
            phone = st.text_input("رقم الجوال")
        with c2:
            prod_list = stock_df['Product'].tolist() if not stock_df.empty else ["صابون لآفار 3 لتر"]
            prod = st.selectbox("المنتج", prod_list)
            qty = st.number_input("الكمية", 1, 1000, 1)
            price = st.number_input("سعر العلبة", 0.0, 1000.0, 0.0)
            days = st.number_input("أيام الاستحقاق", 0, 99, 30)
        
        if st.button("التالي ➡️", use_container_width=True):
            add_order(name, cr, tax, address, phone, prod, qty, days, price if price > 0 else None)
            st.success("✅ تم حفظ الطلب!")
            st.rerun()

    st.subheader("🚀 طلبات بانتظار الاعتماد")
    drafts = orders[orders['Status'] == 'Draft'] if not orders.empty else pd.DataFrame()
    for _, row in drafts.iterrows():
        with st.container(border=True):
            col_info, col_btn, col_del = st.columns([3, 1, 0.5])
            with col_info:
                st.write(f"**العميل:** {row['Customer Name']} | **الإجمالي:** {row['Total Amount']} ريال")
            with col_btn:
                if st.button("إرسال للمحاسب", key=f"p_{row['Order ID']}", use_container_width=True):
                    update_order_status(row['Order ID'], 'Pending'); st.rerun()
            with col_del:
                if st.button("🗑️", key=f"d_{row['Order ID']}", use_container_width=True):
                    delete_order(row['Order ID']); st.rerun()

    st.subheader("✅ فواتير جاهزة")
    inv = orders[orders['Status'] == 'Invoiced'] if not orders.empty else pd.DataFrame()
    for _, row in inv.iterrows():
        with st.container(border=True):
            st.write(f"**العميل:** {row['Customer Name']} | **المبلغ:** {row['Total Amount']} ريال")
            if row['Invoice URL']: st.link_button("📄 فتح الفاتورة", row['Invoice URL'], use_container_width=True)

# --- واجهة المحاسب ---
elif page == "واجهة المحاسب":
    st.header("💰 واجهة المحاسب")
    orders = get_orders()
    pending = orders[orders['Status'] == 'Pending'] if not orders.empty else pd.DataFrame()
    for _, row in pending.iterrows():
        with st.container(border=True):
            st.write(f"**طلب #{row['Order ID']}** - العميل: {row['Customer Name']} - المبلغ: {row['Total Amount']} ريال")
            pdf_file = st.file_uploader("ارفع الفاتورة", type=['pdf'], key=f"f_{row['Order ID']}")
            if pdf_file and st.button("✅ اعتماد ورفع", key=f"b_{row['Order ID']}", use_container_width=True):
                url = upload_to_github(pdf_file.getvalue(), f"inv_{row['Order ID']}.pdf")
                if url: update_order_status(row['Order ID'], 'Invoiced', url); st.rerun()
            if st.button("🗑️ حذف الطلب", key=f"da_{row['Order ID']}", use_container_width=True):
                delete_order(row['Order ID']); st.rerun()

# --- واجهة الإدارة ---
elif page == "واجهة الإدارة":
    st.header("📊 لوحة التحكم والإدارة")
    orders = get_orders()
    stock_df = get_stock()
    
    if not orders.empty:
        # قسم تتبع المديونيات
        st.subheader("🚩 تتبع المديونيات المتأخرة")
        today = date.today()
        # تصفية الفواتير المفوترة والتي تجاوزت تاريخ استحقاقها
        late_orders = orders[(orders['Status'] == 'Invoiced') & (orders['Due Date'] < today)]
        if not late_orders.empty:
            for _, row in late_orders.iterrows():
                st.error(f"⚠️ مديونية متأخرة: {row['Customer Name']} | المبلغ: {row['Total Amount']} ريال | تاريخ الاستحقاق: {row['Due Date']}")
        else:
            st.success("✅ لا توجد مديونيات متأخرة حالياً")
            
        st.divider()
        
        # إحصائيات عامة
        invoiced = orders[orders['Status'] == 'Invoiced']
        c1, c2 = st.columns(2)
        c1.metric("💰 إجمالي المبيعات المفوترة", f"{invoiced['Total Amount'].sum()} ريال")
        c2.metric("⏳ طلبات معلقة", len(orders[orders['Status'] == 'Pending']))
        
        st.divider()
        st.subheader("📜 سجل العمليات")
        st.dataframe(orders, use_container_width=True)
        
        st.subheader("📦 إدارة المخزون")
        for idx, row in stock_df.iterrows():
            col1, col2 = st.columns([2, 1])
            with col1: st.write(f"**المنتج:** {row['Product']} | الكمية: {row['Quantity']}")
            with col2:
                new_q = st.number_input(f"تحديث الكمية لـ {row['Product']}", value=int(row['Quantity']), key=f"s_{idx}")
                if st.button(f"حفظ {idx}", key=f"b_{idx}"):
                    update_stock_quantity(row['Product'], new_q); st.rerun()
    else:
        st.info("لا توجد بيانات")
