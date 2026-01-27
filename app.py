import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

st.set_page_config(layout="wide", page_title="Hardness & Mechanical Control Dashboard")

# =========================
# LOAD DATA
# =========================
@st.cache_data
def load_data():
    url = "https://docs.google.com/spreadsheets/d/1GdnY09hJ2qVHuEBAIJ-eU6B5z8ZdgcGf4P7ZjlAt4JI/export?format=csv"
    df = pd.read_csv(url)

    # strip column names
    df.columns = [c.strip() for c in df.columns]

    # force numeric columns
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
        "TOP COATMASS",
    ]

    for c in num_cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")

    return df


df0 = load_data()

# =========================
# SAFE FILTER FUNCTION
# =========================
def safe_filter(df0, df_f, col, label):
    df0[col] = df0[col].astype(str)
    df_f[col] = df_f[col].astype(str)

    options = sorted(df0[col].dropna().unique())
    default = sorted(df_f[col].dropna().unique())

    if len(default) == 0:
        default = options

    selected = st.sidebar.multiselect(label, options, default=default)
    return df_f[df_f[col].isin(selected)]


# =========================
# SIDEBAR FILTERS
# =========================
st.sidebar.header("🔎 Hierarchical Filter")

df_f = df0.copy()

df_f = safe_filter(df0, df_f, "QUALITY_CODE", "QUALITY CODE")
df_f = safe_filter(df0, df_f, "PRODUCT SPECIFICATION CODE", "STANDARD")
df_f = safe_filter(df0, df_f, "HR STEEL GRADE", "MATERIAL")
df_f = safe_filter(df0, df_f, "ORDER GAUGE", "THICKNESS")
df_f = safe_filter(df0, df_f, "TOP COATMASS", "COATING")

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
    "4️⃣ Thickness / Coating Effect",
    "5️⃣ Control Suggestion"
])

# =========================
# TAB 1
# =========================
with tab1:
    st.subheader("Dataset Overview")
    st.dataframe(df_f, use_container_width=True)

    col1, col2, col3 = st.columns(3)
    col1.metric("Samples", len(df_f))
    col2.metric("Mean Std Hardness", f"{df_f['Standard Hardness'].mean():.1f}")
    col3.metric("Mean LAB Hardness", f"{df_f['HARDNESS 冶金'].mean():.1f}")

# =========================
# TAB 2
# =========================
with tab2:
    st.subheader("Hardness vs Standard")

    fig, ax = plt.subplots()
    ax.hist(df_f["ΔH_LAB"].dropna(), bins=20)
    ax.axvline(0, linestyle="--")
    ax.set_title("ΔH LAB Distribution")
    st.pyplot(fig)

    col1, col2, col3 = st.columns(3)
    col1.metric("ΔH LAB Mean", f"{df_f['ΔH_LAB'].mean():.2f}")
    col2.metric("ΔH LAB P10", f"{np.percentile(df_f['ΔH_LAB'].dropna(),10):.2f}")
    col3.metric("ΔH LAB P90", f"{np.percentile(df_f['ΔH_LAB'].dropna(),90):.2f}")

# =========================
# TAB 3
# =========================
with tab3:
    st.subheader("Mechanical Properties")

    fig, ax = plt.subplots()
    df_f[["TENSILE_YIELD", "TENSILE_TENSILE", "TENSILE_ELONG"]].boxplot(ax=ax)
    st.pyplot(fig)

    st.write(df_f[["TENSILE_YIELD", "TENSILE_TENSILE", "TENSILE_ELONG"]].describe())

# =========================
# TAB 4
# =========================
with tab4:
    st.subheader("Thickness / Coating Effect on Hardness")

    fig, ax = plt.subplots()
    ax.scatter(df_f["ORDER GAUGE"], df_f["HARDNESS 冶金"], alpha=0.7)
    ax.set_xlabel("Thickness")
    ax.set_ylabel("LAB Hardness")
    st.pyplot(fig)

# =========================
# TAB 5
# =========================
with tab5:
    st.subheader("Control Suggestion Logic")

    p10 = np.percentile(df_f["HARDNESS 冶金"].dropna(), 10)
    p50 = np.percentile(df_f["HARDNESS 冶金"].dropna(), 50)

    st.write(f"**LAB Hardness P10:** {p10:.1f}")
    st.write(f"**LAB Hardness P50:** {p50:.1f}")

    if p10 > 7:
        st.success("🟢 Control is conservative")
    elif 5 <= p10 <= 7:
        st.warning("🟡 Control is reasonable")
    else:
        st.error("🔴 Control is risky – need tightening by material / thickness / coating")
