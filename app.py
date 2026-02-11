import streamlit as st
import pandas as pd
from database import init_db, get_orders, add_order, update_order_status, get_stock, upload_to_github
from datetime import datetime, timedelta

# إعداد الصفحة
st.set_page_config(page_title="لآفار للمنظفات - النظام الداخلي", layout="wide")
init_db()

# القائمة الجانبية
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
            products = stock_df['Product'].tolist() if not stock_df.empty else ["صابون لآفار 3 لتر"]
            prod = st.selectbox("المنتج", products)
            qty = st.number_input("الكمية", min_value=1, value=1)
            custom_price = st.number_input("السعر للوحدة (اختياري - اتركه 0 للسعر الافتراضي)", min_value=0.0, value=0.0)
            days = st.number_input("فترة الاستحقاق (بالأيام)", min_value=0, max_value=99, value=30)
            
            # حساب تاريخ الاستحقاق تفاعلياً
            calculated_date = datetime.now() + timedelta(days=days)
            st.info(f"📅 تاريخ الاستحقاق المتوقع: {calculated_date.strftime('%Y-%m-%d')}")

        if st.button("💾 حفظ كمسودة", use_container_width=True):
            # إرسال كافة البيانات للدالة
            add_order(name, cr, tax, address, phone, prod, qty, days, custom_price if custom_price > 0 else None)
            st.success("✅ تم حفظ المسودة بنجاح!")
            st.rerun()

    st.divider()
    st.subheader("🚀 مسودات بانتظار الاعتماد")
    drafts = orders[orders['Status'] == 'Draft'] if not orders.empty else pd.DataFrame()
    if drafts.empty:
        st.info("لا توجد مسودات حالياً")
    else:
        for _, row in drafts.iterrows():
            with st.container(border=True):
                st.write(f"**العميل:** {row['Customer Name']} | **المنتج:** {row['Product']} ({row['Quantity']})")
                if st.button("🚀 إرسال للمحاسب", key=f"p_{row['Order ID']}", use_container_width=True):
                    update_order_status(row['Order ID'], 'Pending')
                    st.rerun()

    st.divider()
    st.subheader("✅ فواتير جاهزة للمشاركة")
    inv = orders[orders['Status'] == 'Invoiced'] if not orders.empty else pd.DataFrame()
    if inv.empty:
        st.info("لا توجد فواتير جاهزة")
    else:
        for _, row in inv.iterrows():
            with st.container(border=True):
                st.write(f"**العميل:** {row['Customer Name']} | **المبلغ:** {row['Total Amount']} ريال")
                if row['Invoice URL']:
                    st.link_button("📄 فتح الفاتورة للمشاركة", row['Invoice URL'], use_container_width=True)

# --- واجهة المحاسب ---
elif page == "واجهة المحاسب":
    st.header("💰 واجهة المحاسب")
    orders = get_orders()
    pending = orders[orders['Status'] == 'Pending'] if not orders.empty else pd.DataFrame()
    if pending.empty:
        st.info("لا توجد طلبات بانتظار الفوترة")
    else:
        for _, row in pending.iterrows():
            with st.container(border=True):
                st.write(f"**طلب #{row['Order ID']}** - العميل: {row['Customer Name']}")
                st.write(f"المبلغ المطلوب: {row['Total Amount']} ريال")
                pdf_file = st.file_uploader("ارفع الفاتورة هنا (PDF)", type=['pdf'], key=f"f_{row['Order ID']}")
                if pdf_file and st.button("✅ اعتماد ورفع الفاتورة", key=f"b_{row['Order ID']}", use_container_width=True):
                    with st.spinner("جاري الرفع والأتمتة..."):
                        file_name = f"invoice_{row['Order ID']}_{datetime.now().strftime('%Y%m%d%H%M%S')}.pdf"
                        url = upload_to_github(pdf_file.getvalue(), file_name)
                        if url:
                            update_order_status(row['Order ID'], 'Invoiced', url)
                            st.success("✅ تم الرفع والاعتماد بنجاح!")
                            st.rerun()

# --- واجهة الإدارة ---
elif page == "واجهة الإدارة":
    st.header("📊 لوحة التحكم والإدارة")
    orders = get_orders()
    if not orders.empty:
        st.subheader("📈 إحصائيات سريعة")
        c1, c2, c3 = st.columns(3)
        invoiced = orders[orders['Status'] == 'Invoiced']
        c1.metric("إجمالي المبيعات", f"{invoiced['Total Amount'].sum()} ريال")
        c2.metric("طلبات بانتظار الفوترة", len(orders[orders['Status'] == 'Pending']))
        c3.metric("إجمالي الطلبات", len(orders))
        
        st.divider()
        st.subheader("📜 سجل العمليات الكامل")
        st.dataframe(orders, use_container_width=True)
        
        csv = orders.to_csv(index=False).encode('utf-8-sig')
        st.download_button("📥 تحميل سجل العمليات (Excel)", csv, "lavar_orders.csv", "text/csv")
    else:
        st.info("لا توجد بيانات حالياً")
