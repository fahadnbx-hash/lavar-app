import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, timedelta
import streamlit as st
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
import io

def get_creds( ):
    """الحصول على بيانات اعتماد Google من Streamlit Secrets"""
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive"
    ]
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
    return ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope )

SHEET_ID = "11t_voMmPrzPF3r_CrvXpreXOh5eZPEKxFLoTaddp43g"

def upload_to_drive(file_content, file_name):
    """رفع ملف PDF إلى Google Drive وإرجاع رابط المشاركة"""
    try:
        creds = get_creds()
        service = build('drive', 'v3', credentials=creds)
        
        # إنشاء بيانات الملف
        file_metadata = {
            'name': file_name,
            'mimeType': 'application/pdf'
        }
        
        # تحويل محتوى الملف إلى BytesIO
        media = MediaIoBaseUpload(
            io.BytesIO(file_content),
            mimetype='application/pdf',
            resumable=True
        )
        
        # رفع الملف
        file = service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id, webViewLink'
        ).execute()
        
        file_id = file.get('id')
        
        # جعل الملف متاحاً للقراءة لأي شخص لديه الرابط
        service.permissions().create(
            fileId=file_id,
            body={'type': 'anyone', 'role': 'reader'}
        ).execute()
        
        # إرجاع رابط المشاركة
        return file.get('webViewLink')
    except Exception as e:
        st.error(f"خطأ في رفع الملف: {str(e)}")
        return None

def get_gsheet_client():
    """الحصول على عميل Google Sheets"""
    return gspread.authorize(get_creds())

def init_db():
    """تهيئة قاعدة البيانات"""
    return True

def get_orders():
    """جلب جميع الطلبات من Google Sheet"""
    try:
        client = get_gsheet_client()
        sh = client.open_by_key(SHEET_ID)
        ws = sh.worksheet("Orders")
        data = ws.get_all_records()
        
        if not data:
            return pd.DataFrame(columns=[
                'Order ID', 'Customer Name', 'CR Number', 'Tax Number',
                'Address', 'Phone', 'Product', 'Quantity', 'Unit Price',
                'Total Amount', 'Due Date', 'Status', 'Invoice URL', 'Customer Docs'
            ])
        
        df = pd.DataFrame(data)
        
        # التأكد من وجود جميع الأعمدة
        required_cols = ['Order ID', 'Customer Name', 'CR Number', 'Tax Number',
                        'Address', 'Phone', 'Product', 'Quantity', 'Unit Price',
                        'Total Amount', 'Due Date', 'Status', 'Invoice URL', 'Customer Docs']
        
        for col in required_cols:
            if col not in df.columns:
                df[col] = ''
        
        # تحويل تاريخ الاستحقاق
        if not df.empty:
            df['Due Date'] = pd.to_datetime(df['Due Date'], errors='coerce')
        
        return df
    except Exception as e:
        st.error(f"خطأ في جلب الطلبات: {str(e)}")
        return pd.DataFrame()

def add_order(customer_name, cr_number, tax_number, address, phone, product, quantity, days_to_due, custom_price=None, docs_path='', status='Draft'):
    """إضافة طلب جديد"""
    try:
        client = get_gsheet_client()
        sh = client.open_by_key(SHEET_ID)
        ws_orders = sh.worksheet("Orders")
        ws_stock = sh.worksheet("Stock")
        
        # جلب سعر المنتج من جدول المخزون
        stock_data = ws_stock.get_all_records()
        stock_df = pd.DataFrame(stock_data)
        
        if custom_price and custom_price > 0:
            unit_price = custom_price
        else:
            matching = stock_df[stock_df['Product'] == product]
            if not matching.empty:
                unit_price = float(matching.iloc[0]['Price'])
            else:
                unit_price = 0
        
        total_amount = unit_price * quantity
        due_date = datetime.now() + timedelta(days=days_to_due)
        
        # حساب رقم الطلب
        all_orders = ws_orders.get_all_values()
        order_id = len(all_orders)
        
        # إضافة الطلب الجديد
        new_row = [
            order_id,
            customer_name,
            cr_number,
            tax_number,
            address,
            phone,
            product,
            quantity,
            unit_price,
            total_amount,
            due_date.strftime('%Y-%m-%d'),
            status,
            '',  # Invoice URL (فارغ في البداية)
            docs_path
        ]
        
        ws_orders.append_row(new_row)
        return order_id
    except Exception as e:
        st.error(f"خطأ في إضافة الطلب: {str(e)}")
        return None

def update_order_status(order_id, status, invoice_url='', docs_path=''):
    """تحديث حالة الطلب"""
    try:
        client = get_gsheet_client()
        sh = client.open_by_key(SHEET_ID)
        ws = sh.worksheet("Orders")
        
        all_values = ws.get_all_values()
        
        for i, row in enumerate(all_values):
            if str(row[0]) == str(order_id):
                row_idx = i + 1
                
                # تحديث الحالة (العمود 12)
                ws.update_cell(row_idx, 12, status)
                
                # تحديث رابط الفاتورة (العمود 13)
                if invoice_url:
                    ws.update_cell(row_idx, 13, invoice_url)
                
                # تحديث مستندات العميل (العمود 14)
                if docs_path:
                    ws.update_cell(row_idx, 14, docs_path)
                
                return True
        
        return False
    except Exception as e:
        st.error(f"خطأ في تحديث الطلب: {str(e)}")
        return False

def get_stock():
    """جلب بيانات المخزون"""
    try:
        client = get_gsheet_client()
        sh = client.open_by_key(SHEET_ID)
        ws = sh.worksheet("Stock")
        data = ws.get_all_records()
        
        if not data:
            return pd.DataFrame(columns=['Product', 'Quantity', 'Min Limit', 'Price'])
        
        return pd.DataFrame(data)
    except Exception as e:
        st.error(f"خطأ في جلب المخزون: {str(e)}")
        return pd.DataFrame()

def update_stock_quantity(product, new_quantity):
    """تحديث كمية المنتج في المخزون"""
    try:
        client = get_gsheet_client()
        sh = client.open_by_key(SHEET_ID)
        ws = sh.worksheet("Stock")
        
        all_values = ws.get_all_values()
        
        for i, row in enumerate(all_values):
            if row[0] == product:
                ws.update_cell(i + 1, 2, new_quantity)
                return True
        
        return False
    except Exception as e:
        st.error(f"خطأ في تحديث المخزون: {str(e)}")
        return False
