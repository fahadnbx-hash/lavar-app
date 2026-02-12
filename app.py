import streamlit as st
import pandas as pd
from database import init_db, get_orders, add_order, update_order_status, get_stock, update_stock_quantity, add_visit, get_visits, delete_visit, delete_order, upload_to_github
from datetime import datetime, date, timedelta
import plotly.express as px
import io
import urllib.parse

# إعداد الصفحة
st.set_page_config(page_title="نظام لآفار للأعمال", layout="wide")
init_db()

# الثوابت
UNIT_COST, LEAD_TIME_DAYS, UNITS_PER_CARTON = 5.0, 9, 6

# تحسينات الواجهة
st.markdown("""
    <style>
    .stApp { text-align: right; direction: rtl; }
    [data-testid="stSidebar"] { text-align: left !important; direction: ltr !important; }
    [data-testid="stSidebar"] * { text-align: right !important; direction: rtl !important; }
    .stMetric { text-align: right; }
    .stMetric label { font-size: 0.7rem !important; }
    .stMetric div { font-size: 1rem !important; }
    </style>
""", unsafe_allow_html=True)

# استمرارية الجلسة
if 'logged_in' not in st.session_state: st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.markdown("<h1 style='text-align: center;'>نظام لآفار للأعمال</h1>", unsafe_allow_html=True)
    with st.container(border=True):
        u = st.text_input("اسم المستخدم")
        p = st.text_input("كلمة المرور", type="password")
        if st.button("دخول للنظام", use_container_width=True):
            if (u == "admin" and p == "lavar2026") or (u == "sales" and p == "lavar_sales") or (u == "acc" and p == "lavar_acc"):
                st.session_state.logged_in, st.session_state.role, st.session_state.user_name = True, u, "المستخدم"
                st.rerun()
            else: st.error("خطأ في البيانات")
    st.stop()

# القائمة الجانبية
with st.sidebar:
    st.markdown("### 🏢 لآفار للمنظفات")
    st.write(f"👤 مرحباً: {st.session_state.user_name}")
    if st.button("🚪 تسجيل الخروج"):
        st.session_state.logged_in = False
        st.rerun()
    pages = ["واجهة الإدارة الذكية", "واجهة المندوب", "واجهة المحاسب"]
    page = st.radio("📌 الانتقال إلى:", pages)

# جلب البيانات
orders, visits, stock_df = get_orders(), get_visits(), get_stock()
current_stock = stock_df.iloc[0]['Quantity'] if not stock_df.empty else 0

# --- واجهة المندوب ---
if page == "واجهة المندوب":
    st.header("📋 واجهة المندوب")
    t1, t2, t3 = st.tabs(["🛒 إدارة الطلبات", "📍 سجل الزيارات", "🧮 الحاسبة"])
    
    with t1:
        with st.container(border=True):
            c1, c2 = st.columns(2)
            with c1:
                name = st.text_input("اسم العميل")
                cr = st.text_input("رقم السجل")
                tax = st.text_input("الرقم الضريبي")
                price = st.number_input("سعر العلبة", value=11.0)
            with c2:
                days = st.number_input("أيام الاستحقاق", value=30)
                qty = st.number_input("الكمية", min_value=1, value=1)
                phone = st.text_input("الجوال")
                addr = st.text_input("العنوان")
            if st.button("تقديم الطلب 🚀"):
                add_order(name, cr, tax, addr, phone, "صابون لآفار 3 لتر", qty, days, price)
                st.success("تم التقديم!"); st.rerun()
        
        st.subheader("🚀 الطلبات الحالية")
        drafts = orders[orders['Status'] == 'Draft']
        if not drafts.empty:
            for i, r in drafts.iterrows():
                with st.container(border=True):
                    col1, col2, col3, col4 = st.columns([4, 2, 1, 1])
                    col1.write(f"**{r['Customer Name']}** | الكمية: {int(r['Quantity'])}")
                    col2.write(f"الإجمالي: {r['Total Amount']} ريال")
                    if col3.button("📤", key=f"s_{r['Order ID']}"):
                        update_order_status(r['Order ID'], 'Pending'); st.rerun()
                    if col4.button("🗑️", key=f"d_{r['Order ID']}"):
                        delete_order(r['Order ID']); st.rerun()
        else: st.info("لا توجد طلبات.")

        st.subheader("✅ الفواتير المعتمدة")
        inv = orders[orders['Status'] == 'Invoiced']
        if not inv.empty:
            for i, r in inv.iterrows():
                with st.container(border=True):
                    ci1, ci2, ci3 = st.columns([4, 2, 2])
                    ci1.write(f"**{r['Customer Name']}** | {int(r['Quantity'])} علبة")
                    if r['Invoice URL']:
                        ci2.link_button("📄 الفاتورة", r['Invoice URL'])
                        msg = urllib.parse.quote(f"فاتورتك من لآفار:\n{r['Invoice URL']}")
                        ci3.link_button("💬 واتساب", f"https://wa.me/{r['Phone']}?text={msg}" )
        else: st.info("لا توجد فواتير.")

    with t2:
        with st.form("v"):
            c1, c2 = st.columns(2)
            cust = c1.text_input("اسم العميل")
            p_qty = c2.number_input("الكمية المتوقعة", value=0)
            p_date = c2.date_input("التاريخ المتوقع")
            if st.form_submit_button("حفظ الزيارة"):
                add_visit(st.session_state.user_name, cust, "دورية", p_qty, str(p_date), "")
                st.success("تم الحفظ!"); st.rerun()
        st.dataframe(visits[visits['Salesman'] == st.session_state.user_name], use_container_width=True)

    with t3:
        c_in = st.number_input("عدد الكراتين", value=0)
        st.info(f"💡 تعادل: {int(c_in * UNITS_PER_CARTON)} علبة")

