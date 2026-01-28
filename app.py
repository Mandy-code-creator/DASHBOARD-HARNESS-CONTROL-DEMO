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
# SINGLE QC TABLE (STRICT CONDITIONS)
# ================================
st.subheader("📋 QC-level Variability Table (STRICT)")
st.caption(
    "Each table satisfies simultaneously: QUALITY_CODE + PRODUCT SPECIFICATION CODE + HR STEEL GRADE + ORDER GAUGE + TOP COATMASS"
)

# ---- FILTER: MATERIAL LEVEL (optional selector) ----
material_cols = [c for c in ["Quality", "Material", "Steel_Grade", "Thickness", "Coating"] if c in df_valid.columns]

with st.expander("🔎 Filter material level"):
    filters = {}
    for c in material_cols:
        options = sorted(df_valid[c].dropna().unique())
        sel = st.multiselect(c, options, default=options)
        filters[c] = sel

filtered = df_valid.copy()
for c, sel in filters.items():
    filtered = filtered[filtered[c].isin(sel)]

# ---- GROUP STRICTLY BY QC CONDITIONS ----
QC_GROUP = [
    "Quality",
    "Material",
    "Steel_Grade",
    "Thickness",
    "Coating",
]
QC_GROUP = [c for c in QC_GROUP if c in filtered.columns]

# ---- BUILD ONE TABLE PER PRODUCT SPEC ----
if "Material" not in filtered.columns:
    st.error("PRODUCT SPECIFICATION CODE (Material) column missing")
else:
    for spec, dfg in filtered.groupby("Material"):
        st.markdown(f"## 🧾 PRODUCT SPECIFICATION CODE: {spec}")
        for col in ["Hardness", "YS", "TS", "EL"]:
            tbl = (
                dfg.groupby(QC_GROUP)[col]
                .agg(
                    count="count",
                    mean="mean",
                    std="std",
                    p10=lambda x: np.percentile(x, 10),
                    p90=lambda x: np.percentile(x, 90),
                )
                .reset_index()
            )
            st.markdown(f"### {col}")
            st.dataframe(tbl)

st.success("✅ Generated STRICT QC tables (one table per PRODUCT SPEC)")("✅ Dashboard loaded successfully (COIL-based, QC-safe)")
