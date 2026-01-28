import streamlit as st
import pandas as pd
import numpy as np
import requests
from io import StringIO

# ================================
# CONFIG
# ================================
DATA_URL = "https://docs.google.com/spreadsheets/d/1GdnY09hJ2qVHuEBAIJ-eU6B5z8ZdgcGf4P7ZjlAt4JI/export?format=csv"

st.set_page_config(page_title="Material-level Hardness Detail", layout="wide")
st.title("📊 Material-level Hardness & Mechanical Detail (Offline only)")

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
    "COIL NO": "COIL_NO",
    "QUALITY_CODE": "Quality_Code",
    "Standard Hardness": "Std_Range_Text",
    "HARDNESS 冶金": "Hardness_LAB",
    "HARDNESS 鍍鋅線 C": "Hardness_LINE",
    "TENSILE_YIELD": "YS",
    "TENSILE_TENSILE": "TS",
    "TENSILE_ELONG": "EL",
}

df = raw.rename(columns={k: v for k, v in column_mapping.items() if k in raw.columns})

# ================================
# REQUIRED COLUMNS CHECK
# ================================
required_cols = [
    "Product_Spec", "Material", "Top_Coatmass", "Order_Gauge",
    "COIL_NO", "Quality_Code",
    "Std_Range_Text", "Hardness_LAB", "Hardness_LINE",
    "YS", "TS", "EL"
]

missing = [c for c in required_cols if c not in df.columns]
if missing:
    st.error(f"❌ Missing required columns: {missing}")
    st.stop()

# ================================
# SPLIT STANDARD HARDNESS TEXT → MIN / MAX
# ================================
def split_std_range(x):
    if isinstance(x, str) and "~" in x:
        try:
            lo, hi = x.split("~")
            return pd.Series([float(lo), float(hi)])
        except:
            return pd.Series([np.nan, np.nan])
    return pd.Series([np.nan, np.nan])

df[["Std_Min", "Std_Max"]] = df["Std_Range_Text"].apply(split_std_range)
df = df.drop(columns=["Std_Range_Text"])

# ================================
# FORCE NUMERIC
# ================================
for c in ["Hardness_LAB", "Hardness_LINE", "YS", "TS", "EL"]:
    df[c] = pd.to_numeric(df[c], errors="coerce")

# ================================
# ANALYSIS TASK SELECTOR
# ================================
st.sidebar.header("🧩 ANALYSIS TASK")

task = st.sidebar.radio(
    "Select analysis task",
    [
        "Summary (raw tables)",
        "QA Strict Spec Check (1 NG = FAIL)"
    ],
    index=0
)

# ================================
# QUALITY CODE FILTER
# ================================
st.sidebar.header("🎛 QUALITY CODE")
quality_codes = sorted(df["Quality_Code"].dropna().unique())
selected_qc = st.sidebar.radio("Select Quality Code", quality_codes)

df = df[df["Quality_Code"] == selected_qc]

# ================================
# GROUP CONDITIONS
# ================================
GROUP_COLS = ["Product_Spec", "Material", "Top_Coatmass", "Order_Gauge"]

count_df = (
    df.groupby(GROUP_COLS)
      .agg(N_Coils=("COIL_NO", "nunique"))
      .reset_index()
)

valid_conditions = count_df[count_df["N_Coils"] >= 30]

if valid_conditions.empty:
    st.warning("⚠️ No condition has ≥ 30 coils")
    st.stop()

valid_conditions = valid_conditions.sort_values("N_Coils", ascending=False)

# =========================================================
# SUMMARY TASK
# =========================================================
if task == "Summary (raw tables)":

    st.subheader("📋 Coil-level Data (Offline measurements only)")
    st.caption(
        "• 1 table = 1 Product Spec + Material + Coatmass + Gauge  \n"
        "• n = total number of coils  \n"
        "• No averaging, no SPC, no batch  \n"
        "• ≥ 30 coils only"
    )

    for _, cond in valid_conditions.iterrows():

        spec   = cond["Product_Spec"]
        mat    = cond["Material"]
        coat   = cond["Top_Coatmass"]
        gauge  = cond["Order_Gauge"]
        n      = int(cond["N_Coils"])

        st.markdown(
            f"## 🧱 Product Spec: `{spec}`  \n"
            f"**Material:** {mat} | **Coatmass:** {coat} | **Gauge:** {gauge}  \n"
            f"➡️ **n = {n} coils**"
        )

        table_df = df[
            (df["Product_Spec"] == spec) &
            (df["Material"] == mat) &
            (df["Top_Coatmass"] == coat) &
            (df["Order_Gauge"] == gauge)
        ][[
            "COIL_NO",
            "Std_Min", "Std_Max",
            "Hardness_LAB", "Hardness_LINE",
            "YS", "TS", "EL"
        ]].sort_values("COIL_NO")

        st.dataframe(table_df, use_container_width=True)

# =========================================================
# QA STRICT SPEC CHECK
# =========================================================
# QA STRICT SPEC CHECK
# =========================================================
if task == "QA Strict Spec Check (1 NG = FAIL)":

    st.subheader("🧪 QA Strict Spec Check – Coil level")
    st.caption("Rule: If ANY coil is out of spec → Product FAIL")

    def is_ng(val, std_min, std_max):
        if pd.isna(val):
            return False
        return (val < std_min) or (val > std_max)

    for (spec, material, coatmass, gauge), df_spec in df.groupby(
        ["Product_Spec", "Material", "Top_Coatmass", "Order_Gauge"]
    ):

        df_spec = df_spec.copy()

        std_min = df_spec["Std_Min"].iloc[0]
        std_max = df_spec["Std_Max"].iloc[0]

        df_spec["NG_LAB"] = df_spec["Hardness_LAB"].apply(
            lambda x: is_ng(x, std_min, std_max)
        )
        df_spec["NG_LINE"] = df_spec["Hardness_LINE"].apply(
            lambda x: is_ng(x, std_min, std_max)
        )

        df_spec["COIL_NG"] = df_spec["NG_LAB"] | df_spec["NG_LINE"]

        df_ng = (
            df_spec[df_spec["COIL_NG"]]
            .drop_duplicates(subset="COIL_NO")
        )

        n_ng = df_ng["COIL_NO"].nunique()
        qa_result = "FAIL" if n_ng > 0 else "PASS"

        header_md = f"""
## 🧱 Product Spec: `{spec}`

**Material:** {material} | **Coatmass:** {coatmass} | **Gauge:** {gauge}

❌ **n = {n_ng} coils out of spec**

🧪 **QA Result:** `{qa_result}`
"""
        st.markdown(header_md)

        show_cols = [
            "COIL_NO",
            "Std_Min", "Std_Max",
            "Hardness_LAB", "Hardness_LINE",
            "YS", "TS", "EL",
            "COIL_NG"
        ]

        st.dataframe(
            df_spec[show_cols].sort_values("COIL_NO"),
            use_container_width=True
        )
