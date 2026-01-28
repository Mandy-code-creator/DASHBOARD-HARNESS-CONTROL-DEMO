# =============================================================
# SPC DASHBOARD – FINAL VERSION (SPEC-SAFE, AUDIT-READY)
# Author: ChatGPT (QC-oriented implementation)
# =============================================================
# PRINCIPLES
# 1) NEVER DROP INVALID SPEC DATA
# 2) INVALID_SPEC = WARNING ONLY (NO QUANT ANALYSIS)
# 3) SPC & STATISTICS USE VALID_SPEC ONLY
# =============================================================

import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import re

# =============================================================
# PAGE CONFIG
# =============================================================
st.set_page_config(
    page_title="SPC Dashboard – FINAL",
    layout="wide"
)

st.title("📊 SPC Dashboard – Spec-safe & Audit-ready")

# =============================================================
# UTILITIES
# =============================================================

def parse_spec_range(spec):
    """
    Parse spec in form 'a~b'
    Return (Hmin, Hmax, status)
    """
    if pd.isna(spec):
        return np.nan, np.nan, "INVALID_SPEC"

    spec = str(spec).strip()
    match = re.match(r"^\s*([0-9]+\.?[0-9]*)\s*~\s*([0-9]+\.?[0-9]*)\s*$", spec)
    if match:
        return float(match.group(1)), float(match.group(2)), "VALID_SPEC"
    else:
        return np.nan, np.nan, "INVALID_SPEC"


def safe_spc_stats(df, value_col):
    """
    Calculate SPC statistics safely
    ONLY for VALID_SPEC
    """
    if df.empty:
        return None

    x = df[value_col].dropna()
    if len(x) < 2:
        return None

    mean = x.mean()
    std = x.std(ddof=1)
    return {
        "mean": mean,
        "std": std,
        "ucl": mean + 3 * std,
        "lcl": mean - 3 * std,
        "p10": np.percentile(x, 10),
        "p90": np.percentile(x, 90)
    }


# =============================================================
# LOAD DATA – GOOGLE SHEETS (SINGLE SOURCE OF TRUTH)
# =============================================================

DATA_URL = "https://docs.google.com/spreadsheets/d/1GdnY09hJ2qVHuEBAIJ-eU6B5z8ZdgcGf4P7ZjlAt4JI/export?format=csv"

st.sidebar.header("📂 Data Source")
st.sidebar.markdown("**Locked source: Google Sheets**")
st.sidebar.code(DATA_URL)

try:
    df = pd.read_csv(DATA_URL)
except Exception as e:
    st.error("Failed to load data from Google Sheets")
    st.exception(e)
    st.stop()

# =============================================================
# DATA LOADED
# =============================================================

required_cols = [
    "Coil_ID",
    "ORDER NUMBER",  # use ORDER NUMBER instead of Batch
    "Hardness",
    "Standard Hardness",
    "YS",
    "TS",
    "EL",
]

# =============================================================
# =============================================================
# SCHEMA NORMALIZATION (EXPLICIT MAP – LOCKED TO YOUR SHEET)
# =============================================================

# Explicit column mapping based on actual Google Sheets header
EXPLICIT_MAP = {
    "COIL_NO": "Coil_ID",
    "ORDER NUMBER": "ORDER NUMBER",  # keep original name as business key
    "Standard Hardness": "Standard Hardness",
    "HARDNESS 冶金": "Hardness",
    "TENSILE_YIELD": "YS",
    "TENSILE_TENSILE": "TS",
    "TENSILE_ELONG": "EL",
}

# apply explicit mapping
mapped_cols = {}
for c in df.columns:
    if c in EXPLICIT_MAP:
        mapped_cols[c] = EXPLICIT_MAP[c]

df = df.rename(columns=mapped_cols)

required_cols = [
    "Coil_ID",
    "Batch",
    "Hardness",
    "Standard Hardness",
    "YS",
    "TS",
    "EL",
]

missing = [c for c in required_cols if c not in df.columns]
if missing:
    st.error("❌ Missing required columns after EXPLICIT mapping")
    st.write("Missing:", missing)
    st.write("Detected columns:", list(df.columns))
    st.stop()

# =============================================================
# SPEC PARSING (CORE LOGIC)
# =============================================================
df[["Hmin_spec", "Hmax_spec", "Spec_status"]] = df[
    "Standard Hardness"
].apply(lambda x: pd.Series(parse_spec_range(x)))

# =============================================================
# DATA PARTITION
# =============================================================
df_valid = df[df["Spec_status"] == "VALID_SPEC"].copy()
df_invalid = df[df["Spec_status"] == "INVALID_SPEC"].copy()

# =============================================================
# TABS
# =============================================================
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "🏠 Overview",
    "🟢 Hardness SPC",
    "🟢 Mechanical SPC",
    "🔴 Spec Warning",
    "📋 Raw Data"
])

