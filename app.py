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

# 2. تحسينات الواجهة (CSS)
st.markdown("""
    <style>
    .stApp { text-align: right; direction: rtl; }
    section[data-testid="stSidebar"] { left: 0 !important; right: auto !important; text-align: right !important; direction: rtl !important; }
    section.main { margin-left: 0 !important; }
    .stMetric { text-align: right; }
    .stMetric label { font-size: 0.75rem !important; color: #666; }
    .stMetric div { font-size: 1.1rem !important; font-weight: bold; }
    .main-title { color: #2E7D32; text-align: center; margin-bottom: 20px; }
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

# 4. القائمة الجانبية (يسار)
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
                        c_i3.link_button("💬 واتساب", wa_url, use_container_width=True )
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
    f1, f2, f3, f4 = st.columns(4)
    f1.metric("📦 المخزون", f"{int(current_stock)} علبة")
    f2.metric("💰 المبيعات", f"{sales_total:,.0f} ريال")
    f3.metric("🔮 طلبات متوقعة", f"{int(potential_qty)} علبة")
    f4.metric("🏭 تكلفة الإنتاج", f"{potential_qty * UNIT_COST:,.0f} ريال")

    t_a, t_b, t_c, t_d = st.tabs(["🧠 التخطيط", "💰 السيولة", "📦 المخزون", "📍 نشاط الميدان"])
    
    with t_a:
        st.subheader("📅 تكلفة الإنتاج الأسبوعية المتوقعة")
        if not visits.empty:
            v_plot = visits.copy()
            v_plot['Date'] = pd.to_datetime(v_plot['Date'])
            v_plot['Week'] = v_plot['Date'].dt.to_period('W').apply(lambda r: r.start_time)
            w_data = v_plot.groupby('Week')['Potential Qty'].sum().reset_index()
            w_data['Cost'] = w_data['Potential Qty'] * UNIT_COST
            w_data['Date_Str'] = w_data['Week'].dt.strftime('%Y-%m-%d')
            st.plotly_chart(px.bar(w_data, x='Date_Str', y='Cost', title="التكلفة المتوقعة أسبوعياً"), use_container_width=True)
        else: st.info("📊 لا توجد بيانات للرسم البياني.")

    with t_b:
        st.subheader("🎯 مبيعات المستهدف")
        target_val = st.number_input("أدخل المبيعات المستهدفة (علبة)", value=5000)
        actual_val = invoiced_adm['Quantity'].sum() if not invoiced_adm.empty else 0
        percent = (actual_val/target_val*100) if target_val > 0 else 0
        st.write(f"📊 نسبة تحقيق المستهدف: **{percent:.1f}%**")
        st.progress(min(actual_val/target_val, 1.0))

    with t_c:
        st.subheader("📦 إدارة المخزون")
        st.metric("المخزون الحالي", f"{int(current_stock)} علبة")
        new_q = st.number_input("تعديل كمية المخزون يدوياً", value=int(current_stock))
        if st.button("تحديث الكمية"):
            update_stock_quantity("صابون لآفار 3 لتر", new_q); st.success("✅ تم التحديث!"); st.rerun()

    with t_d:
        st.subheader("📍 إدارة نشاط الميدان")
        with st.container(border=True):
            h1, h2, h3, h4, h5, h6 = st.columns([1.5, 2, 1.5, 1.5, 2.5, 1])
            h1.write("**المندوب**"); h2.write("**العميل**"); h3.write("**التاريخ**"); h4.write("**الكمية**"); h5.write("**مؤشر الثقة الذكي**"); h6.write("**الإجراء**")
            st.divider()
            if not visits.empty:
                for i, r in visits.iterrows():
                    cv1, cv2, cv3, cv4, cv5, cv6 = st.columns([1.5, 2, 1.5, 1.5, 2.5, 1])
                    cv1.write(r['Salesman'])
                    cv2.write(r['Customer Name'])
                    cv3.write(r['Date'])
                    cv4.write(f"{int(r['Potential Qty'])} علبة")
                    
                    # مؤشر الثقة الذكي للمدير فقط
                    # حساب تلقائي بناءً على معطيات الزيارة
                    auto_conf = 50
                    if r['Visit Type'] == "عميل جديد": auto_conf += 20
                    if r['Potential Qty'] > 500: auto_conf += 10
                    days_diff = (pd.to_datetime(r['Potential Date']) - pd.to_datetime(r['Date'])).days
                    if days_diff < 10: auto_conf += 15
                    auto_conf = min(100, auto_conf)
                    
                    with cv5:
                        st.slider("مؤشر الثقة", 0, 100, auto_conf, key=f"conf_{i}", disabled=False)
                    
                    if cv6.button("حذف 🗑️", key=f"adm_del_{i}"):
                        delete_visit(i); st.rerun()
            else: st.info("ℹ️ لا توجد سجلات حالياً.")
