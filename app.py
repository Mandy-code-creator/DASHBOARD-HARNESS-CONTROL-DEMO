import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

st.set_page_config(
    page_title="Hardness & Mechanical Control Dashboard",
    layout="wide"
)

# =========================
# SAFE STAT FUNCTIONS
# =========================
def safe_percentile(series, q):
    s = series.dropna()
    if len(s) == 0:
        return None
    return np.percentile(s, q)

def safe_mean(series):
    s = series.dropna()
    if len(s) == 0:
        return None
    return s.mean()

# =========================
# LOAD DATA
# =========================
@st.cache_data
def load_data():
    url = "https://docs.google.com/spreadsheets/d/1GdnY09hJ2qVHuEBAIJ-eU6B5z8ZdgcGf4P7ZjlAt4JI/export?format=csv"
    df = pd.read_csv(url)

    # clean column names
    df.columns = [c.strip() for c in df.columns]

    # numeric columns ONLY (TOP COATMASS IS NOT HERE!)
    num_cols = [
        "Standard Hardness",
        "HARDNESS 冶金",
        "HARDNESS 鍍鋅線 N",
        "HARDNESS 鍍鋅線 C",
        "HARDNESS 鍍鋅線 S",
        "TENSILE_YIELD",
        "TENSILE_TENSILE",
        "TENSILE_ELONG",
        "ORDER GAUGE",
    ]

    for c in num_cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")

    # 🔥 COATING: keep category + extract numeric
    df["TOP COATMASS"] = df["TOP COATMASS"].astype(str).str.strip()

    df["COATING_MASS_NUM"] = (
        df["TOP COATMASS"]
        .str.extract(r"(\d+)")
        .astype(float)
    )

    return df

df0 = load_data()

# =========================
# SIDEBAR FILTERS (ROBUST)
# =========================
st.sidebar.header("🔎 Hierarchical Filters")

df_f = df0.copy()

def apply_filter(df_base, df_current, col, label):
    options = sorted(df_base[col].dropna().unique())
    selected = st.sidebar.multiselect(label, options, default=options)
    return df_current[df_current[col].isin(selected)]

df_f = apply_filter(df0, df_f, "QUALITY_CODE", "QUALITY CODE")
df_f = apply_filter(df0, df_f, "PRODUCT SPECIFICATION CODE", "STANDARD")
df_f = apply_filter(df0, df_f, "HR STEEL GRADE", "MATERIAL")
df_f = apply_filter(df0, df_f, "ORDER GAUGE", "THICKNESS")
df_f = apply_filter(df0, df_f, "TOP COATMASS", "COATING TYPE")

st.sidebar.write("✅ Rows after filter:", len(df_f))

if df_f.empty:
    st.error("❌ No data after filtering – combination does not exist")
    st.stop()

# =========================
# CALCULATION
# =========================
df_f["ΔH_LAB"] = df_f["HARDNESS 冶金"] - df_f["Standard Hardness"]
df_f["ΔH_LINE_N"] = df_f["HARDNESS 鍍鋅線 N"] - df_f["Standard Hardness"]
df_f["ΔH_LINE_C"] = df_f["HARDNESS 鍍鋅線 C"] - df_f["Standard Hardness"]
df_f["ΔH_LINE_S"] = df_f["HARDNESS 鍍鋅線 S"] - df_f["Standard Hardness"]

# =========================
# TABS
# =========================
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "1️⃣ Overview",
    "2️⃣ Hardness Analysis",
    "3️⃣ Mechanical Properties",
    "4️⃣ Thickness & Coating Effect",
    "5️⃣ Control Suggestion"
])

# =========================
# TAB 1 – OVERVIEW
# =========================
with tab1:
    st.subheader("Dataset Overview")
    st.dataframe(df_f, use_container_width=True)

    c1, c2, c3 = st.columns(3)
    c1.metric("Samples", len(df_f))
    c2.metric(
        "Mean Std Hardness",
        f"{safe_mean(df_f['Standard Hardness']):.1f}"
        if safe_mean(df_f['Standard Hardness']) is not None else "N/A"
    )
    c3.metric(
        "Mean LAB Hardness",
        f"{safe_mean(df_f['HARDNESS 冶金']):.1f}"
        if safe_mean(df_f['HARDNESS 冶金']) is not None else "N/A"
    )

# =========================
# TAB 2 – HARDNESS
# =========================
with tab2:
    st.subheader("Hardness vs Standard (LAB)")

    fig, ax = plt.subplots()
    ax.hist(df_f["ΔH_LAB"].dropna(), bins=20)
    ax.axvline(0, linestyle="--")
    ax.set_xlabel("ΔH (LAB - Standard)")
    st.pyplot(fig)

    p10 = safe_percentile(df_f["ΔH_LAB"], 10)
    p90 = safe_percentile(df_f["ΔH_LAB"], 90)
    mean_dh = safe_mean(df_f["ΔH_LAB"])

    c1, c2, c3 = st.columns(3)
    c1.metric("ΔH LAB Mean", f"{mean_dh:.2f}" if mean_dh is not None else "N/A")
    c2.metric("ΔH LAB P10", f"{p10:.2f}" if p10 is not None else "N/A")
    c3.metric("ΔH LAB P90", f"{p90:.2f}" if p90 is not None else "N/A")

# =========================
# TAB 3 – MECHANICAL
# =========================
with tab3:
    st.subheader("Mechanical Properties (YS / TS / EL)")

    fig, ax = plt.subplots()
    df_f[["TENSILE_YIELD", "TENSILE_TENSILE", "TENSILE_ELONG"]].boxplot(ax=ax)
    st.pyplot(fig)

    st.write(df_f[["TENSILE_YIELD", "TENSILE_TENSILE", "TENSILE_ELONG"]].describe())

# =========================
# TAB 4 – THICKNESS & COATING
# =========================
with tab4:
    st.subheader("Thickness & Coating Effect on Hardness")

    fig, ax = plt.subplots()
    ax.scatter(
        df_f["ORDER GAUGE"],
        df_f["HARDNESS 冶金"],
        c=df_f["COATING_MASS_NUM"],
        alpha=0.7
    )
    ax.set_xlabel("Thickness")
    ax.set_ylabel("LAB Hardness")
    st.pyplot(fig)

    st.caption("Color scale represents coating mass (numeric extract)")

# =========================
# TAB 5 – CONTROL LOGIC
# =========================
with tab5:
    st.subheader("Hardness Control Suggestion")

    p10_h = safe_percentile(df_f["HARDNESS 冶金"], 10)

    st.write("**LAB Hardness P10:**", f"{p10_h:.1f}" if p10_h is not None else "N/A")

    if p10_h is None:
        st.warning("⚠️ Not enough data to judge control limit")
    elif p10_h > 7:
        st.success("🟢 Control is conservative")
    elif 5 <= p10_h <= 7:
        st.warning("🟡 Control is reasonable")
    else:
        st.error("🔴 Control is risky – define limit by material / thickness / coating")
