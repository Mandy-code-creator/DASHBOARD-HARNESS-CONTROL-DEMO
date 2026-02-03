# ================================
# HARDNESS CONTROL DASHBOARD
# Views 1–2–3 giữ nguyên logic dữ liệu
# View 4: Hardness Safety Analysis (không phá logic cũ)
# ================================

import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from io import BytesIO

# ================================
# CONFIG
# ================================
st.set_page_config(page_title="Hardness Control Dashboard", layout="wide")

DATA_URL = "https://docs.google.com/spreadsheets/d/1GdnY09hJ2qVHuEBAIJ-eU6B5z8ZdgcGf4P7ZjlAt4JI/export?format=csv"

# ================================
# UTILS
# ================================
def fig_to_png(fig, dpi=200):
    buf = BytesIO()
    fig.savefig(buf, format="png", dpi=dpi, bbox_inches="tight")
    buf.seek(0)
    return buf

# ================================
# LOAD DATA
# ================================
@st.cache_data
def load_data():
    return pd.read_csv(DATA_URL)

df = load_data()

# ================================
# SIDEBAR FILTER (GIỮ NGUYÊN)
# ================================
st.sidebar.header("Filter")
spec = st.sidebar.selectbox("Product Spec", sorted(df["Product_Spec"].dropna().unique()))
material = st.sidebar.selectbox("Material", sorted(df["Material"].dropna().unique()))
coat = st.sidebar.selectbox("Top Coat", sorted(df["Top_Coatmass"].dropna().unique()))
gauge = st.sidebar.selectbox("Gauge", sorted(df["Order_Gauge"].dropna().unique()))

view_mode = st.sidebar.radio(
    "View Mode",
    [
        "📈 Trend (LAB / LINE)",
        "📊 Distribution",
        "📐 Hardness Safety Analysis"
    ]
)

# ================================
# FILTER SUB (⚠️ TUYỆT ĐỐI KHÔNG ĐỤNG LOGIC CŨ)
# ================================
sub = df[
    (df["Product_Spec"] == spec) &
    (df["Material"] == material) &
    (df["Top_Coatmass"] == coat) &
    (df["Order_Gauge"] == gauge)
].copy().sort_values("COIL_NO").reset_index(drop=True)

if sub.empty:
    st.warning("No data after filter")
    st.stop()

# STD HARDNESS (logic cũ)
lo, hi = sub[["Std_Min", "Std_Max"]].iloc[0]

lab_df = sub.dropna(subset=["Hardness_LAB"])
line_df = sub.dropna(subset=["Hardness_LINE"])

# ================================
# VIEW 1 — TREND (GIỮ NGUYÊN)
# ================================
if view_mode == "📈 Trend (LAB / LINE)":

    c1, c2 = st.columns(2)

    for title, df_plot, col, label, col_ui in [
        ("LAB", lab_df, "Hardness_LAB", "lab", c1),
        ("LINE", line_df, "Hardness_LINE", "line", c2)
    ]:
        with col_ui:
            fig, ax = plt.subplots(figsize=(5,3))
            ax.plot(df_plot.index + 1, df_plot[col], marker="o")
            ax.axhline(lo, linestyle="--")
            ax.axhline(hi, linestyle="--")
            ax.set_title(f"Hardness {title}")
            ax.set_xlabel("Coil Order")
            ax.set_ylabel("HRB")
            ax.grid(alpha=0.3)
            st.pyplot(fig)
            st.download_button(
                f"⬇️ Download {title} Trend",
                data=fig_to_png(fig),
                file_name=f"{spec}_{title}_trend.png",
                mime="image/png",
                key=f"dl_{label}_{spec}_{gauge}"
            )

# ================================
# VIEW 2 — DISTRIBUTION (GIỮ NGUYÊN)
# ================================
elif view_mode == "📊 Distribution":

    fig, ax = plt.subplots(figsize=(6,4))
    ax.hist(lab_df["Hardness_LAB"], bins=10, alpha=0.5, label="LAB")
    ax.hist(line_df["Hardness_LINE"], bins=10, alpha=0.5, label="LINE")
    ax.axvline(lo, linestyle="--")
    ax.axvline(hi, linestyle="--")
    ax.set_xlabel("HRB")
    ax.set_ylabel("Count")
    ax.legend()
    ax.grid(alpha=0.3)
    st.pyplot(fig)

    st.download_button(
        "⬇️ Download Distribution",
        data=fig_to_png(fig),
        file_name=f"{spec}_distribution.png",
        mime="image/png",
        key=f"dl_dist_{spec}_{gauge}"
    )

# ================================
# VIEW 3 — HARDNESS SAFETY (CHỈ THÊM, KHÔNG PHÁ)
# ================================
elif view_mode == "📐 Hardness Safety Analysis":

    st.markdown("## 📐 Hardness Safety Analysis (Bin = 1 HRB)")
    st.caption("🎯 SAFE = 100% PASS YS + TS + EL")

    mech_cols = [
        "YS", "TS", "EL",
        "Standard_YS_Min", "Standard_YS_Max",
        "Standard_TS_Min", "Standard_TS_Max",
        "Standard_EL_Min", "Standard_EL_Max"
    ]

    missing = [c for c in mech_cols if c not in sub.columns]
    if missing:
        st.warning(f"⚠️ Missing mechanical standard columns: {missing}")
        st.stop()

    sub["MECH_PASS"] = (
        (sub["YS"] >= sub["Standard_YS_Min"]) & (sub["YS"] <= sub["Standard_YS_Max"]) &
        (sub["TS"] >= sub["Standard_TS_Min"]) & (sub["TS"] <= sub["Standard_TS_Max"]) &
        (sub["EL"] >= sub["Standard_EL_Min"]) & (sub["EL"] <= sub["Standard_EL_Max"])
    )

    mech_ok = sub[sub["MECH_PASS"]].copy()

    mech_ok["HRB_LAB_BIN"]  = mech_ok["Hardness_LAB"].round().astype("Int64")
    mech_ok["HRB_LINE_BIN"] = mech_ok["Hardness_LINE"].round().astype("Int64")

    c1, c2 = st.columns(2)

    # LAB
    with c1:
        lab_bin = mech_ok.groupby("HRB_LAB_BIN").agg(
            n=("COIL_NO", "count"), pass_rate=("MECH_PASS", "mean")
        ).reset_index()

        fig, ax = plt.subplots(figsize=(5,4))
        ax.bar(lab_bin["HRB_LAB_BIN"], lab_bin["pass_rate"])
        ax.axhline(1.0, linestyle="--")
        ax.set_ylim(0, 1.05)
        ax.set_title("LAB – SAFE HRB")
        ax.grid(alpha=0.3)
        st.pyplot(fig)

    # LINE
    with c2:
        line_bin = mech_ok.groupby("HRB_LINE_BIN").agg(
            n=("COIL_NO", "count"), pass_rate=("MECH_PASS", "mean")
        ).reset_index()

        fig, ax = plt.subplots(figsize=(5,4))
        ax.bar(line_bin["HRB_LINE_BIN"], line_bin["pass_rate"])
        ax.axhline(1.0, linestyle="--")
        ax.set_ylim(0, 1.05)
        ax.set_title("LINE – SAFE HRB")
        ax.grid(alpha=0.3)
        st.pyplot(fig)
