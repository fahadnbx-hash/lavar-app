import streamlit as st
import pandas as pd
from database import init_db, get_orders, add_order, update_order_status, get_stock, upload_to_github, delete_order, update_stock_quantity, add_visit, get_visits
from datetime import datetime, date, timedelta
import plotly.express as px
import plotly.graph_objects as go

# إعداد الصفحة
st.set_page_config(page_title="نظام لآفار لدعم القرار", layout="wide")
init_db()

# --- نظام تسجيل الدخول (يبقى كما هو) ---
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

available_pages = ["واجهة المندوب", "واجهة المحاسب", "واجهة الإدارة"] if st.session_state.role == "admin" else \
                  (["واجهة المحاسب"] if st.session_state.role == "accountant" else ["واجهة المندوب"])
page = st.sidebar.radio("📌 الانتقال إلى:", available_pages)

# --- واجهة المندوب وواجهة المحاسب (تبقى كما هي لضمان الاستقرار) ---
if page == "واجهة المندوب":
    st.header("📋 واجهة المندوب")
    tab1, tab2 = st.tabs(["🛒 إدارة الطلبات", "📍 سجل الزيارات الميدانية"])
    with tab1:
        orders = get_orders()
        stock_df = get_stock()
        with st.expander("➕ إضافة طلب جديد", expanded=True):
            c1, c2 = st.columns(2)
            with c1:
                name = st.text_input("👤 اسم العميل")
                cr = st.text_input("📄 السجل التجاري")
                tax = st.text_input("🔢 الرقم الضريبي")
                address = st.text_input("📍 العنوان")
                phone = st.text_input("📞 رقم الجوال")
            with c2:
                prod_list = stock_df['Product'].tolist() if not stock_df.empty else ["صابون لآفار 3 لتر"]
                prod = st.selectbox("📦 المنتج", prod_list)
                qty = st.number_input("🔢 الكمية", 1, 1000, 1)
                price = st.number_input("💰 سعر العلبة", 0.0, 1000.0, 0.0)
                days = st.number_input("⏳ أيام الاستحقاق", 0, 99, 30)
            if st.button("التالي ➡️", use_container_width=True):
                add_order(name, cr, tax, address, phone, prod, qty, days, price if price > 0 else None)
                st.success("✅ تم حفظ الطلب بنجاح!"); st.rerun()
        st.markdown("---")
        st.subheader("🚀 طلبات بانتظار الاعتماد")
        drafts = orders[orders['Status'] == 'Draft'] if not orders.empty else pd.DataFrame()
        if not drafts.empty:
            for _, row in drafts.iterrows():
                with st.container(border=True):
                    c_i, c_a, c_d = st.columns([3, 1, 0.5])
                    with c_i:
                        st.markdown(f"**العميل:** {row['Customer Name']} | **المنتج:** {row['Product']}")
                        st.caption(f"📦 {row['Quantity']} علبة × {row['Unit Price']} ريال = {row['Total Amount']} ريال")
                    with c_a:
                        if st.button("إرسال للمحاسب 📤", key=f"p_{row['Order ID']}", use_container_width=True):
                            update_order_status(row['Order ID'], 'Pending'); st.rerun()
                    with c_d:
                        if st.button("🗑️", key=f"d_{row['Order ID']}", use_container_width=True):
                            delete_order(row['Order ID']); st.rerun()
        else: st.info("📭 لا توجد طلبات بانتظار الاعتماد")
        st.subheader("✅ فواتير جاهزة للمشاركة")
        inv = orders[orders['Status'] == 'Invoiced'] if not orders.empty else pd.DataFrame()
        if not inv.empty:
            for _, row in inv.iterrows():
                with st.container(border=True):
                    c_i, c_b = st.columns([3, 1])
                    with c_i: st.write(f"**العميل:** {row['Customer Name']} | **المبلغ:** {row['Total Amount']} ريال")
                    with c_b:
                        if row['Invoice URL']: st.link_button("📄 فتح الفاتورة", row['Invoice URL'], use_container_width=True)
        else: st.info("📭 لا توجد فواتير جاهزة")
    with tab2:
        st.subheader("📍 تسجيل زيارة ميدانية")
        with st.form("visit_form", clear_on_submit=True):
            c1, c2 = st.columns(2)
            with c1:
                v_customer = st.text_input("👤 اسم العميل")
                v_type = st.selectbox("📝 نوع الزيارة", ["زيارة دورية", "عميل محتمل جديد", "متابعة شكوى", "تحصيل"])
            with c2:
                pot_qty = st.number_input("🔮 الكمية المتوقعة (علبة)", 0, 10000, 0)
                pot_date = st.date_input("📅 تاريخ الطلب المتوقع", date.today() + timedelta(days=7))
            v_notes = st.text_area("🗒️ ملاحظات الزيارة")
            if st.form_submit_button("💾 حفظ الزيارة", use_container_width=True):
                add_visit(st.session_state.user_name, v_customer, v_type, pot_qty, str(pot_date), v_notes)
                st.success("✅ تم تسجيل الزيارة!"); st.rerun()
        st.markdown("---")
        st.subheader("📜 سجل زياراتك السابقة")
        visits = get_visits()
        if not visits.empty:
            my_v = visits[visits['Salesman'] == st.session_state.user_name].copy()
            if not my_v.empty:
                st.dataframe(my_v[['Date', 'Customer Name', 'Visit Type', 'Potential Qty', 'Potential Date', 'Notes']], use_container_width=True, hide_index=True)
            else: st.info("لم تسجل زيارات بعد")
        else: st.info("السجل فارغ")

