import streamlit as st
import pandas as pd
from database import init_db, get_orders, add_order, update_order_status, get_stock, upload_to_github, delete_order, update_stock_quantity, add_visit, get_visits
from datetime import datetime, date, timedelta
import plotly.express as px
import io

# 1. إعداد الصفحة وتثبيت الجلسة
st.set_page_config(page_title="نظام لآفار للأعمال", layout="wide", initial_sidebar_state="expanded")
init_db()

# الثوابت التشغيلية
UNIT_COST, LEAD_TIME_DAYS, UNITS_PER_CARTON = 5.0, 9, 6

# دالة حذف زيارة (للمدير)
def remove_visit(index):
    if 'visits_df' in st.session_state:
        st.session_state.visits_df = st.session_state.visits_df.drop(index).reset_index(drop=True)

# 2. تحسينات الواجهة (CSS) للمحاذاة والجمالية
st.markdown("""
    <style>
    .stApp { text-align: right; direction: rtl; }
    .stMetric { text-align: right; }
    .stMetric label { font-size: 0.75rem !important; color: #666; }
    .stMetric div { font-size: 1.1rem !important; font-weight: bold; }
    div[data-testid="stExpander"] { text-align: right; }
    .stTable { direction: rtl; border: 1px solid #eee; }
    .stDataFrame { direction: rtl; }
    .stButton button { width: 100%; }
    th { text-align: right !important; background-color: #f8f9fa; }
    .main-title { color: #2E7D32; text-align: center; margin-bottom: 30px; }
    </style>
""", unsafe_allow_html=True)

# 3. نظام استمرارية تسجيل الدخول
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.markdown("<h1 class='main-title'>🏢 نظام لآفار للأعمال</h1>", unsafe_allow_html=True)
    with st.container(border=True):
        st.subheader("🔐 تسجيل الدخول")
        user = st.text_input("اسم المستخدم")
        password = st.text_input("كلمة المرور", type="password")
        if st.button("دخول للنظام"):
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

# 4. القائمة الجانبية
with st.sidebar:
    st.markdown("<h2 style='text-align: center; color: #2E7D32;'>🏢 لآفار للمنظفات</h2>", unsafe_allow_html=True)
    st.divider()
    st.markdown(f"### 👤 {st.session_state.user_name}")
    pages = ["واجهة الإدارة الذكية", "واجهة المندوب", "واجهة المحاسب"] if st.session_state.role == "admin" else \
            ["واجهة المحاسب"] if st.session_state.role == "accountant" else ["واجهة المندوب"]
    page = st.sidebar.radio("📌 الانتقال إلى:", pages)
    st.divider()
    if st.sidebar.button("🚪 تسجيل الخروج"):
        st.session_state.logged_in = False
        st.rerun()

# جلب البيانات المحدثة
orders, visits, stock_df = get_orders(), get_visits(), get_stock()
current_stock = stock_df.iloc[0]['Quantity'] if not stock_df.empty else 0

