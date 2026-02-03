# =====================================
# FULL STREAMLIT APP – FINAL STABLE
# =====================================

import streamlit as st
import pandas as pd
import numpy as np
import requests
from io import StringIO, BytesIO
import matplotlib.pyplot as plt

# =====================================
# CONFIG
# =====================================
st.set_page_config(page_title="Hardness & Mechanical Control", layout="wide")
st.title("📊 Hardness & Mechanical Control Dashboard")

# =====================================
# UTILS
# =====================================
def fig_to_png(fig, dpi=200):
    buf = BytesIO()
    fig.savefig(buf, format="png", dpi=dpi, bbox_inches="tight")
    buf.seek(0)
    return buf

# =====================================
# LOAD DATA
# =====================================
DATA_URL = "https://docs.google.com/spreadsheets/d/1GdnY09hJ2qVHuEBAIJ-eU6B5z8ZdgcGf4P7ZjlAt4JI/export?format=csv"

@st.cache_data
def load_data(url):
    r = requests.get(url)
    r.encoding = "utf-8"
    return pd.read_csv(StringIO(r.text))

raw = load_data(DATA_URL)

# =====================================
# COLUMN NORMALIZATION
# =====================================
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

# Metallic type
metal_col = [c for c in raw.columns if "METALLIC" in c.upper() and "COATING" in c.upper()]
df["Metallic_Type"] = raw[metal_col[0]] if metal_col else "UNKNOWN"

# Numeric
num_cols = [
    "Hardness_LAB","Hardness_LINE","YS","TS","EL",
    "Standard_YS_Min","Standard_YS_Max",
    "Standard_TS_Min","Standard_TS_Max",
    "Standard_EL_Min",
]
for c in num_cols:
    if c in df.columns:
        df[c] = pd.to_numeric(df[c], errors="coerce")

# =====================================
# SPLIT HARDNESS STANDARD
# =====================================
def split_std(x):
    if isinstance(x, str) and "~" in x:
        try:
            lo, hi = x.split("~")
            return float(lo), float(hi)
        except:
            return np.nan, np.nan
    return np.nan, np.nan

df[["Std_Min","Std_Max"]] = df["Std_Range_Text"].apply(lambda x: pd.Series(split_std(x)))

# =====================================
# SIDEBAR FILTER
# =====================================
st.sidebar.header("🎛 Filters")

rolling = st.sidebar.selectbox("Rolling Type", sorted(df["Rolling_Type"].dropna().unique()))
metal = st.sidebar.selectbox("Metallic Type", sorted(df["Metallic_Type"].dropna().unique()))
qc = st.sidebar.selectbox("Quality Code", sorted(df["Quality_Code"].dropna().unique()))

df = df[
    (df["Rolling_Type"] == rolling) &
    (df["Metallic_Type"] == metal) &
    (df["Quality_Code"] == qc)
]

view_mode = st.sidebar.radio(
    "View Mode",
    [
        "📋 Data Table",
        "📈 Trend",
        "📊 Distribution",
        "📐 Hardness Safety Analysis",
    ]
)

# =====================================
# GROUP CONDITION
# =====================================
GROUP_COLS = ["Product_Spec","Material","Top_Coatmass","Order_Gauge"]

count_df = df.groupby(GROUP_COLS).agg(N=("COIL_NO","nunique")).reset_index()

