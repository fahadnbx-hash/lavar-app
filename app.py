import streamlit as st
import pandas as pd
from database import init_db, get_orders, add_order, update_order_status, get_stock, upload_to_github, delete_order, update_stock_quantity, add_visit, get_visits
from datetime import datetime, date, timedelta
import plotly.express as px
import plotly.graph_objects as go

# إعداد الصفحة
st.set_page_config(page_title="نظام لآفار للمنظفات - النسخة الاحترافية", layout="wide")
init_db()

# الثوابت التشغيلية
UNIT_COST = 5.0
LEAD_TIME_DAYS = 9
UNITS_PER_CARTON = 6

# --- القائمة الجانبية ---
with st.sidebar:
    st.markdown("<h2 style='text-align: center; color: #2E7D32;'>🏢 لآفار للمنظفات</h2>", unsafe_allow_html=True)
    st.divider()

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

# معلومات المستخدم في القائمة الجانبية
st.sidebar.markdown(f"### 👤 {st.session_state.user_name}")
if st.sidebar.button("🚪 تسجيل الخروج", use_container_width=True):
    st.session_state.logged_in = False
    st.rerun()

# تحديد الصفحات المتاحة
if st.session_state.role == "admin":
    available_pages = ["واجهة الإدارة الذكية", "واجهة المندوب", "واجهة المحاسب"]
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
    tab1, tab2, tab3 = st.tabs(["🛒 إدارة الطلبات", "📍 سجل الزيارات الميدانية", "🧮 حاسبة الكراتين"])
    
    with tab1:
        with st.expander("➕ إضافة طلب جديد", expanded=True):
            c1, c2 = st.columns(2)
            with c1:
                name = st.text_input("👤 اسم العميل")
                cr = st.text_input("📄 السجل التجاري")
                tax = st.text_input("🔢 الرقم الضريبي")
                address = st.text_input("📍 العنوان")
                phone = st.text_input("📞 رقم الجوال")
            with c2:
                prod = st.selectbox("📦 المنتج", ["صابون لآفار 3 لتر"])
                qty = st.number_input("🔢 الكمية (بالعلبة)", 1, 10000, 1)
                price = st.number_input("💰 سعر الوحدة (الافتراضي 11)", 0.0, 1000.0, 11.0)
                days = st.number_input("⏳ أيام الاستحقاق", 0, 99, 30)
            if st.button("حفظ كمسودة 💾", use_container_width=True):
                add_order(name, cr, tax, address, phone, prod, qty, days, price)
                st.success("✅ تم حفظ المسودة!"); st.rerun()
        
        st.subheader("🚀 طلبات بانتظار الإرسال")
        drafts = orders[orders['Status'] == 'Draft'] if not orders.empty else pd.DataFrame()
        if not drafts.empty:
            for _, row in drafts.iterrows():
                with st.container(border=True):
                    c_info, c_action = st.columns([4, 1.5])
                    with c_info:
                        st.markdown(f"### 👤 {row['Customer Name']}")
                        st.markdown(f"📦 **الكمية:** `{row['Quantity']}` علبة | 💰 **السعر:** `{row['Unit Price']:.2f}` ريال")
                        st.markdown(f"💵 **الإجمالي:** `{row['Total Amount']:,.2f}` ريال")
                    with c_action:
                        st.write("") 
                        c_send, c_del = st.columns(2)
                        with c_send:
                            if st.button("إرسال 📤", key=f"p_{row['Order ID']}", use_container_width=True):
                                update_order_status(row['Order ID'], 'Pending'); st.rerun()
                        with c_del:
                            if st.button("🗑️", key=f"d_{row['Order ID']}", use_container_width=True):
                                delete_order(row['Order ID']); st.rerun()
        else: st.info("📭 لا توجد مسودات حالياً")

    with tab2:
        st.subheader("📍 تسجيل زيارة ميدانية")
        with st.form("visit_form", clear_on_submit=True):
            c1, c2 = st.columns(2)
            with c1:
                v_customer = st.text_input("👤 اسم العميل")
                v_type = st.selectbox("📝 نوع الزيارة", ["زيارة دورية", "عميل محتمل جديد", "متابعة شكوى"])
            with c2:
                pot_qty = st.number_input("🔮 الكمية المتوقعة", 0, 10000, 0)
                pot_date = st.date_input("📅 تاريخ الطلب المتوقع", date.today() + timedelta(days=7))
            v_notes = st.text_area("🗒️ ملاحظات")
            if st.form_submit_button("💾 حفظ الزيارة"):
                add_visit(st.session_state.user_name, v_customer, v_type, pot_qty, str(pot_date), v_notes)
                st.success("✅ تم تسجيل الزيارة!"); st.rerun()
        
        st.subheader("📜 سجل زياراتك")
        if not visits.empty:
            my_v = visits[visits['Salesman'] == st.session_state.user_name]
            st.dataframe(my_v, use_container_width=True, hide_index=True)

    with tab3:
        st.subheader("🧮 حاسبة التحويل (كرتون ↔ علبة)")
        st.info("💡 الكرتون الواحد يحتوي على 6 علب")
        col_calc1, col_calc2 = st.columns(2)
        with col_calc1:
            with st.container(border=True):
                st.markdown("### من كرتون إلى علب")
                input_cartons = st.number_input("أدخل عدد الكراتين", min_value=0, value=0, step=1)
                result_units = input_cartons * UNITS_PER_CARTON
                st.markdown(f"**النتيجة:** `{result_units}` علبة")
        with col_calc2:
            with st.container(border=True):
                st.markdown("### من علب إلى كراتين")
                input_units = st.number_input("أدخل عدد العلب", min_value=0, value=0, step=1)
                result_cartons = input_units / UNITS_PER_CARTON
                st.markdown(f"**النتيجة:** `{result_cartons:.2f}` كرتون")

