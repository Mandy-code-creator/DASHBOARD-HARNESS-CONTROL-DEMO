# ================================
# FULL STREAMLIT APP – LOGIC CONFIRMED (FIXED)
# ================================

import streamlit as st
import pandas as pd
import numpy as np
import requests
from io import StringIO, BytesIO
import matplotlib.pyplot as plt

# ================================
# UTILITY
# ================================
def fig_to_png(fig, dpi=200):
    buf = BytesIO()
    fig.savefig(buf, format="png", dpi=dpi, bbox_inches="tight")
    buf.seek(0)
    return buf

# ================================
# PAGE CONFIG
# ================================
st.set_page_config(page_title="Material-level Hardness Detail", layout="wide")
st.title("📊 Material-level Hardness & Mechanical Detail")

# ================================
# LOAD DATA
# ================================
DATA_URL = "https://docs.google.com/spreadsheets/d/1GdnY09hJ2qVHuEBAIJ-eU6B5z8ZdgcGf4P7ZjlAt4JI/export?format=csv"

@st.cache_data
def load_data(url):
    r = requests.get(url)
    r.encoding = "utf-8"
    return pd.read_csv(StringIO(r.text))

raw = load_data(DATA_URL)

# ================================
# FIND METALLIC TYPE COLUMN
# ================================
metal_col = None
for c in raw.columns:
    if "METALLIC" in c.upper() and "COATING" in c.upper():
        metal_col = c
        break

if metal_col is None:
    st.error("❌ Cannot find METALLIC COATING TYPE column")
    st.stop()

raw["Metallic_Type"] = raw[metal_col]

# ================================
# RENAME COLUMNS
# ================================
column_mapping = {
    "PRODUCT SPECIFICATION CODE": "Product_Spec",
    "HR STEEL GRADE": "Material",
    "Claasify material": "Rolling_Type",
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
    "Standard_YS_Min": "Standard_YS_Min",
    "Standard_YS_Max": "Standard_YS_Max",
    "Standard_TS_Min": "Standard_TS_Min",
    "Standard_TS_Max": "Standard_TS_Max",
    "Standard_EL_Min": "Standard_EL_Min",
}

df = raw.rename(columns={k: v for k, v in column_mapping.items() if k in raw.columns})

# ================================
# FORCE NUMERIC
# ================================
for c in [
    "Hardness_LAB","Hardness_LINE",
    "YS","TS","EL",
    "Standard_YS_Min","Standard_YS_Max",
    "Standard_TS_Min","Standard_TS_Max",
    "Standard_EL_Min"
]:
    if c in df.columns:
        df[c] = pd.to_numeric(df[c], errors="coerce")

# ================================
# SPLIT STANDARD HARDNESS
# ================================
def split_std(x):
    if isinstance(x, str) and "~" in x:
        try:
            lo, hi = x.split("~")
            return pd.Series([float(lo), float(hi)])
        except:
            return pd.Series([np.nan, np.nan])
    return pd.Series([np.nan, np.nan])

df[["Std_Min","Std_Max"]] = df["Std_Range_Text"].apply(split_std)
df.drop(columns=["Std_Range_Text"], inplace=True)

# ================================
# SIDEBAR FILTERS
# ================================
st.sidebar.header("🎛 FILTERS")

rolling = st.sidebar.radio("Rolling Type", sorted(df["Rolling_Type"].dropna().unique()))
df = df[df["Rolling_Type"] == rolling]

metal = st.sidebar.radio("Metallic Coating", sorted(df["Metallic_Type"].dropna().unique()))
df = df[df["Metallic_Type"] == metal]

qc = st.sidebar.radio("Quality Code", sorted(df["Quality_Code"].dropna().unique()))
df = df[df["Quality_Code"] == qc]

view_mode = st.sidebar.radio(
    "📊 View Mode",
    ["📋 Data Table","📈 Trend (LAB / LINE)","📊 Distribution","📐 Hardness Safety Analysis"]
)

# ================================
# GROUP CONDITION (≥30)
# ================================
GROUP_COLS = ["Product_Spec","Material","Metallic_Type","Top_Coatmass","Order_Gauge"]

count_df = (
    df.groupby(GROUP_COLS)
      .agg(N_Coils=("COIL_NO","nunique"))
      .reset_index()
)

