import streamlit as st
import pandas as pd
from database import (
    init_db, get_orders, add_order, update_order_status,
    get_stock, update_stock_quantity, upload_to_drive
)
from datetime import datetime, timedelta

# إعدادات الصفحة
st.set_page_config(
    page_title="لآفار للمنظفات - النظام الداخلي",
    layout="wide",
    initial_sidebar_state="expanded"
)

# تهيئة قاعدة البيانات
init_db()

# ===== القائمة الجانبية =====
st.sidebar.title("🏢 لآفار للمنظفات")
st.sidebar.write("نظام إدارة الطلبات والفواتير")
st.sidebar.divider()

page = st.sidebar.radio(
    "اختر الواجهة:",
    ["واجهة المندوب", "واجهة المحاسب", "واجهة الإدارة"]
)

# ===== واجهة المندوب =====
if page == "واجهة المندوب":
    st.header("📋 واجهة المندوب - تسجيل واعتماد الطلبات")
    
    orders = get_orders()
    stock_df = get_stock()
    
    # 1. إضافة طلب جديد
    with st.expander("1️⃣ إضافة طلب جديد (مسودة)", expanded=True):
        st.write("**ملء بيانات الطلب الجديد:**")
        
        col1, col2 = st.columns(2)
        
        with col1:
            customer_name = st.text_input("اسم العميل / الشركة")
            cr_number = st.text_input("رقم السجل التجاري")
            tax_number = st.text_input("الرقم الضريبي")
            address = st.text_input("العنوان")
            phone = st.text_input("رقم الجوال")
        
        with col2:
            products = stock_df['Product'].tolist() if not stock_df.empty else ["صابون لآفار 3 لتر"]
            product = st.selectbox("المنتج", products)
            quantity = st.number_input("الكمية", min_value=1, value=1, step=1)
            custom_price = st.number_input("السعر للوحدة (اختياري)", min_value=0.0, value=0.0, step=0.1)
            days_to_due = st.number_input("فترة الاستحقاق (بالأيام)", min_value=0, max_value=99, value=30, step=1)
            
            # عرض تاريخ الاستحقاق المتوقع
            calculated_date = datetime.now() + timedelta(days=days_to_due)
            st.info(f"📅 تاريخ الاستحقاق المتوقع: **{calculated_date.strftime('%Y-%m-%d')}**")
        
        if st.button("💾 حفظ كمسودة", use_container_width=True):
            add_order(
                customer_name, cr_number, tax_number, address, phone,
                product, quantity, days_to_due, custom_price, status='Draft'
            )
            st.success("✅ تم حفظ المسودة بنجاح!")
            st.rerun()
    
    # 2. مراجعة واعتماد المسودات
    st.divider()
    st.subheader("2️⃣ مراجعة واعتماد المسودات")
    
    drafts = orders[orders['Status'] == 'Draft'] if not orders.empty else pd.DataFrame()
    
    if drafts.empty:
        st.info("✨ لا توجد مسودات حالياً")
    else:
        st.write(f"**عدد المسودات:** {len(drafts)}")
        
        for idx, row in drafts.iterrows():
            with st.container(border=True):
                col_info, col_action = st.columns([3, 1])
                
                with col_info:
                    st.write(f"**طلب #{row['Order ID']}**")
                    st.write(f"👤 العميل: {row['Customer Name']}")
                    st.write(f"📦 المنتج: {row['Product']} | الكمية: {row['Quantity']}")
                    st.write(f"💰 المبلغ: {row['Total Amount']} ريال | 📅 الاستحقاق: {row['Due Date']}")
                
                with col_action:
                    if st.button("🚀 إرسال للمحاسب", key=f"approve_{row['Order ID']}", use_container_width=True):
                        update_order_status(row['Order ID'], 'Pending')
                        st.success("✅ تم إرسال الطلب للمحاسب!")
                        st.rerun()
    
    # 3. الطلبات المفوترة (جاهزة للمشاركة مع العميل)
    st.divider()
    st.subheader("✅ الطلبات المفوترة (جاهزة للتسليم للعميل)")
    
    invoiced_orders = orders[orders['Status'] == 'Invoiced'] if not orders.empty else pd.DataFrame()
    
    if invoiced_orders.empty:
        st.info("📭 لا توجد طلبات جاهزة حالياً")
    else:
        st.write(f"**عدد الطلبات الجاهزة:** {len(invoiced_orders)}")
        
        for idx, row in invoiced_orders.iterrows():
            with st.container(border=True):
                col_info, col_action = st.columns([3, 1])
                
                with col_info:
                    st.write(f"**طلب #{row['Order ID']}**")
                    st.write(f"👤 العميل: {row['Customer Name']}")
                    st.write(f"💰 المبلغ: {row['Total Amount']} ريال")
                
                with col_action:
                    if row['Invoice URL']:
                        st.link_button(
                            "📄 فتح الفاتورة",
                            row['Invoice URL'],
                            use_container_width=True
                        )
                        st.caption("💡 بعد فتح الفاتورة، استخدم خيار 'مشاركة' في جوالك لإرسالها عبر الواتساب")
                    else:
                        st.warning("⚠️ الفاتورة لم تُرفع بعد")

