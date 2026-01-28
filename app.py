import streamlit as st
import pandas as pd
import numpy as np
import requests
from io import StringIO

# ================================
# CONFIG
# ================================
DATA_URL = "https://docs.google.com/spreadsheets/d/1GdnY09hJ2qVHuEBAIJ-eU6B5z8ZdgcGf4P7ZjlAt4JI/export?format=csv"

st.set_page_config(page_title="Hardness & Mechanical Variability", layout="wide")
st.title("📊 Hardness & Mechanical Properties Variability Dashboard")

# ================================
# LOAD DATA
# ================================
@st.cache_data

def load_data(url):
    r = requests.get(url)
    r.encoding = "utf-8"
    return pd.read_csv(StringIO(r.text))

raw = load_data(DATA_URL)
st.subheader("🔎 Raw columns")
st.write(list(raw.columns))

# ================================
# COLUMN MAPPING (EXPLICIT)
# ================================
column_mapping = {
    "COIL_NO": "Coil_ID",
    "PRODUCT SPECIFICATION CODE": "Material",
    "HR STEEL GRADE": "Steel_Grade",
    "QUALITY_CODE": "Quality",
    "ORDER GAUGE": "Thickness",
    "TOP COATMASS": "Coating",
    "Standard Hardness": "Standard_Hardness",
    "HARDNESS 冶金": "Hardness",
    "TENSILE_YIELD": "YS",
    "TENSILE_TENSILE": "TS",
    "TENSILE_ELONG": "EL",
}

df = raw.rename(columns={k: v for k, v in column_mapping.items() if k in raw.columns})

# ================================
# CHECK REQUIRED COLUMNS (NO BATCH)
# ================================
required = ["Coil_ID", "Hardness", "YS", "TS", "EL"]
missing = [c for c in required if c not in df.columns]

if missing:
    st.error(f"❌ Missing required columns: {missing}")
    st.stop()

# ================================
# STANDARD HARDNESS PARSE
# ================================
def parse_spec(x):
    try:
        if isinstance(x, str) and "~" in x:
            a, b = x.split("~")
            return float(a), float(b)
    except Exception:
        pass
    return np.nan, np.nan

if "Standard_Hardness" in df.columns:
    df[["Hmin_spec", "Hmax_spec"]] = df["Standard_Hardness"].apply(
        lambda x: pd.Series(parse_spec(x))
    )
    df["Spec_status"] = np.where(
        df[["Hmin_spec", "Hmax_spec"]].isna().any(axis=1),
        "INVALID_SPEC",
        "VALID_SPEC",
    )
else:
    df["Spec_status"] = "INVALID_SPEC"

# ================================
# FILTER VALID DATA ONLY
# ================================
df_valid = df[df["Spec_status"] == "VALID_SPEC"].copy()

# ================================
# VARIABILITY FUNCTION
# ================================
def variability_table(group_cols, value_col):
    return (
        df_valid.groupby(group_cols)[value_col]
        .agg(
            count="count",
            mean="mean",
            std="std",
            p10=lambda x: np.percentile(x, 10),
            p90=lambda x: np.percentile(x, 90),
        )
        .reset_index()
    )

# ================================
# QC GROUPING LEVEL (FIXED)
# ================================
QC_GROUP = [
    c
    for c in [
        "Quality",
        "Material",
        "Steel_Grade",
        "Thickness",
        "Coating",
    ]
    if c in df_valid.columns
]

# ================================
# TABS
# ================================
tabs = st.tabs([
    "🧵 By COIL",
    "🧱 QC-Level Population",
    "🎨 By Coating",
    "📏 By Thickness",
    "⚠️ Spec Warning",
])

# -------- TAB 1: COIL --------
with tabs[0]:
    st.subheader("Variability by COIL_NO (coil-level)")
    for col in ["Hardness", "YS", "TS", "EL"]:
        st.markdown(f"### {col}")
        st.dataframe(variability_table(["Coil_ID"], col))

# -------- TAB 2: QC LEVEL --------
with tabs[1]:
    st.subheader("QC-level Variability")
    st.caption("Grouped by: QUALITY_CODE + PRODUCT SPECIFICATION CODE + HR STEEL GRADE + ORDER GAUGE + TOP COATMASS")
    for col in ["Hardness", "YS", "TS", "EL"]:
        st.markdown(f"### {col}")
        st.dataframe(variability_table(QC_GROUP, col))

# -------- TAB 3: COATING --------
with tabs[2]:
    st.subheader("Variability by Coating")
    if "Coating" in df_valid.columns:
        for col in ["Hardness", "YS", "TS", "EL"]:
            st.markdown(f"### {col}")
            st.dataframe(variability_table(["Coating"], col))
    else:
        st.info("Coating column not available")

# -------- TAB 4: THICKNESS --------
with tabs[3]:
    st.subheader("Variability by Thickness")
    if "Thickness" in df_valid.columns:
        for col in ["Hardness", "YS", "TS", "EL"]:
            st.markdown(f"### {col}")
            st.dataframe(variability_table(["Thickness"], col))
    else:
        st.info("Thickness column not available")

# -------- TAB 5: INVALID SPEC --------
with tabs[4]:
    st.subheader("⚠️ INVALID STANDARD HARDNESS")
    st.write("These records are excluded from quantitative analysis")
    st.dataframe(
        df[df["Spec_status"] == "INVALID_SPEC"][
            [c for c in ["Coil_ID", "Standard_Hardness", "Hardness"] if c in df.columns]
        ]
    )

st.success("✅ Dashboard loaded successfully (COIL-based, QC-safe)")