# --- واجهة المحاسب ---
elif page == "واجهة المحاسب":
    st.header("💰 واجهة المحاسب")
    c_d1, c_d2 = st.columns([1, 4])
    with c_d1:
        st.link_button("📊 نظام دفترة", "https://xhi.daftra.com/", type="primary", use_container_width=True )
    st.divider()
    
    pending = orders[orders['Status'] == 'Pending'] if not orders.empty else pd.DataFrame()
    if not pending.empty:
        for _, row in pending.iterrows():
            with st.container(border=True):
                st.write(f"**طلب #{row['Order ID']}** | العميل: {row['Customer Name']} | **الكمية:** {row['Quantity']} علبة | **المبلغ:** {row['Total Amount']} ريال")
                pdf = st.file_uploader("ارفع الفاتورة (PDF)", type=['pdf'], key=f"f_{row['Order ID']}")
                if pdf and st.button("✅ اعتماد وخصم من المخزون", key=f"b_{row['Order ID']}", use_container_width=True):
                    # خصم الكمية من المخزون آلياً عند الاعتماد
                    new_q = current_stock - row['Quantity']
                    update_stock_quantity(row['Product'], new_q)
                    url = upload_to_github(pdf.getvalue(), f"inv_{row['Order ID']}.pdf")
                    update_order_status(row['Order ID'], 'Invoiced', url)
                    st.success(f"✅ تم الاعتماد وخصم {row['Quantity']} علبة من المخزون!"); st.rerun()
    else: st.info("📭 لا توجد طلبات معلقة")

