import streamlit as st
import pandas as pd
from database import init_db, get_orders, add_order, update_order_status, get_stock, upload_to_github, delete_order, update_stock_quantity, add_visit, get_visits
from datetime import datetime, date, timedelta
import plotly.express as px
import plotly.graph_objects as go

# إعداد الصفحة
st.set_page_config(page_title="نظام لآفار لذكاء الأعمال", layout="wide")
init_db()

# تكلفة الإنتاج الثابتة التي حددتها
UNIT_COST = 5.0

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

available_pages = ["واجهة المندوب", "واجهة المحاسب", "واجهة الإدارة"] if st.session_state.role == "admin" else \
                  (["واجهة المحاسب"] if st.session_state.role == "accountant" else ["واجهة المندوب"])
page = st.sidebar.radio("📌 الانتقال إلى:", available_pages)

# --- واجهة المندوب ---
if page == "واجهة المندوب":
    st.header("📋 واجهة المندوب")
    tab1, tab2 = st.tabs(["🛒 إدارة الطلبات", "📍 سجل الزيارات الميدانية"])
    with tab1:
        orders = get_orders()
        stock_df = get_stock()
        with st.expander("➕ إضافة طلب جديد", expanded=True):
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
            if st.button("حفظ الطلب ➡️", use_container_width=True):
                add_order(name, cr, tax, address, phone, prod, qty, days, price if price > 0 else None)
                st.success("✅ تم حفظ الطلب بنجاح!"); st.rerun()
        
        st.subheader("🚀 طلبات بانتظار الاعتماد")
        drafts = orders[orders['Status'] == 'Draft'] if not orders.empty else pd.DataFrame()
        if not drafts.empty:
            for _, row in drafts.iterrows():
                with st.container(border=True):
                    c_i, c_a, c_d = st.columns([3, 1, 0.5])
                    with c_i:
                        st.markdown(f"**العميل:** {row['Customer Name']} | **المنتج:** {row['Product']}")
                        st.caption(f"📦 {row['Quantity']} علبة × {row['Unit Price']} ريال = {row['Total Amount']} ريال")
                    with c_a:
                        if st.button("إرسال للمحاسب 📤", key=f"p_{row['Order ID']}", use_container_width=True):
                            update_order_status(row['Order ID'], 'Pending'); st.rerun()
                    with c_d:
                        if st.button("🗑️", key=f"d_{row['Order ID']}", use_container_width=True):
                            delete_order(row['Order ID']); st.rerun()
        else: st.info("📭 لا توجد طلبات معلقة")

    with tab2:
        st.subheader("📍 تسجيل زيارة ميدانية")
        with st.form("visit_form", clear_on_submit=True):
            c1, c2 = st.columns(2)
            with c1:
                v_customer = st.text_input("👤 اسم العميل")
                v_type = st.selectbox("📝 نوع الزيارة", ["زيارة دورية", "عميل محتمل جديد", "متابعة شكوى", "تحصيل"])
            with c2:
                pot_qty = st.number_input("🔮 الكمية المتوقعة (علبة)", 0, 10000, 0)
                pot_date = st.date_input("📅 تاريخ الطلب المتوقع", date.today() + timedelta(days=7))
            v_notes = st.text_area("🗒️ ملاحظات الزيارة")
            if st.form_submit_button("💾 حفظ الزيارة", use_container_width=True):
                add_visit(st.session_state.user_name, v_customer, v_type, pot_qty, str(pot_date), v_notes)
                st.success("✅ تم تسجيل الزيارة!"); st.rerun()