# ===== واجهة المحاسب =====
elif page == "واجهة المحاسب":
    st.header("💰 واجهة المحاسب - رفع الفواتير والاعتماد")
    
    orders = get_orders()
    pending_orders = orders[orders['Status'] == 'Pending'] if not orders.empty else pd.DataFrame()
    
    if pending_orders.empty:
        st.info("✨ لا توجد طلبات بانتظار الفوترة حالياً")
    else:
        st.write(f"**عدد الطلبات بانتظار الفوترة:** {len(pending_orders)}")
        st.divider()
        
        for idx, row in pending_orders.iterrows():
            with st.container(border=True):
                # معلومات الطلب
                st.write(f"**طلب رقم #{row['Order ID']}**")
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.write(f"👤 العميل: {row['Customer Name']}")
                    st.write(f"📞 الجوال: {row['Phone']}")
                
                with col2:
                    st.write(f"📦 المنتج: {row['Product']}")
                    st.write(f"📊 الكمية: {row['Quantity']}")
                
                with col3:
                    st.write(f"💰 المبلغ: {row['Total Amount']} ريال")
                    st.write(f"📅 الاستحقاق: {row['Due Date']}")
                
                st.divider()
                
                # رفع الفاتورة
                st.write("**رفع ملف الفاتورة (PDF):**")
                pdf_file = st.file_uploader(
                    "اختر ملف PDF",
                    type=['pdf'],
                    key=f"invoice_{row['Order ID']}"
                )
                
                if pdf_file:
                    st.success(f"✅ تم اختيار الملف: {pdf_file.name}")
                    
                    if st.button(
                        "✅ اعتماد ورفع الفاتورة",
                        key=f"confirm_{row['Order ID']}",
                        use_container_width=True
                    ):
                        with st.spinner("⏳ جاري رفع الفاتورة إلى Google Drive..."):
                            # رفع الملف إلى Google Drive
                            invoice_link = upload_to_drive(
                                pdf_file.getvalue(),
                                f"Invoice_Order_{row['Order ID']}.pdf"
                            )
                            
                            if invoice_link:
                                # تحديث حالة الطلب
                                update_order_status(row['Order ID'], 'Invoiced', invoice_link)
                                st.success("✅ تم رفع الفاتورة واعتمادها بنجاح!")
                                st.info(f"🔗 رابط الفاتورة: {invoice_link}")
                                st.rerun()
                            else:
                                st.error("❌ حدث خطأ في رفع الملف. حاول مرة أخرى.")
                else:
                    st.warning("⚠️ يرجى اختيار ملف PDF أولاً")
                
                st.divider()

# ===== واجهة الإدارة =====
elif page == "واجهة الإدارة":
    st.header("📊 واجهة الإدارة - لوحة التحكم")
    
    orders = get_orders()
    stock_df = get_stock()
    
    # الإحصائيات السريعة
    st.subheader("📈 الإحصائيات السريعة")
    
    col1, col2, col3, col4 = st.columns(4)
    
    if not orders.empty:
        invoiced = orders[orders['Status'] == 'Invoiced']
        pending = orders[orders['Status'] == 'Pending']
        drafts = orders[orders['Status'] == 'Draft']
        
        with col1:
            st.metric("💰 إجمالي المبيعات", f"{invoiced['Total Amount'].sum()} ريال")
        
        with col2:
            st.metric("📦 الطلبات المفوترة", len(invoiced))
        
        with col3:
            st.metric("⏳ بانتظار الفوترة", len(pending))
        
        with col4:
            st.metric("📝 المسودات", len(drafts))
    
    st.divider()
    
    # تعديل المخزون
    st.subheader("📦 إدارة المخزون")
    
    if not stock_df.empty:
        with st.expander("تحديث كميات المخزون", expanded=False):
            for idx, row in stock_df.iterrows():
                col1, col2, col3 = st.columns([2, 1, 1])
                
                with col1:
                    st.write(f"**{row['Product']}**")
                    st.caption(f"الحد الأدنى: {row['Min Limit']}")
                
                with col2:
                    new_qty = st.number_input(
                        "الكمية الجديدة",
                        value=int(row['Quantity']),
                        key=f"stock_{idx}"
                    )
                
                with col3:
                    if st.button("تحديث", key=f"update_stock_{idx}"):
                        update_stock_quantity(row['Product'], new_qty)
                        st.success("✅ تم التحديث!")
                        st.rerun()
    
    st.divider()
    
    # سجل العمليات الكامل
    st.subheader("📜 سجل العمليات الكامل")
    
    if not orders.empty:
        # عرض الجدول
        st.dataframe(
            orders[['Order ID', 'Customer Name', 'Product', 'Quantity', 'Total Amount', 'Due Date', 'Status']],
            use_container_width=True,
            hide_index=True
        )
        
        # الإجماليات
        st.divider()
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("إجمالي الكمية", orders['Quantity'].sum())
        
        with col2:
            st.metric("إجمالي المبالغ", f"{orders['Total Amount'].sum()} ريال")
        
        with col3:
            st.metric("عدد الطلبات", len(orders))
        
        # تحميل ملف Excel
        st.divider()
        csv = orders.to_csv(index=False, encoding='utf-8-sig')
        st.download_button(
            "📥 تحميل سجل العمليات (Excel/CSV)",
            csv,
            "lavar_orders.csv",
            "text/csv",
            use_container_width=True
        )
    else:
        st.info("📭 لا توجد طلبات بعد")
