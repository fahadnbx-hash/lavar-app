import streamlit as st
import pandas as pd
from database import init_db, get_orders, add_order, update_order_status, get_stock, upload_to_github, delete_order, update_stock_quantity, add_visit, get_visits
from datetime import datetime, date, timedelta
import plotly.express as px

# إعداد الصفحة وتثبيت الجلسة
st.set_page_config(page_title="نظام لآفار للأعمال", layout="wide", initial_sidebar_state="expanded")
init_db()

# الثوابت التشغيلية
UNIT_COST, LEAD_TIME_DAYS, UNITS_PER_CARTON = 5.0, 9, 6

# دالة حذف زيارة
def remove_visit(index):
    st.session_state.visits_df = st.session_state.visits_df.drop(index).reset_index(drop=True)

# --- نظام استمرارية تسجيل الدخول ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.markdown("<h1 style='text-align: center; color: #2E7D32;'>🏢 نظام لآفار للأعمال</h1>", unsafe_allow_html=True)
    with st.container(border=True):
        st.subheader("🔐 تسجيل الدخول")
        user = st.text_input("اسم المستخدم")
        password = st.text_input("كلمة المرور", type="password")
        if st.button("دخول للنظام", use_container_width=True):
            if user == "admin" and password == "lavar2026":
                st.session_state.logged_in, st.session_state.role, st.session_state.user_name = True, "admin", "المدير العام"
                st.rerun()
            elif user == "acc" and password == "lavar_acc":
                st.session_state.logged_in, st.session_state.role, st.session_state.user_name = True, "accountant", "المحاسب"
                st.rerun()
            elif user == "sales" and password == "lavar_sales":
                st.session_state.logged_in, st.session_state.role, st.session_state.user_name = True, "sales", "المندوب"
                st.rerun()
            else: st.error("❌ بيانات الدخول غير صحيحة")
    st.stop()

# --- القائمة الجانبية ---
with st.sidebar:
    st.markdown("<h2 style='text-align: center; color: #2E7D32;'>🏢 لآفار للمنظفات</h2>", unsafe_allow_html=True)
    st.divider()
    st.markdown(f"### 👤 {st.session_state.user_name}")
    
    # تحديد الصفحات
    pages = ["واجهة الإدارة الذكية", "واجهة المندوب", "واجهة المحاسب"] if st.session_state.role == "admin" else \
            ["واجهة المحاسب"] if st.session_state.role == "accountant" else ["واجهة المندوب"]
    page = st.sidebar.radio("📌 الانتقال إلى:", pages)
    
    st.divider()
    if st.sidebar.button("🚪 تسجيل الخروج", use_container_width=True):
        st.session_state.logged_in = False
        st.rerun()

# جلب البيانات العامة لضمان ظهورها في كل الأقسام
orders, visits, stock_df = get_orders(), get_visits(), get_stock()
current_stock = stock_df.iloc[0]['Quantity'] if not stock_df.empty else 0

