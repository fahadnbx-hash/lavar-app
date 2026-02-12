import streamlit as st
import pandas as pd
from database import init_db, get_orders, add_order, update_order_status, get_stock, upload_to_github, delete_order, update_stock_quantity, add_visit, get_visits
from datetime import datetime, date, timedelta
import plotly.express as px

# إعداد الصفحة
st.set_page_config(page_title="نظام لآفار المتكامل", layout="wide")
init_db()

# الثوابت
UNIT_COST, LEAD_TIME_DAYS, UNITS_PER_CARTON = 5.0, 9, 6

# دالة حذف الزيارة
def remove_visit(index):
    st.session_state.visits_df = st.session_state.visits_df.drop(index).reset_index(drop=True)

# --- القائمة الجانبية ---
with st.sidebar:
    st.markdown("<h2 style='text-align: center; color: #2E7D32;'>🏢 لآفار للمنظفات</h2>", unsafe_allow_html=True)
    st.divider()

# --- نظام تسجيل الدخول ---
if 'logged_in' not in st.session_state: st.session_state.logged_in = False
if not st.session_state.logged_in:
    st.title("🔐 تسجيل الدخول")
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
        else: st.error("خطأ في البيانات")
    st.stop()

# بيانات المستخدم والخروج
st.sidebar.markdown(f"### 👤 {st.session_state.user_name}")
if st.sidebar.button("🚪 تسجيل الخروج", use_container_width=True):
    st.session_state.logged_in = False
    st.rerun()

# التنقل
pages = ["واجهة الإدارة الذكية", "واجهة المندوب", "واجهة المحاسب"] if st.session_state.role == "admin" else \
        ["واجهة المحاسب"] if st.session_state.role == "accountant" else ["واجهة المندوب"]
page = st.sidebar.radio("📌 الانتقال إلى:", pages)

# جلب البيانات
orders, visits, stock_df = get_orders(), get_visits(), get_stock()
current_stock = stock_df.iloc[0]['Quantity'] if not stock_df.empty else 0

# --- واجهة المندوب ---
if page == "واجهة المندوب":
    st.header("📋 واجهة المندوب")
    t1, t2, t3 = st.tabs(["🛒 الطلبات", "📍 الزيارات", "🧮 الحاسبة"])
    
    with t1:
        with st.expander("➕ إضافة طلب جديد", expanded=True):
            c1, c2 = st.columns(2)
            with c1:
                name, cr, tax = st.text_input("اسم العميل"), st.text_input("السجل التجاري"), st.text_input("الرقم الضريبي")
                addr, phone = st.text_input("العنوان"), st.text_input("الجوال")
            with c2:
                qty = st.number_input("الكمية (علبة)", 1, 10000, 1)
                price = st.number_input("سعر الوحدة", 0.0, 1000.0, 11.0)
                days = st.number_input("أيام الاستحقاق", 0, 99, 30)
            if st.button("حفظ كمسودة 💾", use_container_width=True):
                add_order(name, cr, tax, addr, phone, "صابون لآفار 3 لتر", qty, days, price)
                st.success("تم الحفظ!"); st.rerun()
        
        st.subheader("🚀 المسودات الحالية")
        drafts = orders[orders['Status'] == 'Draft'] if not orders.empty else pd.DataFrame()
        if not drafts.empty:
            for _, r in drafts.iterrows():
                with st.container(border=True):
                    col_d1, col_d2 = st.columns([4, 1])
                    col_d1.write(f"👤 {r['Customer Name']} | 📦 {r['Quantity']} علبة | 💰 {r['Total Amount']} ريال")
                    if col_d2.button("إرسال 📤", key=f"s_{r['Order ID']}"):
                        update_order_status(r['Order ID'], 'Pending'); st.rerun()
        else: st.info("لا توجد مسودات")

    with t2:
        with st.form("visit_form"):
            c1, c2 = st.columns(2)
            with c1: v_cust, v_type = st.text_input("العميل"), st.selectbox("النوع", ["دورية", "جديد", "شكوى"])
            with c2: p_qty, p_date = st.number_input("الكمية المتوقعة", 0), st.date_input("التاريخ المتوقع")
            if st.form_submit_button("حفظ الزيارة"):
                add_visit(st.session_state.user_name, v_cust, v_type, p_qty, str(p_date), "")
                st.success("تم التسجيل!"); st.rerun()

    with t3:
        st.subheader("🧮 حاسبة لآفار (كرتون = 6 علب)")
        c1, c2 = st.columns(2)
        with c1:
            cartons = st.number_input("عدد الكراتين", min_value=0)
            st.success(f"النتيجة: {cartons * UNITS_PER_CARTON} علبة")
        with c2:
            units = st.number_input("عدد العلب", min_value=0)
            st.success(f"النتيجة: {units / UNITS_PER_CARTON:.2f} كرتون")

# --- واجهة المحاسب ---
elif page == "واجهة المحاسب":
    st.header("💰 واجهة المحاسب")
    c1, _ = st.columns([1, 4])
    c1.link_button("📊 نظام دفترة", "https://xhi.daftra.com/", type="primary", use_container_width=True )
    st.divider()
    
    pending = orders[orders['Status'] == 'Pending'] if not orders.empty else pd.DataFrame()
    if not pending.empty:
        for _, r in pending.iterrows():
            with st.container(border=True):
                st.write(f"📦 طلب #{r['Order ID']} | العميل: {r['Customer Name']} | الكمية: {r['Quantity']}")
                pdf = st.file_uploader("ارفع الفاتورة", type=['pdf'], key=f"f_{r['Order ID']}")
                if pdf and st.button("✅ اعتماد وخصم من المخزون", key=f"b_{r['Order ID']}"):
                    update_stock_quantity(r['Product'], current_stock - r['Quantity'])
                    update_order_status(r['Order ID'], 'Invoiced', upload_to_github(pdf.getvalue(), f"inv_{r['Order ID']}.pdf"))
                    st.success("تم الاعتماد!"); st.rerun()
    else: st.info("لا توجد طلبات معلقة")

