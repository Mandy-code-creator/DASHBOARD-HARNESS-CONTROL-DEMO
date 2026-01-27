import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

st.set_page_config(page_title="GI Hardness Control Dashboard", layout="wide")

# ==================================================
# LOAD DATA
# ==================================================
@st.cache_data
def load_data():
    url = "https://docs.google.com/spreadsheets/d/1GdnY09hJ2qVHuEBAIJ-eU6B5z8ZdgcGf4P7ZjlAt4JI/export?format=csv"
    df = pd.read_csv(url)

    # clean column names
    df.columns = (
        df.columns
        .str.strip()
        .str.replace("\n", " ", regex=True)
        .str.replace("  ", " ", regex=True)
    )

    rename_map = {
        "Standard Hardness": "H_STD",
        "HARDNESS 冶金": "H_LAB",
        "HARDNESS 鍍鋅線 N": "H_LINE_N",
        "HARDNESS 鍍鋅線 C": "H_LINE_C",
        "HARDNESS 鍍鋅線 S": "H_LINE_S",
        "TENSILE_YIELD": "YS",
        "TENSILE_TENSILE": "TS",
        "TENSILE_ELONG": "EL",
        "ORDER GAUGE": "THICKNESS",
        "TOP COATMASS": "COATING"
    }
    df = df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns})

    numeric_cols = ["H_STD","H_LAB","H_LINE_N","H_LINE_C","H_LINE_S","YS","TS","EL","THICKNESS"]
    for c in numeric_cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")

    return df.dropna(subset=["H_LAB","H_STD"])


df = load_data()

st.title("🔥 GI Hardness – Mechanical Property Control Dashboard")

# ==================================================
# SIDEBAR FILTER (HIERARCHICAL)
# ==================================================
st.sidebar.header("🔍 Filters")

qc = st.sidebar.multiselect(
    "QUALITY_CODE",
    sorted(df["QUALITY_CODE"].dropna().unique()),
    default=sorted(df["QUALITY_CODE"].dropna().unique())
)

df_f = df[df["QUALITY_CODE"].isin(qc)]

std = st.sidebar.multiselect(
    "Standard",
    sorted(df_f["PRODUCT SPECIFICATION CODE"].dropna().unique()),
    default=sorted(df_f["PRODUCT SPECIFICATION CODE"].dropna().unique())
)
df_f = df_f[df_f["PRODUCT SPECIFICATION CODE"].isin(std)]

grade = st.sidebar.multiselect(
    "HR STEEL GRADE",
    sorted(df_f["HR STEEL GRADE"].dropna().unique()),
    default=sorted(df_f["HR STEEL GRADE"].dropna().unique())
)
df_f = df_f[df_f["HR STEEL GRADE"].isin(grade)]

thk = st.sidebar.multiselect(
    "Thickness (mm)",
    sorted(df_f["THICKNESS"].dropna().unique()),
    default=sorted(df_f["THICKNESS"].dropna().unique())
)
df_f = df_f[df_f["THICKNESS"].isin(thk)]

coat = st.sidebar.multiselect(
    "Coating",
    sorted(df_f["COATING"].dropna().unique()),
    default=sorted(df_f["COATING"].dropna().unique())
)
df_f = df_f[df_f["COATING"].isin(coat)]

# ==================================================
# CALCULATION
# ==================================================
df_f["ΔH_LAB"] = df_f["H_LAB"] - df_f["H_STD"]
df_f["ΔH_LINE"] = df_f[["H_LINE_N","H_LINE_C","H_LINE_S"]].mean(axis=1) - df_f["H_STD"]

# ==================================================
# TABS
# ==================================================
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "① Overview",
    "② Hardness vs Standard",
    "③ Lab vs Line Bias",
    "④ Hardness vs YS / TS / EL",
    "⑤ Control Recommendation"
])

# --------------------------------------------------
with tab1:
    st.subheader("Dataset Overview")
    st.dataframe(df_f.head(200))
    st.write("Total coils:", len(df_f))

# --------------------------------------------------
with tab2:
    st.subheader("Hardness Deviation from Standard")

    fig, ax = plt.subplots()
    ax.hist(df_f["ΔH_LAB"].dropna(), bins=30)
    ax.set_xlabel("ΔH LAB (HRB)")
    ax.set_ylabel("Count")
    st.pyplot(fig)

# --------------------------------------------------
with tab3:
    st.subheader("Lab vs Line Difference")

    fig, ax = plt.subplots()
    ax.scatter(df_f["H_LAB"], df_f["H_LINE_N"], alpha=0.5)
    ax.set_xlabel("Lab Hardness")
    ax.set_ylabel("Line Hardness (N)")
    st.pyplot(fig)

# --------------------------------------------------
with tab4:
    st.subheader("Mechanical Property Sensitivity")

    col1, col2, col3 = st.columns(3)

    with col1:
        fig, ax = plt.subplots()
        ax.scatter(df_f["H_LAB"], df_f["YS"])
        ax.set_xlabel("Hardness")
        ax.set_ylabel("YS")
        st.pyplot(fig)

    with col2:
        fig, ax = plt.subplots()
        ax.scatter(df_f["H_LAB"], df_f["TS"])
        ax.set_xlabel("Hardness")
        ax.set_ylabel("TS")
        st.pyplot(fig)

    with col3:
        fig, ax = plt.subplots()
        ax.scatter(df_f["H_LAB"], df_f["EL"])
        ax.set_xlabel("Hardness")
        ax.set_ylabel("EL")
        st.pyplot(fig)

# --------------------------------------------------
with tab5:
    st.subheader("Control Limit Recommendation")

    p10 = np.nanpercentile(df_f["ΔH_LINE"], 10)
    p90 = np.nanpercentile(df_f["ΔH_LINE"], 90)

    st.metric("ΔH_LINE P10", f"{p10:.2f} HRB")
    st.metric("ΔH_LINE P90", f"{p90:.2f} HRB")

    if p10 > 7:
        st.success("Control is CONSERVATIVE")
    elif 5 <= p10 <= 7:
        st.warning("Control is REASONABLE")
    else:
        st.error("⚠️ Control is RISKY – Review hardness limit")

    st.info("⚠️ Limit must be defined by MATERIAL + THICKNESS + COATING (not global)")
