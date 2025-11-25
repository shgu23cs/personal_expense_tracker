import streamlit as st
import json
import matplotlib.pyplot as plt
from streamlit_option_menu import option_menu
from pathlib import Path
import pandas as pd
from datetime import date, datetime

# ----------------- CONFIG -----------------
st.set_page_config(page_title="Personal Expense Tracker", page_icon="💰")
st.title("")  # Clear default title

# Monthly budget
MONTHLY_BUDGET = 10000  # ₹10,000, change as needed

# Path Settings
current_dir = Path(__file__).parent if "__file__" in locals() else Path.cwd()
css_file = current_dir / "styles" / "main.css"
data_file = current_dir / "data.json"

# Optional: apply CSS
if css_file.exists():
    with open(css_file) as f:
        st.markdown("<style>{}</style>".format(f.read()), unsafe_allow_html=True)

# Initialize session state
if "expenses" not in st.session_state:
    st.session_state.expenses = []

# Load existing data from JSON
if data_file.exists():
    with open(data_file, "r") as f:
        st.session_state.expenses = json.load(f)

# ----------------- SIDEBAR NAVIGATION -----------------
selected = option_menu(
    menu_title=None,
    options=["Add Expense", "Overview", "Visualization"],
    icons=["pencil-fill", "clipboard2-data", "bar-chart-fill"],
    orientation="horizontal",
)

# Categories for personal expenses
categories = ["Housing", "Food", "Transportation", "Entertainment", "Medical", "Subscriptions", "Miscellaneous"]

# ----------------- ADD EXPENSE -----------------
if selected == "Add Expense":
    st.header("Add a Personal Expense")
    with st.form("expense_form"):
        expense_category = st.selectbox("Category", categories)
        expense_description = st.text_input("Description (optional)").title()
        expense_value = st.number_input("Amount", min_value=0.0, format="%.2f")
        expense_date = st.date_input("Date", value=date.today())
        submitted = st.form_submit_button("Add Expense")
        
        if submitted:
            new_expense = {
                "category": expense_category,
                "description": expense_description,
                "value": expense_value,
                "date": str(expense_date),
            }
            st.session_state.expenses.append(new_expense)
            # Save to JSON
            with open(data_file, "w") as f:
                json.dump(st.session_state.expenses, f, indent=4)
            st.success("Expense added successfully!")

# ----------------- OVERVIEW -----------------
elif selected == "Overview":
    st.header("Expenses Overview")
    if not st.session_state.expenses:
        st.info("No expenses added yet. Go to 'Add Expense' tab to add your personal expenses.")
    else:
        df = pd.DataFrame(st.session_state.expenses)
        st.dataframe(df)

        total_expense = df["value"].sum()
        st.metric("Total Expenses", f"₹{total_expense}")

        # ----------------- BUDGET ALERT -----------------
        df["date"] = pd.to_datetime(df["date"])
        today = datetime.today()
        current_month_expenses = df[
            (df["date"].dt.month == today.month) & (df["date"].dt.year == today.year)
        ]
        monthly_total = current_month_expenses["value"].sum()

        if monthly_total > MONTHLY_BUDGET:
            st.warning(f"⚠️ You have exceeded your monthly budget of ₹{MONTHLY_BUDGET}! "
                       f"Current spending: ₹{monthly_total}")
        else:
            st.info(f"Monthly spending: ₹{monthly_total} / ₹{MONTHLY_BUDGET}")
            remaining = MONTHLY_BUDGET - monthly_total
            st.success(f"You have ₹{remaining} remaining for this month.")

# ----------------- VISUALIZATION -----------------
elif selected == "Visualization":
    st.header("Expenses Visualization")
    if not st.session_state.expenses:
        st.info("No expenses added yet. Add some expenses to see the charts.")
    else:
        df = pd.DataFrame(st.session_state.expenses)
        category_summary = df.groupby("category")["value"].sum()

        # Pie chart
        fig, ax = plt.subplots(figsize=(4, 4))
        ax.pie(
            category_summary,
            labels=category_summary.index,
            autopct="%1.1f%%",
            startangle=140,
            textprops={"fontsize": 8},
        )
        ax.set_title("Expense Distribution")
        st.pyplot(fig)
