# ================================
# FULL STREAMLIT APP – LOGIC CONFIRMED
# ================================

import streamlit as st
import pandas as pd
import numpy as np
import requests
from io import StringIO, BytesIO
import matplotlib.pyplot as plt

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
# SPLIT STANDARD RANGE
# ================================
def split_std(x):
    if isinstance(x, str) and "~" in x:
        lo, hi = x.split("~")
        return pd.Series([float(lo), float(hi)])
    return pd.Series([np.nan, np.nan])

df[["Std_Min", "Std_Max"]] = df["Std_Range_Text"].apply(split_std)
df.drop(columns=["Std_Range_Text"], inplace=True)

# ================================
# FORCE NUMERIC
# ================================
for c in ["Hardness_LAB", "Hardness_LINE", "YS", "TS", "EL"]:
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
    ["📋 Data Table", "📈 Trend (LAB / LINE)", "📊 Distribution"],
    index=2
)

# ================================
# GROUP CONDITION (≥30 COILS)
# ================================
GROUP_COLS = ["Product_Spec", "Material", "Metallic_Type", "Top_Coatmass", "Order_Gauge"]

count_df = (
    df.groupby(GROUP_COLS)
      .agg(N_Coils=("COIL_NO", "nunique"))
      .reset_index()
)

valid_conditions = count_df[count_df["N_Coils"] >= 30]

# ================================
# MAIN LOOP
# ================================
for _, cond in valid_conditions.iterrows():

    spec, mat, coat, gauge, n = (
        cond["Product_Spec"],
        cond["Material"],
        cond["Top_Coatmass"],
        cond["Order_Gauge"],
        int(cond["N_Coils"])
    )

    sub = df[
        (df["Product_Spec"] == spec) &
        (df["Material"] == mat) &
        (df["Top_Coatmass"] == coat) &
        (df["Order_Gauge"] == gauge)
    ].copy().reset_index(drop=True)

    lo, hi = sub[["Std_Min", "Std_Max"]].iloc[0]

    st.markdown(f"## 🧱 `{spec}` | {mat} | {coat} | {gauge} | n={n}")

    # ================================
    # VIEW 3 — DISTRIBUTION
    # ================================
    if view_mode == "📊 Distribution":

        lab_df  = sub[sub["Hardness_LAB"]  > 0]
        line_df = sub[sub["Hardness_LINE"] > 0]

        mu_lab, std_lab   = lab_df["Hardness_LAB"].mean(),  lab_df["Hardness_LAB"].std()
        mu_line, std_line = line_df["Hardness_LINE"].mean(), line_df["Hardness_LINE"].std()

        fig, ax = plt.subplots(figsize=(6,4))

        lab_counts, lab_bins, _ = ax.hist(lab_df["Hardness_LAB"], bins=10, alpha=0.5, label="LAB")
        line_counts, line_bins, _ = ax.hist(line_df["Hardness_LINE"], bins=10, alpha=0.5, label="LINE")

        ax.axvline(lo, linestyle="--", label="LSL")
        ax.axvline(hi, linestyle="--", label="USL")

        if std_lab > 0:
            x = np.linspace(mu_lab - 3*std_lab, mu_lab + 3*std_lab, 400)
            ax.plot(x, (1/(std_lab*np.sqrt(2*np.pi))) * np.exp(-0.5*((x-mu_lab)/std_lab)**2)
                    * len(lab_df)*(lab_bins[1]-lab_bins[0]), "--", label="LAB Normal")

        if std_line > 0:
            x = np.linspace(mu_line - 3*std_line, mu_line + 3*std_line, 400)
            ax.plot(x, (1/(std_line*np.sqrt(2*np.pi))) * np.exp(-0.5*((x-mu_line)/std_line)**2)
                    * len(line_df)*(line_bins[1]-line_bins[0]), "--", label="LINE Normal")

        ax.legend(bbox_to_anchor=(1.02,0.5), loc="center left")
        ax.grid(alpha=0.3)
        st.pyplot(fig)

        # ================================
        # FOOTER CARD — DOWNLOAD
        # ================================
        st.markdown(
            """
            <div style="
                border:1px solid #ddd;
                border-radius:8px;
                padding:10px;
                background:#fafafa;
                margin-top:10px">
            <b>⬇️ Export</b>
            </div>
            """,
            unsafe_allow_html=True
        )

        c1, c2 = st.columns(2)

        buf = BytesIO()
        fig.savefig(buf, format="png", dpi=150, bbox_inches="tight")
        buf.seek(0)

        with c1:
            st.download_button(
                "📷 Download PNG",
                buf,
                file_name=f"{spec}_{mat}_{gauge}.png",
                mime="image/png",
                key=f"png_{spec}_{mat}_{gauge}"
            )

        with c2:
            st.download_button(
                "📄 Download CSV",
                sub[["COIL_NO","Hardness_LAB","Hardness_LINE"]].to_csv(index=False),
                file_name=f"{spec}_{mat}_{gauge}.csv",
                mime="text/csv",
                key=f"csv_{spec}_{mat}_{gauge}"
            )
