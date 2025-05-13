
import streamlit as st  # streamlit: for creating the web app.
import pandas as pd    # pandas: for data handling (tables, filtering).
import matplotlib.pyplot as plt  # matplotlib.pyplot & seaborn: for static charts (pie, line, bar).
import seaborn as sns  # seaborn: for static charts (pie, line, bar).
import sqlite3   # sqlite3: to interact with the local database
import hashlib  #hashlib: for secure password hashing.
import plotly.express as px  # plotly.express: included but not actively used in this version.


# ---------- DATABASE SETUP ----------
conn = sqlite3.connect('data.db', check_same_thread=False)
c = conn.cursor()

# Create tables if not already present
def create_users_table():
    c.execute('CREATE TABLE IF NOT EXISTS users(username TEXT, password TEXT)')

def create_expense_table():
    c.execute('''CREATE TABLE IF NOT EXISTS expenses(
                 username TEXT, Date TEXT, Category TEXT, Description TEXT, Amount REAL)''')

def create_budget_table():
    c.execute('''CREATE TABLE IF NOT EXISTS budgets(
                 username TEXT, Category TEXT, Budget REAL)''')

# ---------- AUTHENTICATION ----------
def add_user(username, password):
    c.execute('INSERT INTO users(username, password) VALUES (?,?)', (username, password))
    conn.commit()

def login_user(username, password):
    c.execute('SELECT * FROM users WHERE username = ? AND password = ?', (username, password))
    return c.fetchone()

# ---------- EXPENSE MANAGEMENT ----------
def add_expense(username, date, category, desc, amount):
    c.execute('INSERT INTO expenses VALUES (?,?,?,?,?)', (username, date, category, desc, amount))
    conn.commit()

def get_expenses(username):
    c.execute('SELECT Date, Category, Description, Amount FROM expenses WHERE username=?', (username,))
    data = c.fetchall()
    df = pd.DataFrame(data, columns=['Date', 'Category', 'Description', 'Amount'])
    return df

# ---------- BUDGET MANAGEMENT ----------
def set_budget(username, category, budget):
    c.execute('REPLACE INTO budgets(username, Category, Budget) VALUES (?,?,?)', (username, category, budget))
    conn.commit()

def get_budgets():
    c.execute('SELECT Category, Budget FROM budgets')
    return pd.DataFrame(c.fetchall(), columns=['Category', 'Budget'])

# ---------- PASSWORD HASHING ----------
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def check_password(hashed, user_pass):
    return hashed == hashlib.sha256(user_pass.encode()).hexdigest()

# ---------- STREAMLIT APP CONFIG ----------
st.set_page_config(page_title="Finance Dashboard", layout="wide")
st.title("💸 Personal Finance Dashboard")

menu = ["Login", "SignUp"]
choice = st.sidebar.selectbox("Menu", menu)

# Session state for login tracking
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'username' not in st.session_state:
    st.session_state.username = ""

# Initialize tables
create_users_table()
create_expense_table()
create_budget_table()

# ---------- USER AUTH UI ----------
if choice == "SignUp":
    st.subheader("Create New Account")
    new_user = st.text_input("Username")
    new_pass = st.text_input("Password", type='password')
    if st.button("Signup"):
        hashed_pass = hash_password(new_pass)
        add_user(new_user, hashed_pass)
        st.success("Account Created. Go to Login")

elif choice == "Login":
    st.subheader("Login")
    user = st.text_input("Username")
    passwd = st.text_input("Password", type='password')
    if st.button("Login"):
        hashed = hash_password(passwd)
        result = login_user(user, hashed)
        if result:
            st.session_state.logged_in = True
            st.session_state.username = user
        else:
            st.error("Invalid Credentials")

# ---------- MAIN DASHBOARD ----------
if st.session_state.logged_in:
    st.sidebar.success(f"Logged in as {st.session_state.username}")

    # --- ADD EXPENSE FORM ---
    with st.expander("➕ Add Expense"):
        date = st.date_input("Date")
        category = st.selectbox("Category", ["Food", "Transport", "Shopping", "Health", "Other"], key="add_category")
        desc = st.text_input("Description")
        amount = st.number_input("Amount", min_value=0.0)
        if st.button("Add Expense"):
            add_expense(st.session_state.username, date.strftime('%Y-%m-%d'), category, desc, amount)
            st.success("Expense Added")

    # --- SET BUDGET FORM ---
    with st.expander("💰 Set Budget"):
        cat = st.selectbox("Category", ["Food", "Transport", "Shopping", "Health", "Other"], key="budget_category")
        budget_amt = st.number_input("Set Monthly Budget", min_value=0.0)
        if st.button("Set Budget"):
            set_budget(st.session_state.username, cat, budget_amt)
            st.success("Budget Set")

    st.markdown("---")

    # --- SHOW EXPENSES TABLE ---
    expense_df = get_expenses(st.session_state.username)
    st.subheader("📜 Expense History")
    st.dataframe(expense_df)

    # --- VISUALIZATION FUNCTION ---
    def visualize_expenses(df):
        st.subheader("📊 Spending Analysis")

        if df.empty:
            st.info("No data available for visualization.")
            return

        tab1, tab2, tab3 = st.tabs(["Category Distribution", "Monthly Trend", "Budget vs Actual"])

        # PIE CHART - Category-wise spending
        with tab1:
            category_data = df.groupby('Category')['Amount'].sum()
            if category_data.empty or category_data.sum() == 0:
                st.warning("No category data available for pie chart.")
            else:
                fig, ax = plt.subplots(figsize=(4, 4))  # Smaller pie chart
                category_data.plot.pie(autopct='%1.1f%%', ax=ax)
                ax.set_ylabel("")  # Hide y-label
                st.pyplot(fig, use_container_width=False)  # Prevent full-width stretch

        # LINE CHART - Monthly spending trend
        with tab2:
            df['Date'] = pd.to_datetime(df['Date'])
            monthly = df.resample('M', on='Date')['Amount'].sum()
            if monthly.empty:
                st.warning("Not enough data to show monthly trend.")
            else:
                fig, ax = plt.subplots(figsize=(6, 4))  # Smaller line chart
                monthly.plot(kind='line', marker='o', ax=ax)
                plt.title('Monthly Spending Trend')
                plt.xlabel('Month')
                plt.ylabel('Amount')
                st.pyplot(fig, use_container_width=False)

        # BAR CHART - Budget vs Actual
        with tab3:
            budget_df = get_budgets()
            if budget_df.empty:
                st.warning("No budgets set.")
            else:
                merged = df.groupby('Category')['Amount'].sum().reset_index().merge(
                    budget_df, on='Category', how='right'
                ).fillna(0)

                if merged.empty:
                    st.warning("No budget comparison data.")
                else:
                    merged['Percentage'] = merged['Amount'] / merged['Budget'] * 100
                    fig, ax = plt.subplots(figsize=(6, 4))  # Smaller bar chart
                    sns.barplot(x='Category', y='Percentage', data=merged, ax=ax)
                    plt.axhline(100, color='red', linestyle='--')  # Reference line for 100%
                    plt.title('Budget Utilization (%)')
                    plt.ylabel('Utilization (%)')
                    st.pyplot(fig, use_container_width=False)

    # Call the visualization function
    visualize_expenses(expense_df)

