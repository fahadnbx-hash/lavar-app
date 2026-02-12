import pandas as pd
import streamlit as st
from datetime import datetime

# إعداد البيانات الأولية
def _get_mock_data(sheet_name):
    if sheet_name == "Orders":
        return pd.DataFrame(columns=["Order ID", "Customer Name", "CR", "Tax", "Address", "Phone", "Product", "Quantity", "Unit Price", "Total Amount", "Status", "Order Date", "Due Date", "Invoice URL"])
    elif sheet_name == "Stock":
        return pd.DataFrame({"Product": ["صابون لآفار 3 لتر"], "Quantity": [5000]})
    elif sheet_name == "Visits":
        return pd.DataFrame(columns=["Date", "Salesman", "Customer Name", "Potential Qty", "Potential Date", "Notes"])
    elif sheet_name == "Settings":
        return pd.DataFrame({"Setting": ["annual_target"], "Value": [60000]})
    return pd.DataFrame()

def init_db():
    if 'orders_df' not in st.session_state: st.session_state.orders_df = _get_mock_data("Orders")
    if 'stock_df' not in st.session_state: st.session_state.stock_df = _get_mock_data("Stock")
    if 'visits_df' not in st.session_state: st.session_state.visits_df = _get_mock_data("Visits")
    if 'settings_df' not in st.session_state: st.session_state.settings_df = _get_mock_data("Settings")

def get_orders(): return st.session_state.orders_df
def get_stock(): return st.session_state.stock_df
def get_visits(): return st.session_state.visits_df
def get_annual_target():
    settings_df = st.session_state.settings_df
    target_row = settings_df[settings_df["Setting"] == "annual_target"]
    if not target_row.empty:
        return int(target_row["Value"].iloc[0])
    return 60000 # القيمة الافتراضية

def update_annual_target(new_target):
    settings_df = st.session_state.settings_df
    idx = settings_df[settings_df["Setting"] == "annual_target"].index
    if not idx.empty:
        settings_df.loc[idx, "Value"] = new_target
    else:
        new_setting = pd.DataFrame([{"Setting": "annual_target", "Value": new_target}])
        st.session_state.settings_df = pd.concat([settings_df, new_setting], ignore_index=True)

def add_order(name, cr, tax, address, phone, prod, qty, days, price):
    new_id = f"ORD{len(st.session_state.orders_df) + 1:03d}"
    due = (datetime.now() + pd.Timedelta(days=days)).strftime("%Y-%m-%d")
    new_order = pd.DataFrame([{"Order ID": new_id, "Customer Name": name, "CR": cr, "Tax": tax, "Address": address, "Phone": phone, "Product": prod, "Quantity": qty, "Unit Price": price, "Total Amount": qty * price, "Status": "Draft", "Order Date": datetime.now().strftime("%Y-%m-%d"), "Due Date": due, "Invoice URL": ""}])
    st.session_state.orders_df = pd.concat([st.session_state.orders_df, new_order], ignore_index=True)

def update_order_status(order_id, status, url=""):
    idx = st.session_state.orders_df[st.session_state.orders_df["Order ID"] == order_id].index
    if not idx.empty:
        st.session_state.orders_df.loc[idx, "Status"] = status
        if url: st.session_state.orders_df.loc[idx, "Invoice URL"] = url

def delete_order(order_id):
    st.session_state.orders_df = st.session_state.orders_df[st.session_state.orders_df["Order ID"] != order_id].reset_index(drop=True)

def update_stock_quantity(prod, qty):
    idx = st.session_state.stock_df[st.session_state.stock_df["Product"] == prod].index
    if not idx.empty: st.session_state.stock_df.loc[idx, "Quantity"] = qty

def add_visit(salesman, customer, pot_qty, pot_date, notes):
    new_v = pd.DataFrame([{"Date": datetime.now().strftime("%Y-%m-%d"), "Salesman": salesman, "Customer Name": customer, "Potential Qty": pot_qty, "Potential Date": pot_date, "Notes": notes}])
    st.session_state.visits_df = pd.concat([st.session_state.visits_df, new_v], ignore_index=True)

def delete_visit(index):
    if index in st.session_state.visits_df.index:
        st.session_state.visits_df = st.session_state.visits_df.drop(index).reset_index(drop=True)

def upload_to_github(content, filename): return f"https://raw.githubusercontent.com/mock/inv/{filename}"
