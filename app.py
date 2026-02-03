# ================================
# FULL STREAMLIT APP – FINAL
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
st.title("📊 Material-level Hardness & Mechanical Detail")

# ================================
# UTILITY FUNCTIONS
# ================================
def fig_to_png(fig, dpi=200):
    buf = BytesIO()
    fig.savefig(buf, format="png", dpi=dpi, bbox_inches="tight")
    buf.seek(0)
    return buf

def plot_igf(ax, data, label):
    mu = data.mean()
    sigma = data.std(ddof=1)
    if sigma <= 0:
        return
    x = np.linspace(data.min(), data.max(), 300)
    y = (1 / (sigma * np.sqrt(2 * np.pi))) * np.exp(-0.5 * ((x - mu) / sigma) ** 2)
    ax.plot(x, y, linestyle="--", linewidth=2, label=f"{label} IGF")

# ================================
# REFRESH
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
# METALLIC TYPE
# ================================
metal_col = None
for c in raw.columns:
    if "METALLIC" in c.upper() and "COATING" in c.upper():
        metal_col = c
        break

if metal_col is None:
    st.error("❌ Cannot find METALLIC COATING TYPE column")
    st.stop()

raw["Metallic_Type"] = raw[metal_col]

# ================================
# RENAME COLUMNS
# ================================
df = raw.rename(columns={
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
})

# ================================
# SPLIT HARDNESS STANDARD
# ================================
def split_std(x):
    if isinstance(x, str) and "~" in x:
        try:
            lo, hi = x.split("~")
            return pd.Series([float(lo), float(hi)])
        except:
            pass
    return pd.Series([np.nan, np.nan])

df[["Std_Min", "Std_Max"]] = df["Std_Range_Text"].apply(split_std)

# ================================
# FORCE NUMERIC
# ================================
for c in ["Hardness_LAB", "Hardness_LINE", "YS", "TS", "EL"]:
    df[c] = pd.to_numeric(df[c], errors="coerce")

# ================================
# SIDEBAR FILTERS
# ================================
st.sidebar.header("🎛 Filters")

df = df[df["Rolling_Type"] == st.sidebar.radio("Rolling Type", sorted(df["Rolling_Type"].dropna().unique()))]
df = df[df["Metallic_Type"] == st.sidebar.radio("Metallic Coating", sorted(df["Metallic_Type"].dropna().unique()))]
df = df[df["Quality_Code"] == st.sidebar.radio("Quality Code", sorted(df["Quality_Code"].dropna().unique()))]

view_mode = st.sidebar.radio(
    "📊 View Mode",
    [
        "📋 Data Table",
        "📈 Trend (LAB / LINE)",
        "📊 Distribution",
        "📐 Hardness Safety Analysis"
    ]
)

# ================================
# GROUP CONDITION (≥30 COILS)
# ================================
GROUP_COLS = ["Product_Spec", "Material", "Metallic_Type", "Top_Coatmass", "Order_Gauge"]

valid_conditions = (
    df.groupby(GROUP_COLS)
      .agg(N_Coils=("COIL_NO", "nunique"))
      .reset_index()
      .query("N_Coils >= 30")
)

if valid_conditions.empty:
    st.warning("⚠️ No condition with ≥ 30 coils")
    st.stop()

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
    ].copy()

    lo, hi = sub[["Std_Min", "Std_Max"]].iloc[0]

    lab_df  = sub[sub["Hardness_LAB"]  > 0]
    line_df = sub[sub["Hardness_LINE"] > 0]

    st.markdown(
        f"## 🧱 `{spec}`  \n"
        f"Material: **{mat}** | Coatmass: **{coat}** | Gauge: **{gauge}**  \n"
        f"➡️ n = **{n} coils**"
    )

    # ================================
    # VIEW 1 — TABLE
    # ================================
    if view_mode == "📋 Data Table":
        st.dataframe(sub.sort_values("COIL_NO"), use_container_width=True)

    # ================================
    # VIEW 2 — TREND
    # ================================
    elif view_mode == "📈 Trend (LAB / LINE)":

        sub["X"] = np.arange(1, len(sub) + 1)

        c1, c2 = st.columns(2)

        for title, df_plot, col, label in [
            ("LAB", lab_df, "Hardness_LAB", "lab"),
            ("LINE", line_df, "Hardness_LINE", "line")
        ]:
            with c1 if title == "LAB" else c2:
                fig, ax = plt.subplots(figsize=(5,3))
                ax.plot(df_plot["X"], df_plot[col], marker="o")
                ax.axhline(lo, linestyle="--")
                ax.axhline(hi, linestyle="--")
                ax.set_title(f"Hardness {title}")
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
    # VIEW 3 — DISTRIBUTION
    # ================================
    elif view_mode == "📊 Distribution":

        fig, ax = plt.subplots(figsize=(6,4))
        ax.hist(lab_df["Hardness_LAB"], bins=10, alpha=0.5, label="LAB")
        ax.hist(line_df["Hardness_LINE"], bins=10, alpha=0.5, label="LINE")
        ax.axvline(lo, linestyle="--")
        ax.axvline(hi, linestyle="--")
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
    # VIEW 4 — IGF (BIN = 1 HRB)
    # ================================
    elif view_mode == "📐 Hardness Safety Analysis":

        st.markdown("### 📊 Hardness Distribution + IGF (Bin = 1 HRB)")

        c1, c2 = st.columns(2)

        for title, df_plot, col, label in [
            ("LAB", lab_df, "Hardness_LAB", "lab"),
            ("LINE", line_df, "Hardness_LINE", "line")
        ]:
            with c1 if title == "LAB" else c2:
                fig, ax = plt.subplots(figsize=(5,4))
                bins = np.arange(
                    np.floor(df_plot[col].min()),
                    np.ceil(df_plot[col].max()) + 1,
                    1
                )
                ax.hist(df_plot[col], bins=bins, density=True, alpha=0.6, label=title)
                plot_igf(ax, df_plot[col], title)
                ax.axvline(lo, linestyle="--", label="LSL")
                ax.axvline(hi, linestyle="--", label="USL")
                ax.set_title(f"{title} Hardness + IGF")
                ax.set_xlabel("HRB")
                ax.set_ylabel("Density")
                ax.legend()
                ax.grid(alpha=0.3)
                st.pyplot(fig)
                st.download_button(
                    f"⬇️ Download {title} IGF",
                    data=fig_to_png(fig),
                    file_name=f"{spec}_{title}_IGF.png",
                    mime="image/png",
                    key=f"dl_igf_{label}_{spec}_{gauge}"
                )
