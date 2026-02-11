import streamlit as st
import pandas as pd
from database import init_db, get_orders, add_order, update_order_status, get_stock, upload_to_github, delete_order
from datetime import datetime, timedelta

st.set_page_config(page_title="لآفار للمنظفات", layout="wide")
init_db()

st.sidebar.title("🏢 لآفار للمنظفات")
page = st.sidebar.radio("الانتقال إلى:", ["واجهة المندوب", "واجهة المحاسب", "واجهة الإدارة"])

# --- واجهة المندوب ---
if page == "واجهة المندوب":
    st.header("📋 واجهة المندوب")
    orders = get_orders()
    stock_df = get_stock()
    
    with st.expander("➕ إضافة طلب جديد", expanded=True):
        c1, c2 = st.columns(2)
        with c1:
            name = st.text_input("اسم العميل / الشركة")
            cr = st.text_input("رقم السجل التجاري")
            tax = st.text_input("الرقم الضريبي")
            address = st.text_input("العنوان")
            phone = st.text_input("رقم الجوال")
        with c2:
            prod = st.selectbox("المنتج", stock_df['Product'].tolist() if not stock_df.empty else ["صابون لآفار 3 لتر"])
            qty = st.number_input("الكمية", 1, 1000, 1)
            price = st.number_input("سعر الوحدة (اختياري)", 0.0, 1000.0, 0.0)
            days = st.number_input("أيام الاستحقاق", 0, 99, 30)
        if st.button("💾 حفظ كمسودة", use_container_width=True):
            add_order(name, cr, tax, address, phone, prod, qty, days, price if price > 0 else None)
            st.success("تم الحفظ!")
            st.rerun()

    st.subheader("🚀 مسودات بانتظار الاعتماد")
    drafts = orders[orders['Status'] == 'Draft'] if not orders.empty else pd.DataFrame()
    for _, row in drafts.iterrows():
        with st.container(border=True):
            st.write(f"**العميل:** {row['Customer Name']} | **الإجمالي:** {row['Total Amount']} ريال")
            col1, col2 = st.columns(2)
            with col1:
                if st.button("🚀 إرسال للمحاسب", key=f"p_{row['Order ID']}", use_container_width=True):
                    update_order_status(row['Order ID'], 'Pending')
                    st.rerun()
            with col2:
                if st.button("🗑️ حذف المسودة", key=f"d_{row['Order ID']}", use_container_width=True, type="secondary"):
                    delete_order(row['Order ID'])
                    st.rerun()

    st.subheader("✅ فواتير جاهزة")
    inv = orders[orders['Status'] == 'Invoiced'] if not orders.empty else pd.DataFrame()
    for _, row in inv.iterrows():
        with st.container(border=True):
            st.write(f"**العميل:** {row['Customer Name']} | **المبلغ:** {row['Total Amount']} ريال")
            col1, col2 = st.columns(2)
            with col1:
                if row['Invoice URL']: st.link_button("📄 فتح الفاتورة", row['Invoice URL'], use_container_width=True)
            with col2:
                if st.button("🗑️ حذف الطلب", key=f"di_{row['Order ID']}", use_container_width=True):
                    delete_order(row['Order ID'])
                    st.rerun()

# --- واجهة المحاسب ---
elif page == "واجهة المحاسب":
    st.header("💰 واجهة المحاسب")
    orders = get_orders()
    pending = orders[orders['Status'] == 'Pending'] if not orders.empty else pd.DataFrame()
    for _, row in pending.iterrows():
        with st.container(border=True):
            st.write(f"**طلب #{row['Order ID']}** - العميل: {row['Customer Name']} - المبلغ: {row['Total Amount']} ريال")
            pdf_file = st.file_uploader("ارفع الفاتورة", type=['pdf'], key=f"f_{row['Order ID']}")
            col1, col2 = st.columns(2)
            with col1:
                if pdf_file and st.button("✅ اعتماد ورفع", key=f"b_{row['Order ID']}", use_container_width=True):
                    url = upload_to_github(pdf_file.getvalue(), f"inv_{row['Order ID']}.pdf")
                    if url: update_order_status(row['Order ID'], 'Invoiced', url); st.rerun()
            with col2:
                if st.button("🗑️ حذف/إلغاء الطلب", key=f"da_{row['Order ID']}", use_container_width=True):
                    delete_order(row['Order ID'])
                    st.rerun()

# --- واجهة الإدارة ---
elif page == "واجهة الإدارة":
    st.header("📊 الإدارة")
    orders = get_orders()
    st.dataframe(orders, use_container_width=True)
    if st.button("🗑️ مسح كافة البيانات (تنبيه!)"):
        st.warning("هذا الخيار يتطلب صلاحية مدير النظام.")
