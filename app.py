import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from database_gsheets import init_db, get_orders, add_order, update_order_status, get_stock, update_stock_quantity
from datetime import datetime, timedelta
import urllib.parse
import os
import io

# إعداد الصفحة
st.set_page_config(page_title="لآفار للمنظفات - النظام الداخلي", layout="wide")

# تهيئة قاعدة البيانات
init_db()

# العناوين والترجمة
st.sidebar.title("🧼 نظام لآفار للمنظفات")
page = st.sidebar.radio("انتقل إلى:", ["واجهة المندوب", "واجهة المحاسب", "واجهة الإدارة"])

# --- واجهة المندوب ---
if page == "واجهة المندوب":
    st.header("📋 تسجيل واعتماد طلبات العملاء")
    
    if 'days_to_due' not in st.session_state:
        st.session_state.days_to_due = 30

    st.subheader("1️⃣ إدخال بيانات الطلب (مسودة)")
    
    col1, col2 = st.columns(2)
    with col1:
        customer_name = st.text_input("اسم العميل / الشركة", key="cust_name")
        cr_number = st.text_input("رقم السجل التجاري", key="cr_num")
        tax_number = st.text_input("الرقم الضريبي", key="tax_num")
    with col2:
        phone = st.text_input("رقم الجوال", key="phone_num")
        address = st.text_area("العنوان", key="addr")
    
    st.divider()
    col3, col4, col5, col6 = st.columns(4)
    with col3:
        stock_df = get_stock()
        product = st.selectbox("المنتج", stock_df['Product'].tolist(), key="prod_select")
    with col4:
        quantity = st.number_input("الكمية", min_value=1, value=1, key="qty_input")
    with col5:
        # إضافة خانة السعر كما طلب المستخدم
        default_price = float(stock_df[stock_df['Product'] == product]['Price'].values[0]) if not stock_df.empty else 0.0
        custom_price = st.number_input("السعر للوحدة (ريال)", min_value=0.0, value=default_price, step=0.5, key="price_input")
    with col6:
        days = st.number_input("فترة الاستحقاق (بالأيام)", min_value=0, max_value=99, value=st.session_state.days_to_due, key="days_input")
        st.session_state.days_to_due = days
        calc_date = (datetime.now() + timedelta(days=days)).strftime('%Y-%m-%d')
        st.info(f"📅 تاريخ الاستحقاق: {calc_date}")

    if st.button("💾 حفظ كمسودة"):
        order_id = add_order(customer_name, cr_number, tax_number, address, phone, product, quantity, days, custom_price=custom_price, status='Draft')
        st.success(f"✅ تم حفظ الطلب #{order_id} كمسودة بنجاح")
        st.rerun()

    st.divider()
    st.subheader("2️⃣ إدارة المسودات ورفع المستندات والاعتماد")
    orders = get_orders()
    drafts = orders[orders['Status'] == 'Draft']
    
    if drafts.empty:
        st.info("لا توجد مسودات حالياً")
    else:
        for index, row in drafts.iloc[::-1].iterrows():
            with st.expander(f"📁 مسودة طلب #{row['Order ID']} - {row['Customer Name'] if pd.notnull(row['Customer Name']) else 'بدون اسم'}"):
                st.write(f"**المنتج:** {row['Product']} | **الكمية:** {row['Quantity']} | **السعر:** {row['Unit Price']} ريال | **المبلغ:** {row['Total Amount']} ريال")
                
                up_file = st.file_uploader(f"تحميل مستندات العميل (PDF) لطلب #{row['Order ID']}", type=['pdf'], key=f"doc_{row['Order ID']}")
                
                if st.button(f"🚀 اعتماد وإرسال للمحاسب (# {row['Order ID']})", key=f"conf_{row['Order ID']}"):
                    doc_path = f"docs/confirmed_{row['Order ID']}.pdf" if up_file else row['Customer Docs']
                    update_order_status(row['Order ID'], 'Pending', docs_path=doc_path)
                    st.success(f"تم اعتماد الطلب #{row['Order ID']} ونقله للمحاسب")
                    st.rerun()

    st.divider()
    st.subheader("3️⃣ الطلبات المعتمدة والسابقة")
    confirmed_orders = orders[orders['Status'] != 'Draft']
    if not confirmed_orders.empty:
        for index, row in confirmed_orders.iloc[::-1].iterrows():
            with st.expander(f"✅ طلب #{row['Order ID']} - {row['Customer Name']} ({row['Status']})"):
                st.write(f"**الحالة:** {row['Status']} | **تاريخ الاستحقاق:** {row['Due Date'].strftime('%Y-%m-%d') if pd.notnull(row['Due Date']) else 'غير محدد'}")
                if row['Status'] == 'Invoiced':
                    msg = f"مرحباً {row['Customer Name']}، فاتورتك جاهزة: {row['Invoice URL']}"
                    encoded_msg = urllib.parse.quote(msg)
                    st.link_button("📲 واتساب", f"https://wa.me/{row['Phone']}?text={encoded_msg}")

