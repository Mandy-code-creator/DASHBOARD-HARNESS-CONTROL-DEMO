import streamlit as st
import pandas as pd
import numpy as np

# =========================
# PAGE CONFIG
# =========================
st.set_page_config(
    page_title="GI Hardness Control Dashboard",
    layout="wide"
)

st.title("GI Hardness & Mechanical Property Dashboard")

# =========================
# LOAD DATA FROM GOOGLE SHEET
# =========================
@st.cache_data
def load_data():
    SHEET_ID = "PUT_YOUR_SHEET_ID_HERE"
    url = f"https://docs.google.com/spreadsheets/d/1GdnY09hJ2qVHuEBAIJ-eU6B5z8ZdgcGf4P7ZjlAt4JI/export?format=csv"
    df = pd.read_csv(url)
    return df

df = load_data()

# =========================
# CLEAN COLUMN NAMES (CRITICAL)
# =========================
df.columns = (
    df.columns
    .astype(str)
    .str.replace("\n", " ", regex=False)
    .str.replace("  ", " ", regex=False)
    .str.strip()
)

st.subheader("Column names (debug)")
st.write(df.columns.tolist())

# =========================
# AUTO FIND HARDNESS COLUMNS
# =========================
lab_col = [c for c in df.columns if "HARDNESS" in c and "冶金" in c]
line_col = [c for c in df.columns if "HARDNESS" in c and "鍍鋅線" in c and "C" in c]

spec_col = [c for c in df.columns if "Standard" in c and "Hardness" in c]

if not lab_col:
    st.error("❌ Không tìm thấy cột HARDNESS 冶金 (LAB)")
    st.stop()

if not line_col:
    st.error("❌ Không tìm thấy cột HARDNESS 鍍鋅線 C (LINE)")
    st.stop()

if not spec_col:
    st.error("❌ Không tìm thấy cột Standard Hardness")
    st.stop()

hardness_map = {
    "LAB – 冶金 (center)": lab_col[0],
    "LINE – GI (center C)": line_col[0],
}

# =========================
# SIDEBAR
# =========================
st.sidebar.header("Settings")

hardness_label = st.sidebar.radio(
    "Hardness source",
    list(hardness_map.keys())
)

HARDNESS = df[hardness_map[hardness_label]]
HMAX = df[spec_col[0]]

# =========================
# NUMERIC SAFETY
# =========================
HARDNESS = pd.to_numeric(HARDNESS, errors="coerce")
HMAX = pd.to_numeric(HMAX, errors="coerce")

# =========================
# CORE ANALYSIS
# =========================
df["ΔH_spec"] = HMAX - HARDNESS

def hardness_band(x):
    if pd.isna(x):
        return "NA"
    elif x >= 10:
        return "≥10"
    elif x >= 7:
        return "7–10"
    elif x >= 5:
        return "5–7"
    elif x >= 3:
        return "3–5"
    else:
        return "<3"

df["Hardness_Band"] = df["ΔH_spec"].apply(hardness_band)

def decision_zone(x):
    if pd.isna(x):
        return "NA"
    elif x >= 7:
        return "SAFE"
    elif x >= 5:
        return "WATCH"
    else:
        return "RISK"

df["Zone"] = df["ΔH_spec"].apply(decision_zone)

# =========================
# KPI
# =========================
st.subheader("KPI – Hardness Control")

col1, col2, col3 = st.columns(3)

total = len(df)
safe_pct = (df["Zone"] == "SAFE").mean() * 100
watch_pct = (df["Zone"] == "WATCH").mean() * 100
risk_pct = (df["Zone"] == "RISK").mean() * 100

col1.metric("SAFE (%)", f"{safe_pct:.1f}%")
col2.metric("WATCH (%)", f"{watch_pct:.1f}%")
col3.metric("RISK (%)", f"{risk_pct:.1f}%")

# =========================
# RESULT TABLE
# =========================
st.subheader("Analysis Table")

show_cols = [
    hardness_map[hardness_label],
    spec_col[0],
    "ΔH_spec",
    "Hardness_Band",
    "Zone"
]

extra_cols = [c for c in ["TENSILE_YIELD", "TENSILE_TENSILE", "TENSILE_ELONG"] if c in df.columns]
show_cols.extend(extra_cols)

st.dataframe(
    df[show_cols].sort_values("ΔH_spec").reset_index(drop=True),
    use_container_width=True
)

# =========================
# TECH NOTE
# =========================
st.markdown("""
### Technical note
- ΔH_spec = Hmax − Hardness(center)
- SAFE zone defined as ΔH ≥ 7 HRB
- Threshold will be validated by historical EL / TS / YS correlation
""")
