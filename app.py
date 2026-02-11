import streamlit as st
import pandas as pd
from database import init_db, get_orders, add_order, update_order_status, get_stock, upload_to_github, delete_order, update_stock_quantity, add_visit, get_visits
from datetime import datetime, date, timedelta
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(page_title="نظام لآفار لذكاء الأعمال", layout="wide")
init_db()

# الثوابت التشغيلية
UNIT_COST = 5.0
LEAD_TIME_DAYS = 9  # مدة التجهيز في المصنع

# --- نظام الدخول (ثابت) ---
if 'logged_in' not in st.session_state: st.session_state.logged_in = False
if not st.session_state.logged_in:
    st.title("🔐 تسجيل الدخول - لآفار")
    user = st.text_input("اسم المستخدم")
    password = st.text_input("كلمة المرور", type="password")
    if st.button("دخول"):
        if user == "admin" and password == "lavar2026": st.session_state.logged_in, st.session_state.role, st.session_state.user_name = True, "admin", "المدير العام"
        elif user == "acc" and password == "lavar_acc": st.session_state.logged_in, st.session_state.role, st.session_state.user_name = True, "accountant", "المحاسب"
        elif user == "sales" and password == "lavar_sales": st.session_state.logged_in, st.session_state.role, st.session_state.user_name = True, "sales", "المندوب"
        st.rerun()
    st.stop()

# جلب البيانات
orders = get_orders()
visits = get_visits()
stock_df = get_stock()
current_stock = stock_df.iloc[0]['Quantity'] if not stock_df.empty else 0

# --- واجهة الإدارة الاستراتيجية ---
if st.session_state.role == "admin":
    st.sidebar.markdown(f"### 👤 {st.session_state.user_name}")
    page = st.sidebar.radio("📌 القائمة الاستراتيجية:", ["لوحة التخطيط ودعم القرار", "إدارة العمليات", "واجهة المندوب"])
    
    if page == "لوحة التخطيط ودعم القرار":
        st.header("🧠 محرك التخطيط الاستراتيجي المتقدم")
        
        # 1. إعدادات المحاكاة
        conf = st.sidebar.slider("🎯 نسبة الثقة في توقعات الميدان (%)", 10, 100, 80)
        
        # 2. معالجة البيانات (توقعات الزيارات)
        v_df = visits.copy()
        if not v_df.empty:
            v_df['Potential Date'] = pd.to_datetime(v_df['Potential Date'])
            v_df['Month'] = v_df['Potential Date'].dt.to_period('M').astype(str)
            v_df['Adj Qty'] = v_df['Potential Qty'] * (conf/100)
            monthly_demand = v_df.groupby('Month')['Adj Qty'].sum().reset_index()
        else:
            monthly_demand = pd.DataFrame(columns=['Month', 'Adj Qty'])

        # 3. مستشار لآفار الذكي (التوصيات التنفيذية)
        st.subheader("🤖 المستشار التنفيذي الذكي")
        with st.container(border=True):
            recs = []
            # تحليل سرعة السحب والمخزون
            total_pot = monthly_demand['Adj Qty'].sum() if not monthly_demand.empty else 0
            pending_invoices = orders[orders['Status'] == 'Pending']['Total Amount'].sum() if not orders.empty else 0
            
            if total_pot > current_stock:
                recs.append(f"🔴 **خطر نفاد:** الطلب المتوقع ({int(total_pot)}) أكبر من المخزون ({int(current_stock)}). فجوة الإنتاج: **{int(total_pot - current_stock)}** علبة.")
            elif current_stock > total_pot * 2 and total_pot > 0:
                recs.append("🟡 **تنبيه فائض:** المخزون يغطي ضعف الطلب المتوقع. **التوصية:** تكثيف التسويق أو تقديم عروض (باقة التوفير) لزيادة سرعة السحب.")
            
            if pending_invoices > 5000:
                recs.append(f"💸 **تنبيه سيولة:** هناك **{pending_invoices:,.0f} ريال** معلقة لدى المحاسب. **التوصية:** تسريع إصدار الفواتير لتحصيل السيولة اللازمة للإنتاج.")
            
            if not recs: st.write("✅ الحالة التشغيلية مستقرة.")
            else:
                for r in recs: st.markdown(r)

        # 4. جدول الإنتاج الزمني المخطط (MPS)
        st.subheader("🗓️ جدول الإنتاج الزمني المقترح")
        if not monthly_demand.empty:
            mps = monthly_demand.copy()
            # حساب الإنتاج المطلوب بعد خصم المخزون (توزيع المخزون على الشهور)
            temp_stock = current_stock
            required_prod = []
            for qty in mps['Adj Qty']:
                needed = max(0, qty - temp_stock)
                temp_stock = max(0, temp_stock - qty)
                required_prod.append(needed)
            
            mps['الإنتاج المطلوب'] = required_prod
            mps['تاريخ الجاهزية'] = mps['Month'].apply(lambda x: pd.to_datetime(str(x)).strftime('%Y-%m-01'))
            mps['تاريخ بدء الإنتاج'] = mps['Month'].apply(lambda x: (pd.to_datetime(str(x)) - timedelta(days=LEAD_TIME_DAYS)).strftime('%Y-%m-%d'))
            
            st.table(mps[['Month', 'Adj Qty', 'الإنتاج المطلوب', 'تاريخ بدء الإنتاج', 'تاريخ الجاهزية']].rename(columns={
                'Month': 'الشهر', 'Adj Qty': 'الطلب المتوقع', 'Adj Qty': 'إجمالي الطلب'
            }))
            st.info(f"💡 ملاحظة: تم احتساب تاريخ بدء الإنتاج بناءً على مدة تجهيز **{LEAD_TIME_DAYS} أيام** قبل بداية كل شهر.")
        else: st.info("لا توجد توقعات زيارات حالياً لبناء جدول الإنتاج.")

        # 5. الرسوم البيانية
        c1, c2 = st.columns(2)
        with c1:
            # رسم بياني للسيولة vs تكلفة الإنتاج
            if not monthly_demand.empty:
                fig_fin = go.Figure()
                prod_costs = mps['الإنتاج المطلوب'] * UNIT_COST
                fig_fin.add_trace(go.Bar(x=mps['Month'], y=prod_costs, name='ميزانية الإنتاج المطلوبة', marker_color='red'))
                st.plotly_chart(fig_fin, use_container_width=True)
        with c2:
            st.subheader("📈 معدل السحب الشهري")
            if not monthly_demand.empty:
                st.plotly_chart(px.line(monthly_demand, x='Month', y='Adj Qty', markers=True), use_container_width=True)

    elif page == "إدارة العمليات":
        st.header("📦 إدارة المخزون والطلبات")
        # قسم تعديل المخزون
        with st.container(border=True):
            st.subheader("🛠️ تحديث المخزون الحالي")
            new_q = st.number_input("الكمية الفعلية في المستودع", value=int(current_stock))
            if st.button("تحديث الكمية"):
                update_stock_quantity("صابون لآفار 3 لتر", new_q)
                st.success("تم تحديث المخزون!"); st.rerun()
        
        # قسم الطلبات المعلقة
        st.subheader("📥 الطلبات بانتظار المحاسب")
        pending = orders[orders['Status'] == 'Pending'] if not orders.empty else pd.DataFrame()
        if not pending.empty:
            st.dataframe(pending[['Order ID', 'Customer Name', 'Total Amount', 'Order Date']], use_container_width=True)
        else: st.info("لا توجد طلبات معلقة.")

# --- واجهات المندوب والمحاسب (تبقى مستقرة) ---