# --- واجهة المندوب ---
if page == "واجهة المندوب":
    st.header("📋 واجهة المندوب")
    t1, t2, t3 = st.tabs(["🛒 إدارة الطلبات", "📍 سجل الزيارات الميدانية", "🧮 حاسبة الكراتين"])
    
    with t1:
        st.subheader("➕ إنشاء طلب جديد")
        with st.container(border=True):
            c1, c2 = st.columns(2)
            with c1:
                name = st.text_input("اسم العميل")
                cr = st.text_input("رقم السجل التجاري")
                tax = st.text_input("الرقم الضريبي")
                price = st.number_input("سعر العلبة (الافتراضي 11)", value=11.0)
            with c2:
                days = st.number_input("أيام الاستحقاق (الافتراضي 30)", value=30)
                qty = st.number_input("الكمية بالعلبة", min_value=1, value=1)
                phone = st.text_input("رقم الجوال")
                addr = st.text_input("العنوان")
            if st.button("تقديم الطلب 🚀"):
                add_order(name, cr, tax, addr, phone, "صابون لآفار 3 لتر", qty, days, price)
                st.success("✅ تم تقديم الطلب بنجاح!"); st.rerun()
        
        st.divider()
        st.subheader("🚀 الطلبات الحالية (بانتظار الإرسال للمحاسب)")
        st.markdown("| اسم العميل | الكمية | سعر الوحدة | السعر الإجمالي | الإجراء |")
        st.markdown("| :--- | :--- | :--- | :--- | :--- |")
        drafts = orders[orders['Status'] == 'Draft'] if not orders.empty else pd.DataFrame()
        if not drafts.empty:
            for _, r in drafts.iterrows():
                col1, col2, col3, col4, col5 = st.columns([2, 1, 1, 1, 1])
                col1.write(r['Customer Name'])
                col2.write(r['Quantity'])
                col3.write(r['Unit Price'])
                col4.write(r['Total Amount'])
                if col5.button("إرسال 📤", key=f"s_{r['Order ID']}"):
                    update_order_status(r['Order ID'], 'Pending'); st.rerun()
        else: st.info("ℹ️ لا توجد طلبات حالياً بانتظار الإرسال.")

        st.divider()
        st.subheader("✅ الفواتير المعتمدة للعملاء")
        invoiced = orders[orders['Status'] == 'Invoiced'] if not orders.empty else pd.DataFrame()
        if not invoiced.empty:
            st.dataframe(invoiced[['Order ID', 'Customer Name', 'Quantity', 'Total Amount', 'Invoice URL']], use_container_width=True, hide_index=True)
        else: st.info("ℹ️ لا توجد فواتير معتمدة حالياً.")

    with t2:
        st.subheader("📍 تسجيل زيارة ميدانية")
        with st.form("visit_form_sales"):
            c1, c2 = st.columns(2)
            with c1: v_cust = st.text_input("اسم العميل المزار"); v_type = st.selectbox("نوع الزيارة", ["دورية", "جديد", "شكوى"])
            with c2: p_qty = st.number_input("الكمية المتوقعة", 0); p_date = st.date_input("التاريخ المتوقع للطلب")
            if st.form_submit_button("💾 حفظ الزيارة الميدانية"):
                add_visit(st.session_state.user_name, v_cust, v_type, p_qty, str(p_date), "")
                st.success("✅ تم تسجيل الزيارة!"); st.rerun()
        
        st.divider()
        st.subheader("📜 سجل الزيارات الميدانية (تراكمي)")
        my_visits = visits[visits['Salesman'] == st.session_state.user_name] if not visits.empty else pd.DataFrame()
        st.dataframe(my_visits, use_container_width=True, hide_index=True)

    with t3:
        st.subheader("🧮 حاسبة التحويل السريع (فورية)")
        with st.container(border=True):
            col_calc1, col_calc2 = st.columns(2)
            with col_calc1:
                in_cartons = st.number_input("أدخل عدد الكراتين", min_value=0, value=0, key="calc_c")
                st.success(f"📦 النتيجة: {in_cartons * UNITS_PER_CARTON} علبة")
            with col_calc2:
                in_units = st.number_input("أدخل عدد العلب", min_value=0, value=0, key="calc_u")
                st.success(f"📦 النتيجة: {in_units / UNITS_PER_CARTON:.2f} كرتون")