# --- واجهة الإدارة المحدثة (الذكية) ---
elif page == "واجهة الإدارة":
    st.header("📊 مركز ذكاء الأعمال والتحكم")
    tab_prod, tab_stock, tab_sales, tab_visits = st.tabs(["🏭 تخطيط الإنتاج الذكي", "📦 إدارة المخزون", "💰 السيولة والمبيعات", "📍 نشاط الميدان"])
    orders = get_orders()
    visits = get_visits()
    stock_df = get_stock()
    
    with tab_prod:
        st.subheader("🧠 محاكي التوقعات والإنتاج (شهرياً)")
        confidence = st.slider("🎯 نسبة الثقة في توقعات المناديب (%)", 10, 100, 80)
        
        if not visits.empty:
            visits['Potential Date'] = pd.to_datetime(visits['Potential Date'])
            visits['Month'] = visits['Potential Date'].dt.to_period('M').astype(str)
            visits['Adjusted Qty'] = visits['Potential Qty'] * (confidence / 100)
            m_summary = visits.groupby('Month')['Adjusted Qty'].sum().reset_index()
            m_summary['Production Cost'] = m_summary['Adjusted Qty'] * UNIT_COST
            
            if not orders.empty:
                invoiced = orders[orders['Status'] == 'Invoiced'].copy()
                invoiced['Due Date'] = pd.to_datetime(invoiced['Due Date'])
                invoiced['Month'] = invoiced['Due Date'].dt.to_period('M').astype(str)
                cash_summary = invoiced.groupby('Month')['Total Amount'].sum().reset_index()
                merged = pd.merge(m_summary, cash_summary, on='Month', how='outer').fillna(0)
            else:
                merged = m_summary; merged['Total Amount'] = 0

            current_stock = stock_df['Quantity'].sum() if not stock_df.empty else 0
            total_needed = merged['Adjusted Qty'].sum()
            gap = total_needed - current_stock
            
            c1, c2, c3 = st.columns(3)
            c1.metric("📦 إجمالي الطلب المتوقع", f"{int(total_needed)} علبة")
            c2.metric("🏠 المخزون الحالي", f"{int(current_stock)} علبة")
            c3.metric("🚨 فجوة الإنتاج المطلوبة", f"{int(max(0, gap))} علبة", delta=f"{int(gap)} علبة", delta_color="inverse")

            st.markdown("---")
            fig = go.Figure()
            fig.add_trace(go.Bar(x=merged['Month'], y=merged['Production Cost'], name='تكلفة الإنتاج المطلوبة (ريال)', marker_color='red'))
            fig.add_trace(go.Scatter(x=merged['Month'], y=merged['Total Amount'], name='السيولة القادمة للتحصيل (ريال)', line=dict(color='green', width=4)))
            fig.update_layout(title='المواءمة المالية الشهرية: تكلفة الإنتاج vs التحصيل المتوقع', xaxis_title='الشهر', yaxis_title='ريال سعودي')
            st.plotly_chart(fig, use_container_width=True)

            st.markdown("### 📋 جدول دعم القرار الشهري")
            merged['Balance'] = merged['Total Amount'] - merged['Production Cost']
            st.table(merged.rename(columns={'Month': 'الشهر', 'Adjusted Qty': 'الكمية المتوقعة', 'Production Cost': 'تكلفة الإنتاج', 'Total Amount': 'السيولة المتوفرة', 'Balance': 'الفائض/العجز'}))
        else: st.info("لا توجد بيانات زيارات كافية للتحليل")

    with tab_stock:
        st.subheader("🛠️ تعديل المخزون المباشر")
        if not stock_df.empty:
            for idx, row in stock_df.iterrows():
                with st.container(border=True):
                    col1, col2, col3 = st.columns([2, 1, 1])
                    with col1: st.markdown(f"**المنتج:** {row['Product']}")
                    with col2:
                        new_qty = st.number_input(f"الكمية الحالية لـ {row['Product']}", value=int(row['Quantity']), key=f"q_{idx}")
                    with col3:
                        if st.button(f"تحديث الكمية", key=f"b_{idx}", use_container_width=True):
                            update_stock_quantity(row['Product'], new_qty)
                            st.success("تم التحديث!"); st.rerun()
            
            st.markdown("---")
            st.subheader("⏳ التنبؤ الذكي بنفاد المخزون")
            if not orders.empty:
                invoiced_orders = orders[orders['Status'] == 'Invoiced'].copy()
                if not invoiced_orders.empty:
                    invoiced_orders['Order Date'] = pd.to_datetime(invoiced_orders['Order Date'])
                    last_30_days = datetime.now() - timedelta(days=30)
                    recent_sales = invoiced_orders[invoiced_orders['Order Date'] >= last_30_days]
                    
                    if not recent_sales.empty:
                        daily_sales_avg = recent_sales.groupby('Product')['Quantity'].sum() / 30
                        for idx, row in stock_df.iterrows():
                            p_name = row['Product']
                            if p_name in daily_sales_avg and daily_sales_avg[p_name] > 0:
                                days_left = row['Quantity'] / daily_sales_avg[p_name]
                                dep_date = datetime.now() + timedelta(days=days_left)
                                color = "red" if days_left < 7 else "orange" if days_left < 15 else "green"
                                st.markdown(f"📍 **{p_name}**: سينفد خلال :<span style='color:{color}'>{int(days_left)} يوم</span> (تاريخ {dep_date.strftime('%Y-%m-%d')})", unsafe_allow_html=True)
                    else: st.warning("لا توجد مبيعات في آخر 30 يوم لحساب التنبؤ")
        else: st.info("لا توجد بيانات مخزون")

    with tab_sales:
        if not orders.empty:
            invoiced = orders[orders['Status'] == 'Invoiced'].copy()
            st.metric("💰 إجمالي المبيعات المحصلة/المفوترة", f"{invoiced['Total Amount'].sum():,.2f} ريال")
            invoiced['Due Date'] = pd.to_datetime(invoiced['Due Date'])
            cash_flow = invoiced.groupby('Due Date')['Total Amount'].sum().sort_index().cumsum().reset_index()
            st.plotly_chart(px.area(cash_flow, x='Due Date', y='Total Amount', title="منحنى تراكم السيولة النقدية"), use_container_width=True)
        else: st.info("لا توجد مبيعات مسجلة")

    with tab_visits:
        st.subheader("📍 مراقبة نشاط المناديب")
        if not visits.empty: st.dataframe(visits, use_container_width=True, hide_index=True)
        else: st.info("لا توجد زيارات مسجلة")
