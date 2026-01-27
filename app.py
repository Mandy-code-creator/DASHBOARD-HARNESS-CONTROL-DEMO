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
df.columns = (
    df.columns
      .str.replace("\n", " ", regex=False)
      .str.replace("  ", " ")
      .str.strip()
)

# =========================
# AUTO FIND COLUMNS
# =========================
def find_col(keyword_list):
    for c in df.columns:
        for k in keyword_list:
            if k.lower() in c.lower():
                return c
    return None

COL_STANDARD = find_col(["standard hardness"])
COL_LAB = find_col(["冶金"])
COL_LINE = find_col(["鍍鋅線", "galvanizing", "line c"])

# =========================
# CHECK
# =========================
if not all([COL_STANDARD, COL_LAB, COL_LINE]):
    st.error("❌ Cannot auto-detect hardness columns")
    st.write("Detected columns:")
    st.write(df.columns.tolist())
    st.stop()

# =========================
# REQUIRED PROCESS COLUMNS
# =========================
required_cols = [
    "HR STEEL GRADE",
    "ORDER GAUGE",
    "TOP COATMASS",
    "TENSILE_ELONG",
    COL_STANDARD,
    COL_LAB,
    COL_LINE
]

missing = [c for c in required_cols if c not in df.columns]
if missing:
    st.error(f"❌ Missing columns: {missing}")
    st.stop()

# =========================
# DATA TYPE
# =========================
for c in [COL_STANDARD, COL_LAB, COL_LINE, "TENSILE_ELONG"]:
    df[c] = pd.to_numeric(df[c], errors="coerce")

df = df.dropna(subset=[COL_STANDARD, COL_LAB, COL_LINE])

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
df["ΔH_LINE"] = df[COL_STANDARD] - df[COL_LINE]
df["LINE_MINUS_LAB"] = df[COL_LINE] - df[COL_LAB]

# =========================
# SIDEBAR
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

c1, c2, c3 = st.columns(3)

with c1:
    st.metric("ΔH LAB (P10)", f"{np.percentile(df_g['ΔH_LAB'],10):.2f}")

with c2:
    st.metric("ΔH LINE (P10)", f"{np.percentile(df_g['ΔH_LINE'],10):.2f}")

with c3:
    st.metric("LINE − LAB Mean", f"{df_g['LINE_MINUS_LAB'].mean():.2f}")

# =========================
# SCATTER
# =========================
st.subheader("🔍 Hardness Margin vs Elongation")

fig, ax = plt.subplots(figsize=(9,5))

ax.scatter(df_g["ΔH_LINE"], df_g["TENSILE_ELONG"], label="LINE", alpha=0.7)
ax.scatter(df_g["ΔH_LAB"], df_g["TENSILE_ELONG"], label="LAB", alpha=0.7)

ax.axvline(7, linestyle="--", label="Current control = 7 HRB")

ax.set_xlabel("Standard − Hardness (HRB)")
ax.set_ylabel("Elongation (%)")
ax.legend()
ax.grid(True)

st.pyplot(fig)

# =========================
# SUMMARY TABLE
# =========================
st.subheader("📋 Summary")

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
# CONCLUSION
# =========================
st.subheader("🧠 Interpretation Logic")

st.markdown("""
- **LINE_P10 ≫ 7** → current limit is conservative  
- **LINE_P10 ≈ 5–7** → current limit is reasonable  
- **LINE_P10 < 5 + EL drop** → current limit is risky  

⚠️ Always control **by group (material + thickness + coating)**, not globally.
""")
