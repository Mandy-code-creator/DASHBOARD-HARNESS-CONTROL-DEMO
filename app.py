# ================================
# FULL STREAMLIT APP – LOGIC CONFIRMED
# - GIỮ NGUYÊN LOGIC QA STRICT (1 NG = FAIL)
# - TÁCH BIỂU ĐỒ LAB / LINE
# - KHÔNG VẼ HARDNESS = 0
# - Y TICK STEP = 2.5 HRB
# - LEGEND Ở NGOÀI BIỂU ĐỒ
# - VIEW MODE: TABLE → TREND → DISTRIBUTION
# ================================

import streamlit as st
import pandas as pd
import numpy as np
import requests
from io import StringIO
import matplotlib.pyplot as plt
from io import BytesIO
# ================================
# UTILITY FUNCTION
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
st.title("📊 Material-level Hardness & Mechanical Detail (Offline only)")

# ================================
# REFRESH BUTTON
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
# CHECK REQUIRED COLUMNS
# ================================
required_cols = [
    "Product_Spec","Material","Rolling_Type","Metallic_Type",
    "Top_Coatmass","Order_Gauge","COIL_NO","Quality_Code",
    "Std_Range_Text","Hardness_LAB","Hardness_LINE","YS","TS","EL"
]

missing = [c for c in required_cols if c not in df.columns]
if missing:
    st.error(f"❌ Missing columns: {missing}")
    st.stop()

# ================================
# SPLIT STANDARD RANGE
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
# FORCE NUMERIC
# ================================
for c in ["Hardness_LAB","Hardness_LINE","YS","TS","EL"]:
    df[c] = pd.to_numeric(df[c], errors="coerce")

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

# ================================
# VIEW MODE
# ================================
view_mode = st.sidebar.radio(
    "📊 View Mode",
    ["📋 Data Table","📈 Trend (LAB / LINE)","📊 Distribution"],
    index=0
)
st.write("DEBUG view_mode =", view_mode)

# ================================
# GROUP CONDITION (≥30 COILS)
# ================================
GROUP_COLS = ["Product_Spec","Material","Metallic_Type","Top_Coatmass","Order_Gauge"]

count_df = (
    df.groupby(GROUP_COLS)
      .agg(N_Coils=("COIL_NO","nunique"))
      .reset_index()
)

valid_conditions = count_df[count_df["N_Coils"] >= 30]

if valid_conditions.empty:
    st.warning("⚠️ No condition with ≥ 30 coils")
    st.stop()

