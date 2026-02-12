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

# 2. تحسينات الواجهة (CSS) للمحاذاة والجمالية
st.markdown("""
    <style>
    .stApp { text-align: right; direction: rtl; }
    .stMetric { text-align: right; }
    .stMetric label { font-size: 0.8rem !important; color: #666; }
    .stMetric div { font-size: 1.2rem !important; font-weight: bold; }
    div[data-testid="stExpander"] { text-align: right; }
    .stTable { direction: rtl; border: 1px solid #eee; }
    .stDataFrame { direction: rtl; }
    .stButton button { width: 100%; }
    th { text-align: right !important; background-color: #f1f3f4; }
    .main-title { color: #2E7D32; text-align: center; margin-bottom: 20px; }
    .fixed-header { background-color: #f8f9fa; padding: 10px; border-radius: 5px; font-weight: bold; border: 1px solid #ddd; margin-bottom: 10px; }
    </style>
""", unsafe_allow_html=True)

# 3. نظام استمرارية تسجيل الدخول (Session State)
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.markdown("<h1 class='main-title'>نظام لآفار للأعمال</h1>", unsafe_allow_html=True)
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

# 4. القائمة الجانبية
with st.sidebar:
    st.markdown("<h2 style='text-align: center; color: #2E7D32;'>🏢 لآفار للمنظفات</h2>", unsafe_allow_html=True)
    st.divider()
    st.markdown(f"### 👤 {st.session_state.user_name}")
    pages = ["واجهة الإدارة الذكية", "واجهة المندوب", "واجهة المحاسب"] if st.session_state.role == "admin" else \
            ["واجهة المحاسب"] if st.session_state.role == "accountant" else ["واجهة المندوب"]
    page = st.sidebar.radio("📌 الانتقال إلى:", pages)
    st.divider()
    if st.sidebar.button("🚪 تسجيل الخروج", use_container_width=True):
        st.session_state.logged_in = False
        st.rerun()

# جلب البيانات من قاعدة البيانات
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
            if st.button("تقديم الطلب 🚀", use_container_width=True):
                if name and qty:
                    add_order(name, cr, tax, addr, phone, "صابون لآفار 3 لتر", qty, days, price)
                    st.success("✅ تم تقديم الطلب بنجاح!"); st.rerun()
                else: st.error("يرجى إدخال اسم العميل والكمية")
        
        st.divider()
        st.subheader("🚀 الطلبات الحالية (بانتظار الإرسال للمحاسب)")
        st.markdown("<div class='fixed-header'><div style='display: flex; justify-content: space-between;'><span style='width: 30%;'>اسم العميل</span><span style='width: 15%;'>الكمية</span><span style='width: 15%;'>السعر</span><span style='width: 20%;'>الإجمالي</span><span style='width: 20%;'>الإجراء</span></div></div>", unsafe_allow_html=True)
        
        drafts = orders[orders['Status'] == 'Draft'] if not orders.empty else pd.DataFrame()
        if not drafts.empty:
            for i, r in drafts.iterrows():
                with st.container(border=True):
                    col1, col2, col3, col4, col5 = st.columns([3, 1.5, 1.5, 2, 2])
                    col1.write(r['Customer Name'])
                    col2.write(str(r['Quantity']))
                    col3.write(str(r['Unit Price']))
                    col4.write(str(r['Total Amount']))
                    if col5.button("إرسال 📤", key=f"snd_{r['Order ID']}"):
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
        with st.form("v_form"):
            c1, c2 = st.columns(2)
            with c1:
                v_cust = st.text_input("اسم العميل المزار")
                v_type = st.selectbox("نوع الزيارة", ["دورية", "عميل جديد", "تحصيل", "شكوى"])
            with c2:
                p_qty = st.number_input("الكمية المتوقعة (علبة)", min_value=0, value=0)
                p_date = st.date_input("التاريخ المتوقع للطلب", value=date.today() + timedelta(days=7))
            if st.form_submit_button("💾 حفظ الزيارة الميدانية", use_container_width=True):
                add_visit(st.session_state.user_name, v_cust, v_type, p_qty, str(p_date), "")
                st.success("✅ تم تسجيل الزيارة بنجاح!"); st.rerun()
        
        st.divider()
        st.subheader("📜 سجل زياراتي الميدانية")
        my_visits = visits[visits['Salesman'] == st.session_state.user_name] if not visits.empty else pd.DataFrame()
        if not my_visits.empty:
            st.dataframe(my_visits, use_container_width=True, hide_index=True)
        else: st.info("ℹ️ لم يتم تسجيل أي زيارات بعد.")

    with t3:
        st.subheader("🧮 حاسبة التحويل السريع")
        with st.container(border=True):
            cc1, cc2 = st.columns(2)
            with cc1:
                c_in = st.number_input("عدد الكراتين", min_value=0, value=0, key="c_in")
                st.info(f"💡 تعادل: **{c_in * UNITS_PER_CARTON}** علبة")
            with cc2:
                u_in = st.number_input("عدد العلب", min_value=0, value=0, key="u_in")
                st.info(f"💡 تعادل: **{u_in / UNITS_PER_CARTON:.2f}** كرتون")

