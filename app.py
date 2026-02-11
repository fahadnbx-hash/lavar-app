import streamlit as st
import pandas as pd
from database import init_db, get_orders, add_order, update_order_status, get_stock, upload_to_github, delete_order, update_stock_quantity
from datetime import datetime, timedelta
import plotly.express as px

# إعداد الصفحة
st.set_page_config(page_title="لآفار للمنظفات", layout="wide")
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
            prod_list = stock_df['Product'].tolist() if not stock_df.empty else ["صابون لآفار 3 لتر"]
            prod = st.selectbox("المنتج", prod_list)
            qty = st.number_input("الكمية", 1, 1000, 1)
            price = st.number_input("سعر العلبة", 0.0, 1000.0, 0.0)
            days = st.number_input("أيام الاستحقاق", 0, 99, 30)
        
        if st.button("التالي ➡️", use_container_width=True):
            add_order(name, cr, tax, address, phone, prod, qty, days, price if price > 0 else None)
            st.success("✅ تم حفظ الطلب بنجاح!")
            st.rerun()

    st.divider()
    st.subheader("🚀 طلبات بانتظار الاعتماد")
    drafts = orders[orders['Status'] == 'Draft'] if not orders.empty else pd.DataFrame()
    if drafts.empty:
        st.info("لا توجد طلبات بانتظار الاعتماد حالياً")
    else:
        for _, row in drafts.iterrows():
            with st.container(border=True):
                col_info, col_btn, col_del = st.columns([3, 1, 0.6])
                with col_info:
                    st.markdown(f"**العميل:** {row['Customer Name']} | **المنتج:** {row['Product']}")
                    st.markdown(f"🔢 الكمية: `{row['Quantity']}` | 💵 سعر العلبة: `{row['Unit Price']} ريال` | 💰 الإجمالي: **{row['Total Amount']} ريال**")
                with col_btn:
                    if st.button("إرسال للمحاسب", key=f"p_{row['Order ID']}", use_container_width=True):
                        update_order_status(row['Order ID'], 'Pending')
                        st.rerun()
                with col_del:
                    if st.button("🗑️", key=f"d_{row['Order ID']}", help="حذف الطلب", use_container_width=True):
                        delete_order(row['Order ID'])
                        st.rerun()

    st.divider()
    st.subheader("✅ فواتير جاهزة للمشاركة")
    inv = orders[orders['Status'] == 'Invoiced'] if not orders.empty else pd.DataFrame()
    if inv.empty:
        st.info("لا توجد فواتير جاهزة")
    else:
        for _, row in inv.iterrows():
            with st.container(border=True):
                col_info, col_btn, col_del = st.columns([3, 1, 0.6])
                with col_info:
                    st.markdown(f"**العميل:** {row['Customer Name']} | 💰 الإجمالي: **{row['Total Amount']} ريال**")
                with col_btn:
                    if row['Invoice URL']:
                        st.link_button("📄 فتح الفاتورة", row['Invoice URL'], use_container_width=True)
                with col_del:
                    if st.button("🗑️", key=f"di_{row['Order ID']}", help="حذف الطلب", use_container_width=True):
                        delete_order(row['Order ID'])
                        st.rerun()

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
                col_info, col_del = st.columns([4, 0.5])
                with col_info:
                    st.write(f"**العميل:** {row['Customer Name']} | **المبلغ:** {row['Total Amount']} ريال")
                    st.write(f"🔢 الكمية: {row['Quantity']} | 💵 سعر العلبة: {row['Unit Price']} ريال")
                with col_del:
                    if st.button("🗑️", key=f"da_{row['Order ID']}", help="إلغاء الطلب", use_container_width=True):
                        delete_order(row['Order ID'])
                        st.rerun()
                
                pdf_file = st.file_uploader("ارفع الفاتورة (PDF)", type=['pdf'], key=f"f_{row['Order ID']}")
                if pdf_file and st.button("✅ اعتماد ورفع الفاتورة", key=f"b_{row['Order ID']}", use_container_width=True):
                    with st.spinner("جاري الرفع..."):
                        url = upload_to_github(pdf_file.getvalue(), f"inv_{row['Order ID']}.pdf")
                        if url:
                            update_order_status(row['Order ID'], 'Invoiced', url)
                            st.success("تم الاعتماد!")
                            st.rerun()

# --- واجهة الإدارة ---
elif page == "واجهة الإدارة":
    st.header("📊 لوحة التحكم والإدارة")
    orders = get_orders()
    stock_df = get_stock()
    
    if not orders.empty:
        # 1. إحصائيات سريعة
        st.subheader("📈 نظرة عامة")
        c1, c2, c3, c4 = st.columns(4)
        invoiced = orders[orders['Status'] == 'Invoiced']
        pending = orders[orders['Status'] == 'Pending']
        
        c1.metric("💰 إجمالي المبيعات المفوترة", f"{invoiced['Total Amount'].sum()} ريال")
        c2.metric("⏳ طلبات معلقة", len(pending))
        c3.metric("📦 كمية العلب المباعة", invoiced['Quantity'].sum())
        c4.metric("📈 متوسط قيمة الطلب", f"{round(invoiced['Total Amount'].mean(), 2) if not invoiced.empty else 0} ريال")
        
        st.divider()
        
        # 2. رسم بياني للتدفق النقدي (100 يوم)
        st.subheader("📅 توقعات التدفق النقدي (100 يوم)")
        if not invoiced.empty:
            cash_flow = invoiced.groupby('Due Date')['Total Amount'].sum().reset_index()
            fig = px.line(cash_flow, x='Due Date', y='Total Amount', title='المبالغ المتوقع تحصيلها بناءً على تاريخ الاستحقاق', markers=True)
            st.plotly_chart(fig, use_container_width=True)
        
        st.divider()
        
        # 3. إدارة المخزون والأسعار
        st.subheader("📦 إدارة المخزون والأسعار")
        with st.expander("تعديل كميات وأسعار المخزون"):
            for idx, row in stock_df.iterrows():
                col1, col2, col3 = st.columns([2, 1, 1])
                with col1:
                    st.write(f"**المنتج:** {row['Product']}")
                with col2:
                    new_qty = st.number_input(f"الكمية لـ {row['Product']}", value=int(row['Quantity']), key=f"sq_{idx}")
                with col3:
                    if st.button(f"تحديث {row['Product']}", key=f"sb_{idx}"):
                        update_stock_quantity(row['Product'], new_qty)
                        st.success("تم التحديث!")
                        st.rerun()

        st.divider()
        
        # 4. سجل العمليات الكامل
        st.subheader("📜 سجل العمليات التفصيلي")
        st.dataframe(orders, use_container_width=True)
        
        # زر التصدير
        csv = orders.to_csv(index=False).encode('utf-8-sig')
        st.download_button("📥 تحميل سجل العمليات كملف Excel", csv, "lavar_report.csv", "text/csv", use_container_width=True)
    else:
        st.info("لا توجد بيانات حالياً في النظام")