# =====================================
# MAIN LOOP
# =====================================
for _, g in count_df.iterrows():

    spec, mat, coat, gauge, n = (
        g["Product_Spec"], g["Material"], g["Top_Coatmass"], g["Order_Gauge"], g["N"]
    )

    sub = df[
        (df["Product_Spec"] == spec) &
        (df["Material"] == mat) &
        (df["Top_Coatmass"] == coat) &
        (df["Order_Gauge"] == gauge)
    ].copy().sort_values("COIL_NO")

    lo, hi = sub[["Std_Min","Std_Max"]].iloc[0]

    # QA strict
    sub["NG_LAB"] = (sub["Hardness_LAB"] < lo) | (sub["Hardness_LAB"] > hi)
    sub["NG_LINE"] = (sub["Hardness_LINE"] < lo) | (sub["Hardness_LINE"] > hi)

    # Mechanical pass
    ys_lo, ys_hi = sub["Standard_YS_Min"].iloc[0], sub["Standard_YS_Max"].iloc[0]
    ts_lo, ts_hi = sub["Standard_TS_Min"].iloc[0], sub["Standard_TS_Max"].iloc[0]
    el_lo = sub["Standard_EL_Min"].iloc[0]

    sub["MECH_PASS"] = (
        (sub["YS"].between(ys_lo, ys_hi)) &
        (sub["TS"].between(ts_lo, ts_hi)) &
        (sub["EL"] >= el_lo)
    )

    st.markdown(
        f"## 🧱 `{spec}` | {mat} | {coat} | {gauge}  \n"
        f"➡️ n = **{n} coils**"
    )

    # =========================
    # VIEW 1
    # =========================
    if view_mode == "📋 Data Table":
        if n < 30:
            st.warning("⚠️ Require ≥ 30 coils")
            continue

        st.dataframe(
            sub[
                [
                    "COIL_NO","Hardness_LAB","Hardness_LINE",
                    "YS","TS","EL",
                    "Std_Min","Std_Max",
                    "NG_LAB","NG_LINE",
                ]
            ],
            use_container_width=True
        )

    # =========================
    # VIEW 2
    # =========================
    elif view_mode == "📈 Trend":
        if n < 30:
            st.warning("⚠️ Require ≥ 30 coils")
            continue

        sub["X"] = np.arange(1, len(sub)+1)

        fig, ax = plt.subplots(figsize=(6,4))
        ax.plot(sub["X"], sub["Hardness_LAB"], marker="o", label="LAB")
        ax.plot(sub["X"], sub["Hardness_LINE"], marker="o", label="LINE")
        ax.axhline(lo, linestyle="--")
        ax.axhline(hi, linestyle="--")
        ax.legend()
        ax.grid(alpha=0.3)
        st.pyplot(fig)

    # =========================
    # VIEW 3
    # =========================
    elif view_mode == "📊 Distribution":
        if n < 30:
            st.warning("⚠️ Require ≥ 30 coils")
            continue

        out_rate = (sub["NG_LAB"] | sub["NG_LINE"]).mean()

        if out_rate == 0:
            decision = "🟢 SAFE"
        elif out_rate < 0.05:
            decision = "🟡 WARNING"
        else:
            decision = "🔴 RISK"

        fig, ax = plt.subplots(figsize=(6,4))
        ax.hist(sub["Hardness_LAB"], bins=10, alpha=0.5, label="LAB")
        ax.hist(sub["Hardness_LINE"], bins=10, alpha=0.5, label="LINE")
        ax.axvline(lo, linestyle="--")
        ax.axvline(hi, linestyle="--")
        ax.legend()
        ax.grid(alpha=0.3)

        st.pyplot(fig)
        st.info(f"📌 AUTO DECISION: **{decision}**")

    # =========================
    # VIEW 4
    # =========================
    elif view_mode == "📐 Hardness Safety Analysis":

        mech_ok = sub[sub["MECH_PASS"]].copy()
        mech_ok["HRB_BIN"] = mech_ok["Hardness_LAB"].round().astype("Int64")

        bin_df = mech_ok.groupby("HRB_BIN")["MECH_PASS"].mean().reset_index()

        fig, ax = plt.subplots(figsize=(6,4))
        ax.bar(bin_df["HRB_BIN"], bin_df["MECH_PASS"])
        ax.axhline(1.0, linestyle="--")
        ax.set_ylim(0,1.05)
        ax.grid(alpha=0.3)
        st.pyplot(fig)