valid_conditions = count_df[count_df["N_Coils"] >= 30]
if valid_conditions.empty:
    st.warning("⚠️ No condition with ≥30 coils")
    st.stop()

# ================================
# MAIN LOOP
# ================================
for _, cond in valid_conditions.iterrows():

    spec, mat, coat, gauge, n = (
        cond["Product_Spec"], cond["Material"],
        cond["Top_Coatmass"], cond["Order_Gauge"],
        int(cond["N_Coils"])
    )

    sub = df[
        (df["Product_Spec"] == spec) &
        (df["Material"] == mat) &
        (df["Top_Coatmass"] == coat) &
        (df["Order_Gauge"] == gauge)
    ].copy().sort_values("COIL_NO").reset_index(drop=True)

    lo, hi = sub[["Std_Min","Std_Max"]].iloc[0]

    # ================================
    # MECHANICAL STANDARD
    # ================================
    mech_cols = [
        "Standard_YS_Min","Standard_YS_Max",
        "Standard_TS_Min","Standard_TS_Max",
        "Standard_EL_Min"
    ]
    if any(c not in sub.columns for c in mech_cols):
        st.warning(f"⚠️ Missing mechanical standard columns for {spec}")
        continue

    ys_lo, ys_hi = sub["Standard_YS_Min"].iloc[0], sub["Standard_YS_Max"].iloc[0]
    ts_lo, ts_hi = sub["Standard_TS_Min"].iloc[0], sub["Standard_TS_Max"].iloc[0]
    el_lo = sub["Standard_EL_Min"].iloc[0]

    sub["MECH_PASS"] = (
        (sub["YS"] >= ys_lo) & (sub["YS"] <= ys_hi) &
        (sub["TS"] >= ts_lo) & (sub["TS"] <= ts_hi) &
        (sub["EL"] >= el_lo)
    )

    # ================================
    # QA STRICT LOGIC (UNCHANGED)
    # ================================
    sub["NG_LAB"]  = (sub["Hardness_LAB"]  < lo) | (sub["Hardness_LAB"]  > hi)
    sub["NG_LINE"] = (sub["Hardness_LINE"] < lo) | (sub["Hardness_LINE"] > hi)
    sub["COIL_NG"] = sub["NG_LAB"] | sub["NG_LINE"]

    n_out = sub[sub["COIL_NG"]]["COIL_NO"].nunique()
    qa_result = "FAIL" if n_out > 0 else "PASS"

    st.markdown(
        f"## 🧱 `{spec}`  \n"
        f"Material: **{mat}** | Coatmass: **{coat}** | Gauge: **{gauge}**  \n"
        f"➡️ n = **{n}** | ❌ Out = **{n_out}** | 🧪 **{qa_result}**"
    )

    # ================================
    # VIEW 4 — HARDNESS SAFETY
    # ================================
    if view_mode == "📐 Hardness Safety Analysis":

        mech_ok = sub[sub["MECH_PASS"]].copy()
        mech_ok["HRB_LAB_BIN"]  = mech_ok["Hardness_LAB"].round().astype("Int64")
        mech_ok["HRB_LINE_BIN"] = mech_ok["Hardness_LINE"].round().astype("Int64")

        c1, c2 = st.columns(2)

        with c1:
            lab_bin = mech_ok.groupby("HRB_LAB_BIN").agg(
                n=("COIL_NO","count"),
                pass_rate=("MECH_PASS","mean")
            ).reset_index()

            fig, ax = plt.subplots(figsize=(5,4))
            ax.bar(lab_bin["HRB_LAB_BIN"], lab_bin["pass_rate"])
            ax.axhline(1.0, linestyle="--")
            ax.set_ylim(0,1.05)
            ax.set_title("LAB – Mechanical Pass Rate")
            ax.grid(alpha=0.3)
            st.pyplot(fig)

        with c2:
            line_bin = mech_ok.groupby("HRB_LINE_BIN").agg(
                n=("COIL_NO","count"),
                pass_rate=("MECH_PASS","mean")
            ).reset_index()

            fig, ax = plt.subplots(figsize=(5,4))
            ax.bar(line_bin["HRB_LINE_BIN"], line_bin["pass_rate"])
            ax.axhline(1.0, linestyle="--")
            ax.set_ylim(0,1.05)
            ax.set_title("LINE – Mechanical Pass Rate")
            ax.grid(alpha=0.3)
            st.pyplot(fig)