# --- واجهة المحاسب ---
elif page == "واجهة المحاسب":
    st.header("💰 واجهة المحاسب")
    st.subheader("⏳ طلبات بانتظار إصدار الفاتورة")
    st.markdown("| اسم العميل | الكمية | سعر الوحدة | السعر الإجمالي | رفع الفاتورة |")
    st.markdown("| :--- | :--- | :--- | :--- | :--- |")
    pending = orders[orders['Status'] == 'Pending'] if not orders.empty else pd.DataFrame()
    if not pending.empty:
        for _, r in pending.iterrows():
            with st.container(border=True):
                cp1, cp2, cp3, cp4, cp5 = st.columns([2, 1, 1, 1, 2])
                cp1.write(r['Customer Name'])
                cp2.write(r['Quantity'])
                cp3.write(r['Unit Price'])
                cp4.write(r['Total Amount'])
                pdf = cp5.file_uploader("PDF", type=['pdf'], key=f"f_{r['Order ID']}", label_visibility="collapsed")
                if pdf and st.button("✅ اعتماد", key=f"acc_{r['Order ID']}"):
                    update_stock_quantity(r['Product'], current_stock - r['Quantity'])
                    update_order_status(r['Order ID'], 'Invoiced', upload_to_github(pdf.getvalue(), f"inv_{r['Order ID']}.pdf"))
                    st.success("تم الاعتماد!"); st.rerun()
    else: st.info("ℹ️ لا توجد طلبات بانتظار إصدار الفاتورة حالياً.")

    st.divider()
    st.subheader("📜 سجل العملاء والفواتير المعتمدة")
    invoiced_acc = orders[orders['Status'] == 'Invoiced'] if not orders.empty else pd.DataFrame()
    if not invoiced_acc.empty:
        st.dataframe(invoiced_acc, use_container_width=True, hide_index=True)
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            invoiced_acc.to_excel(writer, index=False, sheet_name='Invoices')
        st.download_button(label="📥 تصدير السجل إلى Excel", data=output.getvalue(), file_name=f"lavar_invoices_{date.today()}.xlsx")
    else: st.info("ℹ️ السجل فارغ حالياً.")

    st.markdown("  
  
", unsafe_allow_html=True)
    c_df1, c_df2 = st.columns([5, 1.2])
    with c_df2: st.link_button("📊 نظام دفترة", "https://xhi.daftra.com/", type="primary" )

# --- واجهة الإدارة ---
elif page == "واجهة الإدارة الذكية":
    st.header("📊 مركز القيادة والتحكم الاستراتيجي")
    invoiced_adm = orders[orders['Status'] == 'Invoiced'] if not orders.empty else pd.DataFrame()
    sales_val = invoiced_adm['Total Amount'].sum() if not invoiced_adm.empty else 0
    pot_qty = visits['Potential Qty'].sum() if not visits.empty else 0
    
    st.markdown("### 📈 ملخص الأداء العام")
    st.markdown("##### **الفعلـي**")
    ca1, ca2, ca3, ca4 = st.columns(4)
    ca1.metric("📦 المخزون الحالي", f"{int(current_stock)} علبة")
    ca2.metric("💰 مبيعات محققة", f"{sales_val:,.0f} ريال")
    ca3.metric("📄 فواتير صادرة", f"{len(invoiced_adm)}")
    ca4.metric("📦 كميات مباعة", f"{int(invoiced_adm['Quantity'].sum()) if not invoiced_adm.empty else 0} علبة")

    st.markdown("##### **المتوقـع**")
    ce1, ce2, ce3, ce4 = st.columns(4)
    ce1.metric("🔮 طلبات متوقعة", f"{int(pot_qty)} علبة")
    ce2.metric("💵 قيمة متوقعة", f"{pot_qty * 15.0:,.0f} ريال")
    ce3.metric("🏭 تكلفة الإنتاج", f"{pot_qty * UNIT_COST:,.0f} ريال")
    ce4.metric("📍 إجمالي الزيارات", f"{len(visits)}")

    tab1, tab2, tab3, tab4 = st.tabs(["🧠 التخطيط", "💰 السيولة والمبيعات", "📦 إدارة المخزون", "📍 الميدان"])
    
    with tab1:
        st.subheader("📋 جدول التوصيات الإدارية")
        with st.container(border=True):
            if current_stock < 1000: st.warning("⚠️ توصية: المخزون منخفض، يرجى جدولة إنتاج عاجل.")
            elif pot_qty > current_stock: st.error("⚠️ توصية: الطلب المتوقع يتجاوز المخزون الحالي.")
            else: st.success("✅ الحالة مستقرة، لا توجد توصيات عاجلة حالياً.")

        st.subheader("📅 تكلفة الإنتاج المتوقعة أسبوعياً")
        v_df = visits.copy() if not visits.empty else pd.DataFrame(columns=['Potential Date', 'Potential Qty'])
        if not v_df.empty:
            v_df['Potential Date'] = pd.to_datetime(v_df['Potential Date'])
            v_df['Week'] = v_df['Potential Date'].dt.to_period('W').apply(lambda r: r.start_time)
            weekly = v_df.groupby('Week')['Potential Qty'].sum().reset_index()
            weekly['Cost'] = weekly['Potential Qty'] * UNIT_COST
            fig = px.bar(weekly, x='Week', y='Cost', labels={'Week': 'تاريخ الأسبوع', 'Cost': 'التكلفة المتوقعة'}, color_discrete_sequence=['#FF4B4B'])
            st.plotly_chart(fig, use_container_width=True)
        else: st.info("📊 سيظهر الرسم البياني هنا عند وجود بيانات زيارات.")

        st.subheader("🗓️ جدول الإنتاج المقترح (قاعدة 9 أيام)")
        mps = pd.DataFrame(columns=["الشهر", "الطلب المتوقع", "الإنتاج المطلوب", "تاريخ البدء"])
        if not v_df.empty:
            v_df['Month'] = v_df['Potential Date'].dt.to_period('M').astype(str)
            monthly = v_df.groupby('Month')['Potential Qty'].sum().reset_index()
            temp_s, req_p = current_stock, []
            for q in monthly['Potential Qty']:
                needed = max(0, q - temp_s)
                temp_s = max(0, temp_s - q)
                req_p.append(int(needed))
            mps = pd.DataFrame({"الشهر": monthly['Month'], "الطلب المتوقع": monthly['Potential Qty'].astype(int), "الإنتاج المطلوب": req_p, "تاريخ البدء": monthly['Month'].apply(lambda x: (pd.to_datetime(str(x)) - timedelta(days=9)).strftime('%Y-%m-%d'))})
        st.table(mps)

    with tab2:
        st.subheader("💵 تحليل السيولة والتدفقات")
        if not invoiced_adm.empty:
            invoiced_adm['Due Date'] = pd.to_datetime(invoiced_adm['Due Date'])
            invoiced_adm['Month'] = invoiced_adm['Due Date'].dt.to_period('M').astype(str)
            st.plotly_chart(px.bar(invoiced_adm.groupby('Month')['Total Amount'].sum().reset_index(), x='Month', y='Total Amount', title="التدفقات النقدية الداخلة (حسب تاريخ الاستحقاق)"), use_container_width=True)
            st.markdown("##### تفاصيل استحقاق الفواتير")
            st.dataframe(invoiced_adm[['Customer Name', 'Quantity', 'Total Amount', 'Due Date']], use_container_width=True, hide_index=True)
        
        st.divider()
        st.subheader("🎯 نظام المبيعات المستهدفة")
        target = st.number_input("أدخل كمية المبيعات المستهدفة (علبة)", value=5000)
        achieved = invoiced_adm['Quantity'].sum() if not invoiced_adm.empty else 0
        percent = (achieved / target * 100) if target > 0 else 0
        st.progress(min(percent/100, 1.0))
        st.write(f"نسبة تحقيق المستهدف: {percent:.1f}% ({int(achieved)} من {target} علبة)")

    with tab3:
        st.subheader("📦 إدارة المخزون")
        st.metric("المخزون الحالي", f"{int(current_stock)} علبة")
        new_q = st.number_input("تحديث المخزون يدوياً", value=int(current_stock))
        if st.button("حفظ التحديث"):
            update_stock_quantity("صابون لآفار 3 لتر", new_q); st.rerun()

    with tab4:
        st.subheader("📍 سجل نشاط الميدان (إدارة)")
        st.markdown("**المندوب | العميل | التاريخ | الكمية المتوقعة | الإجراء**")
        if not visits.empty:
            for i, r in visits.iterrows():
                with st.container(border=True):
                    cv1, cv2, cv3, cv4, cv5 = st.columns([1.5, 2, 1.5, 2, 1])
                    cv1.write(r['Salesman'])
                    cv2.write(r['Customer Name'])
                    cv3.write(r['Date'])
                    cv4.write(f"{int(r['Potential Qty'])} علبة")
                    if cv5.button("حذف 🗑️", key=f"dv_{i}"):
                        remove_visit(i); st.rerun()
        else: st.info("ℹ️ لا توجد زيارات مسجلة حالياً.")