# --- واجهة المحاسب ---
elif page == "واجهة المحاسب":
    st.header("💰 واجهة المحاسب")
    st.subheader("⏳ طلبات بانتظار إصدار الفاتورة")
    st.markdown("<div class='fixed-header'><div style='display: flex; justify-content: space-between;'><span style='width: 30%;'>اسم العميل</span><span style='width: 15%;'>الكمية</span><span style='width: 20%;'>الإجمالي</span><span style='width: 35%;'>رفع الفاتورة والاعتماد</span></div></div>", unsafe_allow_html=True)
    
    pending = orders[orders['Status'] == 'Pending'] if not orders.empty else pd.DataFrame()
    if not pending.empty:
        for _, r in pending.iterrows():
            with st.container(border=True):
                cp1, cp2, cp3, cp4 = st.columns([3, 1.5, 2, 3.5])
                cp1.write(r['Customer Name'])
                cp2.write(str(r['Quantity']))
                cp3.write(f"{r['Total Amount']} ريال")
                with cp4:
                    c_file, c_btn = st.columns([2, 1])
                    pdf = c_file.file_uploader("رفع PDF", type=['pdf'], key=f"pdf_{r['Order ID']}", label_visibility="collapsed")
                    if pdf and c_btn.button("✅ اعتماد", key=f"btn_{r['Order ID']}"):
                        update_stock_quantity(r['Product'], current_stock - r['Quantity'])
                        update_order_status(r['Order ID'], 'Invoiced', upload_to_github(pdf.getvalue(), f"inv_{r['Order ID']}.pdf"))
                        st.success("تم الاعتماد!"); st.rerun()
    else: st.info("ℹ️ لا توجد طلبات معلقة حالياً.")

    st.divider()
    st.subheader("📜 سجل الفواتير المعتمدة")
    invoiced_all = orders[orders['Status'] == 'Invoiced'] if not orders.empty else pd.DataFrame()
    if not invoiced_all.empty:
        st.dataframe(invoiced_all, use_container_width=True, hide_index=True)
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            invoiced_all.to_excel(writer, index=False)
        st.download_button("📥 تحميل السجل كملف Excel", output.getvalue(), "invoices.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    else: st.info("ℹ️ لا توجد فواتير معتمدة.")

    st.markdown("  
  
", unsafe_allow_html=True)
    st.columns([5, 1])[1].link_button("📊 نظام دفترة", "https://xhi.daftra.com/", type="primary" )

# --- واجهة الإدارة ---
elif page == "واجهة الإدارة الذكية":
    st.header("📊 مركز القيادة والتحكم")
    
    invoiced_adm = orders[orders['Status'] == 'Invoiced'] if not orders.empty else pd.DataFrame()
    sales_total = invoiced_adm['Total Amount'].sum() if not invoiced_adm.empty else 0
    potential_qty = visits['Potential Qty'].sum() if not visits.empty else 0
    
    st.markdown("### 📈 ملخص الأداء العام")
    st.markdown("##### **الأرقام الفعلية**")
    f1, f2, f3, f4 = st.columns(4)
    f1.metric("📦 المخزون", f"{int(current_stock)} علبة")
    f2.metric("💰 المبيعات", f"{sales_total:,.0f} ريال")
    f3.metric("📄 الفواتير", len(invoiced_adm))
    f4.metric("🚚 الكمية المباعة", f"{int(invoiced_adm['Quantity'].sum()) if not invoiced_adm.empty else 0}")

    st.markdown("##### **الأرقام المتوقعة**")
    e1, e2, e3, e4 = st.columns(4)
    e1.metric("🔮 طلبات متوقعة", f"{int(potential_qty)} علبة")
    e2.metric("💵 قيمة متوقعة", f"{potential_qty * 11.0:,.0f} ريال")
    e3.metric("🏭 تكلفة الإنتاج", f"{potential_qty * UNIT_COST:,.0f} ريال")
    e4.metric("📍 زيارات الميدان", len(visits))

    t_a, t_b, t_c, t_d = st.tabs(["🧠 التخطيط", "💰 السيولة", "📦 المخزون", "📍 الميدان"])
    
    with t_a:
        st.subheader("📋 التوصيات الإدارية")
        with st.container(border=True):
            if current_stock < 1000: st.warning("⚠️ تنبيه: المخزون تحت حد الأمان (1000 علبة).")
            elif potential_qty > current_stock: st.error("⚠️ تنبيه: الطلب المتوقع أكبر من المخزون المتوفر.")
            else: st.success("✅ وضع المخزون والطلب مستقر حالياً.")

        st.subheader("📅 تكلفة الإنتاج الأسبوعية")
        if not visits.empty:
            v_plot = visits.copy()
            v_plot['Date'] = pd.to_datetime(v_plot['Date'])
            v_plot['Week'] = v_plot['Date'].dt.to_period('W').apply(lambda r: r.start_time)
            w_data = v_plot.groupby('Week')['Potential Qty'].sum().reset_index()
            w_data['Cost'] = w_data['Potential Qty'] * UNIT_COST
            st.plotly_chart(px.bar(w_data, x='Week', y='Cost', title="تكلفة الإنتاج المتوقعة حسب الأسبوع"), use_container_width=True)
        else: st.info("📊 سيظهر الرسم البياني هنا عند توفر بيانات.")

        st.subheader("🗓️ جدول الإنتاج المقترح")
        if not visits.empty:
            v_plot = visits.copy()
            v_plot['Date'] = pd.to_datetime(v_plot['Date'])
            v_plot['Month'] = v_plot['Date'].dt.to_period('M').astype(str)
            m_data = v_plot.groupby('Month')['Potential Qty'].sum().reset_index()
            m_data['Production'] = m_data['Potential Qty'].apply(lambda x: int(max(0, x - current_stock)))
            st.table(m_data.rename(columns={'Month': 'الشهر', 'Potential Qty': 'الطلب المتوقع', 'Production': 'الإنتاج المطلوب'}))
        else: st.info("ℹ️ لا توجد بيانات إنتاج مقترحة.")

    with t_b:
        st.subheader("💰 تحليل السيولة والمستهدف")
        if not invoiced_adm.empty:
            invoiced_adm['Due Date'] = pd.to_datetime(invoiced_adm['Due Date'])
            invoiced_adm['Month'] = invoiced_adm['Due Date'].dt.to_period('M').astype(str)
            st.plotly_chart(px.bar(invoiced_adm.groupby('Month')['Total Amount'].sum().reset_index(), x='Month', y='Total Amount'), use_container_width=True)
            st.dataframe(invoiced_adm[['Customer Name', 'Total Amount', 'Due Date']], use_container_width=True, hide_index=True)
        
        st.divider()
        target_val = st.number_input("المبيعات المستهدفة (علبة)", value=5000)
        actual_val = invoiced_adm['Quantity'].sum() if not invoiced_adm.empty else 0
        st.write(f"🎯 نسبة الإنجاز: {(actual_val/target_val*100):.1f}%")
        st.progress(min(actual_val/target_val, 1.0))

    with t_c:
        st.subheader("📦 حالة المخزون")
        days_s = (current_stock / (potential_qty/30)) if potential_qty > 0 else 99
        st.metric("أيام الأمان", f"{int(days_s)} يوم")
        if st.button("تحديث المخزون (اختبار)"): update_stock_quantity("صابون لآفار 3 لتر", 0); st.rerun()

    with t_d:
        st.subheader("📍 إدارة نشاط الميدان")
        st.markdown("<div class='fixed-header'><div style='display: flex; justify-content: space-between;'><span style='width: 20%;'>المندوب</span><span style='width: 25%;'>العميل</span><span style='width: 20%;'>التاريخ</span><span style='width: 20%;'>الكمية</span><span style='width: 15%;'>الإجراء</span></div></div>", unsafe_allow_html=True)
        if not visits.empty:
            for i, r in visits.iterrows():
                with st.container(border=True):
                    cv1, cv2, cv3, cv4, cv5 = st.columns([1.5, 2, 1.5, 2, 1])
                    cv1.write(r['Salesman'])
                    cv2.write(r['Customer Name'])
                    cv3.write(r['Date'])
                    cv4.write(f"{int(r['Potential Qty'])} علبة")
                    if cv5.button("حذف 🗑️", key=f"adm_del_{i}"):
                        # ملاحظة: يتطلب حذف حقيقي من قاعدة البيانات
                        st.warning("تم الحذف بنجاح (محاكاة)"); st.rerun()
        else: st.info("ℹ️ السجل فارغ.")
