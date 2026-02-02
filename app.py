import streamlit as st
import pandas as pd
import numpy as np
import requests
from io import StringIO
import matplotlib.pyplot as plt

# ================================
# BUTTON REFRESH GOOGLE SHEET
# ================================
if st.sidebar.button("🔄 Refresh Data"):
    st.cache_data.clear()
    st.rerun()
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
# FORCE FIND & CREATE METALLIC TYPE COLUMN
# ================================
metal_col = None
for c in raw.columns:
    if "METALLIC" in c.upper() and "COATING" in c.upper():
        metal_col = c
        break

if metal_col is None:
    st.error("❌ Cannot find METALLIC COATING TYPE column in raw data")
    st.stop()

raw["Metallic_Type"] = raw[metal_col]

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
# REQUIRED COLUMNS CHECK
# ================================
required_cols = [
    "Product_Spec", "Material", "Top_Coatmass", "Order_Gauge",
    "COIL_NO", "Quality_Code", "Rolling_Type", 
    "Std_Range_Text", "Hardness_LAB", "Hardness_LINE",
    "YS", "TS", "EL", "Metallic_Type",

]

missing = [c for c in required_cols if c not in df.columns]
if missing:
    st.error(f"❌ Missing required columns: {missing}")
    st.stop()

# ================================
# SPLIT STANDARD HARDNESS
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
# SIDEBAR – TASK
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
# ROLLING TYPE FILTER (FROM SHEET)
# ================================
st.sidebar.header("🎛 ROLLING TYPE")

rolling_types = sorted(df["Rolling_Type"].dropna().unique())

selected_rolling = st.sidebar.radio(
    "Select Rolling Type",
    rolling_types
)

df = df[df["Rolling_Type"] == selected_rolling]

# ================================
# METALLIC COATING TYPE FILTER
# ================================
st.sidebar.header("🎛 METALLIC COATING TYPE")

metallic_types = sorted(df["Metallic_Type"].dropna().unique())

selected_metallic = st.sidebar.radio(
    "Select Metallic Coating Type",
    metallic_types
)

df = df[df["Metallic_Type"] == selected_metallic]

# ================================
# QUALITY CODE FILTER
# ================================
st.sidebar.header("🎛 QUALITY CODE")
quality_codes = sorted(df["Quality_Code"].dropna().unique())
selected_qc = st.sidebar.radio("Select Quality Code", quality_codes)
df = df[df["Quality_Code"] == selected_qc]
# ================================


# ================================
# GROUP + COUNT (>=30 coils)
# ================================
GROUP_COLS = ["Product_Spec", "Material", "Metallic_Type", "Top_Coatmass", "Order_Gauge"]

count_df = (
    df.groupby(GROUP_COLS)
      .agg(N_Coils=("COIL_NO", "nunique"))
      .reset_index()
)

valid_conditions = (
    count_df[count_df["N_Coils"] >= 30]
    .sort_values("N_Coils", ascending=False)
)

if valid_conditions.empty:
    st.warning("⚠️ No condition has ≥ 30 coils")
    st.stop()

