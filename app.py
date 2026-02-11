import streamlit as st
import pandas as pd
from database import init_db, get_orders, add_order, update_order_status, get_stock, upload_to_github, delete_order, update_stock_quantity, add_visit, get_visits
from datetime import datetime, date, timedelta
import plotly.express as px
import plotly.graph_objects as go

# إعداد الصفحة
st.set_page_config(page_title="نظام لآفار المتكامل", layout="wide")
init_db()

UNIT_COST = 5.0
LEAD_TIME_DAYS = 9

# --- نظام تسجيل الدخول ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.title("🔐 تسجيل الدخول - لآفار")
    user = st.text_input("اسم المستخدم")
    password = st.text_input("كلمة المرور", type="password")
    if st.button("دخول", use_container_width=True):
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
st.sidebar.markdown(f"### 👤 {st.session_state.user_name}")
if st.sidebar.button("🚪 تسجيل الخروج", use_container_width=True):
    st.session_state.logged_in = False
    st.rerun()

# تحديد الصفحات بناءً على الدور
if st.session_state.role == "admin":
    available_pages = ["واجهة المندوب", "واجهة المحاسب", "واجهة الإدارة"]
elif st.session_state.role == "accountant":
    available_pages = ["واجهة المحاسب"]
else:
    available_pages = ["واجهة المندوب"]

page = st.sidebar.radio("📌 الانتقال إلى:", available_pages)

# جلب البيانات العامة
orders = get_orders()
visits = get_visits()
stock_df = get_stock()
current_stock = stock_df.iloc[0]['Quantity'] if not stock_df.empty else 0

# --- واجهة المندوب ---
if page == "واجهة المندوب":
    st.header("📋 واجهة المندوب")
    tab1, tab2 = st.tabs(["🛒 إدارة الطلبات", "📍 سجل الزيارات الميدانية"])
    with tab1:
        with st.expander("➕ إضافة طلب جديد", expanded=True):
            c1, c2 = st.columns(2)
            with c1:
                name = st.text_input("👤 اسم العميل")
                prod = st.selectbox("📦 المنتج", ["صابون لآفار 3 لتر"])
                qty = st.number_input("🔢 الكمية", 1, 10000, 1)
            with c2:
                price = st.number_input("💰 سعر العلبة", 0.0, 1000.0, 0.0)
                days = st.number_input("⏳ أيام الاستحقاق", 0, 99, 30)
            if st.button("حفظ الطلب 💾", use_container_width=True):
                add_order(name, "", "", "", "", prod, qty, days, price)
                st.success("✅ تم حفظ الطلب!"); st.rerun()
        
        st.subheader("🚀 طلبات بانتظار الاعتماد")
        drafts = orders[orders['Status'] == 'Draft'] if not orders.empty else pd.DataFrame()
        if not drafts.empty:
            for _, row in drafts.iterrows():
                with st.container(border=True):
                    c_i, c_a = st.columns([4, 1])
                    with c_i: st.write(f"**العميل:** {row['Customer Name']} | **الكمية:** {row['Quantity']}")
                    with c_a:
                        if st.button("إرسال للمحاسب 📤", key=f"p_{row['Order ID']}"):
                            update_order_status(row['Order ID'], 'Pending'); st.rerun()
        
        st.subheader("✅ فواتير جاهزة")
        inv = orders[orders['Status'] == 'Invoiced'] if not orders.empty else pd.DataFrame()
        if not inv.empty:
            for _, row in inv.iterrows():
                with st.container(border=True):
                    st.write(f"**العميل:** {row['Customer Name']} | **المبلغ:** {row['Total Amount']} ريال")
                    if row['Invoice URL']: st.link_button("📄 عرض الفاتورة", row['Invoice URL'])

    with tab2:
        st.subheader("📍 تسجيل زيارة ميدانية")
        with st.form("v_form"):
            c1, c2 = st.columns(2)
            with c1: v_cust = st.text_input("اسم العميل"); v_type = st.selectbox("النوع", ["دورية", "جديد"])
            with c2: v_qty = st.number_input("الكمية المتوقعة", 0); v_date = st.date_input("تاريخ الطلب")
            if st.form_submit_button("حفظ الزيارة"):
                add_visit(st.session_state.user_name, v_cust, v_type, v_qty, str(v_date), "")
                st.success("تم!"); st.rerun()
        st.dataframe(visits, use_container_width=True)

