import streamlit as st
import pandas as pd
import requests
from io import StringIO

# ================================
# CONFIG
# ================================
DATA_URL = "https://docs.google.com/spreadsheets/d/1GdnY09hJ2qVHuEBAIJ-eU6B5z8ZdgcGf4P7ZjlAt4JI/export?format=csv"

st.set_page_config(
    page_title="Coil-level Mechanical Data",
    layout="wide"
)

st.title("📄 Coil-level Hardness & Mechanical Properties")
st.caption("Raw data only – NO average, NO SPC, NO batch, NO chart")

# ================================
# LOAD DATA
# ================================
@st.cache_data
def load_data(url):
    r = requests.get(url)
    r.encoding = "utf-8"
    return pd.read_csv(StringIO(r.text))

raw = load_data(DATA_URL)

# ================================
# COLUMN MAPPING
# ================================
column_mapping = {
    "PRODUCT SPECIFICATION CODE": "Product_Spec",
    "HR STEEL GRADE": "Material",
    "TOP COATMASS": "Top_Coatmass",
    "ORDER GAUGE": "Order_Gauge",
    "HARDNESS 冶金": "Hardness",
    "TENSILE_YIELD": "YS",
    "TENSILE_TENSILE": "TS",
    "TENSILE_ELONG": "EL",
}

df = raw.rename(
    columns={k: v for k, v in column_mapping.items() if k in raw.columns}
)

# ================================
# CHECK REQUIRED COLUMNS
# ================================
required_cols = [
    "Product_Spec",
    "Material",
    "Top_Coatmass",
    "Order_Gauge",
    "Hardness",
    "YS",
    "TS",
    "EL",
]

missing = [c for c in required_cols if c not in df.columns]
if missing:
    st.error(f"❌ Missing required columns: {missing}")
    st.stop()

# ================================
# FORCE NUMERIC (NO CALCULATION)
# ================================
for c in ["Hardness", "YS", "TS", "EL"]:
    df[c] = pd.to_numeric(df[c], errors="coerce")

# ================================
# OPTIONAL FILTERS (SAFE)
# ================================
with st.sidebar:
    st.header("🔎 Filter (optional)")

    spec_sel = st.multiselect(
        "Product Spec",
        sorted(df["Product_Spec"].dropna().unique())
    )

    mat_sel = st.multiselect(
        "Material",
        sorted(df["Material"].dropna().unique())
    )

    if spec_sel:
        df = df[df["Product_Spec"].isin(spec_sel)]
    if mat_sel:
        df = df[df["Material"].isin(mat_sel)]

# ================================
# DISPLAY RAW COIL DATA
# ================================
st.subheader("📋 Coil-level Raw Data")
st.write(f"Total coils: **{len(df)}**")

display_cols = [
    "Product_Spec",
    "Material",
    "Top_Coatmass",
    "Order_Gauge",
    "Hardness",
    "YS",
    "TS",
    "EL",
]

st.dataframe(
    df[display_cols].reset_index(drop=True),
    use_container_width=True
)

st.success("✅ Displayed RAW coil data only – no calculation applied")