elif page == "واجهة المحاسب":
    st.header("💰 واجهة المحاسب")
    orders = get_orders()
    pending = orders[orders['Status'] == 'Pending'] if not orders.empty else pd.DataFrame()
    if not pending.empty:
        for _, row in pending.iterrows():
            with st.container(border=True):
                st.write(f"**طلب #{row['Order ID']}** | العميل: {row['Customer Name']} | المبلغ: {row['Total Amount']} ريال")
                pdf = st.file_uploader("ارفع الفاتورة (PDF)", type=['pdf'], key=f"f_{row['Order ID']}")
                c1, c2 = st.columns([4, 1])
                with c1:
                    if pdf and st.button("✅ اعتماد ورفع", key=f"b_{row['Order ID']}", use_container_width=True):
                        url = upload_to_github(pdf.getvalue(), f"inv_{row['Order ID']}.pdf")
                        if url: update_order_status(row['Order ID'], 'Invoiced', url); st.rerun()
                with c2:
                    if st.button("🗑️", key=f"da_{row['Order ID']}", use_container_width=True):
                        delete_order(row['Order ID']); st.rerun()
    else: st.info("📭 لا توجد طلبات معلقة")

# --- واجهة الإدارة (التطوير الاستراتيجي الجديد) ---
elif page == "واجهة الإدارة":
    st.header("📊 لوحة دعم القرار والإنتاج")
    tab_prod, tab_sales, tab_visits = st.tabs(["🏭 تخطيط الإنتاج الذكي", "💰 المبيعات والسيولة", "📍 مراقبة الميدان"])
    orders = get_orders()
    visits = get_visits()
    
    with tab_prod:
        st.subheader("🎯 خطة الإنتاج الموصى بها (أرباع السنة القادمة)")
        if not visits.empty:
            # معالجة التواريخ
            visits['Potential Date'] = pd.to_datetime(visits['Potential Date'])
            visits['Quarter'] = visits['Potential Date'].dt.to_period('Q').astype(str)
            
            # حساب الإنتاج الموصى به لكل ربع
            q_summary = visits.groupby('Quarter')['Potential Qty'].sum().reset_index()
            
            # إضافة بيانات التدفق النقدي لنفس الأرباع للمقارنة
            if not orders.empty:
                invoiced = orders[orders['Status'] == 'Invoiced'].copy()
                invoiced['Due Date'] = pd.to_datetime(invoiced['Due Date'])
                invoiced['Quarter'] = invoiced['Due Date'].dt.to_period('Q').astype(str)
                cash_summary = invoiced.groupby('Quarter')['Total Amount'].sum().reset_index()
                merged_data = pd.merge(q_summary, cash_summary, on='Quarter', how='outer').fillna(0)
            else:
                merged_data = q_summary
                merged_data['Total Amount'] = 0

            # رسم بياني مزدوج: الإنتاج vs السيولة
            fig = go.Figure()
            fig.add_trace(go.Bar(x=merged_data['Quarter'], y=merged_data['Potential Qty'], name='حجم الإنتاج الموصى به (علبة)', marker_color='blue'))
            fig.add_trace(go.Scatter(x=merged_data['Quarter'], y=merged_data['Total Amount'], name='التدفق النقدي المتوقع (ريال)', yaxis='y2', line=dict(color='green', width=3)))
            
            fig.update_layout(
                title='مواءمة الإنتاج مع التدفقات النقدية',
                xaxis_title='ربع السنة',
                yaxis=dict(title='كمية الإنتاج (علبة)'),
                yaxis2=dict(title='السيولة (ريال)', overlaying='y', side='right'),
                legend=dict(x=0, y=1.1, orientation='h')
            )
            st.plotly_chart(fig, use_container_width=True)

            # جدول دعم القرار
            st.markdown("### 📋 جدول دعم القرار")
            st.table(merged_data.rename(columns={
                'Quarter': 'الفترة (الربع السنوي)',
                'Potential Qty': 'الإنتاج الموصى به (علبة)',
                'Total Amount': 'السيولة المتوفرة للتحصيل (ريال)'
            }))
            
            st.info("💡 **نصيحة النظام:** إذا كانت السيولة المتوفرة (الخط الأخضر) أقل من حجم الإنتاج الموصى به (الأعمدة الزرقاء)، يرجى مراجعة سياسة التحصيل أو تقليل حجم الإنتاج لتجنب عجز السيولة.")
        else:
            st.info("لا توجد بيانات زيارات كافية لبناء خطة الإنتاج.")

    with tab_sales:
        if not orders.empty:
            invoiced = orders[orders['Status'] == 'Invoiced'].copy()
            c1, c2 = st.columns(2)
            c1.metric("💰 إجمالي المبيعات", f"{invoiced['Total Amount'].sum()} ريال")
            c2.metric("⏳ فواتير بانتظار التحصيل", len(invoiced))
            
            st.subheader("📉 تدفقات الكاش حسب تواريخ الاستحقاق")
            invoiced['Due Date'] = pd.to_datetime(invoiced['Due Date'])
            cash_flow = invoiced.groupby('Due Date')['Total Amount'].sum().reset_index()
            fig_cash = px.area(cash_flow, x='Due Date', y='Total Amount', title="منحنى السيولة القادمة")
            st.plotly_chart(fig_cash, use_container_width=True)
            
            st.dataframe(orders, use_container_width=True)
        else: st.info("لا توجد بيانات مبيعات")

    with tab_visits:
        st.subheader("📍 نشاط الميدان والزيارات")
        if not visits.empty:
            st.dataframe(visits, use_container_width=True)
        else: st.info("لا توجد زيارات مسجلة")