# --- واجهة المحاسب ---
elif page == "واجهة المحاسب":
    st.header("💰 طلبات بانتظار الفوترة (المعتمدة فقط)")
    orders = get_orders()
    pending_orders = orders[orders['Status'] == 'Pending']
    
    if pending_orders.empty:
        st.info("لا توجد طلبات معتمدة بانتظار الفوترة حالياً")
    else:
        for index, row in pending_orders.iterrows():
            with st.container(border=True):
                c1, c2, c3 = st.columns([2, 2, 1])
                with c1:
                    st.write(f"**العميل:** {row['Customer Name']}")
                    st.write(f"**القيمة:** {row['Total Amount']} ريال")
                with c2:
                    st.file_uploader(f"رفع الفاتورة PDF (# {row['Order ID']})", type=['pdf'], key=f"acc_file_{row['Order ID']}")
                with c3:
                    if st.button("إصدار الفاتورة", key=f"acc_btn_{row['Order ID']}"):
                        fake_url = f"https://lavar.sa/inv/INV-{row['Order ID']}.pdf"
                        update_order_status(row['Order ID'], 'Invoiced', fake_url)
                        st.success("تم التحديث")
                        st.rerun()

# --- واجهة الإدارة ---
elif page == "واجهة الإدارة":
    st.header("📊 الإدارة والمخزون")
    orders = get_orders()
    stock = get_stock()
    
    # إحصائيات سريعة
    if not orders.empty:
        total_sales = orders[orders['Status'] != 'Draft']['Total Amount'].sum()
        st.metric("إجمالي المبيعات المعتمدة", f"{total_sales} ريال")
    
    st.divider()
    
    # --- ميزة التصدير إلى Excel ---
    st.subheader("📥 تصدير البيانات")
    if not orders.empty:
        # إنشاء ملف Excel في الذاكرة
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            orders.to_excel(writer, index=False, sheet_name='سجل العمليات')
        
        st.download_button(
            label="📥 تحميل سجل العمليات كملف Excel",
            data=buffer.getvalue(),
            file_name=f"lavar_orders_{datetime.now().strftime('%Y%m%d')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    else:
        st.info("لا توجد بيانات للتصدير حالياً")

    st.divider()
    st.subheader("📦 تعديل المخزون")
    for index, row in stock.iterrows():
        col_s1, col_s2, col_s3 = st.columns([2, 2, 1])
        with col_s1: st.write(f"**{row['Product']}**")
        with col_s2: new_qty = st.number_input("الكمية", value=int(row['Quantity']), key=f"st_{index}")
        with col_s3: 
            if st.button("تحديث", key=f"up_{index}"):
                update_stock_quantity(row['Product'], new_qty)
                st.rerun()

    st.divider()
    st.subheader("📋 سجل العمليات الكامل")
    if not orders.empty:
        confirmed = orders[orders['Status'] != 'Draft']
        total_row = pd.DataFrame([{
            'Order ID': 'مجموع المعتمد',
            'Customer Name': '-',
            'Quantity': confirmed['Quantity'].sum(),
            'Total Amount': confirmed['Total Amount'].sum(),
            'Status': '-'
        }])
        display_df = pd.concat([orders, total_row], ignore_index=True)
        st.dataframe(display_df, use_container_width=True)
