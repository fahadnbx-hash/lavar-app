import pandas as pd
import streamlit as st
from datetime import datetime

def _get_mock_data(sheet_name):
    if sheet_name == "Orders":
        return pd.DataFrame(columns=["Order ID", "Customer Name", "Product", "Quantity", "Unit Price", "Total Amount", "Status", "Order Date", "Due Date", "Invoice URL", "CR", "Tax", "Address", "Phone"])
    elif sheet_name == "Stock":
        return pd.DataFrame([{"Product": "صابون لآفار 3 لتر", "Quantity": 500}])
    elif sheet_name == "Visits":
        return pd.DataFrame(columns=["Date", "Salesman", "Customer Name", "Visit Type", "Potential Qty", "Potential Date", "Notes"])
    return pd.DataFrame()

def init_db():
    if 'orders_df' not in st.session_state: st.session_state.orders_df = _get_mock_data("Orders")
    if 'stock_df' not in st.session_state: st.session_state.stock_df = _get_mock_data("Stock")
    if 'visits_df' not in st.session_state: st.session_state.visits_df = _get_mock_data("Visits")

def get_orders(): return st.session_state.orders_df
def get_stock(): return st.session_state.stock_df
def get_visits(): return st.session_state.visits_df

def add_order(name, cr, tax, address, phone, prod, qty, days, price):
    new_id = f"ORD{len(st.session_state.orders_df) + 1:03d}"
    due = (datetime.now() + pd.Timedelta(days=days)).strftime("%Y-%m-%d")
    new_row = pd.DataFrame([{"Order ID": new_id, "Customer Name": name, "CR": cr, "Tax": tax, "Address": address, "Phone": phone, "Product": prod, "Quantity": qty, "Unit Price": price, "Total Amount": qty * price, "Status": "Draft", "Order Date": datetime.now().strftime("%Y-%m-%d"), "Due Date": due, "Invoice URL": ""}])
    st.session_state.orders_df = pd.concat([st.session_state.orders_df, new_row], ignore_index=True)

def update_order_status(order_id, status, url=""):
    idx = st.session_state.orders_df[st.session_state.orders_df["Order ID"] == order_id].index
    if not idx.empty:
        st.session_state.orders_df.loc[idx, "Status"] = status
        if url: st.session_state.orders_df.loc[idx, "Invoice URL"] = url

def update_stock_quantity(prod, qty):
    idx = st.session_state.stock_df[st.session_state.stock_df["Product"] == prod].index
    if not idx.empty: st.session_state.stock_df.loc[idx, "Quantity"] = qty

def add_visit(salesman, customer, v_type, pot_qty, pot_date, notes):
    new_v = pd.DataFrame([{"Date": datetime.now().strftime("%Y-%m-%d"), "Salesman": salesman, "Customer Name": customer, "Visit Type": v_type, "Potential Qty": pot_qty, "Potential Date": pot_date, "Notes": notes}])
    st.session_state.visits_df = pd.concat([st.session_state.visits_df, new_v], ignore_index=True)

def delete_order(order_id):
    st.session_state.orders_df = st.session_state.orders_df[st.session_state.orders_df["Order ID"] != order_id].reset_index(drop=True)

def upload_to_github(content, filename): return f"http://mock-drive.com/{filename}"