# --- واجهة المندوب ---
if page == "واجهة المندوب":
    st.header("📋 واجهة المندوب")
    tab1, tab2, tab3 = st.tabs(["🛒 إدارة الطلبات", "📍 سجل الزيارات الميدانية", "🧮 حاسبة الكراتين"])
    
    with tab1:
        st.subheader("➕ إنشاء طلب جديد")
        with st.container(border=True):
            c1, c2 = st.columns(2)
            with c1:
                name = st.text_input("👤 اسم العميل", placeholder="أدخل اسم العميل...")
                cr = st.text_input("📄 السجل التجاري")
                tax = st.text_input("🔢 الرقم الضريبي")
                addr = st.text_input("📍 العنوان")
                phone = st.text_input("📞 رقم الجوال")
            with c2:
                prod = st.selectbox("📦 المنتج", ["صابون لآفار 3 لتر"])
                qty = st.number_input("🔢 الكمية (بالعلبة)", 1, 10000, 1)
                price = st.number_input("💰 سعر الوحدة (الافتراضي 11)", 0.0, 1000.0, 11.0)
                days = st.number_input("⏳ أيام الاستحقاق", 0, 99, 30)
            if st.button("حفظ الطلب كمسودة 💾", use_container_width=True):
                add_order(name, cr, tax, addr, phone, prod, qty, days, price)
                st.success("✅ تم حفظ المسودة بنجاح!"); st.rerun()
        
        st.divider()
        st.subheader("🚀 المسودات الحالية (بانتظار الإرسال)")
        drafts = orders[orders['Status'] == 'Draft'] if not orders.empty else pd.DataFrame()
        if not drafts.empty:
            for _, row in drafts.iterrows():
                with st.container(border=True):
                    c_d1, c_d2 = st.columns([4, 1])
                    c_d1.write(f"👤 {row['Customer Name']} | 📦 {row['Quantity']} علبة | 💰 {row['Total Amount']} ريال")
                    if c_d2.button("إرسال 📤", key=f"send_{row['Order ID']}", use_container_width=True):
                        update_order_status(row['Order ID'], 'Pending'); st.rerun()
        else: st.info("📭 لا توجد مسودات حالياً")

        st.divider()
        st.subheader("✅ الفواتير المعتمدة للعملاء")
        invoiced = orders[orders['Status'] == 'Invoiced'] if not orders.empty else pd.DataFrame()
        if not invoiced.empty:
            st.dataframe(invoiced[['Order ID', 'Customer Name', 'Quantity', 'Total Amount', 'Invoice URL']], use_container_width=True, hide_index=True)
        else: st.info("ℹ️ لا توجد فواتير معتمدة حالياً")

    with tab2:
        st.subheader("📍 تسجيل زيارة ميدانية")
        with st.form("visit_form_new", clear_on_submit=True):
            c1, c2 = st.columns(2)
            with c1: v_cust = st.text_input("اسم العميل المزار")
            with c1: v_type = st.selectbox("نوع الزيارة", ["دورية", "عميل جديد", "شكوى"])
            with c2: p_qty = st.number_input("الكمية المتوقعة", 0)
            with c2: p_date = st.date_input("التاريخ المتوقع للطلب")
            if st.form_submit_button("💾 حفظ الزيارة الميدانية"):
                add_visit(st.session_state.user_name, v_cust, v_type, p_qty, str(p_date), "")
                st.success("✅ تم تسجيل الزيارة!"); st.rerun()

    with tab3:
        st.subheader("🧮 حاسبة التحويل السريع")
        with st.container(border=True):
            col_calc1, col_calc2 = st.columns(2)
            with col_calc1:
                in_cartons = st.number_input("أدخل عدد الكراتين", min_value=0, value=0)
                st.success(f"📦 النتيجة: {in_cartons * UNITS_PER_CARTON} علبة")
            with col_calc2:
                in_units = st.number_input("أدخل عدد العلب", min_value=0, value=0)
                st.success(f"📦 النتيجة: {in_units / UNITS_PER_CARTON:.2f} كرتون")

# --- واجهة المحاسب ---
elif page == "واجهة المحاسب":
    st.header("💰 واجهة المحاسب")
    c_btn, _ = st.columns([1, 4])
    c_btn.link_button("📊 نظام دفترة", "https://xhi.daftra.com/", type="primary", use_container_width=True )
    st.divider()
    
    st.subheader("⏳ طلبات بانتظار الاعتماد المالي")
    pending = orders[orders['Status'] == 'Pending'] if not orders.empty else pd.DataFrame()
    if not pending.empty:
        for _, row in pending.iterrows():
            with st.container(border=True):
                st.write(f"📦 **طلب #{row['Order ID']}** | العميل: {row['Customer Name']} | الكمية: {row['Quantity']} علبة")
                pdf = st.file_uploader("ارفع نسخة الفاتورة (PDF)", type=['pdf'], key=f"file_{row['Order ID']}")
                if pdf and st.button("✅ اعتماد وخصم من المخزون", key=f"acc_{row['Order ID']}", use_container_width=True):
                    update_stock_quantity(row['Product'], current_stock - row['Quantity'])
                    update_order_status(row['Order ID'], 'Invoiced', upload_to_github(pdf.getvalue(), f"inv_{row['Order ID']}.pdf"))
                    st.success("✅ تم الاعتماد وتحديث المخزون!"); st.rerun()
    else: st.info("📭 لا توجد طلبات بانتظار الاعتماد حالياً")

