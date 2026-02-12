import streamlit as st
import pandas as pd
from database import init_db, get_orders, add_order, update_order_status, get_stock, upload_to_github, delete_order, update_stock_quantity, add_visit, get_visits
from datetime import datetime, date, timedelta
import plotly.express as px
import plotly.graph_objects as go

# 1. إعداد الصفحة
st.set_page_config(page_title="نظام لآفار للمنظفات الذكي", layout="wide")
init_db()

# الثوابت التشغيلية
UNIT_COST = 5.0
LEAD_TIME_DAYS = 9

# 2. نظام تسجيل الدخول
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

# 3. واجهة المندوب
if page == "واجهة المندوب":
    st.header("📋 واجهة المندوب")
    tab1, tab2 = st.tabs(["🛒 إدارة الطلبات", "📍 سجل الزيارات الميدانية"])
    
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
                qty = st.number_input("🔢 الكمية", 1, 10000, 1)
                price = st.number_input("💰 سعر الوحدة", 0.0, 1000.0, 15.0)
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
                        # الملخص التفصيلي المطلوب
                        st.markdown(f"👤 **العميل:** {row['Customer Name']}")
                        st.markdown(f"📦 **التفاصيل:** {row['Quantity']} علبة × {row['Unit Price']:.2f} ريال | **الإجمالي:** {row['Total Amount']:,.2f} ريال")
                    with c_action:
                        c_send, c_del = st.columns(2)
                        with c_send:
                            if st.button("إرسال 📤", key=f"p_{row['Order ID']}", use_container_width=True):
                                update_order_status(row['Order ID'], 'Pending'); st.rerun()
                        with c_del:
                            if st.button("🗑️", key=f"d_{row['Order ID']}", use_container_width=True):
                                delete_order(row['Order ID']); st.rerun()
        else: st.info("📭 لا توجد مسودات حالياً")

        st.subheader("✅ فواتير معتمدة")
        inv = orders[orders['Status'] == 'Invoiced'] if not orders.empty else pd.DataFrame()
        if not inv.empty:
            for _, row in inv.iterrows():
                with st.container(border=True):
                    st.write(f"**العميل:** {row['Customer Name']} | **المبلغ:** {row['Total Amount']} ريال")
                    if row['Invoice URL']: st.link_button("📄 فتح الفاتورة", row['Invoice URL'])

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

# 4. واجهة المحاسب
elif page == "واجهة المحاسب":
    st.header("💰 واجهة المحاسب")
    pending = orders[orders['Status'] == 'Pending'] if not orders.empty else pd.DataFrame()
    if not pending.empty:
        for _, row in pending.iterrows():
            with st.container(border=True):
                st.write(f"**طلب #{row['Order ID']}** | العميل: {row['Customer Name']} | المبلغ: {row['Total Amount']} ريال")
                pdf = st.file_uploader("ارفع الفاتورة (PDF)", type=['pdf'], key=f"f_{row['Order ID']}")
                if pdf and st.button("✅ اعتماد ورفع", key=f"b_{row['Order ID']}"):
                    url = upload_to_github(pdf.getvalue(), f"inv_{row['Order ID']}.pdf")
                    update_order_status(row['Order ID'], 'Invoiced', url); st.rerun()
    else: st.info("📭 لا توجد طلبات معلقة")

# 5. واجهة الإدارة الذكية
elif page == "واجهة الإدارة الذكية":
    st.header("📊 مركز القيادة والتحكم الاستراتيجي")
    tab_strat, tab_sales, tab_stock, tab_visits = st.tabs(["🧠 التخطيط ودعم القرار", "💰 السيولة والمبيعات", "📦 إدارة المخزون", "📍 نشاط الميدان"])
    
    with tab_strat:
        st.subheader("🤖 مستشار لآفار التنفيذي")
        conf = st.slider("🎯 نسبة الثقة في التوقعات (%)", 10, 100, 80)
        
        v_df = visits.copy()
        if not v_df.empty:
            v_df['Potential Date'] = pd.to_datetime(v_df['Potential Date'])
            v_df['Month'] = v_df['Potential Date'].dt.to_period('M').astype(str)
            v_df['Adj Qty'] = v_df['Potential Qty'] * (conf/100)
            monthly_demand = v_df.groupby('Month')['Adj Qty'].sum().reset_index()
        else:
            monthly_demand = pd.DataFrame(columns=['Month', 'Adj Qty'])

        with st.container(border=True):
            recs = []
            total_forecast = monthly_demand['Adj Qty'].sum() if not monthly_demand.empty else 0
            pending_invoices = orders[orders['Status'] == 'Pending']['Total Amount'].sum() if not orders.empty else 0
            
            if total_forecast > current_stock:
                gap = total_forecast - current_stock
                recs.append(f"🔴 **خطر نفاد:** الطلب المتوقع ({int(total_forecast)}) أكبر من المخزون ({int(current_stock)}). الفجوة: **{int(gap)}** علبة.")
            elif current_stock > total_forecast * 1.5 and total_forecast > 0:
                recs.append("🟡 **تنبيه فائض:** المخزون مرتفع جداً. **التوصية:** تكثيف التسويق أو العروض الترويجية.")
            
            if pending_invoices > 5000:
                recs.append(f"💸 **بطء الفواتير:** هناك **{pending_invoices:,.0f} ريال** معلقة. **التوصية:** تسريع إصدار الفواتير.")
            
            if not recs: st.write("✅ الحالة التشغيلية مستقرة.")
            else:
                for r in recs: st.markdown(r)

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
        else: st.info("لا توجد بيانات لبناء الجدول")

    with tab_sales:
        st.subheader("💰 تحليل المبيعات والسيولة")
        if not orders.empty:
            inv = orders[orders['Status'] == 'Invoiced'].copy()
            if not inv.empty:
                inv['Due Date'] = pd.to_datetime(inv['Due Date'])
                inv['Month'] = inv['Due Date'].dt.to_period('M').astype(str)
                m_sales = inv.groupby('Month')['Total Amount'].sum().reset_index()
                st.plotly_chart(px.bar(m_sales, x='Month', y='Total Amount', title="التحصيلات الشهرية"), use_container_width=True)

    with tab_stock:
        st.subheader("📦 إدارة المخزون")
        new_q = st.number_input("تحديث الكمية الفعلية (صابون لآفار 3 لتر)", value=int(current_stock))
        if st.button("حفظ التحديث"):
            update_stock_quantity("صابون لآفار 3 لتر", new_q)
            st.success("تم التحديث!"); st.rerun()

    with tab_visits:
        st.subheader("📍 سجل نشاط الميدان")
        st.dataframe(visits, use_container_width=True)