# --- واجهة الإدارة ---
elif page == "واجهة الإدارة الذكية":
    st.header("📊 مركز القيادة والتحكم")
    
    # ملخص الأداء
    invoiced = orders[orders['Status'] == 'Invoiced'] if not orders.empty else pd.DataFrame()
    sales_val = invoiced['Total Amount'].sum() if not invoiced.empty else 0
    pot_qty = visits['Potential Qty'].sum() if not visits.empty else 0
    
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("📦 المخزون الحالي", f"{int(current_stock)} علبة")
    c2.metric("💰 مبيعات محققة", f"{sales_val:,.0f} ريال")
    c3.metric("🔮 طلبات متوقعة", f"{int(pot_qty)} علبة")
    c4.metric("🏭 تكلفة الإنتاج", f"{pot_qty * UNIT_COST:,.0f} ريال")

    tab1, tab2, tab3, tab4 = st.tabs(["🧠 التخطيط", "💰 المبيعات", "📦 المخزون", "📍 الميدان"])
    
    with tab1:
        conf = st.slider("نسبة الثقة (%)", 10, 100, 80)
        v_df = visits.copy()
        if not v_df.empty:
            v_df['Potential Date'] = pd.to_datetime(v_df['Potential Date'])
            v_df['Month'] = v_df['Potential Date'].dt.to_period('M').astype(str)
            v_df['Week'] = v_df['Potential Date'].dt.to_period('W').astype(str)
            v_df['Adj Qty'] = v_df['Potential Qty'] * (conf/100)
            monthly = v_df.groupby('Month')['Adj Qty'].sum().reset_index()
            weekly_cost = v_df.groupby('Week')['Adj Qty'].sum().reset_index()
            weekly_cost['Cost'] = weekly_cost['Adj Qty'] * UNIT_COST
        else:
            monthly, weekly_cost = pd.DataFrame(columns=['Month', 'Adj Qty']), pd.DataFrame(columns=['Week', 'Cost'])

        st.subheader("📅 تكلفة الإنتاج الأسبوعية")
        if not weekly_cost.empty: st.plotly_chart(px.bar(weekly_cost, x='Week', y='Cost', color_discrete_sequence=['red']), use_container_width=True)
        else: st.info("لا توجد بيانات أسبوعية")

        st.subheader("🗓️ جدول الإنتاج (9 أيام)")
        if not monthly.empty:
            mps = monthly.copy()
            temp_s, req_p = current_stock, []
            for q in mps['Adj Qty']:
                needed = max(0, q - temp_s)
                temp_s = max(0, temp_s - q)
                req_p.append(needed)
            mps['الإنتاج'] = req_p
            mps['تاريخ البدء'] = mps['Month'].apply(lambda x: (pd.to_datetime(str(x)) - timedelta(days=9)).strftime('%Y-%m-%d'))
            st.table(mps.rename(columns={'Month': 'الشهر', 'Adj Qty': 'الطلب المتوقع'}))
            
            total_p = sum(req_p)
            if total_p > 0:
                st.info(f"💡 يجب إنتاج {int(total_p)} علبة")
                st.markdown("#### 💰 تحليل فجوة السيولة")
                prod_cost = total_p * UNIT_COST
                cash_flow = invoiced['Total Amount'].sum() # تبسيط
                st.write(f"التكلفة: {prod_cost:,.0f} | السيولة: {cash_flow:,.0f}")
                if cash_flow >= prod_cost: st.success("مغطاة بالكامل")
                else: st.error(f"عجز: {prod_cost - cash_flow:,.0f} ريال")
            else: st.success("✅ المخزون كافٍ حالياً")
        else: st.info("لا توجد بيانات إنتاج")

    with tab2:
        st.subheader("💰 المبيعات الشهرية")
        if not invoiced.empty:
            invoiced['M'] = pd.to_datetime(invoiced['Due Date']).dt.to_period('M').astype(str)
            st.plotly_chart(px.bar(invoiced.groupby('M')['Total Amount'].sum().reset_index(), x='M', y='Total Amount'), use_container_width=True)
        else: st.info("لا توجد مبيعات")

    with tab3:
        st.subheader("📦 إدارة المخزون")
        new_q = st.number_input("تعديل يدوي", value=int(current_stock))
        if st.button("تحديث"):
            update_stock_quantity("صابون لآفار 3 لتر", new_q); st.rerun()

    with tab4:
        st.subheader("📍 سجل نشاط الميدان")
        if not visits.empty:
            # عرض جدول منظم بعناوين ثابتة
            cols = st.columns([1.5, 2, 1.5, 2, 1])
            cols[0].write("**المندوب**"); cols[1].write("**العميل**"); cols[2].write("**التاريخ**"); cols[3].write("**الكمية**"); cols[4].write("**حذف**")
            st.divider()
            for i, r in visits.iterrows():
                c = st.columns([1.5, 2, 1.5, 2, 1])
                c[0].write(r['Salesman']); c[1].write(r['Customer Name']); c[2].write(r['Date']); c[3].write(f"{r['Potential Qty']} ({r['Potential Date']})")
                if c[4].button("🗑️", key=f"v_{i}"):
                    remove_visit(i); st.rerun()
        else: st.info("السجل فارغ")
