import streamlit as st
import pandas as pd
from database import init_db, get_orders, add_order, update_order_status, get_stock, update_stock_quantity
from datetime import datetime
import urllib.parse

# تهيئة الصفحة
st.set_page_config(page_title="لآفار للمنظفات - النظام الداخلي", layout="wide", initial_sidebar_state="expanded")

# تهيئة قاعدة البيانات
init_db()

# القائمة الجانبية
st.sidebar.title("🏢 لآفار للمنظفات")
page = st.sidebar.radio("الانتقال إلى:", ["واجهة المندوب", "واجهة المحاسب", "واجهة الإدارة"])

# --- واجهة المندوب ---
if page == "واجهة المندوب":
    st.header("📋 تسجيل واعتماد طلبات العملاء")
    
    # 1. إدخال بيانات الطلب (مسودة)
    with st.expander("1️⃣ إدخال بيانات الطلب (مسودة)", expanded=True):
        stock_df = get_stock()
        products = stock_df['Product'].tolist() if not stock_df.empty else ["صابون لآفار 3 لتر"]
        
        c1, c2 = st.columns(2)
        with c1:
            customer_name = st.text_input("اسم العميل / الشركة")
            cr_number = st.text_input("رقم السجل التجاري")
            tax_number = st.text_input("الرقم الضريبي")
            address = st.text_input("العنوان")
        with c2:
            phone = st.text_input("رقم الجوال")
            product = st.selectbox("المنتج", products)
            quantity = st.number_input("الكمية", min_value=1, value=1)
            custom_price = st.number_input("السعر للوحدة (اختياري)", min_value=0.0, value=0.0)
            days_to_due = st.number_input("فترة الاستحقاق (بالأيام)", min_value=0, max_value=99, value=30)
            
            # حساب التاريخ تفاعلياً
            from datetime import timedelta
            calculated_date = datetime.now() + timedelta(days=days_to_due)
            st.info(f"تاريخ الاستحقاق المتوقع: {calculated_date.strftime('%Y-%m-%d')}")

        if st.button("💾 حفظ كمسودة"):
            price = custom_price if custom_price > 0 else None
            add_order(customer_name, cr_number, tax_number, address, phone, product, quantity, days_to_due, price, status='Draft')
            st.success("تم حفظ المسودة بنجاح!")

    # 2. اعتماد الطلبات وإرسالها للمحاسب
    st.divider()
    st.subheader("2️⃣ مراجعة واعتماد المسودات")
    orders = get_orders()
    drafts = orders[orders['Status'] == 'Draft'] if not orders.empty else pd.DataFrame()
    
    if drafts.empty:
        st.info("لا توجد مسودات حالياً")
    else:
        for _, row in drafts.iterrows():
            with st.container(border=True):
                col_a, col_b = st.columns([3, 1])
                with col_a:
                    st.write(f"**العميل:** {row['Customer Name']} | **المنتج:** {row['Product']} ({row['Quantity']})")
                    st.file_uploader(f"رفع مستندات العميل (PDF)", type=['pdf'], key=f"doc_{row['Order ID']}")
                with col_b:
                    if st.button("🚀 اعتماد وإرسال للمحاسب", key=f"confirm_{row['Order ID']}"):
                        update_order_status(row['Order ID'], 'Pending')
                        st.success("تم الإرسال للمحاسب!")
                        st.rerun()

    # 3. الطلبات المفوترة (جديد: للمشاركة مع العميل)
    st.divider()
    st.subheader("✅ الطلبات المفوترة (جاهزة للتسليم للعميل)")
    invoiced_orders = orders[orders['Status'] == 'Invoiced'] if not orders.empty else pd.DataFrame()
    
    if invoiced_orders.empty:
        st.info("لا توجد طلبات جاهزة حالياً")
    else:
        for _, row in invoiced_orders.iterrows():
            with st.container(border=True):
                st.write(f"**العميل:** {row['Customer Name']} | **المبلغ:** {row['Total Amount']} ريال")
                if row['Invoice URL']:
                    st.link_button("📄 فتح الفاتورة لإرسالها للعميل", row['Invoice URL'])
                    st.caption("ملاحظة: بعد فتح الفاتورة، استخدم خيار 'مشاركة' في جوالك لإرسالها عبر الواتساب")

# --- واجهة المحاسب ---
elif page == "واجهة المحاسب":
    st.header("💰 قسم الحسابات والفواتير")
    orders = get_orders()
    pending_orders = orders[orders['Status'] == 'Pending'] if not orders.empty else pd.DataFrame()
    
    if pending_orders.empty:
        st.info("لا توجد طلبات بانتظار الفوترة")
    else:
        for _, row in pending_orders.iterrows():
            with st.container(border=True):
                st.write(f"**طلب رقم:** {row['Order ID']} | **العميل:** {row['Customer Name']} | **المبلغ:** {row['Total Amount']} ريال")
                
                # في التطبيق الحقيقي، هنا يتم رفع الملف وحفظه في S3 أو Drive
                # لمحاكاة ذلك، سنطلب من المحاسب وضع رابط الملف المرفوع
                invoice_link = st.text_input(f"رابط ملف الفاتورة المرفوع (PDF)", key=f"link_{row['Order ID']}")
                
                if st.button("✅ اعتماد الفاتورة", key=f"acc_{row['Order ID']}"):
                    if invoice_link:
                        update_order_status(row['Order ID'], 'Invoiced', invoice_link)
                        st.success("تم اعتماد الفاتورة بنجاح!")
                        st.rerun()
                    else:
                        st.error("يرجى وضع رابط الفاتورة أولاً")

# --- واجهة الإدارة ---
elif page == "واجهة الإدارة":
    st.header("📊 لوحة التحكم والإدارة")
    orders = get_orders()
    stock_df = get_stock()
    
    # إحصائيات سريعة
    c1, c2, c3 = st.columns(3)
    if not orders.empty:
        invoiced = orders[orders['Status'] == 'Invoiced']
        c1.metric("مبيعات اليوم", f"{invoiced['Total Amount'].sum()} ريال")
        c2.metric("طلبات بانتظار الفوترة", len(orders[orders['Status'] == 'Pending']))
        
        # تنبيه المخزون
        low_stock = stock_df[stock_df['Quantity'] < stock_df['Min Limit']]
        c3.metric("منتجات منخفضة المخزون", len(low_stock))
        if not low_stock.empty:
            st.warning(f"تنبيه: {low_stock['Product'].iloc[0]} وصل للحد الأدنى!")

    # تعديل المخزون
    with st.expander("📦 إدارة المخزون"):
        for index, row in stock_df.iterrows():
            new_qty = st.number_input(f"تعديل كمية {row['Product']}", value=int(row['Quantity']), key=f"stock_{index}")
            if st.button(f"تحديث {row['Product']}", key=f"btn_{index}"):
                update_stock_quantity(row['Product'], new_qty)
                st.success("تم تحديث المخزون")
                st.rerun()

    # سجل العمليات وتصدير إكسل
    st.subheader("📜 سجل العمليات الكامل")
    if not orders.empty:
        st.dataframe(orders)
        
        # إضافة صف المجموع
        total_qty = orders['Quantity'].sum()
        total_val = orders['Total Amount'].sum()
        st.write(f"**الإجمالي العام:** الكمية: {total_qty} | المبالغ: {total_val} ريال")
        
        # تصدير إكسل
        csv = orders.to_csv(index=False).encode('utf-8-sig')
        st.download_button("📥 تحميل سجل العمليات كملف Excel (CSV)", csv, "lavar_orders.csv", "text/csv")