# =============================================================
# TAB 1 – OVERVIEW
# =============================================================
with tab1:
    st.subheader("Overview")

    col1, col2, col3 = st.columns(3)
    col1.metric("Total Records", len(df))
    col2.metric("VALID_SPEC", len(df_valid))
    col3.metric("INVALID_SPEC", len(df_invalid))

    st.markdown("""
    **Rules applied:**
    - INVALID_SPEC is **kept for warning only**
    - SPC / statistics use **VALID_SPEC only**
    - No silent data cleaning
    """)

# =============================================================
# TAB 2 – HARDNESS SPC
# =============================================================
with tab2:
    st.subheader("Hardness SPC (VALID_SPEC only)")

    stats = safe_spc_stats(df_valid, "Hardness")

    if stats is None:
        st.warning("Not enough VALID_SPEC data for SPC analysis")
    else:
        fig, ax = plt.subplots(figsize=(10, 4))
        ax.plot(df_valid.index + 1, df_valid["Hardness"], marker="o")
        ax.axhline(stats["mean"], linestyle="--", label="Mean")
        ax.axhline(stats["ucl"], linestyle=":", label="UCL")
        ax.axhline(stats["lcl"], linestyle=":", label="LCL")
        ax.set_xlabel("Sample")
        ax.set_ylabel("Hardness")
        ax.legend()
        st.pyplot(fig)

        st.json(stats)

# =============================================================
# TAB 3 – MECHANICAL SPC (YS / TS / EL)
# =============================================================
with tab3:
    st.subheader("Mechanical Properties SPC (VALID_SPEC only)")

    for col in ["YS", "TS", "EL"]:
        st.markdown(f"### {col}")
        stats = safe_spc_stats(df_valid, col)

        if stats is None:
            st.warning(f"Not enough data for {col}")
            continue

        fig, ax = plt.subplots(figsize=(10, 3))
        ax.plot(df_valid.index + 1, df_valid[col], marker="o")
        ax.axhline(stats["mean"], linestyle="--")
        ax.axhline(stats["ucl"], linestyle=":")
        ax.axhline(stats["lcl"], linestyle=":")
        ax.set_ylabel(col)
        st.pyplot(fig)

# =============================================================
# TAB 4 – SPEC WARNING
# =============================================================
with tab4:
    st.subheader("⚠️ INVALID SPEC – WARNING ONLY")

    st.markdown("""
    - These records are **NOT used** for SPC or statistics
    - Purpose:
        - QC warning
        - Spec input error detection
        - Master data governance
    """)

    st.dataframe(
        df_invalid[[
            "Coil_ID",
            "Batch",
            "Standard Hardness",
            "Hardness"
        ]]
    )

# =============================================================
# TAB 5 – VARIABILITY TABLES (BY LEVELS)
# =============================================================
with tab5:
    st.subheader("📐 Variability Tables by Level (VALID_SPEC only)")

    st.markdown("""
    Các bảng dưới đây **chỉ dùng VALID_SPEC** để đánh giá **độ biến động (variability)**.
    Mỗi bảng tương ứng **một cấp độ phân tích** khác nhau.
    """)

    df_v = df_valid.copy()

    def variability_table(group_cols, value_col):
        return (
            df_v
            .groupby(group_cols)[value_col]
            .agg([
                ("count", "count"),
                ("mean", "mean"),
                ("std", "std"),
                ("min", "min"),
                ("max", "max")
            ])
            .reset_index()
        )

    # -------- LEVEL 0: COIL LEVEL --------
    st.markdown("### 🧵 By COIL_NO (coil-level variability)")
    for col in ["Hardness", "TS", "YS", "EL"]:
        st.markdown(f"**{col}**")
        st.dataframe(variability_table(["Coil_ID"], col))

    # -------- LEVEL 1: MATERIAL --------
    st.markdown("### 🧱 By Material")
    for col in ["Hardness", "TS", "YS", "EL"]:
        st.markdown(f"**{col}**")
        st.dataframe(variability_table(["Material"], col))

    # -------- LEVEL 2: MATERIAL + COATING --------
    st.markdown("### 🎨 By Material + Coating")
    for col in ["Hardness", "TS", "YS", "EL"]:
        st.markdown(f"**{col}**")
        st.dataframe(variability_table(["Material", "Coating"], col))

    # -------- LEVEL 3: MATERIAL + COATING + THICKNESS --------
    st.markdown("### 📏 By Material + Coating + Thickness")
    for col in ["Hardness", "TS", "YS", "EL"]:
        st.markdown(f"**{col}**")
        st.dataframe(variability_table(["Material", "Coating", "Thickness"], col))

# =============================================================
# END OF FILE
# =============================================================
with tab5:
    st.subheader("Raw Data (Full, Unfiltered)")
    st.dataframe(df)

# =============================================================
# END OF FILE
# =============================================================