# --- واجهة الإدارة الذكية ---
elif page == "واجهة الإدارة الذكية":
    st.header("📊 مركز القيادة والتحكم الاستراتيجي")
    st.markdown("### 📈 ملخص الأداء العام")
    invoiced_orders = orders[orders['Status'] == 'Invoiced'] if not orders.empty else pd.DataFrame()
    total_sales_val = invoiced_orders['Total Amount'].sum() if not invoiced_orders.empty else 0
    total_sales_qty = invoiced_orders['Quantity'].sum() if not invoiced_orders.empty else 0
    total_pot_qty = visits['Potential Qty'].sum() if not visits.empty else 0
    
    col_actual1, col_actual2, col_actual3, col_actual4 = st.columns(4)
    col_actual1.metric("📦 المخزون الحالي", f"{int(current_stock)} علبة")
    col_actual2.metric("💰 مبيعات محققة", f"{total_sales_val:,.0f} ريال")
    col_actual3.metric("🔮 طلبات متوقعة", f"{int(total_pot_qty)} علبة")
    col_actual4.metric("🏭 تكلفة الإنتاج", f"{total_pot_qty * UNIT_COST:,.0f} ريال")

    tab_strat, tab_sales, tab_stock, tab_visits = st.tabs(["🧠 التخطيط ودعم القرار", "💰 السيولة والمبيعات", "📦 إدارة المخزون", "📍 نشاط الميدان"])
    
    with tab_strat:
        st.subheader("🤖 مستشار لآفار التنفيذي")
        conf = st.slider("🎯 نسبة الثقة في التوقعات (%)", 10, 100, 80)
        v_df = visits.copy()
        if not v_df.empty:
            v_df['Potential Date'] = pd.to_datetime(v_df['Potential Date'])
            v_df['Month'] = v_df['Potential Date'].dt.to_period('M').astype(str)
            v_df['Week'] = v_df['Potential Date'].dt.to_period('W').astype(str)
            v_df['Adj Qty'] = v_df['Potential Qty'] * (conf/100)
            monthly_demand = v_df.groupby('Month')['Adj Qty'].sum().reset_index()
            weekly_prod_cost = v_df.groupby('Week')['Adj Qty'].sum().reset_index()
            weekly_prod_cost['Cost'] = weekly_prod_cost['Adj Qty'] * UNIT_COST
        else:
            monthly_demand = pd.DataFrame(columns=['Month', 'Adj Qty'])
            weekly_prod_cost = pd.DataFrame(columns=['Week', 'Cost'])

        with st.container(border=True):
            total_forecast = monthly_demand['Adj Qty'].sum() if not monthly_demand.empty else 0
            if total_forecast > current_stock:
                gap = total_forecast - current_stock
                st.markdown(f"🔴 **خطر نفاد:** الطلب المتوقع ({int(total_forecast)}) أكبر من المخزون ({int(current_stock)}). الفجوة: **{int(gap)}** علبة.")
            else: st.write("✅ الحالة التشغيلية مستقرة.")

        st.subheader("🗓️ جدول الإنتاج المقترح (قاعدة 9 أيام)")
        if not monthly_demand.empty:
            mps = monthly_demand.copy()
            temp_stock = current_stock
            required_prod = []
            for qty in mps['Adj Qty']:
                needed = max(0, qty - temp_stock)
                temp_stock = max(0, temp_stock - qty)
                required_prod.append(needed)
            mps['الإنتاج المطلوب'] = required_prod
            mps['تاريخ بدء الإنتاج'] = mps['Month'].apply(lambda x: (pd.to_datetime(str(x)) - timedelta(days=LEAD_TIME_DAYS)).strftime('%Y-%m-%d'))
            st.table(mps[['Month', 'Adj Qty', 'الإنتاج المطلوب', 'تاريخ بدء الإنتاج']].rename(columns={'Month': 'الشهر المستهدف', 'Adj Qty': 'الطلب المتوقع'}))
            
            total_needed_now = mps['الإنتاج المطلوب'].sum()
            if total_needed_now > 0:
                earliest_date = mps[mps['الإنتاج المطلوب'] > 0]['تاريخ بدء الإنتاج'].min()
                st.info(f"💡 **التوصية:** يجب إنتاج **{int(total_needed_now)}** علبة، والبدء في **{earliest_date}**.")
                st.markdown("#### 💰 تحليل تغطية تكلفة الإنتاج")
                production_cost = total_needed_now * UNIT_COST
                relevant_invoices = invoiced_orders[pd.to_datetime(invoiced_orders['Due Date']) <= pd.to_datetime(earliest_date)]
                expected_cash_flow = relevant_invoices['Total Amount'].sum() if not relevant_invoices.empty else 0
                st.write(f"- تكلفة الإنتاج: {production_cost:,.0f} ريال | التدفق النقدي المتوقع: {expected_cash_flow:,.0f} ريال")
                if expected_cash_flow >= production_cost:
                    st.success(f"✅ مغطاة بالكامل. الفائض: {expected_cash_flow - production_cost:,.0f} ريال.")
                else:
                    st.error(f"⚠️ عجز: تحتاج لتوفير {production_cost - expected_cash_flow:,.0f} ريال.")
            else:
                st.success("✅ **المخزون الحالي كافٍ ولا توجد حاجة لطلبات إنتاج حالياً.**")
        else: st.info("لا توجد بيانات لبناء الجدول")

    with tab_sales:
        st.subheader("💰 تحليل المبيعات والسيولة")
        if not invoiced_orders.empty:
            inv = invoiced_orders.copy()
            inv['Due Date'] = pd.to_datetime(inv['Due Date'])
            inv['Month'] = inv['Due Date'].dt.to_period('M').astype(str)
            inv['Week'] = inv['Due Date'].dt.to_period('W').astype(str)
            c1, c2 = st.columns(2)
            with c1:
                st.plotly_chart(px.bar(inv.groupby('Month')['Total Amount'].sum().reset_index(), x='Month', y='Total Amount', title="التحصيلات الشهرية", color_discrete_sequence=['green']), use_container_width=True)
            with c2:
                st.plotly_chart(px.bar(inv.groupby('Week')['Total Amount'].sum().reset_index(), x='Week', y='Total Amount', title="التحصيلات الأسبوعية", color_discrete_sequence=['blue']), use_container_width=True)

    with tab_stock:
        st.subheader("📦 إدارة المخزون")
        c1, c2 = st.columns(2)
        with c1: st.metric("الكمية الحالية", f"{int(current_stock)} علبة")
        with c2:
            new_q = st.number_input("تحديث الكمية يدوياً", value=int(current_stock))
            if st.button("حفظ التحديث"):
                update_stock_quantity("صابون لآفار 3 لتر", new_q)
                st.success("تم التحديث!"); st.rerun()

    with tab_visits:
        st.subheader("📍 سجل نشاط الميدان")
        st.dataframe(visits, use_container_width=True)