# ================================
# MAIN LOOP
# ================================
for _, cond in valid_conditions.iterrows():

    spec, mat, coat, gauge, n = (
        cond["Product_Spec"], cond["Material"], cond["Top_Coatmass"],
        cond["Order_Gauge"], int(cond["N_Coils"])
    )

    sub = df[
        (df["Product_Spec"] == spec) &
        (df["Material"] == mat) &
        (df["Top_Coatmass"] == coat) &
        (df["Order_Gauge"] == gauge)
    ].copy().sort_values("COIL_NO").reset_index(drop=True)

    lo, hi = sub[["Std_Min","Std_Max"]].iloc[0]

    # ===== QA STRICT LOGIC (KHÔNG ĐỔI) =====
    sub["NG_LAB"]  = (sub["Hardness_LAB"]  < lo) | (sub["Hardness_LAB"]  > hi)
    sub["NG_LINE"] = (sub["Hardness_LINE"] < lo) | (sub["Hardness_LINE"] > hi)
    sub["COIL_NG"] = sub["NG_LAB"] | sub["NG_LINE"]

    n_out = sub[sub["COIL_NG"]]["COIL_NO"].nunique()
    qa_result = "FAIL" if n_out > 0 else "PASS"

    st.markdown(
        f"## 🧱 `{spec}`  \n"
        f"Material: **{mat}** | Coatmass: **{coat}** | Gauge: **{gauge}**  \n"
        f"➡️ n = **{n} coils** | ❌ Out = **{n_out}** | 🧪 **{qa_result}**"
    )

    # ================================
     # ================================
    # VIEW 1 — DATA TABLE
    # ================================
    if view_mode == "📋 Data Table":

        show_cols = [
            "COIL_NO",
            "Std_Min", "Std_Max",
            "Hardness_LAB", "Hardness_LINE",
            "NG_LAB", "NG_LINE",
            "YS", "TS", "EL",
            "Standard_YS_Min", "Standard_YS_Max",
            "Standard_TS_Min", "Standard_TS_Max",
            "Standard_EL_Min", "Standard_EL_Max",
        ]

        show_cols = [c for c in show_cols if c in sub.columns]

        st.dataframe(
            sub[show_cols].sort_values("COIL_NO"),
            use_container_width=True
        )

    # ================================
    # VIEW 2 — TREND
    # ================================
    elif view_mode == "📈 Trend (LAB / LINE)":

        sub["X"] = np.arange(1, len(sub) + 1)

        lab_df  = sub[sub["Hardness_LAB"]  > 0]
        line_df = sub[sub["Hardness_LINE"] > 0]

        y_min = np.floor(min(lo, lab_df["Hardness_LAB"].min(), line_df["Hardness_LINE"].min()))
        y_max = np.ceil (max(hi, lab_df["Hardness_LAB"].max(), line_df["Hardness_LINE"].max()))

        c1, c2 = st.columns(2)

        with c1:
            fig, ax = plt.subplots(figsize=(5,3))
            ax.plot(lab_df["X"], lab_df["Hardness_LAB"], marker="o")
            ax.axhline(lo, linestyle="--")
            ax.axhline(hi, linestyle="--")
            ax.set_ylim(y_min, y_max)
            ax.set_yticks(np.arange(y_min, y_max+0.01, 2.5))
            ax.set_title("Hardness LAB")
            ax.grid(alpha=0.3)
            st.pyplot(fig)
            img = fig_to_png(fig)
            st.download_button(
            "⬇️ Download LAB Trend",
            data=img,
            file_name=f"{spec}_LAB_trend.png",
            mime="image/png",
            key=f"dl_lab_{spec}_{mat}_{gauge}_{coat}"
            )

        with c2:
            fig, ax = plt.subplots(figsize=(5,3))
            ax.plot(line_df["X"], line_df["Hardness_LINE"], marker="o")
            ax.axhline(lo, linestyle="--")
            ax.axhline(hi, linestyle="--")
            ax.set_ylim(y_min, y_max)
            ax.set_yticks(np.arange(y_min, y_max+0.01, 2.5))
            ax.set_title("Hardness LINE")
            ax.grid(alpha=0.3)
            st.pyplot(fig)
            img = fig_to_png(fig)
            st.download_button(
            "⬇️ Download LINE Trend",
            data=img,
            file_name=f"{spec}_LINE_trend.png",
            mime="image/png",
            key=f"dl_line_{spec}_{mat}_{gauge}_{coat}"
            )


    # ================================
    # ================================
    # VIEW 3 — DISTRIBUTION
    # ================================
    elif view_mode == "📊 Distribution":
    
        # ===== FILTER DATA =====
        lab_df  = sub[sub["Hardness_LAB"]  > 0]
        line_df = sub[sub["Hardness_LINE"] > 0]
    
        # ===== STATISTIC =====
        mu_lab   = lab_df["Hardness_LAB"].mean()
        std_lab  = lab_df["Hardness_LAB"].std()
    
        mu_line  = line_df["Hardness_LINE"].mean()
        std_line = line_df["Hardness_LINE"].std()
    
        # ===== FIGURE =====
        fig, ax = plt.subplots(figsize=(6, 4))
    
        # ===== HISTOGRAM =====
        lab_counts, lab_bins, _ = ax.hist(
            lab_df["Hardness_LAB"],
            bins=10,
            alpha=0.5,
            label="LAB",
            edgecolor="black"
        )
    
        line_counts, line_bins, _ = ax.hist(
            line_df["Hardness_LINE"],
            bins=10,
            alpha=0.5,
            label="LINE",
            edgecolor="black"
        )
    
        # ===== NORMAL CURVE LAB (±3σ) =====
        if std_lab > 0:
            x_lab = np.linspace(mu_lab - 3*std_lab, mu_lab + 3*std_lab, 400)
            pdf_lab = (1/(std_lab*np.sqrt(2*np.pi))) * np.exp(
                -0.5 * ((x_lab - mu_lab) / std_lab) ** 2
            )
    
            ax.plot(
                x_lab,
                pdf_lab * len(lab_df) * (lab_bins[1] - lab_bins[0]),
                linestyle="--",
                linewidth=2,
                label="LAB Normal"
            )
    
        # ===== NORMAL CURVE LINE (±3σ) =====
        if std_line > 0:
            x_line = np.linspace(mu_line - 3*std_line, mu_line + 3*std_line, 400)
            pdf_line = (1/(std_line*np.sqrt(2*np.pi))) * np.exp(
                -0.5 * ((x_line - mu_line) / std_line) ** 2
            )
    
            ax.plot(
                x_line,
                pdf_line * len(line_df) * (line_bins[1] - line_bins[0]),
                linestyle="--",
                linewidth=2,
                label="LINE Normal"
            )
    
        # ===== SPEC LIMIT =====
        ax.axvline(lo, linestyle="--", linewidth=1, label="LSL")
        ax.axvline(hi, linestyle="--", linewidth=1, label="USL")
    
        # ===== STAT TEXT (OUTSIDE PLOT) =====
        stat_text = (
            f"LAB  : μ = {mu_lab:.2f}, σ = {std_lab:.2f}\n"
            f"LINE : μ = {mu_line:.2f}, σ = {std_line:.2f}"
        )
    
        ax.text(
            1.02, 0.98,
            stat_text,
            transform=ax.transAxes,
            ha="left",
            va="top",
            fontsize=10,
            bbox=dict(facecolor="white", alpha=0.85, edgecolor="none")
        )
    
        # ===== FINAL STYLE =====
        ax.set_title(f"{spec} | Hardness Distribution")
        ax.set_xlabel("HRB")
        ax.set_ylabel("Count")
        ax.legend(bbox_to_anchor=(1.02, 0.5), loc="center left", frameon=False)
        ax.grid(alpha=0.3)
    
        st.pyplot(fig)
        img = fig_to_png(fig)
        st.download_button(
            "⬇️ Download Distribution Chart",
            data=img,
            file_name=f"{spec}_hardness_distribution.png",
            mime="image/png",
            key=f"dl_dist_{spec}_{mat}_{gauge}_{coat}"
        )


