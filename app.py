import streamlit as st
import pandas as pd
from database import init_db, get_orders, add_order, update_order_status, get_stock, update_stock_quantity, add_visit, get_visits, delete_visit, delete_order, upload_to_github
from datetime import datetime, date, timedelta
import plotly.express as px
import io
import urllib.parse

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
    .stMetric label { font-size: 0.75rem !important; color: #666; }
    .stMetric div { font-size: 1.1rem !important; font-weight: bold; }
    div[data-testid="stExpander"] { text-align: right; }
    .stTable { direction: rtl; border: 1px solid #eee; }
    .stDataFrame { direction: rtl; }
    .stButton button { width: 100%; }
    th { text-align: right !important; background-color: #f1f3f4; }
    td { text-align: right !important; }
    .main-title { color: #2E7D32; text-align: center; margin-bottom: 20px; }
    [data-testid="stSidebar"] { left: 0 !important; right: auto !important; }
    [data-testid="stSidebar"] * { text-align: right !important; direction: rtl !important; }
    .recommendation-box { border: 1px solid #ddd; padding: 15px; border-radius: 5px; background-color: #f9f9f9; margin-bottom: 10px; }
    .alert-red { background-color: #ffebee; border-left: 4px solid #d32f2f; padding: 10px; border-radius: 4px; }
    .alert-green { background-color: #e8f5e9; border-left: 4px solid #388e3c; padding: 10px; border-radius: 4px; }
    .alert-yellow { background-color: #fff3e0; border-left: 4px solid #f57c00; padding: 10px; border-radius: 4px; }
    </style>
""", unsafe_allow_html=True)

# 3. نظام استمرارية تسجيل الدخول
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.markdown("<h1 class='main-title'>نظام لآفار للأعمال</h1>", unsafe_allow_html=True)
    with st.container(border=True):
        st.subheader("🔐 تسجيل الدخول")
        user = st.text_input("اسم المستخدم")
        password = st.text_input("كلمة المرور", type="password")
        if st.button("دخول للنظام", use_container_width=True):
            if (user == "admin" and password == "lavar2026") or \
               (user == "acc" and password == "lavar_acc") or \
               (user == "sales" and password == "lavar_sales"):
                st.session_state.logged_in, st.session_state.role, st.session_state.user_name = True, user, "المستخدم"
                st.rerun()
            else: st.error("❌ بيانات الدخول غير صحيحة")
    st.stop()

# 4. القائمة الجانبية
with st.sidebar:
    st.markdown("<h2 style='text-align: center; color: #2E7D32;'>🏢 لآفار للمنظفات</h2>", unsafe_allow_html=True)
    st.divider()
    st.markdown(f"### 👤 مرحباً: {st.session_state.user_name}")
    pages = ["واجهة الإدارة الذكية", "واجهة المندوب", "واجهة المحاسب"]
    page = st.sidebar.radio("📌 الانتقال إلى:", pages)
    st.divider()
    if st.sidebar.button("🚪 تسجيل الخروج", use_container_width=True):
        st.session_state.logged_in = False
        st.rerun()

# جلب البيانات
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
        with st.container(border=True):
            h1, h2, h3, h4, h5 = st.columns([3, 1, 1, 1.5, 2.5])
            h1.write("**اسم العميل**"); h2.write("**الكمية**"); h3.write("**السعر**"); h4.write("**الإجمالي**"); h5.write("**الإجراء**")
            st.divider()
            drafts = orders[orders['Status'] == 'Draft'] if not orders.empty else pd.DataFrame()
            if not drafts.empty:
                for i, r in drafts.iterrows():
                    col1, col2, col3, col4, col5 = st.columns([3, 1, 1, 1.5, 2.5])
                    col1.write(r['Customer Name'])
                    col2.write(str(int(r['Quantity'])))
                    col3.write(str(r['Unit Price']))
                    col4.write(str(r['Total Amount']))
                    b1, b2 = col5.columns(2)
                    if b1.button("إرسال 📤", key=f"snd_{r['Order ID']}"):
                        update_order_status(r['Order ID'], 'Pending'); st.rerun()
                    if b2.button("حذف 🗑️", key=f"del_{r['Order ID']}"):
                        delete_order(r['Order ID']); st.rerun()
            else: st.info("ℹ️ لا توجد طلبات حالياً بانتظار الإرسال.")

        st.divider()
        st.subheader("✅ الفواتير المعتمدة للعملاء")
        invoiced = orders[orders['Status'] == 'Invoiced'] if not orders.empty else pd.DataFrame()
        if not invoiced.empty:
            for i, r in invoiced.iterrows():
                with st.container(border=True):
                    c_i1, c_i2, c_i3 = st.columns([4, 2, 2])
                    c_i1.write(f"**العميل:** {r['Customer Name']} | **الكمية:** {int(r['Quantity'])} | **الإجمالي:** {r['Total Amount']} ريال")
                    if r['Invoice URL']:
                        c_i2.link_button("📄 عرض الفاتورة", r['Invoice URL'], use_container_width=True)
                        msg = urllib.parse.quote(f"مرحباً {r['Customer Name']}\nإليك فاتورة طلبك من لآفار للمنظفات:\n{r['Invoice URL']}")
                        wa_url = f"https://wa.me/{r['Phone']}?text={msg}"
                        c_i3.link_button("💬 واتساب", wa_url, use_container_width=True)
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
                st.info(f"💡 تعادل: **{int(c_in * UNITS_PER_CARTON)}** علبة")
            with cc2:
                u_in = st.number_input("عدد العلب", min_value=0, value=0, key="u_in")
                st.info(f"💡 تعادل: **{u_in / UNITS_PER_CARTON:.2f}** كرتون")

# --- واجهة المحاسب ---
elif page == "واجهة المحاسب":
    st.header("💰 واجهة المحاسب")
    st.subheader("⏳ طلبات بانتظار إصدار الفاتورة")
    with st.container(border=True):
        h1, h2, h3, h4 = st.columns([3, 1.5, 2, 4.5])
        h1.write("**اسم العميل**"); h2.write("**الكمية**"); h3.write("**الإجمالي**"); h4.write("**الإجراء**")
        st.divider()
        pending = orders[orders['Status'] == 'Pending'] if not orders.empty else pd.DataFrame()
        if not pending.empty:
            for _, r in pending.iterrows():
                cp1, cp2, cp3, cp4 = st.columns([3, 1.5, 2, 4.5])
                cp1.write(r['Customer Name'])
                cp2.write(str(int(r['Quantity'])))
                cp3.write(f"{r['Total Amount']} ريال")
                with cp4:
                    c_file, c_btn, c_del = st.columns([2, 1, 1])
                    pdf = c_file.file_uploader("رفع PDF", type=['pdf'], key=f"pdf_{r['Order ID']}", label_visibility="collapsed")
                    if pdf and c_btn.button("✅", key=f"btn_{r['Order ID']}"):
                        update_stock_quantity(r['Product'], current_stock - r['Quantity'])
                        update_order_status(r['Order ID'], 'Invoiced', upload_to_github(pdf.getvalue(), f"inv_{r['Order ID']}.pdf"))
                        st.success("تم الاعتماد!"); st.rerun()
                    if c_del.button("🗑️", key=f"acc_del_{r['Order ID']}"):
                        delete_order(r['Order ID']); st.rerun()
        else: st.info("ℹ️ لا توجد طلبات معلقة حالياً.")

    st.divider()
    st.subheader("📜 سجل الفواتير المعتمدة")
    invoiced_all = orders[orders['Status'] == 'Invoiced'] if not orders.empty else pd.DataFrame()
    if not invoiced_all.empty:
        st.dataframe(invoiced_all, use_container_width=True, hide_index=True)
        try:
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                invoiced_all.to_excel(writer, index=False)
            st.download_button("📥 تحميل السجل كملف Excel", output.getvalue(), "invoices.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        except: st.warning("⚠️ ميزة تصدير الإكسل قيد التحديث.")
    else: st.info("ℹ️ لا توجد فواتير معتمدة.")

    st.markdown("<br><br>", unsafe_allow_html=True)
    st.columns([5, 1])[1].link_button("📊 نظام دفترة", "https://xhi.daftra.com/", type="primary")

# --- واجهة الإدارة الذكية (صفحة واحدة متكاملة) ---
elif page == "واجهة الإدارة الذكية":
    st.header("📊 مركز القيادة والتحكم - لآفار للأعمال")
    
    # ===== حساب البيانات الأساسية =====
    invoiced_adm = orders[orders['Status'] == 'Invoiced'] if not orders.empty else pd.DataFrame()
    sales_total = invoiced_adm['Total Amount'].sum() if not invoiced_adm.empty else 0
    sales_qty = invoiced_adm['Quantity'].sum() if not invoiced_adm.empty else 0
    potential_qty = visits['Potential Qty'].sum() if not visits.empty else 0
    
    # ===== نظام مؤشر الثقة الذكي =====
    if 'confidence_level' not in st.session_state:
        st.session_state.confidence_level = 70
    
    # حساب الطلب المرجح (الكمية المتوقعة × مؤشر الثقة)
    weighted_demand = potential_qty * (st.session_state.confidence_level / 100.0)
    
    # حساب توصية الإنتاج
    safety_stock = 500
    production_needed = max(0, weighted_demand + safety_stock - current_stock)
    production_cost = production_needed * UNIT_COST
    
    # حساب التدفقات النقدية المتوقعة (الفواتير التي تستحق خلال 9 أيام)
    today = pd.to_datetime(date.today())
    future_date = today + timedelta(days=LEAD_TIME_DAYS)
    future_invoices = invoiced_adm[
        (pd.to_datetime(invoiced_adm['Due Date']) >= today) & 
        (pd.to_datetime(invoiced_adm['Due Date']) <= future_date)
    ] if not invoiced_adm.empty else pd.DataFrame()
    expected_cash_flow = future_invoices['Total Amount'].sum() if not future_invoices.empty else 0
    
    # حساب فجوة التمويل
    financing_gap = max(0, production_cost - expected_cash_flow)
    cash_coverage_percent = (expected_cash_flow / production_cost * 100) if production_cost > 0 else 0
    
    # ===== الصف الأول: البيانات الفعلية (ACTUAL) =====
    st.markdown("### 📊 الصف الأول: البيانات الفعلية (ACTUAL)")
    f1, f2, f3, f4 = st.columns(4)
    f1.metric("📦 المخزون الحالي", f"{int(current_stock)} علبة")
    f2.metric("💰 المبيعات المحققة", f"{sales_total:,.0f} ريال")
    f3.metric("🛍️ كمية المبيعات", f"{int(sales_qty)} علبة")
    f4.metric("📋 عدد الفواتير", f"{len(invoiced_adm)} فاتورة")
    
    # ===== الصف الثاني: البيانات المتوقعة (PREDICTED) =====
    st.markdown("### 🔮 الصف الثاني: البيانات المتوقعة (PREDICTED)")
    e1, e2, e3, e4 = st.columns(4)
    e1.metric("📈 الطلب المرجح", f"{int(weighted_demand)} علبة")
    e2.metric("💵 القيمة المتوقعة", f"{weighted_demand * 11:,.0f} ريال")
    e3.metric("🏭 تكلفة الإنتاج", f"{production_cost:,.0f} ريال")
    e4.metric("⚠️ فجوة التمويل", f"{financing_gap:,.0f} ريال")
    
    st.divider()
    
    # ===== مؤشر الثقة الذكي للمدير =====
    st.markdown("### 🎯 مؤشر الثقة الذكي (Smart Confidence Slider)")
    with st.container(border=True):
        col_conf1, col_conf2 = st.columns([3, 1])
        with col_conf1:
            st.session_state.confidence_level = st.slider(
                "اضبط مؤشر الثقة في توقعات الطلب (يؤثر على توصيات الإنتاج والتمويل)",
                0, 100, st.session_state.confidence_level, 5
            )
        with col_conf2:
            st.metric("مؤشر الثقة", f"{st.session_state.confidence_level}%")
    
    st.info(f"💡 **التأثير الحالي:** الطلب المرجح = {int(potential_qty)} × {st.session_state.confidence_level}% = **{int(weighted_demand)} علبة**")
    
    st.divider()
    
    # ===== توصية الإنتاج الذكية =====
    st.markdown("### 🎯 توصية الإنتاج الذكية")
    if production_needed <= 0:
        st.markdown("""
        <div class='alert-green'>
        <h4>✅ المخزون في وضع صحي ومستقر</h4>
        <p>المخزون الحالي كافٍ لتغطية الطلبات المتوقعة خلال الفترة القادمة. لا توجد حاجة لخطوط إنتاج إضافية حالياً.</p>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div class='alert-red'>
        <h4>⚠️ تنبيه: نقص متوقع في المخزون</h4>
        <p><strong>التوصية:</strong> إنتاج <strong>{int(production_needed)} علبة</strong> بتكلفة تقديرية <strong>{production_cost:,.0f} ريال</strong></p>
        <p><strong>الكمية المرجحة:</strong> {int(weighted_demand)} علبة × {st.session_state.confidence_level}% ثقة</p>
        </div>
        """, unsafe_allow_html=True)
    
    st.divider()
    
    # ===== تحليل فجوة التمويل والسيولة =====
    st.markdown("### 💰 تحليل فجوة التمويل والسيولة")
    with st.container(border=True):
        col1, col2, col3 = st.columns(3)
        col1.metric("💵 التدفقات النقدية المتوقعة", f"{expected_cash_flow:,.0f} ريال")
        col2.metric("📊 نسبة التغطية", f"{cash_coverage_percent:.1f}%")
        col3.metric("🔴 التمويل المطلوب ضخه", f"{financing_gap:,.0f} ريال")
    
    st.markdown(f"""
    **ملخص السيولة والتمويل:**
    - التدفقات النقدية المتوقعة خلال {LEAD_TIME_DAYS} أيام: **{expected_cash_flow:,.0f} ريال**
    - تكلفة الإنتاج المطلوبة: **{production_cost:,.0f} ريال**
    - نسبة التغطية: **{cash_coverage_percent:.1f}%**
    - الفجوة التمويلية: **{financing_gap:,.0f} ريال** (إن وجدت)
    """)
    
    st.divider()
    
    # ===== خريطة التدفق الزمني للإنتاج الأسبوعي =====
    st.markdown("### 📅 خريطة التدفق الزمني للإنتاج الأسبوعي")
    if not visits.empty:
        v_plot = visits.copy()
        v_plot['Date'] = pd.to_datetime(v_plot['Date'])
        v_plot['Week'] = v_plot['Date'].dt.to_period('W')
        w_data = v_plot.groupby('Week')['Potential Qty'].sum().reset_index()
        w_data['Week_Start'] = w_data['Week'].apply(lambda x: x.start_time.strftime('%Y-%m-%d'))
        w_data['Weighted_Qty'] = (w_data['Potential Qty'] * (st.session_state.confidence_level / 100.0)).astype(int)
        w_data['Cost'] = w_data['Weighted_Qty'] * UNIT_COST
        
        display_table = w_data[['Week_Start', 'Potential Qty', 'Weighted_Qty', 'Cost']].copy()
        display_table.columns = ['الأسبوع', 'الكمية المتوقعة', 'الكمية المرجحة', 'التكلفة (ريال)']
        st.dataframe(display_table, use_container_width=True, hide_index=True)
    else:
        st.info("📊 لا توجد بيانات زيارات لعرض خريطة التدفق الزمني.")
    
    st.divider()
    
    # ===== جدول الفواتير المستحقة والمتأخرة =====
    st.markdown("### 📋 جدول الفواتير المستحقة والمتأخرة")
    if not invoiced_adm.empty:
        inv_display = invoiced_adm[['Customer Name', 'Quantity', 'Total Amount', 'Due Date']].copy()
        inv_display.columns = ['العميل', 'الكمية', 'القيمة (ريال)', 'تاريخ الاستحقاق']
        
        # تلوين الفواتير المتأخرة بناءً على تاريخ الاستحقاق الفعلي
        def highlight_overdue(row):
            due_date = pd.to_datetime(row['تاريخ الاستحقاق'])
            if due_date < today:
                return ['background-color: #ffcdd2'] * len(row)  # أحمر للمتأخرة
            elif due_date <= today + timedelta(days=3):
                return ['background-color: #fff3e0'] * len(row)  # أصفر للقريبة
            return [''] * len(row)
        
        st.dataframe(inv_display.style.apply(highlight_overdue, axis=1), use_container_width=True, hide_index=True)
    else:
        st.info("ℹ️ لا توجد فواتير معتمدة حالياً.")
    
    st.divider()
    
    # ===== نظام تحقيق المستهدف السنوي =====
    st.markdown("### 🎯 نظام تحقيق المستهدف السنوي")
    with st.container(border=True):
        target_val_year = st.number_input("أدخل المستهدف السنوي (علبة)", value=60000, min_value=1, key="annual_target") # افتراضي 5000 * 12
        
        # حساب الكمية المباعة للسنة الحالية
        current_year = datetime.now().year
        sales_qty_year = invoiced_adm[pd.to_datetime(invoiced_adm["Order Date"]).dt.year == current_year]["Quantity"].sum() if not invoiced_adm.empty else 0
        
        percent_year = (sales_qty_year / target_val_year * 100) if target_val_year > 0 else 0
        
        col_t1, col_t2 = st.columns([2, 1])
        with col_t1:
            st.write(f"**نسبة تحقيق المستهدف السنوي: {percent_year:.1f}%**")
            st.progress(min(sales_qty_year / target_val_year, 1.0))
        with col_t2:
            st.metric("المتحقق", f"{int(sales_qty_year)} علبة")
            st.metric("المستهدف", f"{int(target_val_year)} علبة")
    
    st.divider()
    
    # ===== إدارة المخزون =====
    st.markdown("### 📦 إدارة المخزون")
    with st.container(border=True):
        st.metric("المخزون الحالي", f"{int(current_stock)} علبة")
        new_q = st.number_input("تعديل كمية المخزون يدوياً", value=int(current_stock))
        if st.button("تحديث الكمية"):
            update_stock_quantity("صابون لآفار 3 لتر", new_q)
            st.success("✅ تم التحديث!")
            st.rerun()
    
    st.divider()
    
    # ===== جدول إدارة نشاط الميدان مع مؤشر الثقة =====
    st.markdown("### 📍 إدارة نشاط الميدان")
    with st.container(border=True):
        h1, h2, h3, h4, h5, h6 = st.columns([1.5, 2, 1.5, 1.5, 2.5, 1])
        h1.write("**المندوب**")
        h2.write("**العميل**")
        h3.write("**التاريخ**")
        h4.write("**الكمية**")
        h5.write("**مؤشر الثقة**")
        h6.write("**الإجراء**")
        st.divider()
        
        if not visits.empty:
            for i, r in visits.iterrows():
                cv1, cv2, cv3, cv4, cv5, cv6 = st.columns([1.5, 2, 1.5, 1.5, 2.5, 1])
                cv1.write(r['Salesman'])
                cv2.write(r['Customer Name'])
                cv3.write(r['Date'])
                cv4.write(f"{int(r['Potential Qty'])} علبة")
                
                # حساب مؤشر الثقة الذكي تلقائياً بناءً على عوامل مختلفة
                auto_conf = 50  # قاعدة أساسية
                if r['Visit Type'] == "عميل جديد":
                    auto_conf += 20
                if r['Potential Qty'] > 500:
                    auto_conf += 10
                days_diff = (pd.to_datetime(r['Potential Date']) - pd.to_datetime(r['Date'])).days
                if days_diff < 10:
                    auto_conf += 15
                auto_conf = min(100, auto_conf)
                
                with cv5:
                    st.slider("مؤشر الثقة", 0, 100, auto_conf, key=f"conf_{i}", disabled=False)
                
                if cv6.button("حذف 🗑️", key=f"adm_del_{i}"):
                    delete_visit(i)
                    st.rerun()
        else:
            st.info("ℹ️ لا توجد سجلات حالياً.")
