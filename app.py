# =============================================================
# HARDNESS & MECHANICAL PROPERTY CONTROL DASHBOARD
# Streamlit – 5 Tabs | Robust Filters | No-empty logic
# =============================================================
import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

st.set_page_config(page_title="Hardness Control Dashboard", layout="wide")

# =============================================================
# DATA LOADING
# =============================================================
@st.cache_data
def load_data():
    url = "https://docs.google.com/spreadsheets/d/1GdnY09hJ2qVHuEBAIJ-eU6B5z8ZdgcGf4P7ZjlAt4JI/export?format=csv"
    df = pd.read_csv(url)

    # ---- normalize column names ----
    df.columns = df.columns.str.strip()

    numeric_cols = [
        "Standard Hardness",
        "HARDNESS 冶金",
        "HARDNESS 鍍鋅線 N",
        "HARDNESS 鍍鋅線 C",
        "HARDNESS 鍍鋅線 S",
        "TOP COATMASS",
        "ORDER GAUGE",
        "TENSILE_YIELD",
        "TENSILE_TENSILE",
        "TENSILE_ELONG",
    ]

    for c in numeric_cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")

    return df


df = load_data()

# =============================================================
# SIDEBAR FILTERS (NEVER EMPTY)
# =============================================================
st.sidebar.header("🔎 Filters")

# ---- helper: safe multiselect ----
def safe_multiselect(label, series):
    opts = sorted(series.dropna().unique().tolist())
    if not opts:
        return []
    return st.sidebar.multiselect(label, opts, default=opts)

quality_sel = safe_multiselect("QUALITY_CODE", df["QUALITY_CODE"])
material_sel = safe_multiselect("HR STEEL GRADE", df["HR STEEL GRADE"])
standard_sel = safe_multiselect("Standard", df.get("冶金/ Standard", pd.Series()))

# coating by TOP COATMASS (grouped)
if "TOP COATMASS" in df.columns:
    coat_bins = pd.cut(df["TOP COATMASS"], bins=[0,50,100,150,200,300,1000])
    df["COATING_GROUP"] = coat_bins.astype(str)
else:
    df["COATING_GROUP"] = "UNKNOWN"

coating_sel = safe_multiselect("Coating (TOP COATMASS)", df["COATING_GROUP"])

# thickness filter
if "ORDER GAUGE" in df.columns:
    g_min, g_max = float(df["ORDER GAUGE"].min()), float(df["ORDER GAUGE"].max())
    gauge_range = st.sidebar.slider("Thickness (ORDER GAUGE)", g_min, g_max, (g_min, g_max))
else:
    gauge_range = None

# =============================================================
# APPLY FILTERS
# =============================================================
df_f = df.copy()

if quality_sel:
    df_f = df_f[df_f["QUALITY_CODE"].isin(quality_sel)]
if material_sel:
    df_f = df_f[df_f["HR STEEL GRADE"].isin(material_sel)]
if standard_sel and "冶金/ Standard" in df_f.columns:
    df_f = df_f[df_f["冶金/ Standard"].isin(standard_sel)]
if coating_sel:
    df_f = df_f[df_f["COATING_GROUP"].isin(coating_sel)]
if gauge_range and "ORDER GAUGE" in df_f.columns:
    df_f = df_f[(df_f["ORDER GAUGE"] >= gauge_range[0]) & (df_f["ORDER GAUGE"] <= gauge_range[1])]

# ---- GUARANTEE NOT EMPTY ----
if df_f.empty:
    st.warning("⚠️ Filter too strict – showing full dataset")
    df_f = df.copy()

# =============================================================
# DERIVED METRICS (SAFE)
# =============================================================
if {"HARDNESS 冶金","Standard Hardness"}.issubset(df_f.columns):
    df_f["ΔH_LAB"] = df_f["HARDNESS 冶金"] - df_f["Standard Hardness"]
else:
    df_f["ΔH_LAB"] = np.nan

# =============================================================
# TABS LAYOUT (5 TABS)
# =============================================================
T1, T2, T3, T4, T5 = st.tabs([
    "📊 Overview",
    "🧪 Hardness Analysis",
    "🏭 Material / Standard",
    "🧮 Mechanical Properties",
    "📋 Summary Tables",
])

# =============================================================
# TAB 1 – OVERVIEW
# =============================================================
with T1:
    st.subheader("Overall Snapshot")

    c1, c2, c3 = st.columns(3)

    if df_f["ΔH_LAB"].dropna().shape[0] > 0:
        c1.metric("Mean ΔH LAB", f"{df_f['ΔH_LAB'].mean():.2f}")
        c2.metric("P10 ΔH LAB", f"{np.percentile(df_f['ΔH_LAB'].dropna(),10):.2f}")
        c3.metric("P90 ΔH LAB", f"{np.percentile(df_f['ΔH_LAB'].dropna(),90):.2f}")
    else:
        st.info("Not enough hardness data")

# =============================================================
# TAB 2 – HARDNESS ANALYSIS
# =============================================================
with T2:
    st.subheader("Hardness vs Coating & Thickness")

    fig, ax = plt.subplots()
    ax.scatter(df_f["TOP COATMASS"], df_f["HARDNESS 冶金"], alpha=0.6)
    ax.set_xlabel("TOP COATMASS")
    ax.set_ylabel("HARDNESS 冶金")
    st.pyplot(fig)

# =============================================================
# TAB 3 – MATERIAL / STANDARD RELATION
# =============================================================
with T3:
    st.subheader("Material × Standard × Thickness")

    grp = (
        df_f.groupby([
            "QUALITY_CODE",
            "HR STEEL GRADE",
            "冶金/ Standard",
            "COATING_GROUP",
        ])
        .agg(
            Mean_H_LAB=("HARDNESS 冶金","mean"),
            Mean_H_LINE=("HARDNESS 鍍鋅線 N","mean"),
            Count=("HARDNESS 冶金","count"),
        )
        .reset_index()
    )

    st.dataframe(grp)

# =============================================================
# TAB 4 – MECHANICAL PROPERTIES
# =============================================================
with T4:
    st.subheader("Tensile Properties")

    cols = ["TENSILE_YIELD","TENSILE_TENSILE","TENSILE_ELONG"]
    for c in cols:
        if c in df_f.columns:
            fig, ax = plt.subplots()
            ax.hist(df_f[c].dropna(), bins=20)
            ax.set_title(c)
            st.pyplot(fig)

# =============================================================
# TAB 5 – SUMMARY TABLES
# =============================================================
with T5:
    st.subheader("Mean Hardness Table")

    summary = (
        df_f.groupby([
            "QUALITY_CODE",
            "HR STEEL GRADE",
            "冶金/ Standard",
            "ORDER GAUGE",
            "COATING_GROUP",
        ])
        .agg(
            Mean_H_LAB=("HARDNESS 冶金","mean"),
            Mean_H_LINE=("HARDNESS 鍍鋅線 N","mean"),
            Mean_YS=("TENSILE_YIELD","mean"),
            Mean_TS=("TENSILE_TENSILE","mean"),
            Mean_EL=("TENSILE_ELONG","mean"),
            Count=("HARDNESS 冶金","count"),
        )
        .reset_index()
    )

    st.dataframe(summary)
