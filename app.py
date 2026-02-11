import streamlit as st
import pandas as pd
from database import init_db, get_orders, add_order, update_order_status, get_stock, upload_to_github, delete_order, update_stock_quantity, add_visit, get_visits
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
        if user == "admin" and password == "lavar2026":
            st.session_state.logged_in, st.session_state.role, st.session_state.user_name = True, "admin", "المدير العام"
            st.rerun()
        elif user == "acc" and password == "lavar_acc":
            st.session_state.logged_in, st.session_state.role, st.session_state.user_name = True, "accountant", "المحاسب"
            st.rerun()
        elif user == "sales" and password == "lavar_sales":
            st.session_state.logged_in, st.session_state.role, st.session_state.user_name = True, "sales", "المندوب"
            st.rerun()
        else: st.error("بيانات الدخول غير صحيحة")
    st.stop()

# القائمة الجانبية
st.sidebar.title(f"👤 {st.session_state.user_name}")
if st.sidebar.button("تسجيل الخروج"):
    st.session_state.logged_in = False
    st.rerun()

available_pages = ["واجهة المندوب", "واجهة المحاسب", "واجهة الإدارة"] if st.session_state.role == "admin" else \
                  (["واجهة المحاسب"] if st.session_state.role == "accountant" else ["واجهة المندوب"])
page = st.sidebar.radio("الانتقال إلى:", available_pages)

# --- واجهة المندوب ---
if page == "واجهة المندوب":
    st.header("📋 واجهة المندوب")
    tab1, tab2 = st.tabs(["🛒 إضافة طلب", "📍 سجل الزيارات الميدانية"])
    
    with tab1:
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
                    st.write(f"**العميل:** {row['Customer Name']} | **المنتج:** {row['Product']}")
                    st.write(f"📦 الكمية: {row['Quantity']} | 💰 سعر العلبة: {row['Unit Price']} ريال | 💵 الإجمالي: {row['Total Amount']} ريال")
                with col_btn:
                    if st.button("إرسال للمحاسب", key=f"p_{row['Order ID']}", use_container_width=True):
                        update_order_status(row['Order ID'], 'Pending'); st.rerun()
                with col_del:
                    if st.button("🗑️", key=f"d_{row['Order ID']}", use_container_width=True):
                        delete_order(row['Order ID']); st.rerun()

    with tab2:
        st.subheader("📍 تسجيل زيارة ميدانية")
        with st.form("visit_form"):
            v_customer = st.text_input("اسم العميل المزوار")
            v_type = st.selectbox("نوع الزيارة", ["زيارة دورية", "عميل محتمل جديد", "متابعة شكوى", "تحصيل"])
            st.markdown("---")
            st.write("🔮 **الطلبات المحتملة (لتنظيم الإنتاج)**")
            pot_qty = st.number_input("الكمية المتوقع طلبها (علبة)", 0, 10000, 0)
            pot_date = st.date_input("التاريخ المتوقع للطلب", date.today() + timedelta(days=7))
            v_notes = st.text_area("ملاحظات الزيارة")
            if st.form_submit_button("💾 تسجيل الزيارة", use_container_width=True):
                add_visit(st.session_state.user_name, v_customer, v_type, pot_qty, str(pot_date), v_notes)
                st.success("✅ تم تسجيل الزيارة بنجاح!")

# واجهات المحاسب والإدارة تبقى كما هي مع إضافة تقارير الزيارات للإدارة
elif page == "واجهة المحاسب":
    st.header("💰 واجهة المحاسب")
    orders = get_orders()
    pending = orders[orders['Status'] == 'Pending'] if not orders.empty else pd.DataFrame()
    for _, row in pending.iterrows():
        with st.container(border=True):
            st.write(f"**طلب #{row['Order ID']}** - العميل: {row['Customer Name']} - المبلغ: {row['Total Amount']} ريال")
            pdf_file = st.file_uploader("ارفع الفاتورة", type=['pdf'], key=f"f_{row['Order ID']}")
            col1, col2 = st.columns([4, 1])
            with col1:
                if pdf_file and st.button("✅ اعتماد ورفع", key=f"b_{row['Order ID']}", use_container_width=True):
                    url = upload_to_github(pdf_file.getvalue(), f"inv_{row['Order ID']}.pdf")
                    if url: update_order_status(row['Order ID'], 'Invoiced', url); st.rerun()
            with col2:
                if st.button("🗑️", key=f"da_{row['Order ID']}", use_container_width=True):
                    delete_order(row['Order ID']); st.rerun()

elif page == "واجهة الإدارة":
    st.header("📊 لوحة التحكم والمراقبة")
    tab_m, tab_p, tab_v = st.tabs(["💰 المبيعات", "🏭 تخطيط الإنتاج", "📍 نشاط الميدان"])
    orders = get_orders()
    visits = get_visits()
    
    with tab_m:
        if not orders.empty:
            invoiced = orders[orders['Status'] == 'Invoiced']
            st.metric("💰 إجمالي المبيعات المفوترة", f"{invoiced['Total Amount'].sum()} ريال")
            st.dataframe(orders, use_container_width=True)
        else: st.info("لا توجد بيانات")

    with tab_p:
        st.subheader("🔮 توقعات الطلب القادم")
        if not visits.empty:
            pot_orders = visits[visits['Potential Qty'] > 0].copy()
            if not pot_orders.empty:
                st.metric("📦 إجمالي الكميات المحتملة", f"{pot_orders['Potential Qty'].sum()} علبة")
                fig = px.bar(pot_orders, x='Potential Date', y='Potential Qty', color='Customer Name', title="الجدول الزمني للإنتاج")
                st.plotly_chart(fig, use_container_width=True)
                st.table(pot_orders[['Customer Name', 'Potential Qty', 'Potential Date', 'Salesman']])
            else: st.info("لا توجد طلبات محتملة")

    with tab_v:
        st.subheader("📍 سجل نشاط المناديب")
        if not visits.empty:
            st.dataframe(visits, use_container_width=True)
        else: st.info("لا توجد زيارات")
