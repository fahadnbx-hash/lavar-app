import streamlit as st
import pandas as pd
from database import init_db, get_orders, add_order, update_order_status, get_stock, upload_to_github, delete_order, update_stock_quantity, add_visit, get_visits
from datetime import datetime, date, timedelta
import plotly.express as px
import plotly.graph_objects as go

# إعداد الصفحة
st.set_page_config(page_title="نظام لآفار الاستراتيجي", layout="wide")
init_db()

UNIT_COST = 5.0

# --- نظام تسجيل الدخول (ثابت) ---
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

# تحديد الصلاحيات
if st.session_state.role == "admin":
    available_pages = ["واجهة المندوب", "واجهة المحاسب", "واجهة الإدارة"]
elif st.session_state.role == "accountant":
    available_pages = ["واجهة المحاسب"]
else:
    available_pages = ["واجهة المندوب"]

page = st.sidebar.radio("📌 الانتقال إلى:", available_pages)

# جلب البيانات
orders = get_orders()
visits = get_visits()
stock_df = get_stock()

# --- واجهة المندوب (كاملة) ---
if page == "واجهة المندوب":
    st.header("📋 مركز عمليات المندوب")
    t1, t2 = st.tabs(["🛒 الطلبات", "📍 الزيارات الميدانية"])
    with t1:
        with st.expander("➕ إنشاء طلب جديد"):
            c1, c2 = st.columns(2)
            with c1:
                name = st.text_input("👤 اسم العميل")
                cr = st.text_input("📄 السجل التجاري")
                tax = st.text_input("🔢 الرقم الضريبي")
                address = st.text_input("📍 العنوان")
                phone = st.text_input("📞 رقم الجوال")
            with c2:
                prod_list = stock_df['Product'].tolist() if not stock_df.empty else ["صابون لآفار 3 لتر"]
                prod = st.selectbox("📦 المنتج", prod_list)
                qty = st.number_input("🔢 الكمية", 1, 10000, 1)
                price = st.number_input("💰 سعر العلبة", 0.0, 1000.0, 0.0)
                days = st.number_input("⏳ أيام الاستحقاق", 0, 99, 30)
            if st.button("حفظ المسودة", use_container_width=True):
                add_order(name, cr, tax, address, phone, prod, qty, days, price)
                st.success("تم الحفظ!"); st.rerun()
        
        st.subheader("🚀 مسوداتك الحالية")
        drafts = orders[orders['Status'] == 'Draft'] if not orders.empty else pd.DataFrame()
        if not drafts.empty:
            for _, row in drafts.iterrows():
                with st.container(border=True):
                    c_i, c_a = st.columns([4, 1])
                    with c_i: st.write(f"**العميل:** {row['Customer Name']} | **المبلغ:** {row['Total Amount']} ريال")
                    with c_a:
                        if st.button("إرسال 📤", key=f"p_{row['Order ID']}"):
                            update_order_status(row['Order ID'], 'Pending'); st.rerun()
        
        st.subheader("✅ فواتير جاهزة للعميل")
        inv = orders[orders['Status'] == 'Invoiced'] if not orders.empty else pd.DataFrame()
        if not inv.empty:
            for _, row in inv.iterrows():
                with st.container(border=True):
                    st.write(f"**العميل:** {row['Customer Name']} | {row['Total Amount']} ريال")
                    if row['Invoice URL']: st.link_button("📄 تحميل الفاتورة", row['Invoice URL'])

    with t2:
        with st.form("v_form"):
            c1, c2 = st.columns(2)
            with c1: v_cust = st.text_input("اسم العميل"); v_type = st.selectbox("النوع", ["دورية", "جديد", "تحصيل"])
            with c2: v_qty = st.number_input("الكمية المتوقعة", 0); v_date = st.date_input("تاريخ الطلب")
            v_notes = st.text_area("ملاحظات")
            if st.form_submit_button("حفظ الزيارة"):
                add_visit(st.session_state.user_name, v_cust, v_type, v_qty, str(v_date), v_notes)
                st.success("تم!"); st.rerun()
        st.dataframe(visits[visits['Salesman'] == st.session_state.user_name] if not visits.empty else pd.DataFrame(), use_container_width=True)

# --- واجهة المحاسب (كاملة) ---
elif page == "واجهة المحاسب":
    st.header("💰 مركز المحاسبة")
    pending = orders[orders['Status'] == 'Pending'] if not orders.empty else pd.DataFrame()
    if not pending.empty:
        for _, row in pending.iterrows():
            with st.container(border=True):
                st.write(f"**طلب #{row['Order ID']}** | {row['Customer Name']} | {row['Total Amount']} ريال")
                up = st.file_uploader("ارفع PDF", key=f"up_{row['Order ID']}")
                if up and st.button("اعتماد", key=f"acc_{row['Order ID']}"):
                    url = upload_to_github(up.getvalue(), f"inv_{row['Order ID']}.pdf")
                    update_order_status(row['Order ID'], 'Invoiced', url); st.rerun()
    else: st.info("لا توجد طلبات معلقة")

