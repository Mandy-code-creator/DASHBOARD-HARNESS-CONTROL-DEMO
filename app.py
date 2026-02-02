import streamlit as st
import pandas as pd
import numpy as np
import requests
from io import StringIO
import matplotlib.pyplot as plt

# ================================
# PAGE CONFIG
# ================================
st.set_page_config(page_title="Material-level Hardness Detail", layout="wide")
st.title("📊 Material-level Hardness & Mechanical Detail (Offline only)")

# ================================
# BUTTON REFRESH
# ================================
if st.sidebar.button("🔄 Refresh Data"):
    st.cache_data.clear()
    st.rerun()

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
}

df = raw.rename(columns={k: v for k, v in column_mapping.items() if k in raw.columns})

# ================================
# SPLIT STANDARD HARDNESS
# ================================
def split_std(x):
    if isinstance(x, str) and "~" in x:
        try:
            lo, hi = x.split("~")
            return pd.Series([float(lo), float(hi)])
        except:
            pass
    return pd.Series([np.nan, np.nan])

df[["Std_Min", "Std_Max"]] = df["Std_Range_Text"].apply(split_std)
df.drop(columns=["Std_Range_Text"], inplace=True)

# ================================
# FORCE NUMERIC
# ================================
for c in ["Hardness_LAB", "Hardness_LINE", "YS", "TS", "EL"]:
    df[c] = pd.to_numeric(df[c], errors="coerce")

# ================================
# SIDEBAR FILTERS
# ================================
st.sidebar.header("🧩 TASK")
task = st.sidebar.radio(
    "Select Task",
    ["Summary (raw tables)", "QA Strict Spec Check (1 NG = FAIL)"]
)

st.sidebar.header("🎛 FILTERS")

rolling = st.sidebar.radio(
    "Rolling Type",
    sorted(df["Rolling_Type"].dropna().unique())
)
df = df[df["Rolling_Type"] == rolling]

metallic = st.sidebar.radio(
    "Metallic Coating",
    sorted(df["Metallic_Type"].dropna().unique())
)
df = df[df["Metallic_Type"] == metallic]

qc = st.sidebar.radio(
    "Quality Code",
    sorted(df["Quality_Code"].dropna().unique())
)
df = df[df["Quality_Code"] == qc]

# ================================
# GROUP VALID CONDITIONS
# ================================
GROUP_COLS = ["Product_Spec", "Material", "Metallic_Type", "Top_Coatmass", "Order_Gauge"]

valid_conditions = (
    df.groupby(GROUP_COLS)
      .agg(N=("COIL_NO", "nunique"))
      .reset_index()
      .query("N >= 30")
)

if valid_conditions.empty:
    st.warning("⚠️ No condition ≥ 30 coils")
    st.stop()

# =========================================================
# QA STRICT SPEC CHECK
# =========================================================
if task == "QA Strict Spec Check (1 NG = FAIL)":

    for _, cond in valid_conditions.iterrows():

        spec, mat, coat, gauge, n = (
            cond["Product_Spec"],
            cond["Material"],
            cond["Top_Coatmass"],
            cond["Order_Gauge"],
            int(cond["N"])
        )

        sub = df[
            (df["Product_Spec"] == spec) &
            (df["Material"] == mat) &
            (df["Top_Coatmass"] == coat) &
            (df["Order_Gauge"] == gauge)
        ].sort_values("COIL_NO").reset_index(drop=True)

        lo, hi = sub["Std_Min"].iloc[0], sub["Std_Max"].iloc[0]

        # ===== QA LOGIC (UNCHANGED) =====
        sub["NG_LAB"]  = (sub["Hardness_LAB"]  < lo) | (sub["Hardness_LAB"]  > hi)
        sub["NG_LINE"] = (sub["Hardness_LINE"] < lo) | (sub["Hardness_LINE"] > hi)
        sub["COIL_NG"] = sub["NG_LAB"] | sub["NG_LINE"]

        n_out = sub[sub["COIL_NG"]]["COIL_NO"].nunique()
        qa_result = "FAIL" if n_out > 0 else "PASS"

        st.markdown(
            f"## 🧱 `{spec}`  \n"
            f"Material: **{mat}** | Coat: **{coat}** | Gauge: **{gauge}**  \n"
            f"n = **{n}** | ❌ NG = **{n_out}** | 🧪 **{qa_result}**"
        )

        k1, k2, k3 = st.columns(3)
        k1.metric("Total Coils", n)
        k2.metric("Out of Spec", n_out)
        k3.metric("QA Result", qa_result)

        st.dataframe(sub, use_container_width=True)

        # =========================
        # PREPARE CHART DATA
        # =========================
        sub["X"] = sub.index + 1

        lab_df  = sub[sub["Hardness_LAB"]  > 0]
        line_df = sub[sub["Hardness_LINE"] > 0]

        y_min = np.floor(min(lo, lab_df["Hardness_LAB"].min(), line_df["Hardness_LINE"].min()))
        y_max = np.ceil (max(hi, lab_df["Hardness_LAB"].max(), line_df["Hardness_LINE"].max()))

        # =========================
        # CHART — LAB
        # =========================
        fig, ax = plt.subplots(figsize=(9, 3))
        ax.plot(lab_df["X"], lab_df["Hardness_LAB"], marker="o")
        ax.axhline(lo, linestyle="--", label="LSL")
        ax.axhline(hi, linestyle="--", label="USL")
        ax.set_title(f"{spec} | Hardness LAB")
        ax.set_ylim(y_min, y_max)
        ax.set_yticks(np.arange(y_min, y_max + 0.01, 2.5))
        ax.legend(bbox_to_anchor=(1.02, 0.5), loc="center left", frameon=False)
        ax.grid(alpha=0.3)
        st.pyplot(fig)

        # =========================
        # CHART — LINE
        # =========================
        fig, ax = plt.subplots(figsize=(9, 3))
        ax.plot(line_df["X"], line_df["Hardness_LINE"], marker="o")
        ax.axhline(lo, linestyle="--", label="LSL")
        ax.axhline(hi, linestyle="--", label="USL")
        ax.set_title(f"{spec} | Hardness LINE")
        ax.set_ylim(y_min, y_max)
        ax.set_yticks(np.arange(y_min, y_max + 0.01, 2.5))
        ax.legend(bbox_to_anchor=(1.02, 0.5), loc="center left", frameon=False)
        ax.grid(alpha=0.3)
        st.pyplot(fig)
