import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

st.set_page_config(page_title="GI Hardness Control Dashboard", layout="wide")

# =========================
# LOAD DATA
# =========================
@st.cache_data
def load_data():
    url = "https://docs.google.com/spreadsheets/d/1GdnY09hJ2qVHuEBAIJ-eU6B5z8ZdgcGf4P7ZjlAt4JI/export?format=csv"
    df = pd.read_csv(url)

    # ---- clean headers ----
    df.columns = [c.strip() for c in df.columns]

    # ---- clean string columns ----
    for c in df.select_dtypes(include="object").columns:
        df[c] = df[c].astype(str).str.strip()

    # ---- numeric fixes ----
    df["ORDER GAUGE"] = pd.to_numeric(df["ORDER GAUGE"], errors="coerce").round(3)

    return df

df = load_data()

st.title("🔥 GI Hardness – Mechanical Property Control Dashboard")

# =========================
# SAFE SELECTBOX
# =========================
def safe_selectbox(label, series):
    opts = sorted(series.dropna().unique())
    if len(opts) == 0:
        st.sidebar.error(f"No data available for {label}")
        st.stop()
    return st.sidebar.selectbox(label, opts)

# =========================
# SIDEBAR – HIERARCHICAL FILTER
# =========================
st.sidebar.header("🔎 Hierarchical Filter")

qc = safe_selectbox("QUALITY_CODE", df["QUALITY_CODE"])
df1 = df[df["QUALITY_CODE"] == qc]
st.sidebar.caption(f"Rows: {len(df1)}")

spec = safe_selectbox("PRODUCT SPECIFICATION CODE", df1["PRODUCT SPECIFICATION CODE"])
df2 = df1[df1["PRODUCT SPECIFICATION CODE"] == spec]
st.sidebar.caption(f"Rows: {len(df2)}")

material = safe_selectbox("HR STEEL GRADE", df2["HR STEEL GRADE"])
df3 = df2[df2["HR STEEL GRADE"] == material]
st.sidebar.caption(f"Rows: {len(df3)}")

thk = safe_selectbox("ORDER GAUGE", df3["ORDER GAUGE"])
df4 = df3[df3["ORDER GAUGE"] == thk]
st.sidebar.caption(f"Rows: {len(df4)}")

coat = safe_selectbox("TOP COATMASS", df4["TOP COATMASS"])
df_f = df4[df4["TOP COATMASS"] == coat]

st.sidebar.success(f"Final rows: {len(df_f)}")

if len(df_f) < 5:
    st.warning("⚠️ Not enough data for statistical analysis")
    st.stop()

# =========================
# DERIVED METRICS
# =========================
df_f = df_f.copy()

df_f["ΔH_LAB"]  = df_f["HARDNESS 冶金"] - df_f["Standard Hardness"]
df_f["ΔH_LINE"] = df_f["HARDNESS 鍍鋅線 C"] - df_f["Standard Hardness"]

# =========================
# KPI SECTION
# =========================
st.subheader("📊 Key Control Metrics")

c1, c2, c3, c4 = st.columns(4)

def safe_p10(series):
    s = series.dropna()
    if len(s) < 3:
        return np.nan
    return np.percentile(s, 10)

c1.metric("ΔH LAB P10", f"{safe_p10(df_f['ΔH_LAB']):.2f}")
c2.metric("ΔH LINE P10", f"{safe_p10(df_f['ΔH_LINE']):.2f}")
c3.metric("YS P10", f"{safe_p10(df_f['TENSILE_YIELD']):.1f}")
c4.metric("TS P10", f"{safe_p10(df_f['TENSILE_TENSILE']):.1f}")

# =========================
# SCATTER ANALYSIS
# =========================
st.subheader("🔗 Hardness vs Mechanical Properties")

col1, col2 = st.columns(2)

with col1:
    fig, ax = plt.subplots()
    ax.scatter(df_f["ΔH_LINE"], df_f["TENSILE_YIELD"])
    ax.axvline(-7, linestyle="--")
    ax.set_xlabel("ΔH LINE (HRB)")
    ax.set_ylabel("Yield Strength")
    ax.set_title("ΔH LINE vs YS")
    st.pyplot(fig)

with col2:
    fig, ax = plt.subplots()
    ax.scatter(df_f["ΔH_LINE"], df_f["TENSILE_TENSILE"])
    ax.axvline(-7, linestyle="--")
    ax.set_xlabel("ΔH LINE (HRB)")
    ax.set_ylabel("Tensile Strength")
    ax.set_title("ΔH LINE vs TS")
    st.pyplot(fig)

# =========================
# ELONGATION CHECK
# =========================
st.subheader("🧪 Hardness vs Elongation")

fig, ax = plt.subplots()
ax.scatter(df_f["ΔH_LINE"], df_f["TENSILE_ELONG"])
ax.axvline(-7, linestyle="--", color="black")
ax.set_xlabel("ΔH LINE (HRB)")
ax.set_ylabel("Elongation (%)")
ax.set_title("ΔH LINE vs EL")
st.pyplot(fig)

# =========================
# INTERPRETATION
# =========================
st.subheader("🧠 Interpretation Logic")

line_p10 = safe_p10(df_f["ΔH_LINE"])

if line_p10 > -5:
    st.success("Control is conservative")
elif -7 <= line_p10 <= -5:
    st.info("Control is reasonable")
else:
    st.error("⚠️ Control is risky – check YS & EL trend")

st.caption(
    "⚠️ Control limits must be defined by material + thickness + coating, not globally."
)
