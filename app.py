import streamlit as st
import pandas as pd
from database import init_db, get_orders, add_order, update_order_status, get_stock, upload_to_github
from datetime import datetime

st.set_page_config(page_title="لآفار للمنظفات", layout="wide")
init_db()

st.sidebar.title("🏢 لآفار للمنظفات")
page = st.sidebar.radio("الانتقال إلى:", ["واجهة المندوب", "واجهة المحاسب", "واجهة الإدارة"])

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
        with c2:
            prod = st.selectbox("المنتج", stock_df['Product'].tolist() if not stock_df.empty else ["صابون لآفار 3 لتر"])
            qty = st.number_input("الكمية", 1, 1000, 1)
            days = st.number_input("أيام الاستحقاق", 0, 99, 30)
        if st.button("💾 حفظ كمسودة"):
            add_order(name, cr, tax, "", "", prod, qty, days)
            st.success("تم الحفظ!")
            st.rerun()

    st.subheader("🚀 مسودات بانتظار الاعتماد")
    drafts = orders[orders['Status'] == 'Draft'] if not orders.empty else pd.DataFrame()
    for _, row in drafts.iterrows():
        with st.container(border=True):
            st.write(f"العميل: {row['Customer Name']} | المنتج: {row['Product']}")
            if st.button("إرسال للمحاسب", key=f"p_{row['Order ID']}"):
                update_order_status(row['Order ID'], 'Pending')
                st.rerun()

    st.subheader("✅ فواتير جاهزة للمشاركة")
    inv = orders[orders['Status'] == 'Invoiced'] if not orders.empty else pd.DataFrame()
    for _, row in inv.iterrows():
        with st.container(border=True):
            st.write(f"العميل: {row['Customer Name']}")
            if row['Invoice URL']:
                st.link_button("📄 فتح الفاتورة للمشاركة", row['Invoice URL'])

elif page == "واجهة المحاسب":
    st.header("💰 واجهة المحاسب")
    orders = get_orders()
    pending = orders[orders['Status'] == 'Pending'] if not orders.empty else pd.DataFrame()
    for _, row in pending.iterrows():
        with st.container(border=True):
            st.write(f"طلب #{row['Order ID']} - العميل: {row['Customer Name']}")
            pdf_file = st.file_uploader("ارفع الفاتورة هنا (PDF)", type=['pdf'], key=f"f_{row['Order ID']}")
            if pdf_file and st.button("✅ اعتماد ورفع الفاتورة", key=f"b_{row['Order ID']}"):
                with st.spinner("جاري الرفع والأتمتة..."):
                    file_name = f"invoice_{row['Order ID']}_{datetime.now().strftime('%Y%m%d%H%M%S')}.pdf"
                    url = upload_to_github(pdf_file.getvalue(), file_name)
                    if url:
                        update_order_status(row['Order ID'], 'Invoiced', url)
                        st.success("تم الرفع والاعتماد بنجاح!")
                        st.rerun()

elif page == "واجهة الإدارة":
    st.header("📊 الإدارة")
    orders = get_orders()
    st.dataframe(orders)
