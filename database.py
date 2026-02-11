import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, timedelta
import streamlit as st

# إعداد الاتصال بـ Google Sheets باستخدام Secrets من Streamlit
def get_gsheet_client():
    # في Streamlit Cloud، يتم وضع بيانات الاعتماد في Secrets
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    
    # استخراج البيانات من st.secrets (يجب إعدادها في Streamlit Cloud)
    creds_dict = {
        "type": st.secrets["gcp_service_account"]["type"],
        "project_id": st.secrets["gcp_service_account"]["project_id"],
        "private_key_id": st.secrets["gcp_service_account"]["private_key_id"],
        "private_key": st.secrets["gcp_service_account"]["private_key"],
        "client_email": st.secrets["gcp_service_account"]["client_email"],
        "client_id": st.secrets["gcp_service_account"]["client_id"],
        "auth_uri": st.secrets["gcp_service_account"]["auth_uri"],
        "token_uri": st.secrets["gcp_service_account"]["token_uri"],
        "auth_provider_x509_cert_url": st.secrets["gcp_service_account"]["auth_provider_x509_cert_url"],
        "client_x509_cert_url": st.secrets["gcp_service_account"]["client_x509_cert_url"]
    }
    
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    return gspread.authorize(creds)

# اسم ملف Google Sheet
SHEET_NAME = "Lavar_Database"

def init_db():
    try:
        client = get_gsheet_client()
        # محاولة فتح الشيت أو إنشاؤه إذا لم يوجد
        try:
            sh = client.open(SHEET_NAME)
        except gspread.SpreadsheetNotFound:
            sh = client.create(SHEET_NAME)
            # إنشاء ورقة المخزون
            ws_stock = sh.get_worksheet(0)
            ws_stock.update_title("Stock")
            ws_stock.append_row(['Product', 'Quantity', 'Min Limit', 'Price'])
            ws_stock.append_row(['صابون لآفار 3 لتر', 150, 30, 45])
            
            # إنشاء ورقة الطلبات
            ws_orders = sh.add_worksheet(title="Orders", rows="100", cols="20")
            ws_orders.append_row([
                'Order ID', 'Customer Name', 'CR Number', 'Tax Number', 'Address', 
                'Phone', 'Product', 'Quantity', 'Unit Price', 'Total Amount', 
                'Due Date', 'Status', 'Invoice URL', 'Customer Docs'
            ])
        return True
    except Exception as e:
        st.error(f"خطأ في الاتصال بـ Google Sheets: {e}")
        return False

def get_orders():
    client = get_gsheet_client()
    sh = client.open(SHEET_NAME)
    ws = sh.worksheet("Orders")
    data = ws.get_all_records()
    df = pd.DataFrame(data)
    if not df.empty:
        df['Due Date'] = pd.to_datetime(df['Due Date'], errors='coerce')
    return df

def add_order(customer_name, cr_number, tax_number, address, phone, product, quantity, days_to_due, custom_price=None, docs_path='', status='Draft'):
    client = get_gsheet_client()
    sh = client.open(SHEET_NAME)
    ws_orders = sh.worksheet("Orders")
    ws_stock = sh.worksheet("Stock")
    
    # الحصول على السعر
    if custom_price is not None:
        unit_price = custom_price
    else:
        stock_data = ws_stock.get_all_records()
        stock_df = pd.DataFrame(stock_data)
        unit_price = stock_df[stock_df['Product'] == product]['Price'].values[0] if product in stock_df['Product'].values else 0
    
    total_amount = unit_price * quantity
    due_date = datetime.now() + timedelta(days=days_to_due)
    order_id = len(ws_orders.get_all_values())
    
    new_row = [
        order_id, customer_name, cr_number, tax_number, address, 
        phone, product, quantity, unit_price, total_amount, 
        due_date.strftime('%Y-%m-%d'), status, '', docs_path
    ]
    ws_orders.append_row(new_row)
    return order_id

def update_order_status(order_id, status, invoice_url='', docs_path=''):
    client = get_gsheet_client()
    sh = client.open(SHEET_NAME)
    ws = sh.worksheet("Orders")
    cell = ws.find(str(order_id))
    if cell:
        ws.update_cell(cell.row, 12, status) # عمود Status
        if invoice_url:
            ws.update_cell(cell.row, 13, invoice_url) # عمود Invoice URL
        if docs_path:
            ws.update_cell(cell.row, 14, docs_path) # عمود Customer Docs
        return True
    return False

def get_stock():
    client = get_gsheet_client()
    sh = client.open(SHEET_NAME)
    ws = sh.worksheet("Stock")
    return pd.DataFrame(ws.get_all_records())

def update_stock_quantity(product, new_quantity):
    client = get_gsheet_client()
    sh = client.open(SHEET_NAME)
    ws = sh.worksheet("Stock")
    cell = ws.find(product)
    if cell:
        ws.update_cell(cell.row, 2, new_quantity)
        return True
    return False