# --- واجهة الإدارة (الاحترافية والعميقة) ---
elif page == "واجهة الإدارة":
    st.header("🏢 لوحة القيادة الاستراتيجية")
    tab_strat, tab_stock, tab_finance = st.tabs(["🎯 التخطيط الاستراتيجي", "📦 التحكم بالمخزون", "💸 تحليل السيولة"])
    
    with tab_strat:
        st.subheader("📈 تحليل فجوة الإنتاج والطلب المتوقع")
        conf = st.slider("نسبة التفاؤل في التوقعات (%)", 10, 100, 80)
        
        if not visits.empty:
            v_df = visits.copy()
            v_df['Potential Date'] = pd.to_datetime(v_df['Potential Date'])
            v_df['Month'] = v_df['Potential Date'].dt.to_period('M').astype(str)
            v_df['Adj Qty'] = v_df['Potential Qty'] * (conf/100)
            
            # حساب الفجوة
            total_stock = stock_df['Quantity'].sum() if not stock_df.empty else 0
            total_pot = v_df['Adj Qty'].sum()
            prod_gap = max(0, total_pot - total_stock)
            
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("إجمالي التوقعات", f"{int(total_pot)} علبة")
            c2.metric("المخزون الحالي", f"{int(total_stock)} علبة")
            c3.metric("فجوة الإنتاج", f"{int(prod_gap)} علبة", delta=f"{int(total_pot - total_stock)}", delta_color="inverse")
            c4.metric("تكلفة الإنتاج", f"{int(prod_gap * UNIT_COST)} ريال")
            
            # رسم بياني احترافي
            m_data = v_df.groupby('Month')['Adj Qty'].sum().reset_index()
            fig = px.line(m_data, x='Month', y='Adj Qty', title="مسار الطلب المتوقع (شهرياً)", markers=True)
            fig.add_bar(x=m_data['Month'], y=m_data['Adj Qty'], name="الكمية")
            st.plotly_chart(fig, use_container_width=True)
        else: st.info("بيانات الزيارات غير كافية")

    with tab_stock:
        st.subheader("🚨 مراقبة المخزون الذكية")
        if not stock_df.empty:
            # حساب متوسط البيع (آخر 30 يوم)
            inv_orders = orders[orders['Status'] == 'Invoiced'].copy()
            daily_avg = {}
            if not inv_orders.empty:
                inv_orders['Order Date'] = pd.to_datetime(inv_orders['Order Date'])
                recent = inv_orders[inv_orders['Order Date'] >= (datetime.now() - timedelta(days=30))]
                daily_avg = (recent.groupby('Product')['Quantity'].sum() / 30).to_dict()

            for idx, row in stock_df.iterrows():
                p = row['Product']
                q = row['Quantity']
                avg = daily_avg.get(p, 0)
                days_left = q / avg if avg > 0 else 999
                
                # نظام إشارات المرور
                status_color = "🔴" if days_left < 7 else "🟡" if days_left < 15 else "🟢"
                
                with st.container(border=True):
                    cc1, cc2, cc3 = st.columns([2, 1, 1])
                    with cc1: st.markdown(f"### {status_color} {p}")
                    with cc2: 
                        new_q = st.number_input("تعديل الكمية", value=int(q), key=f"edit_{idx}")
                        if st.button("تحديث", key=f"btn_{idx}"):
                            update_stock_quantity(p, new_q); st.rerun()
                    with cc3:
                        st.write(f"المعدل اليومي: {avg:.1f}")
                        st.write(f"يكفي لـ: **{int(days_left) if days_left < 999 else '∞'} يوم**")
        else: st.info("المخزون فارغ")

    with tab_finance:
        st.subheader("💰 تحليل السيولة والأرباح المتوقعة")
        if not orders.empty:
            inv = orders[orders['Status'] == 'Invoiced'].copy()
            inv['Due Date'] = pd.to_datetime(inv['Due Date'])
            inv['Month'] = inv['Due Date'].dt.to_period('M').astype(str)
            
            fin_m = inv.groupby('Month')['Total Amount'].sum().reset_index()
            # إضافة تكلفة الإنتاج المتوقعة من tab_strat
            st.plotly_chart(px.bar(fin_m, x='Month', y='Total Amount', title="التحصيلات المتوقعة شهرياً"), use_container_width=True)
            st.dataframe(fin_m, use_container_width=True)
