import streamlit as st
import pandas as pd
from database import init_db, get_orders, add_order, update_order_status, get_stock, update_stock_quantity, add_visit, get_visits, delete_visit, delete_order, upload_to_github, get_annual_target, update_annual_target, get_master_confidence, update_master_confidence, update_visit_confidence, get_visit_confidence, update_order, delete_order_by_id, update_stock, delete_stock_item, update_visit, delete_visit_by_index, update_setting, delete_setting, clear_all_data
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
    .metric-card { background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%); border-radius: 8px; padding: 12px 8px; margin: 5px 0; box-shadow: 0 2px 4px rgba(0, 0, 0, 0.08); border: 1px solid rgba(255, 255, 255, 0.5); text-align: center; }
    .metric-card-actual { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; }
    .metric-card-predicted { background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); color: white; }
    .metric-value { font-size: 1.6rem !important; font-weight: 800 !important; margin: 5px 0; letter-spacing: 0.5px; }
    .metric-label { font-size: 0.75rem !important; font-weight: 600 !important; opacity: 0.9; margin-bottom: 2px; }
    .metric-icon { font-size: 1.8rem; margin-bottom: 4px; }
    .row-header { font-size: 1.1rem; font-weight: 700; color: #2E7D32; margin: 15px 0 10px 0; padding-bottom: 8px; border-bottom: 2px solid #2E7D32; }
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
            if (user == "admin" and password == "1234") or \
               (user == "acc" and password == "1234") or \
               (user == "sales" and password == "1234"):
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
    t1, t2 = st.tabs(["🛒 إدارة الطلبات", "📍 سجل الزيارات الميدانية"])
    
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
            v_cust = st.text_input("اسم العميل المزار")
            p_qty = st.number_input("الكمية المتوقعة (علبة)", min_value=0, value=0)
            p_date = st.date_input("التاريخ المتوقع للطلب", value=date.today() + timedelta(days=7))
            if st.form_submit_button("💾 حفظ الزيارة الميدانية", use_container_width=True):
                add_visit(st.session_state.user_name, v_cust, int(p_qty), str(p_date), "")
                st.success("✅ تم تسجيل الزيارة بنجاح!"); st.rerun()
        
        st.divider()
        st.subheader("📜 سجل زياراتي الميدانية")
        my_visits = visits[visits['Salesman'] == st.session_state.user_name] if not visits.empty else pd.DataFrame()
        if not my_visits.empty:
            st.dataframe(my_visits, use_container_width=True, hide_index=True)
        else: st.info("ℹ️ لم يتم تسجيل أي زيارات بعد.")



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
    
    # ===== محرك خطة الإنتاج الزمني =====
    def calculate_production_plan():
        production_orders = []
        remaining_stock = current_stock
        today = pd.to_datetime(date.today())
        year_end = pd.to_datetime(f"{today.year}-12-31")
        
        if visits.empty:
            return production_orders
        
        visits_sorted = visits.sort_values('Potential Date')
        
        for idx, visit in visits_sorted.iterrows():
            potential_date = pd.to_datetime(visit['Potential Date'])
            
            if potential_date > year_end or potential_date < today:
                continue
            
            conf_key = f"conf_{idx}"
            if conf_key in st.session_state:
                individual_conf = st.session_state[conf_key]
            else:
                auto_conf = 60
                if visit['Potential Qty'] > 500:
                    auto_conf += 10
                days_diff = (potential_date - pd.to_datetime(visit['Date'])).days
                if days_diff < 10:
                    auto_conf += 15
                individual_conf = min(100, auto_conf)
            
            # تطبيق ضابط الإيقاع العام
            master_conf = st.session_state.get('master_confidence', 100) / 100.0
            confidence = (individual_conf / 100.0) * master_conf
            
            weighted_qty = visit['Potential Qty'] * confidence
            
            if remaining_stock < weighted_qty:
                production_qty = weighted_qty - remaining_stock
                production_cost = production_qty * UNIT_COST
                order_date = potential_date - timedelta(days=LEAD_TIME_DAYS)
                
                available_cash = 0
                if not invoiced_adm.empty:
                    due_invoices = invoiced_adm[
                        (pd.to_datetime(invoiced_adm['Due Date']) >= today) & 
                        (pd.to_datetime(invoiced_adm['Due Date']) <= order_date)
                    ]
                    available_cash = due_invoices['Total Amount'].sum()
                
                financing_gap = max(0, production_cost - available_cash)
                cash_coverage = (available_cash / production_cost * 100) if production_cost > 0 else 0
                
                production_orders.append({
                    'order_date': order_date.strftime('%Y-%m-%d'),
                    'delivery_date': potential_date.strftime('%Y-%m-%d'),
                    'quantity': int(production_qty),
                    'cost': production_cost,
                    'available_cash': available_cash,
                    'financing_gap': financing_gap,
                    'cash_coverage': cash_coverage,
                    'customer': visit['Customer Name'],
                    'confidence': confidence * 100
                })
                
                remaining_stock = production_qty
            else:
                remaining_stock -= weighted_qty
        
        return production_orders
    
    production_plan = calculate_production_plan()
    
    # ===== نظام مؤشر الثقة الذكي =====
    if 'confidence_level' not in st.session_state:
        st.session_state.confidence_level = 70
    
    # حساب الطلب المرجح (الكمية المتوقعة × مؤشر الثقة)
    # حساب الطلب المرجح بناءً على المؤشرات الفردية مع ضابط الإيقاع العام
    if not visits.empty:
        weighted_demand = 0
        for idx, visit in visits.iterrows():
            conf_key = f"conf_{idx}"
            if conf_key in st.session_state:
                individual_conf = st.session_state[conf_key]
            else:
                auto_conf = 60
                if visit['Potential Qty'] > 500:
                    auto_conf += 10
                days_diff = (pd.to_datetime(visit['Potential Date']) - pd.to_datetime(visit['Date'])).days
                if days_diff < 10:
                    auto_conf += 15
                individual_conf = min(100, auto_conf)
            
            # تطبيق ضابط الإيقاع العام
            master_conf = st.session_state.get('master_confidence', 100) / 100.0
            final_conf = (individual_conf / 100.0) * master_conf
            weighted_demand += visit['Potential Qty'] * final_conf
    else:
        weighted_demand = 0
    
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
    st.markdown('<div class="row-header">📊 البيانات الفعلية (ACTUAL)</div>', unsafe_allow_html=True)
    f1, f2, f3, f4 = st.columns(4)
    with f1:
        st.markdown('<div class="metric-card metric-card-actual"><div class="metric-icon">📦</div><div class="metric-label">المخزون الحالي</div><div class="metric-value">{}</div><div class="metric-label">علبة</div></div>'.format(int(current_stock)), unsafe_allow_html=True)
    with f2:
        st.markdown('<div class="metric-card metric-card-actual"><div class="metric-icon">💰</div><div class="metric-label">المبيعات المحققة</div><div class="metric-value">{:,.0f}</div><div class="metric-label">ريال</div></div>'.format(sales_total), unsafe_allow_html=True)
    with f3:
        st.markdown('<div class="metric-card metric-card-actual"><div class="metric-icon">🛍️</div><div class="metric-label">كمية المبيعات</div><div class="metric-value">{}</div><div class="metric-label">علبة</div></div>'.format(int(sales_qty)), unsafe_allow_html=True)
    with f4:
        st.markdown('<div class="metric-card metric-card-actual"><div class="metric-icon">📋</div><div class="metric-label">عدد الفواتير</div><div class="metric-value">{}</div><div class="metric-label">فاتورة</div></div>'.format(len(invoiced_adm)), unsafe_allow_html=True)
    
    # ===== الصف الثاني: البيانات المتوقعة (PREDICTED) =====
    st.markdown('<div class="row-header">🔮 البيانات المتوقعة (PREDICTED)</div>', unsafe_allow_html=True)
    e1, e2, e3, e4 = st.columns(4)
    with e1:
        st.markdown('<div class="metric-card metric-card-predicted"><div class="metric-icon">📈</div><div class="metric-label">الطلب المرجح</div><div class="metric-value">{}</div><div class="metric-label">علبة</div></div>'.format(int(weighted_demand)), unsafe_allow_html=True)
    with e2:
        st.markdown('<div class="metric-card metric-card-predicted"><div class="metric-icon">💵</div><div class="metric-label">القيمة المتوقعة</div><div class="metric-value">{:,.0f}</div><div class="metric-label">ريال</div></div>'.format(weighted_demand * 11), unsafe_allow_html=True)
    with e3:
        st.markdown('<div class="metric-card metric-card-predicted"><div class="metric-icon">🏭</div><div class="metric-label">تكلفة الإنتاج</div><div class="metric-value">{:,.0f}</div><div class="metric-label">ريال</div></div>'.format(production_cost), unsafe_allow_html=True)
    with e4:
        st.markdown('<div class="metric-card metric-card-predicted"><div class="metric-icon">⚠️</div><div class="metric-label">فجوة التمويل</div><div class="metric-value">{:,.0f}</div><div class="metric-label">ريال</div></div>'.format(financing_gap), unsafe_allow_html=True)
    
    st.divider()
    
    # ===== مؤشر الثقة الذكي للمدير =====
    st.markdown("### 🎯 مؤشر الثقة الذكي (Smart Confidence Slider) - ضابط الإيقاع العام")
    with st.container(border=True):
        col_conf1, col_conf2 = st.columns([3, 1])
        with col_conf1:
            current_master = get_master_confidence()
            master_confidence = st.slider(
                "ضابط الإيقاع العام: اضبط هنا لتطبيق تأثير عام على جميع المؤشرات الفردية في الجدول أدناه",
                0, 100, current_master, 5, key="master_confidence_slider"
            )
            if master_confidence != current_master:
                update_master_confidence(master_confidence)
            st.session_state.master_confidence = master_confidence
        with col_conf2:
            st.metric("مؤشر الإيقاع", f"{master_confidence}%")
    
    # حساب متوسط الثقة من المؤشرات الفردية
    if not visits.empty:
        individual_confidences = []
        for idx in visits.index:
            conf_key = f"conf_{idx}"
            if conf_key in st.session_state:
                individual_confidences.append(st.session_state[conf_key])
        avg_confidence = sum(individual_confidences) / len(individual_confidences) if individual_confidences else 100
    else:
        avg_confidence = 100
    
    st.info(f"💡 **متوسط الثقة من الميدان:** {avg_confidence:.0f}% | **ضابط الإيقاع:** {master_confidence}% | **الثقة المطبقة:** {(avg_confidence * master_confidence / 100):.0f}%")
    
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
    
    st.markdown("### 📋 خطة أوامر الإنتاج المقترحة (الزمنية والمالية)")
    
    if production_plan:
        with st.container(border=True):
            h1, h2, h3, h4, h5, h6, h7, h8 = st.columns([1.5, 1.5, 1.2, 1.2, 1.2, 1.2, 1.2, 1.2])
            h1.write("**تاريخ الأمر**")
            h2.write("**تاريخ التسليم**")
            h3.write("**الكمية**")
            h4.write("**التكلفة**")
            h5.write("**السيولة**")
            h6.write("**التغطية%**")
            h7.write("**الفجوة**")
            h8.write("**الثقة%**")
            st.divider()
            
            for order in production_plan:
                c1, c2, c3, c4, c5, c6, c7, c8 = st.columns([1.5, 1.5, 1.2, 1.2, 1.2, 1.2, 1.2, 1.2])
                c1.write(order['order_date'])
                c2.write(order['delivery_date'])
                c3.write(f"{order['quantity']} علبة")
                c4.write(f"{order['cost']:,.0f} ر")
                c5.write(f"{order['available_cash']:,.0f} ر")
                
                if order['cash_coverage'] >= 100:
                    c6.markdown(f"<span style='color: green; font-weight: bold;'>{order['cash_coverage']:.0f}%</span>", unsafe_allow_html=True)
                elif order['cash_coverage'] >= 50:
                    c6.markdown(f"<span style='color: orange; font-weight: bold;'>{order['cash_coverage']:.0f}%</span>", unsafe_allow_html=True)
                else:
                    c6.markdown(f"<span style='color: red; font-weight: bold;'>{order['cash_coverage']:.0f}%</span>", unsafe_allow_html=True)
                
                c7.write(f"{order['financing_gap']:,.0f} ر")
                c8.write(f"{order['confidence']:.0f}%")
    else:
        st.info("✅ لا توجد طلبات مستقبلية مسجلة أو المخزون كافي لتغطية الطلبات المتوقعة.")
    
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
        current_annual_target = get_annual_target()
        target_val_year = st.number_input("أدخل المستهدف السنوي (علبة)", value=current_annual_target, min_value=1, key="annual_target_input")
        
        if target_val_year != current_annual_target:
            update_annual_target(target_val_year)
        
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
                auto_conf = 60  # قاعدة أساسية معدلة
                if r['Potential Qty'] > 500:
                    auto_conf += 10
                days_diff = (pd.to_datetime(r['Potential Date']) - pd.to_datetime(r['Date'])).days
                if days_diff < 10:
                    auto_conf += 15
                auto_conf = min(100, auto_conf)
                
                with cv5:
                    # قراءة قيمة الثقة من قاعدة البيانات إن وجدت
                    saved_conf = get_visit_confidence(i)
                    default_conf = saved_conf if saved_conf is not None else auto_conf
                    
                    conf_val = st.slider("مؤشر الثقة", 0, 100, default_conf, key=f"conf_{i}")
                    
                    # حفظ قيمة الثقة في قاعدة البيانات عند التغيير
                    if conf_val != default_conf:
                        update_visit_confidence(i, conf_val)
                    
                    weighted_qty = r['Potential Qty'] * (conf_val / 100.0)
                    st.caption(f"📊 {int(weighted_qty)} علبة")
                
                if cv6.button("حذف 🗑️", key=f"adm_del_{i}"):
                    delete_visit(i)
                    st.rerun()
        else:
            st.info("ℹ️ لا توجد سجلات حالياً.")

    # ===== قسم إدارة البيانات (Admin Panel) =====
    st.markdown("---")
    st.markdown("### ⚙️ لوحة إدارة البيانات (Admin Only)")
    
    with st.expander("🔧 إدارة الفواتير", expanded=False):
        st.subheader("تعديل أو حذف الفواتير")
        orders = get_orders()
        if not orders.empty:
            col1, col2 = st.columns([3, 1])
            with col1:
                selected_order = st.selectbox("اختر فاتورة للتعديل أو الحذف", 
                    [f"{row['Order ID']} - {row['Customer Name']}" for _, row in orders.iterrows()],
                    key="admin_order_select")
            
            if selected_order:
                order_id = selected_order.split(" - ")[0]
                col_edit, col_del = st.columns(2)
                with col_edit:
                    if st.button("✏️ تعديل", key=f"edit_order_{order_id}"):
                        st.info("اختر الحقل والقيمة الجديدة")
                        field = st.selectbox("الحقل المراد تعديله", 
                            ["Customer Name", "Quantity", "Unit Price", "Status"], key=f"field_{order_id}")
                        new_val = st.text_input(f"القيمة الجديدة لـ {field}", key=f"newval_{order_id}")
                        if st.button("حفظ التعديل", key=f"save_{order_id}"):
                            update_order(order_id, field, new_val)
                            st.success("✅ تم التعديل بنجاح")
                            st.rerun()
                
                with col_del:
                    if st.button("🗑️ حذف", key=f"del_order_{order_id}"):
                        delete_order_by_id(order_id)
                        st.success("✅ تم الحذف بنجاح")
                        st.rerun()
    
    with st.expander("📦 إدارة المخزون", expanded=False):
        st.subheader("تعديل أو حذف المخزون")
        stock = get_stock()
        if not stock.empty:
            col1, col2 = st.columns([3, 1])
            with col1:
                selected_product = st.selectbox("اختر منتج", stock["Product"].tolist(), key="admin_stock_select")
            
            if selected_product:
                col_edit, col_del = st.columns(2)
                with col_edit:
                    if st.button("✏️ تعديل الكمية", key=f"edit_stock_{selected_product}"):
                        new_qty = st.number_input("الكمية الجديدة", min_value=0, key=f"newqty_{selected_product}")
                        if st.button("حفظ", key=f"save_stock_{selected_product}"):
                            update_stock(selected_product, new_qty)
                            st.success("✅ تم التعديل بنجاح")
                            st.rerun()
                
                with col_del:
                    if st.button("🗑️ حذف المنتج", key=f"del_stock_{selected_product}"):
                        delete_stock_item(selected_product)
                        st.success("✅ تم الحذف بنجاح")
                        st.rerun()
    
    with st.expander("👥 إدارة الزيارات الميدانية", expanded=False):
        st.subheader("تعديل أو حذف الزيارات")
        visits = get_visits()
        if not visits.empty:
            visit_options = [f"{idx}: {row['Customer Name']} - {row['Potential Qty']} علبة" 
                           for idx, row in visits.iterrows()]
            selected_visit_str = st.selectbox("اختر زيارة", visit_options, key="admin_visit_select")
            
            if selected_visit_str:
                visit_idx = int(selected_visit_str.split(":")[0])
                col_edit, col_del = st.columns(2)
                
                with col_edit:
                    if st.button("✏️ تعديل", key=f"edit_visit_{visit_idx}"):
                        field = st.selectbox("الحقل المراد تعديله", 
                            ["Customer Name", "Potential Qty", "Potential Date", "Notes"], 
                            key=f"field_visit_{visit_idx}")
                        new_val = st.text_input(f"القيمة الجديدة", key=f"newval_visit_{visit_idx}")
                        if st.button("حفظ التعديل", key=f"save_visit_{visit_idx}"):
                            update_visit(visit_idx, field, new_val)
                            st.success("✅ تم التعديل بنجاح")
                            st.rerun()
                
                with col_del:
                    if st.button("🗑️ حذف الزيارة", key=f"del_visit_{visit_idx}"):
                        delete_visit_by_index(visit_idx)
                        st.success("✅ تم الحذف بنجاح")
                        st.rerun()
    
    with st.expander("⚡ خطر - مسح جميع البيانات", expanded=False):
        st.warning("⚠️ هذا الإجراء سيمسح جميع البيانات بشكل نهائي!")
        if st.button("🔥 مسح كل البيانات", key="clear_all"):
            if st.checkbox("أنا متأكد من حذف جميع البيانات", key="confirm_clear"):
                clear_all_data()
                st.error("❌ تم مسح جميع البيانات!")
                st.rerun()