# --- واجهة الإدارة الذكية ---
elif page == "واجهة الإدارة الذكية":
    st.header("📊 مركز القيادة والتحكم الاستراتيجي")
    
    # 1. ملخص الأداء العام (ظاهر دائماً)
    st.markdown("### 📈 ملخص الأداء العام")
    invoiced_orders = orders[orders['Status'] == 'Invoiced'] if not orders.empty else pd.DataFrame()
    total_sales_val = invoiced_orders['Total Amount'].sum() if not invoiced_orders.empty else 0
    total_sales_qty = invoiced_orders['Quantity'].sum() if not invoiced_orders.empty else 0
    total_pot_qty = visits['Potential Qty'].sum() if not visits.empty else 0
    
    st.markdown("##### **الفعلـي**")
    col_a1, col_a2, col_a3, col_a4 = st.columns(4)
    col_a1.metric("📦 المخزون الحالي", f"{int(current_stock)} علبة")
    col_a2.metric("💰 مبيعات محققة", f"{total_sales_val:,.0f} ريال")
    col_a3.metric("📄 فواتير صادرة", f"{len(invoiced_orders)}")
    col_a4.metric("📦 كميات مباعة", f"{int(total_sales_qty)} علبة")

    st.markdown("##### **المتوقـع**")
    col_e1, col_e2, col_e3, col_e4 = st.columns(4)
    col_e1.metric("🔮 طلبات متوقعة", f"{int(total_pot_qty)} علبة")
    col_e2.metric("💵 قيمة متوقعة", f"{total_pot_qty * 15.0:,.0f} ريال")
    col_e3.metric("🏭 تكلفة الإنتاج", f"{total_pot_qty * UNIT_COST:,.0f} ريال")
    col_e4.metric("📍 إجمالي الزيارات", f"{len(visits)}")

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
            monthly_demand, weekly_prod_cost = pd.DataFrame(columns=['Month', 'Adj Qty']), pd.DataFrame(columns=['Week', 'Cost'])

        st.subheader("📅 تكلفة الإنتاج المتوقعة أسبوعياً")
        if not weekly_prod_cost.empty: st.plotly_chart(px.bar(weekly_prod_cost, x='Week', y='Cost', color_discrete_sequence=['#FF4B4B']), use_container_width=True)
        else: st.info("📊 سيظهر الرسم البياني هنا عند وجود بيانات")

        st.subheader("🗓️ جدول الإنتاج المقترح (قاعدة 9 أيام)")
        mps = monthly_demand.copy() if not monthly_demand.empty else pd.DataFrame(columns=['Month', 'Adj Qty'])
        if not mps.empty:
            temp_s, req_p = current_stock, []
            for q in mps['Adj Qty']:
                needed = max(0, q - temp_s)
                temp_s = max(0, temp_s - q)
                req_p.append(needed)
            mps['الإنتاج المطلوب'] = req_p
            mps['تاريخ بدء الإنتاج'] = mps['Month'].apply(lambda x: (pd.to_datetime(str(x)) - timedelta(days=LEAD_TIME_DAYS)).strftime('%Y-%m-%d'))
            st.table(mps.rename(columns={'Month': 'الشهر المستهدف', 'Adj Qty': 'الطلب المتوقع'}))
            
            total_n = sum(req_p)
            if total_n > 0:
                st.info(f"💡 التوصية: إنتاج {int(total_n)} علبة")
                st.markdown("#### 💰 تحليل تغطية التكاليف")
                st.write(f"تكلفة الإنتاج: {total_n * UNIT_COST:,.0f} | السيولة المتاحة: {total_sales_val:,.0f}")
            else: st.success("✅ المخزون كافٍ ولا حاجة لإنتاج جديد.")
        else: st.table(pd.DataFrame(columns=["الشهر المستهدف", "الطلب المتوقع", "الإنتاج المطلوب", "تاريخ بدء الإنتاج"]))

    with tab_sales:
        st.subheader("💰 تحليل المبيعات والسيولة")
        if not invoiced_orders.empty:
            invoiced_orders['M'] = pd.to_datetime(invoiced_orders['Due Date']).dt.to_period('M').astype(str)
            st.plotly_chart(px.bar(invoiced_orders.groupby('M')['Total Amount'].sum().reset_index(), x='M', y='Total Amount'), use_container_width=True)
        else: st.info("📊 الرسوم البيانية للمبيعات ستظهر هنا")

    with tab_stock:
        st.subheader("📦 إدارة المخزون والمخزون الآمن")
        avg_d = total_sales_qty / 30 if total_sales_qty > 0 else 1
        days_s = current_stock / avg_d
        st.metric("أيام الأمان المقدرة", f"{int(days_s)} يوم")
        with st.container(border=True):
            new_qty_input = st.number_input("تحديث المخزون يدوياً (صابون لآفار 3 لتر)", value=int(current_stock))
            if st.button("حفظ تحديث المخزون"):
                update_stock_quantity("صابون لآفار 3 لتر", new_qty_input); st.rerun()

    with tab_visits:
        st.subheader("📍 إدارة سجل نشاط الميدان")
        # جدول منظم واحترافي
        if not visits.empty:
            for i, r in visits.iterrows():
                with st.container(border=True):
                    c_v1, c_v2, c_v3, c_v4, c_v5 = st.columns([1.5, 2, 1.5, 2, 1])
                    if i == 0:
                        st.markdown("**المندوب | العميل | التاريخ | الكمية المتوقعة | الإجراء**")
                        st.divider()
                    c_v1.write(r['Salesman'])
                    c_v2.write(r['Customer Name'])
                    c_v3.write(r['Date'])
                    c_v4.write(f"{r['Potential Qty']} علبة")
                    if c_v5.button("حذف 🗑️", key=f"del_v_{i}", use_container_width=True):
                        remove_visit(i); st.rerun()
        else:
            st.markdown("**المندوب | العميل | التاريخ | الكمية المتوقعة | الإجراء**")
            st.info("ℹ️ لا توجد زيارات ميدانية مسجلة حالياً")
