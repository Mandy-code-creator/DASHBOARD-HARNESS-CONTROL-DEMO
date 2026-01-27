import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# =========================
# PAGE CONFIG
# =========================
st.set_page_config(
    page_title="GI Hardness Control Dashboard",
    layout="wide"
)

st.title("GI HARDNESS CONTROL – LAB vs LINE vs STANDARD")

# =========================
# LOAD DATA
# =========================
DATA_URL = "https://docs.google.com/spreadsheets/d/1GdnY09hJ2qVHuEBAIJ-eU6B5z8ZdgcGf4P7ZjlAt4JI/export?format=csv"

@st.cache_data
def load_data(url):
    return pd.read_csv(url)

df = load_data(DATA_URL)

# =========================
# CLEAN COLUMN NAMES
# =========================
df.columns = df.columns.str.strip()

# =========================
# COLUMN DEFINITIONS
# =========================
COL_STANDARD = "Standard Hardness"
COL_LAB = "HARDNESS\n冶金"
COL_LINE_C = "HARDNESS\n鍍鋅線\nC"

# =========================
# BASIC CHECK
# =========================
required_cols = [
    "HR STEEL GRADE",
    "ORDER GAUGE",
    "TOP COATMASS",
    COL_STANDARD,
    COL_LAB,
    COL_LINE_C,
    "TENSILE_ELONG"
]

missing = [c for c in required_cols if c not in df.columns]

if missing:
    st.error(f"❌ Missing columns: {missing}")
    st.stop()

# =========================
# DATA TYPE
# =========================
for c in [COL_STANDARD, COL_LAB, COL_LINE_C, "TENSILE_ELONG"]:
    df[c] = pd.to_numeric(df[c], errors="coerce")

df = df.dropna(subset=[COL_STANDARD, COL_LAB, COL_LINE_C])

# =========================
# CREATE GROUP
# =========================
df["GROUP"] = (
    df["HR STEEL GRADE"].astype(str) + " | " +
    df["ORDER GAUGE"].astype(str) + "mm | " +
    df["TOP COATMASS"].astype(str)
)

# =========================
# CALCULATE DELTA
# =========================
df["ΔH_LAB"] = df[COL_STANDARD] - df[COL_LAB]
df["ΔH_LINE"] = df[COL_STANDARD] - df[COL_LINE_C]
df["LINE_MINUS_LAB"] = df[COL_LINE_C] - df[COL_LAB]

# =========================
# SIDEBAR FILTER
# =========================
st.sidebar.header("Filter")

group_selected = st.sidebar.selectbox(
    "Select Group",
    sorted(df["GROUP"].unique())
)

df_g = df[df["GROUP"] == group_selected]

# =========================
# KPI
# =========================
st.subheader("📊 Key Statistics")

col1, col2, col3 = st.columns(3)

with col1:
    st.metric(
        "ΔH LAB (P10)",
        f"{np.percentile(df_g['ΔH_LAB'],10):.2f}"
    )

with col2:
    st.metric(
        "ΔH LINE (P10)",
        f"{np.percentile(df_g['ΔH_LINE'],10):.2f}"
    )

with col3:
    st.metric(
        "LINE − LAB Mean",
        f"{df_g['LINE_MINUS_LAB'].mean():.2f}"
    )

# =========================
# SCATTER: ΔH vs EL
# =========================
st.subheader("🔍 Hardness Margin vs Elongation")

fig, ax = plt.subplots(figsize=(9,5))

ax.scatter(
    df_g["ΔH_LINE"],
    df_g["TENSILE_ELONG"],
    alpha=0.7,
    label="LINE"
)

ax.scatter(
    df_g["ΔH_LAB"],
    df_g["TENSILE_ELONG"],
    alpha=0.7,
    label="LAB"
)

ax.axvline(7, linestyle="--", label="Control limit = 7 HRB")

ax.set_xlabel("Standard − Hardness (HRB)")
ax.set_ylabel("Elongation (%)")
ax.legend()
ax.grid(True)

st.pyplot(fig)

# =========================
# SUMMARY TABLE
# =========================
st.subheader("📋 Summary Table")

summary = (
    df_g
    .groupby("GROUP")
    .agg(
        Coil_Count=("GROUP", "count"),
        LAB_P10=("ΔH_LAB", lambda x: np.percentile(x,10)),
        LINE_P10=("ΔH_LINE", lambda x: np.percentile(x,10)),
        LINE_LAB_MEAN=("LINE_MINUS_LAB", "mean"),
        EL_MIN=("TENSILE_ELONG", "min")
    )
    .reset_index()
)

st.dataframe(summary, use_container_width=True)

# =========================
# TECHNICAL CONCLUSION
# =========================
st.subheader("🧠 Technical Interpretation")

st.markdown("""
**How to judge current control limit (Standard − 7 HRB):**

- If **LINE_P10 ≫ 7** and **EL is stable** → limit is conservative  
- If **LINE_P10 ≈ 5~7** → limit is reasonable  
- If **LINE_P10 < 5** and **EL drops** → limit is risky  

⚠️ Control limit should be defined **by GROUP**, not globally.
""")