# =========================================================
# SUMMARY
# =========================================================
if task == "Summary (raw tables)":

    st.subheader("📋 Coil-level Data (Offline measurements only)")
    st.caption("≥ 30 coils | No averaging | Raw data only")

    for _, cond in valid_conditions.iterrows():

        spec, mat, coat, gauge, n = (
            cond["Product_Spec"],
            cond["Material"],
            cond["Top_Coatmass"],
            cond["Order_Gauge"],
            int(cond["N_Coils"])
        )

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
if task == "QA Strict Spec Check (1 NG = FAIL)":

    st.subheader("🧪 QA Strict Spec Check – Coil level")
    st.caption("If ANY coil is out of spec → FAIL")

    for _, cond in valid_conditions.iterrows():

        spec, mat, coat, gauge, n = (
            cond["Product_Spec"],
            cond["Material"],
            cond["Top_Coatmass"],
            cond["Order_Gauge"],
            int(cond["N_Coils"])
        )

        sub = df[
            (df["Product_Spec"] == spec) &
            (df["Material"] == mat) &
            (df["Top_Coatmass"] == coat) &
            (df["Order_Gauge"] == gauge)
        ].copy()

        lo = sub["Std_Min"].iloc[0]
        hi = sub["Std_Max"].iloc[0]

        # ===== NG LOGIC =====
        sub["NG_LAB"]  = (sub["Hardness_LAB"]  < lo) | (sub["Hardness_LAB"]  > hi)
        sub["NG_LINE"] = (sub["Hardness_LINE"] < lo) | (sub["Hardness_LINE"] > hi)

        sub["COIL_NG"] = sub["NG_LAB"] | sub["NG_LINE"]

        # ===== DELTA & OUT OF LIMIT =====
        sub["Δ_LINE_LAB"] = sub["Hardness_LINE"] - sub["Hardness_LAB"]

        sub["OOL_LAB"] = np.where(
            sub["Hardness_LAB"] > hi, sub["Hardness_LAB"] - hi,
            np.where(sub["Hardness_LAB"] < lo, lo - sub["Hardness_LAB"], 0)
        )

        sub["OOL_LINE"] = np.where(
            sub["Hardness_LINE"] > hi, sub["Hardness_LINE"] - hi,
            np.where(sub["Hardness_LINE"] < lo, lo - sub["Hardness_LINE"], 0)
        )

        n_out = sub[sub["COIL_NG"]]["COIL_NO"].nunique()
        qa_result = "FAIL" if n_out > 0 else "PASS"

        st.markdown(
            f"## 🧱 Product Spec: `{spec}`  \n"
            f"**Material:** {mat} | **Coatmass:** {coat} | **Gauge:** {gauge}  \n"
            f"➡️ **n = {n} coils**  \n"
            f"❌ **n_out = {n_out} coils out of spec**  \n"
            f"🧪 **QA Result:** `{qa_result}`"
        )

        show_cols = [
            "COIL_NO",
            "Std_Min", "Std_Max",
            "Hardness_LAB", "Hardness_LINE",
            "Δ_LINE_LAB",
            "OOL_LAB", "OOL_LINE",
            "NG_LAB", "NG_LINE",
            "YS", "TS", "EL"
        ]

        st.dataframe(
            sub[show_cols].sort_values("COIL_NO"),
            use_container_width=True
        )
        # =========================
        # PREPARE DATA FOR CHART
        # =========================
        sub_plot = sub.sort_values("COIL_NO").reset_index(drop=True).copy()
        sub_plot["X"] = sub_plot.index + 1

        # ❌ KHÔNG VẼ HARDNESS = 0
        lab_df  = sub_plot[sub_plot["Hardness_LAB"]  > 0]
        line_df = sub_plot[sub_plot["Hardness_LINE"] > 0]

        # Y SCALE (INTEGER STEP)
        y_min = int(np.floor(min(lo, lab_df["Hardness_LAB"].min(), line_df["Hardness_LINE"].min())))
        y_max = int(np.ceil (max(hi, lab_df["Hardness_LAB"].max(), line_df["Hardness_LINE"].max())))

        # =========================
        # CHART 1 — HARDNESS LAB
        # =========================
        fig_lab, ax_lab = plt.subplots(figsize=(9, 3))

        ax_lab.plot(
            lab_df["X"],
            lab_df["Hardness_LAB"],
            marker="o",
            linewidth=2,
            label="LAB"
        )

        ax_lab.axhline(lo, linestyle="--", linewidth=1, label="LSL")
        ax_lab.axhline(hi, linestyle="--", linewidth=1, label="USL")

        ax_lab.set_title(f"{spec} | Hardness LAB")
        ax_lab.set_ylabel("HRB")
        ax_lab.set_xlabel("Coil order (by COIL_NO)")
        ax_lab.set_ylim(y_min, y_max)
        ax_lab.set_yticks(np.arange(y_min, y_max + 0.01, 2.5))
        ax_lab.grid(alpha=0.3)

        ax_lab.legend(
            loc="center left",
            bbox_to_anchor=(1.02, 0.5),
            frameon=False
        )

        st.pyplot(fig_lab)

        # =========================
        # CHART 2 — HARDNESS LINE
        # =========================
        fig_line, ax_line = plt.subplots(figsize=(9, 3))

        ax_line.plot(
            line_df["X"],
            line_df["Hardness_LINE"],
            marker="o",
            linewidth=2,
            label="LINE"
        )

        ax_line.axhline(lo, linestyle="--", linewidth=1, label="LSL")
        ax_line.axhline(hi, linestyle="--", linewidth=1, label="USL")

        ax_line.set_title(f"{spec} | Hardness LINE")
        ax_line.set_ylabel("HRB")
        ax_line.set_xlabel("Coil order (by COIL_NO)")
        ax_line.set_ylim(y_min, y_max)
        ax_line.set_yticks(np.arange(y_min, y_max + 0.01, 2.5))
        ax_line.grid(alpha=0.3)

        ax_line.legend(
            loc="center left",
            bbox_to_anchor=(1.02, 0.5),
            frameon=False
        )

        st.pyplot(fig_line)
