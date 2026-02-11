import streamlit as st
import pandas as pd
from database import init_db, get_orders, add_order, update_order_status, get_stock, upload_to_github, delete_order, update_stock_quantity, add_visit, get_visits
from datetime import datetime, date, timedelta
import plotly.express as px
import plotly.graph_objects as go

# إعداد الصفحة
st.set_page_config(page_title="نظام لآفار لذكاء الأعمال المتكامل", layout="wide")
init_db()

# الثوابت التشغيلية
UNIT_COST = 5.0
LEAD_TIME_DAYS = 9  # مدة التجهيز في المصنع

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

# القائمة الجانبية
st.sidebar.markdown(f"### 👤 {st.session_state.user_name}")
if st.sidebar.button("🚪 تسجيل الخروج", use_container_width=True):
    st.session_state.logged_in = False
    st.rerun()

# جلب البيانات
orders = get_orders()
visits = get_visits()
stock_df = get_stock()
current_stock = stock_df.iloc[0]['Quantity'] if not stock_df.empty else 0

# --- واجهة الإدارة الشاملة ---
if st.session_state.role == "admin":
    st.header("📊 مركز القيادة والتحكم الاستراتيجي")
    
    # التبويبات الرئيسية (استعادة كافة الخانات السابقة + الإضافات الجديدة)
    tab_strat, tab_sales, tab_stock, tab_visits = st.tabs([
        "🧠 التخطيط ودعم القرار", 
        "💰 المبيعات والسيولة", 
        "📦 إدارة المخزون", 
        "📍 نشاط الميدان"
    ])

    # 1. تبويب التخطيط الاستراتيجي (التطوير الجديد)
    with tab_strat:
        st.subheader("🤖 مستشار لآفار التنفيذي")
        conf = st.slider("🎯 نسبة الثقة في توقعات الميدان (%)", 10, 100, 80)
        
        # معالجة بيانات التوقعات
        v_df = visits.copy()
        if not v_df.empty:
            v_df['Potential Date'] = pd.to_datetime(v_df['Potential Date'])
            v_df['Month'] = v_df['Potential Date'].dt.to_period('M').astype(str)
            v_df['Adj Qty'] = v_df['Potential Qty'] * (conf/100)
            monthly_demand = v_df.groupby('Month')['Adj Qty'].sum().reset_index()
        else:
            monthly_demand = pd.DataFrame(columns=['Month', 'Adj Qty'])

        # قسم التوصيات الذكية
        with st.container(border=True):
            recs = []
            total_pot = monthly_demand['Adj Qty'].sum() if not monthly_demand.empty else 0
            pending_cash = orders[orders['Status'] == 'Pending']['Total Amount'].sum() if not orders.empty else 0
            
            if total_pot > current_stock:
                recs.append(f"🔴 **توصية إنتاج:** فجوة إنتاج قدرها **{int(total_pot - current_stock)}** علبة. ابدأ التصنيع فوراً.")
            elif current_stock > total_pot * 1.5 and total_pot > 0:
                recs.append("🟡 **توصية تسويق:** المخزون مرتفع. ابدأ حملة ترويجية لتسريع السحب.")
            
            if pending_cash > 3000:
                recs.append(f"💸 **توصية تحصيل:** سيولة معلقة بقيمة **{pending_cash:,.0f} ريال**. يجب تسريع الفواتير.")
            
            if not recs: st.write("✅ المؤشرات التشغيلية مستقرة.")
            else:
                for r in recs: st.markdown(r)

        # جدول الإنتاج المتقدم (MPS)
        st.subheader("🗓️ جدول الإنتاج الزمني (قاعدة 9 أيام)")
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
        else: st.info("لا توجد بيانات لبناء الجدول.")

    # 2. تبويب المبيعات والسيولة (استعادة الخانات السابقة)
    with tab_sales:
        st.subheader("💰 تحليل التدفقات النقدية")
        if not orders.empty:
            invoiced = orders[orders['Status'] == 'Invoiced'].copy()
            if not invoiced.empty:
                c1, c2 = st.columns(2)
                with c1: st.metric("إجمالي المبيعات المفوترة", f"{invoiced['Total Amount'].sum():,.2f} ريال")
                with c2: st.metric("عدد الطلبات المنفذة", len(invoiced))
                
                invoiced['Due Date'] = pd.to_datetime(invoiced['Due Date'])
                cash_flow = invoiced.groupby('Due Date')['Total Amount'].sum().sort_index().cumsum().reset_index()
                st.plotly_chart(px.area(cash_flow, x='Due Date', y='Total Amount', title="منحنى السيولة التراكمي"), use_container_width=True)
            else: st.info("لا توجد فواتير مصدرة بعد.")
        else: st.info("لا توجد بيانات مبيعات.")

    # 3. تبويب إدارة المخزون (استعادة خانات التعديل)
    with tab_stock:
        st.subheader("📦 التحكم في المستودع")
        with st.container(border=True):
            st.write(f"**المنتج الحالي:** صابون لآفار 3 لتر")
            new_q = st.number_input("تحديث الكمية الفعلية", value=int(current_stock))
            if st.button("حفظ التعديل"):
                update_stock_quantity("صابون لآفار 3 لتر", new_q)
                st.success("تم التحديث!"); st.rerun()

    # 4. تبويب نشاط الميدان (استعادة سجل الزيارات)
    with tab_visits:
        st.subheader("📍 سجل زيارات المناديب الكامل")
        if not visits.empty:
            st.dataframe(visits, use_container_width=True, hide_index=True)
        else: st.info("السجل فارغ حالياً.")

# --- واجهات المندوب والمحاسب تبقى كما هي لضمان استقرار العمليات ---
