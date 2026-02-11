import pandas as pd
import streamlit as st
from datetime import datetime

def init_db():
    # تهيئة مخازن البيانات في حال عدم وجودها (Session State)
    if 'orders_df' not in st.session_state:
        st.session_state.orders_df = pd.DataFrame(columns=["Order ID", "Customer Name", "Product", "Quantity", "Unit Price", "Total Amount", "Status", "Order Date", "Due Date", "Invoice URL"])
    if 'stock_df' not in st.session_state:
        st.session_state.stock_df = pd.DataFrame([
            {"Product": "صابون لآفار 3 لتر", "Quantity": 500},
            {"Product": "منظف أرضيات 1 لتر", "Quantity": 300},
            {"Product": "معطر جو 500 مل", "Quantity": 150}
        ])
    if 'visits_df' not in st.session_state:
        st.session_state.visits_df = pd.DataFrame(columns=["Date", "Salesman", "Customer Name", "Visit Type", "Potential Qty", "Potential Date", "Notes"])

def get_orders(): return st.session_state.orders_df
def get_stock(): return st.session_state.stock_df
def get_visits(): return st.session_state.visits_df

def add_order(name, cr, tax, address, phone, prod, qty, days, price):
    new_id = f"ORD{len(st.session_state.orders_df) + 1:03d}"
    due = (datetime.now() + pd.Timedelta(days=days)).strftime("%Y-%m-%d")
    new_row = pd.DataFrame([{
        "Order ID": new_id, "Customer Name": name, "Product": prod, "Quantity": qty, 
        "Unit Price": price, "Total Amount": qty * price, "Status": "Draft", 
        "Order Date": datetime.now().strftime("%Y-%m-%d"), "Due Date": due, "Invoice URL": ""
    }])
    st.session_state.orders_df = pd.concat([st.session_state.orders_df, new_row], ignore_index=True)

def update_order_status(order_id, status, url=""):
    idx = st.session_state.orders_df[st.session_state.orders_df["Order ID"] == order_id].index
    if not idx.empty:
        st.session_state.orders_df.loc[idx, "Status"] = status
        if url: st.session_state.orders_df.loc[idx, "Invoice URL"] = url

def update_stock_quantity(product_name, new_qty):
    idx = st.session_state.stock_df[st.session_state.stock_df["Product"] == product_name].index
    if not idx.empty:
        st.session_state.stock_df.loc[idx, "Quantity"] = new_qty

def delete_order(order_id):
    st.session_state.orders_df = st.session_state.orders_df[st.session_state.orders_df["Order ID"] != order_id].reset_index(drop=True)

def add_visit(salesman, customer, v_type, pot_qty, pot_date, notes):
    new_v = pd.DataFrame([{
        "Date": datetime.now().strftime("%Y-%m-%d"), "Salesman": salesman, 
        "Customer Name": customer, "Visit Type": v_type, "Potential Qty": pot_qty, 
        "Potential Date": pot_date, "Notes": notes
    }])
    st.session_state.visits_df = pd.concat([st.session_state.visits_df, new_v], ignore_index=True)

def upload_to_github(content, filename): return f"https://lavar-drive.com/{filename}" # رابط تجريبي
