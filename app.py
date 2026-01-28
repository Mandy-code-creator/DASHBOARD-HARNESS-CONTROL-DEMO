import streamlit as st
import pandas as pd
import numpy as np
import requests
from io import StringIO

# ================================
# CONFIG
# ================================
DATA_URL = "https://docs.google.com/spreadsheets/d/1GdnY09hJ2qVHuEBAIJ-eU6B5z8ZdgcGf4P7ZjlAt4JI/export?format=csv"

st.set_page_config(page_title="Material-level Mechanical Summary", layout="wide")
st.title("📊 Material-level Hardness & Mechanical Properties Summary")

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
# COLUMN MAPPING (EXPLICIT & SAFE)
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

df = raw.rename(columns={k: v for k, v in column_mapping.items() if k in raw.columns})

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
# GROUP LOGIC (MATERIAL LEVEL)
# ================================
GROUP_COLS = [
    "Product_Spec",
    "Material",
    "Top_Coatmass",
    "Order_Gauge",
]

# ================================
# AGGREGATION: MEAN + STDEV ONLY
# ================================
summary = (
    df.groupby(GROUP_COLS)
      .agg(
          Hardness_mean=("Hardness", "mean"),
          Hardness_stdev=("Hardness", "std"),
          YS_mean=("YS", "mean"),
          YS_stdev=("YS", "std"),
          TS_mean=("TS", "mean"),
          TS_stdev=("TS", "std"),
          EL_mean=("EL", "mean"),
          EL_stdev=("EL", "std"),
      )
      .reset_index()
)

# ================================
st.subheader("📋 Material-level Summary (One condition per table)")
st.caption(
    "Each table contains ONLY ONE combination of "
    "Material + Top Coatmass + Order Gauge"
)

# ===== Product_Spec ORDER (more data first) =====
spec_order = (
    summary.groupby("Product_Spec")
           .size()
           .sort_values(ascending=False)
           .index
)

for spec in spec_order:

    st.markdown(f"## 🧱 Product Spec: `{spec}`")

    df_spec = summary[summary["Product_Spec"] == spec]

    # ===== LOOP EACH UNIQUE CONDITION =====
    for (mat, coat, gauge), df_one in df_spec.groupby(
        ["Material", "Top_Coatmass", "Order_Gauge"]
    ):

        st.markdown(
            f"### 🔹 Material: **{mat}** | "
            f"Coatmass: **{coat}** | "
            f"Gauge: **{gauge}**"
        )

        st.dataframe(
            df_one.drop(
                columns=["Product_Spec", "Material", "Top_Coatmass", "Order_Gauge"]
            ),
            use_container_width=True
        )