# --- واجهة المحاسب ---
elif page == "واجهة المحاسب":
    st.header("💰 واجهة المحاسب")
    pending = orders[orders['Status'] == 'Pending'] if not orders.empty else pd.DataFrame()
    if not pending.empty:
        for _, row in pending.iterrows():
            with st.container(border=True):
                st.write(f"**طلب #{row['Order ID']}** | {row['Customer Name']} | {row['Total Amount']} ريال")
                up = st.file_uploader("ارفع الفاتورة (PDF)", key=f"up_{row['Order ID']}")
                if up and st.button("اعتماد الرفع", key=f"acc_{row['Order ID']}"):
                    url = upload_to_github(up.getvalue(), f"inv_{row['Order ID']}.pdf")
                    update_order_status(row['Order ID'], 'Invoiced', url); st.rerun()
    else: st.info("لا توجد طلبات معلقة")

# --- واجهة الإدارة ---
elif page == "واجهة الإدارة":
    st.header("📊 مركز القيادة والتحكم الاستراتيجي")
    t1, t2, t3 = st.tabs(["🧠 التخطيط ودعم القرار", "💰 السيولة والمبيعات", "📦 إدارة المخزون"])
    
    with t1:
        st.subheader("🤖 مستشار لآفار التنفيذي")
        conf = st.slider("🎯 نسبة الثقة في التوقعات (%)", 10, 100, 80)
        
        # تحليل التوقعات والإنتاج
        v_df = visits.copy()
        if not v_df.empty:
            v_df['Potential Date'] = pd.to_datetime(v_df['Potential Date'])
            v_df['Month'] = v_df['Potential Date'].dt.to_period('M').astype(str)
            v_df['Adj Qty'] = v_df['Potential Qty'] * (conf/100)
            m_demand = v_df.groupby('Month')['Adj Qty'].sum().reset_index()
            
            # التوصيات
            total_pot = m_demand['Adj Qty'].sum()
            with st.container(border=True):
                if total_pot > current_stock:
                    st.error(f"⚠️ **توصية إنتاج:** الطلب المتوقع ({int(total_pot)}) يتجاوز المخزون. انت بحاجة لإنتاج **{int(total_pot - current_stock)}** علبة.")
                    # جدول الإنتاج
                    mps = m_demand.copy()
                    mps['الإنتاج المطلوب'] = mps['Adj Qty'].apply(lambda x: max(0, x)) # تبسيط للجدول
                    mps['تاريخ بدء الإنتاج'] = mps['Month'].apply(lambda x: (pd.to_datetime(str(x)) - timedelta(days=LEAD_TIME_DAYS)).strftime('%Y-%m-%d'))
                    st.table(mps[['Month', 'Adj Qty', 'الإنتاج المطلوب', 'تاريخ بدء الإنتاج']].rename(columns={'Month': 'الشهر', 'Adj Qty': 'الطلب'}))
                else:
                    st.success("✅ المخزون الحالي يغطي التوقعات.")
        else: st.info("لا توجد بيانات زيارات حالياً.")

    with t2:
        st.subheader("💰 تحليل التدفق النقدي")
        if not orders.empty:
            inv = orders[orders['Status'] == 'Invoiced'].copy()
            if not inv.empty:
                st.metric("إجمالي التحصيلات", f"{inv['Total Amount'].sum()} ريال")
                inv['Due Date'] = pd.to_datetime(inv['Due Date'])
                cf = inv.groupby('Due Date')['Total Amount'].sum().sort_index().cumsum().reset_index()
                st.plotly_chart(px.area(cf, x='Due Date', y='Total Amount'), use_container_width=True)

    with t3:
        st.subheader("📦 إدارة المخزون")
        new_q = st.number_input("تحديث الكمية الفعلية", value=int(current_stock))
        if st.button("حفظ التحديث"):
            update_stock_quantity("صابون لآفار 3 لتر", new_q); st.rerun()
