import streamlit as st
import pandas as pd
import numpy as np
import requests
from io import StringIO

# ================================
# CONFIG
# ================================
DATA_URL = "https://docs.google.com/spreadsheets/d/1GdnY09hJ2qVHuEBAIJ-eU6B5z8ZdgcGf4P7ZjlAt4JI/export?format=csv"

st.set_page_config(
    page_title="Material-level Mechanical Summary",
    layout="wide"
)
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
# FORCE NUMERIC (SAFETY)
# ================================
for c in ["Hardness", "YS", "TS", "EL"]:
    df[c] = pd.to_numeric(df[c], errors="coerce")

# ================================
# COUNT NUMBER OF COILS (n)
# ================================
count_df = (
    df.groupby(
        ["Product_Spec", "Material", "Top_Coatmass", "Order_Gauge"],
        dropna=False
    )
    .size()
    .reset_index(name="N_Coils")
)

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
# AGGREGATION: MEAN + STDEV
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
# MERGE COIL COUNT INTO SUMMARY
# ================================
summary = summary.merge(
    count_df,
    on=["Product_Spec", "Material", "Top_Coatmass", "Order_Gauge"],
    how="left"
)

# ================================
# DISPLAY
# ================================
st.subheader("📋 Material-level Summary (One condition per table)")
st.caption(
    "Each table represents ONLY ONE combination of "
    "Material + Top Coatmass + Order Gauge. "
    "Tables with more coils (n) are displayed first."
)

# ===== Product_Spec ORDER (more conditions first) =====
spec_order = (
    summary.groupby("Product_Spec")
           .size()
           .sort_values(ascending=False)
           .index
)

for spec in spec_order:

    st.markdown(f"## 🧱 Product Spec: `{spec}`")

    df_spec = summary[summary["Product_Spec"] == spec]

    # ===== SORT CONDITIONS BY SAMPLE SIZE =====
    df_spec = df_spec.sort_values("N_Coils", ascending=False)

    for _, row in df_spec.iterrows():

        st.markdown(
            f"### 🔹 Material: **{row['Material']}** | "
            f"Coatmass: **{row['Top_Coatmass']}** | "
            f"Gauge: **{row['Order_Gauge']}** "
            f"➡️ **n = {int(row['N_Coils'])} coils**"
        )

        st.dataframe(
            row.drop(
                labels=[
                    "Product_Spec",
                    "Material",
                    "Top_Coatmass",
                    "Order_Gauge",
                    "N_Coils",
                ]
            ).to_frame(name="Value"),
            use_container_width=True
        )

st.success("✅ Report generated successfully (CÁCH 1 – One condition per table)")
