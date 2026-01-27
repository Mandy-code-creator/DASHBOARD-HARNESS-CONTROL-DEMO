import streamlit as st
import pandas as pd
import numpy as np

# =========================
# PAGE CONFIG
# =========================
st.set_page_config(page_title="GI Hardness Control", layout="wide")

# =========================
# LOAD DATA
# =========================
@st.cache_data
def load_data():
    url = "https://docs.google.com/spreadsheets/d/1GdnY09hJ2qVHuEBAIJ-eU6B5z8ZdgcGf4P7ZjlAt4JI/export?format=csv"
    df = pd.read_csv(url)

    # --- strip column names ---
    df.columns = [c.strip() for c in df.columns]

    # --- parse Standard Hardness: "56~62" ---
    def parse_spec(x):
        try:
            if isinstance(x, str) and "~" in x:
                a, b = x.split("~")
                return float(a), float(b)
        except:
            pass
        return np.nan, np.nan

    df[["Hmin_spec", "Hmax_spec"]] = df["Standard Hardness"].apply(
        lambda x: pd.Series(parse_spec(x))
    )

    df["Spec_status"] = np.where(
        df["Hmin_spec"].isna() | df["Hmax_spec"].isna(),
        "INVALID_SPEC",
        "VALID_SPEC"
    )

    # --- numeric columns ---
    num_cols = [
        "ORDER GAUGE",
        "TOP COATMASS",
        "HARDNESS 冶金",
        "HARDNESS 鍍鋅線 C",
        "TENSILE_YIELD",
        "TENSILE_TENSILE",
        "TENSILE_ELONG"
    ]
    for c in num_cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")

    return df

df = load_data()

# =========================
# SIDEBAR FILTERS (SAFE)
# =========================
st.sidebar.header("Filters")

def safe_multiselect(label, series):
    opts = sorted(series.dropna().unique().tolist())
    if len(opts) == 0:
        return []
    return st.sidebar.multiselect(label, opts, default=opts)

f_quality = safe_multiselect("QUALITY_CODE", df["QUALITY_CODE"])
f_spec    = safe_multiselect("PRODUCT SPECIFICATION CODE", df["PRODUCT SPECIFICATION CODE"])
f_grade   = safe_multiselect("HR STEEL GRADE", df["HR STEEL GRADE"])
f_gauge   = safe_multiselect("ORDER GAUGE", df["ORDER GAUGE"])
f_coat    = safe_multiselect("TOP COATMASS", df["TOP COATMASS"])

df_f = df[
    df["QUALITY_CODE"].isin(f_quality)
    & df["PRODUCT SPECIFICATION CODE"].isin(f_spec)
    & df["HR STEEL GRADE"].isin(f_grade)
    & df["ORDER GAUGE"].isin(f_gauge)
    & df["TOP COATMASS"].isin(f_coat)
]

if df_f.empty:
    st.warning("Filter too strict – fallback to full dataset")
    df_f = df.copy()

# =========================
# DERIVED VALUES (ONLY VALID SPEC)
# =========================
df_v = df_f[df_f["Spec_status"] == "VALID_SPEC"].copy()

df_v["ΔH_LAB_high"]  = df_v["HARDNESS 冶金"] - df_v["Hmax_spec"]
df_v["ΔH_LINE_high"] = df_v["HARDNESS 鍍鋅線 C"] - df_v["Hmax_spec"]
df_v["ΔH_LINE_LAB"]  = df_v["HARDNESS 鍍鋅線 C"] - df_v["HARDNESS 冶金"]

# =========================
# TABS
# =========================
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "Overview",
    "Hardness",
    "Mechanical",
    "Group Summary",
    "Spec Warning"
])

# =========================
# TAB 1 – OVERVIEW
# =========================
with tab1:
    st.subheader("Overview")

    col1, col2, col3 = st.columns(3)

    col1.metric("Total Coils", len(df_f))
    col2.metric("Valid Spec", (df_f["Spec_status"] == "VALID_SPEC").sum())
    col3.metric("Invalid Spec", (df_f["Spec_status"] == "INVALID_SPEC").sum())

    if len(df_v) > 0:
        p10 = np.percentile(df_v["ΔH_LINE_high"].dropna(), 10)
        st.metric("LINE ΔH vs Hmax (P10)", f"{p10:.2f} HRB")

# =========================
# TAB 2 – HARDNESS
# =========================
with tab2:
    st.subheader("Hardness Analysis (VALID SPEC ONLY)")

    show_cols = [
        "QUALITY_CODE",
        "PRODUCT SPECIFICATION CODE",
        "HR STEEL GRADE",
        "ORDER GAUGE",
        "TOP COATMASS",
        "Hmin_spec",
        "Hmax_spec",
        "HARDNESS 冶金",
        "HARDNESS 鍍鋅線 C",
        "ΔH_LAB_high",
        "ΔH_LINE_high",
        "ΔH_LINE_LAB"
    ]
    st.dataframe(df_v[show_cols])

# =========================
# TAB 3 – MECHANICAL
# =========================
with tab3:
    st.subheader("Mechanical Properties")

    mech_cols = [
        "QUALITY_CODE",
        "ORDER GAUGE",
        "TOP COATMASS",
        "HARDNESS 鍍鋅線 C",
        "TENSILE_YIELD",
        "TENSILE_TENSILE",
        "TENSILE_ELONG"
    ]
    st.dataframe(df_v[mech_cols])

# =========================
# TAB 4 – GROUP SUMMARY
# =========================
with tab4:
    st.subheader("Group Mean Summary")

    group_cols = [
        "QUALITY_CODE",
        "PRODUCT SPECIFICATION CODE",
        "HR STEEL GRADE",
        "ORDER GAUGE",
        "TOP COATMASS"
    ]

    summary = (
        df_v
        .groupby(group_cols)
        .agg(
            coils=("HARDNESS 冶金", "count"),
            H_LAB_mean=("HARDNESS 冶金", "mean"),
            H_LINE_mean=("HARDNESS 鍍鋅線 C", "mean"),
            ΔH_LINE_P10=("ΔH_LINE_high", lambda x: np.percentile(x.dropna(), 10) if len(x.dropna()) > 0 else np.nan),
            YS_mean=("TENSILE_YIELD", "mean"),
            TS_mean=("TENSILE_TENSILE", "mean"),
            EL_mean=("TENSILE_ELONG", "mean")
        )
        .reset_index()
    )

    st.dataframe(summary)

# =========================
# TAB 5 – SPEC WARNING
# =========================
with tab5:
    st.subheader("INVALID STANDARD HARDNESS")

    warn_cols = [
        "QUALITY_CODE",
        "PRODUCT SPECIFICATION CODE",
        "HR STEEL GRADE",
        "ORDER GAUGE",
        "TOP COATMASS",
        "Standard Hardness"
    ]

    st.dataframe(df_f[df_f["Spec_status"] == "INVALID_SPEC"][warn_cols])
