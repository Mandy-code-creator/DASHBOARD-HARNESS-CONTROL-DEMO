import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# =========================
# PAGE CONFIG
# =========================
st.set_page_config(
    page_title="Quality-driven Hardness Analysis",
    layout="wide"
)

st.title("🔍 QUALITY → STANDARD → MATERIAL → THICKNESS → COATING")
st.caption("Hardness control logic driven by QUALITY_CODE")

# =========================
# LOAD DATA
# =========================
DATA_URL = "https://docs.google.com/spreadsheets/d/1GdnY09hJ2qVHuEBAIJ-eU6B5z8ZdgcGf4P7ZjlAt4JI/export?format=csv"

@st.cache_data
def load_data(url):
    return pd.read_csv(url)

df = load_data(DATA_URL)

# =========================
# CLEAN COLUMNS
# =========================
df.columns = df.columns.str.replace("\n", " ", regex=False).str.strip()

# =========================
# COLUMN MAP
# =========================
COL_STD = "Standard Hardness"
COL_LAB = "HARDNESS 冶金"
COL_LINE = "HARDNESS 鍍鋅線 C"

COL_YS = "TENSILE_YIELD"
COL_TS = "TENSILE_TENSILE"
COL_EL = "TENSILE_ELONG"

# =========================
# REQUIRED CHECK
# =========================
required = [
    "QUALITY_CODE",
    "PRODUCT SPECIFICATION CODE",
    "HR STEEL GRADE",
    "ORDER GAUGE",
    "TOP COATMASS",
    COL_STD, COL_LAB, COL_LINE,
    COL_YS, COL_TS, COL_EL
]

missing = [c for c in required if c not in df.columns]
if missing:
    st.error(f"❌ Missing columns: {missing}")
    st.stop()

# =========================
# TYPE CONVERSION
# =========================
for c in [COL_STD, COL_LAB, COL_LINE, COL_YS, COL_TS, COL_EL, "ORDER GAUGE"]:
    df[c] = pd.to_numeric(df[c], errors="coerce")

df = df.dropna(subset=[COL_STD, COL_LAB, COL_LINE])

# =========================
# DERIVED METRICS
# =========================
df["ΔH_LAB"] = df[COL_STD] - df[COL_LAB]
df["ΔH_LINE"] = df[COL_STD] - df[COL_LINE]
df["LINE_MINUS_LAB"] = df[COL_LINE] - df[COL_LAB]

# =========================
# SIDEBAR – HIERARCHY FILTER
# =========================
st.sidebar.header("🔎 Hierarchical Filter")

qc = st.sidebar.selectbox(
    "QUALITY_CODE",
    sorted(df["QUALITY_CODE"].dropna().unique())
)

df_qc = df[df["QUALITY_CODE"] == qc]

spec = st.sidebar.selectbox(
    "PRODUCT SPECIFICATION",
    sorted(df_qc["PRODUCT SPECIFICATION CODE"].dropna().unique())
)

df_spec = df_qc[df_qc["PRODUCT SPECIFICATION CODE"] == spec]

mat = st.sidebar.selectbox(
    "HR STEEL GRADE",
    sorted(df_spec["HR STEEL GRADE"].dropna().unique())
)

df_mat = df_spec[df_spec["HR STEEL GRADE"] == mat]

thk = st.sidebar.selectbox(
    "ORDER GAUGE (mm)",
    sorted(df_mat["ORDER GAUGE"].dropna().unique())
)

df_thk = df_mat[df_mat["ORDER GAUGE"] == thk]

coat = st.sidebar.selectbox(
    "TOP COATMASS",
    sorted(df_thk["TOP COATMASS"].dropna().unique())
)

df_f = df_thk[df_thk["TOP COATMASS"] == coat]

# =========================
# SAFE FUNCTIONS
# =========================
def p10(x):
    x = x.dropna()
    return np.nan if len(x) < 3 else np.percentile(x, 10)

def corr(x, y):
    d = pd.concat([x, y], axis=1).dropna()
    return np.nan if len(d) < 5 else d.corr().iloc[0,1]

# =========================
# KPI
# =========================
st.subheader("📊 Hardness & Mechanical Risk Indicators")

c1, c2, c3, c4 = st.columns(4)

c1.metric("ΔH LINE (P10)", f"{p10(df_f['ΔH_LINE']):.2f}")
c2.metric("YS (P10)", f"{p10(df_f[COL_YS]):.1f}")
c3.metric("TS (P10)", f"{p10(df_f[COL_TS]):.1f}")
c4.metric("Min EL (%)", f"{df_f[COL_EL].min():.1f}")

# =========================
# RELATIONSHIP PLOTS
# =========================
st.subheader("🔗 Hardness Relationship Analysis")

if len(df_f) >= 3:
    fig, ax = plt.subplots(1, 3, figsize=(16,4), sharex=True)

    ax[0].scatter(df_f["ΔH_LINE"], df_f[COL_YS])
    ax[0].set_title("ΔH vs YS")

    ax[1].scatter(df_f["ΔH_LINE"], df_f[COL_TS])
    ax[1].set_title("ΔH vs TS")

    ax[2].scatter(df_f["ΔH_LINE"], df_f[COL_EL])
    ax[2].set_title("ΔH vs EL")

    for a in ax:
        a.axvline(7, linestyle="--", label="Typical limit")
        a.set_xlabel("Standard − LINE Hardness")
        a.grid(True)

    st.pyplot(fig)
else:
    st.info("Not enough data for relationship analysis")

# =========================
# SUMMARY TABLE
# =========================
st.subheader("📋 Summary by Coils (Filtered Scope)")

summary = df_f[[
    "QUALITY_CODE",
    "PRODUCT SPECIFICATION CODE",
    "HR STEEL GRADE",
    "ORDER GAUGE",
    "TOP COATMASS",
    COL_STD, COL_LAB, COL_LINE,
    "ΔH_LINE",
    COL_YS, COL_TS, COL_EL
]]

st.dataframe(summary, use_container_width=True)

# =========================
# INTERPRETATION
# =========================
st.subheader("🧠 Engineering Interpretation")

st.markdown("""
- QUALITY_CODE defines **risk tolerance** – never mix across QC  
- Thickness & coating strongly affect **cooling rate → hardness bias**
- LINE hardness margin must protect **YS first, EL later**
- One global −7 HRB limit is **technically incorrect**
""")
