import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

st.set_page_config(page_title="GI Hardness Control Dashboard", layout="wide")

# =====================================================
# LOAD DATA
# =====================================================
@st.cache_data
def load_data():
    url = "https://docs.google.com/spreadsheets/d/1GdnY09hJ2qVHuEBAIJ-eU6B5z8ZdgcGf4P7ZjlAt4JI/export?format=csv"
    df = pd.read_csv(url)

    # Clean column names
    df.columns = (
        df.columns
        .str.strip()
        .str.replace("\n", " ", regex=True)
        .str.replace("  ", " ", regex=True)
    )

    # Rename columns (CHỐT CỨNG)
    col_map = {
        "QUALITY_CODE": "QUALITY_CODE",
        "PRODUCT SPECIFICATION CODE": "STANDARD",
        "HR STEEL GRADE": "MATERIAL",
        "ORDER GAUGE": "THICKNESS",
        "TOP COATMASS": "COATING",

        "Standard Hardness": "H_STD",
        "HARDNESS 冶金": "H_LAB",
        "HARDNESS 鍍鋅線 C": "H_LINE",

        "TENSILE_YIELD": "YS",
        "TENSILE_TENSILE": "TS",
        "TENSILE_ELONG": "EL"
    }
    df = df.rename(columns={k: v for k, v in col_map.items() if k in df.columns})

    # Force numeric
    num_cols = ["H_STD","H_LAB","H_LINE","YS","TS","EL","THICKNESS"]
    for c in num_cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")

    # Drop only rows without CORE data
    df = df.dropna(subset=["H_STD","H_LAB","H_LINE","YS","TS","EL"])

    return df


df0 = load_data()
df_f = df0.copy()

st.title("🔥 GI Hardness – Mechanical Property Control Dashboard")

# =====================================================
# SAFE HIERARCHICAL FILTER (KEY FIX)
# =====================================================
st.sidebar.header("🔍 Hierarchical Filter")

def safe_multiselect(label, full_series, filtered_series):
    opts = sorted(full_series.dropna().unique())
    default = sorted(filtered_series.dropna().unique())

    # Nếu default rỗng → fallback về toàn bộ option
    if len(default) == 0:
        default = opts

    return st.sidebar.multiselect(label, opts, default=default)


qc = safe_multiselect(
    "QUALITY_CODE",
    df0["QUALITY_CODE"],
    df_f["QUALITY_CODE"]
)
df_f = df_f[df_f["QUALITY_CODE"].isin(qc)]

std = safe_multiselect(
    "Standard",
    df0["STANDARD"],
    df_f["STANDARD"]
)
df_f = df_f[df_f["STANDARD"].isin(std)]

mat = safe_multiselect(
    "Material (HR STEEL GRADE)",
    df0["MATERIAL"],
    df_f["MATERIAL"]
)
df_f = df_f[df_f["MATERIAL"].isin(mat)]

thk = safe_multiselect(
    "Thickness (ORDER GAUGE)",
    df0["THICKNESS"],
    df_f["THICKNESS"]
)
df_f = df_f[df_f["THICKNESS"].isin(thk)]

coat = safe_multiselect(
    "Coating (TOP COATMASS)",
    df0["COATING"],
    df_f["COATING"]
)
df_f = df_f[df_f["COATING"].isin(coat)]

# Guard cuối – chỉ cảnh báo, KHÔNG crash
if df_f.empty:
    st.warning("⚠️ No valid data for this combination. Please adjust filters.")
    st.stop()

# =====================================================
# CALCULATION
# =====================================================
df_f["ΔH_LAB"]  = df_f["H_LAB"]  - df_f["H_STD"]
df_f["ΔH_LINE"] = df_f["H_LINE"] - df_f["H_STD"]

# =====================================================
# TABS
# =====================================================
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "① Group Overview",
    "② Hardness Behavior",
    "③ Mechanical Response",
    "④ Thickness Sensitivity",
    "⑤ Control Recommendation"
])

# -----------------------------------------------------
with tab1:
    st.subheader("Group Overview")

    c1, c2, c3 = st.columns(3)
    c1.metric("Mean H_STD", f"{df_f['H_STD'].mean():.2f}")
    c2.metric("Mean H_LAB", f"{df_f['H_LAB'].mean():.2f}")
    c3.metric("Mean H_LINE", f"{df_f['H_LINE'].mean():.2f}")

    st.dataframe(df_f.head(200), use_container_width=True)

# -----------------------------------------------------
with tab2:
    st.subheader("Hardness Distribution vs Standard")

    fig, ax = plt.subplots()
    ax.hist(df_f["ΔH_LAB"], bins=30, alpha=0.7, label="LAB")
    ax.hist(df_f["ΔH_LINE"], bins=30, alpha=0.7, label="LINE")
    ax.axvline(0, color="black", linestyle="--")
    ax.set_xlabel("ΔH (Hardness – Standard)")
    ax.set_ylabel("Count")
    ax.legend()
    st.pyplot(fig)

# -----------------------------------------------------
with tab3:
    st.subheader("Hardness Impact on Mechanical Properties")

    col1, col2, col3 = st.columns(3)

    with col1:
        fig, ax = plt.subplots()
        ax.scatter(df_f["ΔH_LINE"], df_f["YS"])
        ax.set_xlabel("ΔH_LINE")
        ax.set_ylabel("YS")
        st.pyplot(fig)

    with col2:
        fig, ax = plt.subplots()
        ax.scatter(df_f["ΔH_LINE"], df_f["TS"])
        ax.set_xlabel("ΔH_LINE")
        ax.set_ylabel("TS")
        st.pyplot(fig)

    with col3:
        fig, ax = plt.subplots()
        ax.scatter(df_f["ΔH_LINE"], df_f["EL"])
        ax.set_xlabel("ΔH_LINE")
        ax.set_ylabel("EL")
        st.pyplot(fig)

# -----------------------------------------------------
with tab4:
    st.subheader("Thickness Sensitivity (ΔH vs YS)")

    fig, ax = plt.subplots()
    for t in sorted(df_f["THICKNESS"].unique()):
        sub = df_f[df_f["THICKNESS"] == t]
        ax.scatter(sub["ΔH_LINE"], sub["YS"], label=f"{t} mm", alpha=0.6)

    ax.set_xlabel("ΔH_LINE")
    ax.set_ylabel("YS")
    ax.legend()
    st.pyplot(fig)

# -----------------------------------------------------
with tab5:
    st.subheader("Control Recommendation")

    p10 = np.percentile(df_f["ΔH_LINE"], 10)
    ys_p10 = np.percentile(df_f["YS"], 10)
    ts_p10 = np.percentile(df_f["TS"], 10)
    el_min = df_f["EL"].min()

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("ΔH_LINE P10", f"{p10:.2f}")
    c2.metric("YS P10", f"{ys_p10:.1f}")
    c3.metric("TS P10", f"{ts_p10:.1f}")
    c4.metric("EL MIN", f"{el_min:.1f}")

    if p10 > 7:
        st.success("🟢 Control is CONSERVATIVE")
    elif 5 <= p10 <= 7:
        st.warning("🟡 Control is REASONABLE")
    else:
        st.error("🔴 Control is RISKY – Review hardness limit")

    st.info(
        "Limit must be defined by MATERIAL + THICKNESS + COATING.\n"
        "YS drives the limit, TS is safety constraint, EL confirms formability."
    )
