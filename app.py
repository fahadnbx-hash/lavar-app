# --- في واجهة المندوب (إضافة قسم الطلبات المكتملة) ---
st.subheader("✅ الطلبات المفوترة (جاهزة للتسليم)")
invoiced_orders = orders[orders['Status'] == 'Invoiced']
for _, row in invoiced_orders.iterrows():
    with st.container(border=True):
        st.write(f"**العميل:** {row['Customer Name']} | **المبلغ:** {row['Total Amount']} ريال")
        # زر يفتح الملف المرفوع مباشرة
        if row['Invoice URL']:
            st.link_button("📄 فتح الفاتورة لإرسالها للعميل", row['Invoice URL'])
        else:
            st.warning("الفاتورة لم ترفع بعد")
