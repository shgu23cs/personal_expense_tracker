# app.py
import streamlit as st
from pathlib import Path
import json
from datetime import date, datetime
import pandas as pd
import matplotlib.pyplot as plt
from streamlit_option_menu import option_menu
import requests

# ---------------- CONFIG ----------------
st.set_page_config(page_title="Personal Expense Tracker", page_icon="💰", layout="wide")

PROJECT_DIR = Path(__file__).parent
DATA_FILE = PROJECT_DIR / "data.json"
SETTINGS_FILE = PROJECT_DIR / "settings.json"
CSS_FILE = PROJECT_DIR / "styles" / "main.css"

# ---------------- UTIL ----------------
def load_json(path, default):
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return default
    return default

def save_json(path, data):
    path.write_text(json.dumps(data, indent=4), encoding="utf-8")

def get_next_id(records):
    if not records:
        return 1
    ids = [r.get("id", 0) for r in records]
    return max(ids) + 1

# ---------------- DEFAULTS ----------------
DEFAULT_CATEGORIES = [
    "Housing", "Food", "Transportation", "Entertainment",
    "Medical", "Subscriptions", "Miscellaneous", "Savings"
]
DEFAULT_SETTINGS = {"monthly_budget": 10000.0, "categories": DEFAULT_CATEGORIES}

# ---------------- LOAD ----------------
records = load_json(DATA_FILE, [])
settings = load_json(SETTINGS_FILE, DEFAULT_SETTINGS)

# Apply CSS if present
if CSS_FILE.exists():
    with open(CSS_FILE) as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# ---------------- SESSION STATE ----------------
if "records" not in st.session_state:
    st.session_state.records = records.copy()

if "settings" not in st.session_state:
    st.session_state.settings = settings.copy()

# ensure every record has an id (backfill)
changed = False
for r in st.session_state.records:
    if "id" not in r:
        r["id"] = get_next_id(st.session_state.records)
        changed = True
if changed:
    save_json(DATA_FILE, st.session_state.records)

# ---------------- NAVIGATION ----------------
selected = option_menu(
    menu_title=None,
    options=["Overview", "Add Expense", "Add Income", "Visualization", "Receipt Scanner", "Settings", "Delete Expense"],
    icons=["clipboard2-data", "plus-circle", "cash-stack", "bar-chart-fill", "camera", "gear", "trash"],
    orientation="horizontal"
)

# ---------------- HELPERS ----------------
def df_from_records():
    df = pd.DataFrame(st.session_state.records)
    if df.empty:
        return df
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"])
    return df

def add_record(category, description, value, exp_date, type_="expense"):
    new = {
        "id": int(get_next_id(st.session_state.records)),
        "type": type_,
        "category": category,
        "description": description or "",
        "value": float(value),
        "date": str(exp_date)
    }
    st.session_state.records.append(new)
    save_json(DATA_FILE, st.session_state.records)

def delete_record_by_id(record_id):
    before = len(st.session_state.records)
    st.session_state.records = [r for r in st.session_state.records if int(r.get("id", -1)) != int(record_id)]
    save_json(DATA_FILE, st.session_state.records)
    return before - len(st.session_state.records)

def export_csv_bytes(df):
    return df.to_csv(index=False).encode("utf-8")

# ---------------- OCR API ----------------
OCR_API_KEY = "K83611298488957"

def extract_text_from_image(image_file):
    url = "https://api.ocr.space/parse/image"

    result = requests.post(
        url,
        files={"file": image_file},
        data={"apikey": OCR_API_KEY, "language": "eng"},
    )

    result_json = result.json()
    try:
        text = result_json["ParsedResults"][0]["ParsedText"]
        return text
    except:
        return "❌ OCR failed. Try a clearer image."

# ---------------- PAGES ----------------

# ---------- OVERVIEW ----------
if selected == "Overview":
    st.markdown("<h1 style='text-align:center;'>💰 Personal Expense Tracker</h1>", unsafe_allow_html=True)
    st.header("Overview")

    df = df_from_records()
    if df.empty:
        st.info("No expenses added yet. Go to 'Add Expense' to add your first entry.")
    else:
        total_expense = df[df["type"]=="expense"]["value"].sum()
        total_income = df[df["type"]=="income"]["value"].sum()
        remaining_balance = total_income - total_expense

        today = datetime.today()
        this_month = df[(df["date"].dt.month == today.month) & (df["date"].dt.year == today.year)]
        monthly_total = this_month[this_month["type"]=="expense"]["value"].sum()

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total Expenses", f"₹{total_expense:,.2f}")
        col2.metric("Total Income", f"₹{total_income:,.2f}")
        col3.metric("Monthly Expenses", f"₹{monthly_total:,.2f}")
        col4.metric("Remaining Balance", f"₹{remaining_balance:,.2f}")

        st.markdown("### Expense History")
        df_display = df.sort_values("date", ascending=False).reset_index(drop=True)

        for idx, row in df_display.iterrows():
            cols = st.columns([1.2, 3, 2, 1])
            cols[0].write(f"₹{row['value']:,.2f}")
            cols[1].write(f"**{row['category']}**\n\n{row['description']}")
            cols[2].write(row["date"].strftime("%Y-%m-%d"))
            btn_key = f"del_overview_{int(row['id'])}"
            if cols[3].button("Delete", key=btn_key):
                deleted = delete_record_by_id(row["id"])
                if deleted:
                    st.success("Deleted entry.")
                else:
                    st.error("Could not delete entry.")
                st.rerun()

        csv_bytes = export_csv_bytes(df_display)
        st.download_button("📥 Download CSV", csv_bytes, file_name="expenses.csv", mime="text/csv")