# --- واجهة المحاسب ---
elif page == "واجهة المحاسب":
    st.header("💰 واجهة المحاسب")
    pending = orders[orders['Status'] == 'Pending']
    if not pending.empty:
        for i, r in pending.iterrows():
            with st.container(border=True):
                cp1, cp2, cp3 = st.columns([4, 3, 1])
                cp1.write(f"**{r['Customer Name']}** | {int(r['Quantity'])} علبة | {r['Total Amount']} ريال")
                pdf = cp2.file_uploader("رفع الفاتورة", type=['pdf'], key=f"p_{r['Order ID']}")
                if pdf and st.button("اعتماد ✅", key=f"b_{r['Order ID']}"):
                    update_stock_quantity(r['Product'], current_stock - r['Quantity'])
                    update_order_status(r['Order ID'], 'Invoiced', upload_to_github(pdf.getvalue(), f"inv_{r['Order ID']}.pdf"))
                    st.success("تم!"); st.rerun()
                if cp3.button("🗑️", key=f"ad_{r['Order ID']}"):
                    delete_order(r['Order ID']); st.rerun()
    else: st.info("لا توجد طلبات معلقة.")
    
    st.divider()
    st.columns([5, 1])[1].link_button("📊 دفترة", "https://xhi.daftra.com/", type="primary" )

# --- واجهة الإدارة ---
elif page == "واجهة الإدارة الذكية":
    st.header("📊 مركز القيادة")
    f1, f2, f3 = st.columns(3)
    f1.metric("📦 المخزون", f"{int(current_stock)} علبة")
    f2.metric("💰 المبيعات", f"{orders[orders['Status']=='Invoiced']['Total Amount'].sum():,.0f} ريال")
    f3.metric("🔮 المتوقع", f"{visits['Potential Qty'].sum():,.0f} علبة")

    t_a, t_b, t_c, t_d = st.tabs(["🧠 التخطيط", "💰 السيولة", "📦 المخزون", "📍 الميدان"])
    
    with t_a:
        st.subheader("🗓️ الإنتاج المتوقع")
        if not visits.empty:
            v = visits.copy(); v['Date'] = pd.to_datetime(v['Date'])
            v['Week'] = v['Date'].dt.to_period('W').apply(lambda r: r.start_time.strftime('%Y-%m-%d'))
            st.plotly_chart(px.bar(v.groupby('Week')['Potential Qty'].sum().reset_index(), x='Week', y='Potential Qty', title="الطلب الأسبوعي"), use_container_width=True)
        else: st.info("لا توجد بيانات.")

    with t_b:
        st.subheader("🎯 المستهدف")
        target = st.number_input("المستهدف", value=5000)
        actual = orders[orders['Status']=='Invoiced']['Quantity'].sum()
        st.progress(min(actual/target, 1.0))
        st.write(f"نسبة الإنجاز: {(actual/target*100):.1f}%")

    with t_c:
        st.subheader("📦 إدارة المخزون")
        new_q = st.number_input("تعديل المخزون", value=int(current_stock))
        if st.button("تحديث"):
            update_stock_quantity("صابون لآفار 3 لتر", new_q); st.success("تم!"); st.rerun()

    with t_d:
        st.subheader("📍 نشاط الميدان")
        if not visits.empty:
            for i, r in visits.iterrows():
                with st.container(border=True):
                    cv1, cv2, cv3 = st.columns([6, 1, 1])
                    cv1.write(f"**{r['Salesman']}** -> {r['Customer Name']} | الكمية: {int(r['Potential Qty'])}")
                    if cv3.button("🗑️", key=f"dv_{i}"):
                        delete_visit(i); st.rerun()
        else: st.info("السجل فارغ.")
