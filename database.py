import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, timedelta
import streamlit as st
import io

# استيراد مكتبات جوجل بطريقة آمنة
try:
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaIoBaseUpload
except ImportError:
    st.error("جاري تحميل مكتبات إضافية... يرجى عمل Reboot للتطبيق" )

def get_creds():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds_info = st.secrets["gcp_service_account"]
    return ServiceAccountCredentials.from_json_keyfile_dict(creds_info, scope )

SHEET_ID = "11t_voMmPrzPF3r_CrvXpreXOh5eZPEKxFLoTaddp43g"
FOLDER_ID = "1Ggs1BCHsnBwCx3A3uB1y2USPoqKGsViI" # المجلد الذي أنشأته

@st.cache_resource
def get_gsheet_client():
    return gspread.authorize(get_creds())

@st.cache_data(ttl=10)
def get_orders():
    try:
        client = get_gsheet_client()
        sh = client.open_by_key(SHEET_ID)
        ws = sh.worksheet("Orders")
        data = ws.get_all_records()
        if not data: return pd.DataFrame()
        df = pd.DataFrame(data)
        if not df.empty and 'Due Date' in df.columns:
            df['Due Date'] = pd.to_datetime(df['Due Date'], errors='coerce')
        return df
    except Exception as e:
        return pd.DataFrame()

@st.cache_data(ttl=60)
def get_stock():
    try:
        client = get_gsheet_client()
        sh = client.open_by_key(SHEET_ID)
        ws = sh.worksheet("Stock")
        data = ws.get_all_records()
        return pd.DataFrame(data) if data else pd.DataFrame()
    except Exception as e:
        return pd.DataFrame()

def add_order(customer_name, cr_number, tax_number, address, phone, product, quantity, days_to_due, custom_price=None, status='Draft'):
    try:
        client = get_gsheet_client()
        sh = client.open_by_key(SHEET_ID)
        ws_orders = sh.worksheet("Orders")
        ws_stock = sh.worksheet("Stock")
        stock_df = pd.DataFrame(ws_stock.get_all_records())
        
        unit_price = custom_price if custom_price and custom_price > 0 else (stock_df[stock_df['Product'] == product]['Price'].values[0] if product in stock_df['Product'].values else 0)
        total_amount = float(unit_price) * int(quantity)
        due_date = datetime.now() + timedelta(days=int(days_to_due))
        order_id = len(ws_orders.get_all_values())
        
        new_row = [order_id, customer_name, cr_number, tax_number, address, phone, product, quantity, unit_price, total_amount, due_date.strftime('%Y-%m-%d'), status, '', '']
        ws_orders.append_row(new_row)
        st.cache_data.clear()
        return True
    except Exception as e:
        st.error(f"خطأ في الإضافة: {str(e)}")
        return False

def update_order_status(order_id, status, invoice_url=''):
    try:
        client = get_gsheet_client()
        sh = client.open_by_key(SHEET_ID)
        ws = sh.worksheet("Orders")
        all_values = ws.get_all_values()
        for i, row in enumerate(all_values):
            if str(row[0]) == str(order_id):
                ws.update_cell(i + 1, 12, status)
                if invoice_url: ws.update_cell(i + 1, 13, invoice_url)
                st.cache_data.clear()
                return True
        return False
    except Exception as e:
        st.error(f"خطأ في التحديث: {str(e)}")
        return False

def upload_to_drive(file_content, file_name):
    try:
        creds = get_creds()
        from googleapiclient.discovery import build
        service = build('drive', 'v3', credentials=creds)
        
        file_metadata = {
            'name': file_name, 
            'mimeType': 'application/pdf',
            'parents': [FOLDER_ID]
        }
        
        media = MediaIoBaseUpload(io.BytesIO(file_content), mimetype='application/pdf', resumable=True)
        file = service.files().create(body=file_metadata, media_body=media, fields='id, webViewLink').execute()
        
        # جعل الملف متاحاً للقراءة
        service.permissions().create(fileId=file.get('id'), body={'type': 'anyone', 'role': 'reader'}).execute()
        
        return file.get('webViewLink')
    except Exception as e:
        st.error(f"خطأ في الرفع: {str(e)}")
        return None

def update_stock_quantity(product, new_quantity):
    try:
        client = get_gsheet_client()
        sh = client.open_by_key(SHEET_ID)
        ws = sh.worksheet("Stock")
        all_values = ws.get_all_values()
        for i, row in enumerate(all_values):
            if row[0] == product:
                ws.update_cell(i + 1, 2, new_quantity)
                st.cache_data.clear()
                return True
        return False
    except Exception as e:
        return False

def init_db(): return True
