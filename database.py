import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, timedelta
import streamlit as st
import base64
from github import Github

def get_creds():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds_info = st.secrets["gcp_service_account"]
    return ServiceAccountCredentials.from_json_keyfile_dict(creds_info, scope )

SHEET_ID = "11t_voMmPrzPF3r_CrvXpreXOh5eZPEKxFLoTaddp43g"
GITHUB_TOKEN = st.secrets["github_token"]
REPO_NAME = "fahadnbx-hash/lavar-app"

@st.cache_resource
def get_gsheet_client():
    return gspread.authorize(get_creds())

def upload_to_github(file_content, file_name):
    try:
        g = Github(GITHUB_TOKEN)
        repo = g.get_repo(REPO_NAME)
        path = f"invoices/{file_name}"
        repo.create_file(path, f"Upload invoice {file_name}", file_content, branch="main")
        raw_url = f"https://raw.githubusercontent.com/{REPO_NAME}/main/{path}"
        return raw_url
    except Exception as e:
        st.error(f"خطأ في الرفع: {str(e )}")
        return None

@st.cache_data(ttl=5)
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

@st.cache_data(ttl=30)
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
        order_id = datetime.now().strftime("%Y%m%d%H%M%S")
        new_row = [order_id, customer_name, cr_number, tax_number, address, phone, product, quantity, unit_price, total_amount, due_date.strftime('%Y-%m-%d'), status, '', '']
        ws_orders.append_row(new_row)
        st.cache_data.clear()
        return True
    except Exception as e:
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
        return False

def delete_order(order_id):
    try:
        client = get_gsheet_client()
        sh = client.open_by_key(SHEET_ID)
        ws = sh.worksheet("Orders")
        all_values = ws.get_all_values()
        for i, row in enumerate(all_values):
            if str(row[0]) == str(order_id):
                ws.delete_rows(i + 1)
                st.cache_data.clear()
                return True
        return False
    except Exception as e:
        return False

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
                st.cache_data.clear()
                return True
        return False
    except Exception as e:
        return False

def init_db(): return True
