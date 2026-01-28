import streamlit as st
import pandas as pd
import requests
from io import StringIO

# ================================
# CONFIG
# ================================
DATA_URL = "https://docs.google.com/spreadsheets/d/1GdnY09hJ2qVHuEBAIJ-eU6B5z8ZdgcGf4P7ZjlAt4JI/export?format=csv"

st.set_page_config(
    page_title="Mechanical Raw Data – One Condition Only",
    layout="wide"
)
st.title("📋 Mechanical Properties – Coil Level (One Condition per Table)")

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
required = [
    "Product_Spec",
    "Material",
    "Top_Coatmass",
    "Order_Gauge",
    "Hardness",
    "YS",
    "TS",
    "EL",
]

missing = [c for c in required if c not in df.columns]
if missing:
    st.error(f"❌ Missing required columns: {missing}")
    st.stop()

# ================================
# FORCE NUMERIC (SAFE)
# ================================
for c in ["Hardness", "YS", "TS", "EL"]:
    df[c] = pd.to_numeric(df[c], errors="coerce")

# ================================
# GROUP BY ONE CONDITION ONLY
# ================================
GROUP_COLS = [
    "Product_Spec",
    "Material",
    "Top_Coatmass",
    "Order_Gauge",
]

condition_order = (
    df.groupby(GROUP_COLS)
      .size()
      .reset_index(name="N_Coils")
      .sort_values("N_Coils", ascending=False)
)

# ================================
# DISPLAY
# ================================
st.caption(
    "Raw coil-level data only. "
    "Each table contains ONE and ONLY ONE condition "
    "(Product Spec + Material + Coatmass + Gauge)."
)

for _, cond in condition_order.iterrows():

    spec = cond["Product_Spec"]
    mat = cond["Material"]
    coat = cond["Top_Coatmass"]
    gauge = cond["Order_Gauge"]
    n = int(cond["N_Coils"])

    df_cond = df[
        (df["Product_Spec"] == spec) &
        (df["Material"] == mat) &
        (df["Top_Coatmass"] == coat) &
        (df["Order_Gauge"] == gauge)
    ]

    st.markdown(
        f"## 🧱 {spec} | {mat} | Coatmass {coat} | Gauge {gauge} "
        f"(n = {n} coils)"
    )

    st.dataframe(
        df_cond[
            ["Hardness", "YS", "TS", "EL"]
        ],
        use_container_width=True
    )

st.success("✅ One-condition-per-table raw data displayed correctly")