# ---------- ADD EXPENSE ----------
elif selected == "Add Expense":
    st.header("Add Expense")
    categories = st.session_state.settings.get("categories", DEFAULT_CATEGORIES)
    
    with st.form("add_expense_form"):
        col1, col2 = st.columns([2, 1])
        
        with col1:
            category = st.selectbox("Category", categories)
            description = st.text_input("Description (optional)")
            exp_date = st.date_input("Date", value=date.today())
        
        with col2:
            value = st.number_input("Amount (₹)", min_value=0.0, format="%.2f")
            submitted = st.form_submit_button("Add Expense")
        
        if submitted:
            if value <= 0:
                st.error("Amount must be greater than 0.")
            else:
                add_record(category, description, value, exp_date, type_="expense")
                st.success("Expense added.")
                st.rerun()

# ---------- ADD INCOME ----------
elif selected == "Add Income":
    st.header("Add Income")
    income_sources = ["Salary", "Business", "Gift", "Other"]
    
    category = st.selectbox("Income Source", income_sources)
    description = st.text_input("Description")
    value = st.number_input("Amount", min_value=0.0, format="%.2f")
    income_date = st.date_input("Date")
    
    if st.button("Add Income"):
        add_record(category, description, value, income_date, type_="income")
        st.success("Income added successfully!")
        st.rerun()

# ---------- VISUALIZATION ----------
elif selected == "Visualization":
    st.header("Visualization")
    df = df_from_records()

    if df.empty:
        st.info("No expenses to visualize.")
    else:
        # ----- CATEGORY PIE CHART -----
        cat_sum = df[df["type"]=="expense"].groupby("category")["value"].sum().sort_values(ascending=False)
        if not cat_sum.empty:
            fig1, ax1 = plt.subplots(figsize=(3, 2))
            ax1.pie(cat_sum, labels=cat_sum.index, autopct="%1.1f%%", startangle=140, textprops={"fontsize": 9})
            ax1.set_title("Expense Distribution by Category", fontsize=12)
            st.pyplot(fig1, clear_figure=True)

        st.markdown("---")

        # ----- DAILY & MONTHLY BAR CHART -----
        df_exp = df[df["type"]=="expense"].copy()
        df_exp['date'] = pd.to_datetime(df_exp['date'])
        daily_sum = df_exp.groupby(df_exp["date"].dt.date)["value"].sum()
        monthly_total = daily_sum.sum()

        fig2, ax2 = plt.subplots(figsize=(6,3))
        ax2.bar(daily_sum.index.astype(str), daily_sum.values, width=0.4, color='red')
        ax2.set_title(f"Daily Expenses (Month total: ₹{monthly_total:,.2f})")
        ax2.set_ylabel("₹")
        ax2.tick_params(axis='x', rotation=60)
        st.pyplot(fig2, clear_figure=True)

        # ----- REMAINING BALANCE BAR -----
        total_income = df[df["type"]=="income"]["value"].sum()
        remaining_balance = total_income - monthly_total
        monthly_balance = pd.Series([remaining_balance], index=[datetime.today().strftime("%B")])
        fig3, ax3 = plt.subplots(figsize=(4,2))
        ax3.bar(monthly_balance.index, monthly_balance.values, width=0.2, color='green')
        ax3.set_title("Monthly Remaining Balance")
        ax3.set_ylabel("₹")
        st.pyplot(fig3, clear_figure=True)

# ---------- RECEIPT SCANNER ----------
elif selected == "Receipt Scanner":
    st.header("Scan Receipt (OCR)")
    uploaded = st.file_uploader("Upload receipt (JPG, PNG, PDF)", type=["jpg", "jpeg", "png", "pdf"])
    if uploaded:
        st.image(uploaded, caption="Uploaded Receipt", use_column_width=True)
        if st.button("Extract Text"):
            extracted = extract_text_from_image(uploaded)
            st.text_area("Extracted Text", extracted, height=250)

# ---------- SETTINGS ----------
elif selected == "Settings":
    st.header("Settings")
    current_budget = float(st.session_state.settings.get("monthly_budget", 50000.0))
    new_budget = st.number_input("Set monthly budget (₹)", min_value=0.0, value=current_budget, format="%.2f")
    if st.button("Save Budget"):
        st.session_state.settings["monthly_budget"] = float(new_budget)
        save_json(SETTINGS_FILE, st.session_state.settings)
        st.success("Budget saved.")

    st.subheader("Categories (one per line)")
    cats = st.session_state.settings.get("categories", DEFAULT_CATEGORIES)
    cats_text = st.text_area("Edit categories", value="\n".join(cats), height=200)
    if st.button("Save Categories"):
        new_cats = [c.strip() for c in cats_text.splitlines() if c.strip()]
        if new_cats:
            st.session_state.settings["categories"] = new_cats
            save_json(SETTINGS_FILE, st.session_state.settings)
            st.success("Categories saved.")
        else:
            st.error("Please provide at least one category.")

# ---------- DELETE EXPENSE ----------
elif selected == "Delete Expense":
    st.header("Delete Expense")
    df = df_from_records()
    if df.empty:
        st.info("No expenses to delete.")
    else:
        options = [f"{int(r['id'])} | {r['date'].strftime('%Y-%m-%d')} - {r['category']} - ₹{float(r['value']):,.2f}" for r in df.sort_values("date", ascending=False).to_dict("records")]
        choice = st.selectbox("Select expense to delete", options)
        selected_id = int(choice.split("|")[0].strip())
        if st.button("Delete Selected Expense"):
            deleted = delete_record_by_id(selected_id)
            if deleted:
                st.success("Deleted selected expense.")
                st.rerun()
            else:
                st.error("Could not delete the selected expense.")

# ---------- FOOTER ----------

