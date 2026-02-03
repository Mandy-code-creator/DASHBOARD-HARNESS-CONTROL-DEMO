import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

# =====================
# PAGE CONFIG
# =====================
st.set_page_config(
    page_title="Hardness Control Dashboard",
    layout="wide"
)

DATA_URL = (
    "https://docs.google.com/spreadsheets/d/"
    "1GdnY09hJ2qVHuEBAIJ-eU6B5z8ZdgcGf4P7ZjlAt4JI/"
    "export?format=csv"
)

# =====================
# LOAD DATA
# =====================
@st.cache_data
def load_data():
    df = pd.read_csv(DATA_URL)
    return df

df = load_data()

# =====================
# SIDEBAR FILTER
# =====================
st.sidebar.header("🔍 Filter")

spec = st.sidebar.selectbox(
    "Product Spec",
    sorted(df["Product_Spec"].dropna().unique())
)

df_spec = df[df["Product_Spec"] == spec]

material = st.sidebar.selectbox(
    "Material",
    sorted(df_spec["Material"].dropna().unique())
)

df_mat = df_spec[df_spec["Material"] == material]

coat = st.sidebar.selectbox(
    "Top Coatmass",
    sorted(df_mat["Top_Coatmass"].dropna().unique())
)

df_coat = df_mat[df_mat["Top_Coatmass"] == coat]

gauge = st.sidebar.selectbox(
    "Order Gauge",
    sorted(df_coat["Order_Gauge"].dropna().unique())
)

sub = (
    df_coat[df_coat["Order_Gauge"] == gauge]
    .copy()
    .sort_values("COIL_NO")
    .reset_index(drop=True)
)

# =====================
# STANDARD
# =====================
if sub.empty:
    st.error("❌ No data found for selected condition")
    st.stop()

lo = sub["Std_Min"].iloc[0]
hi = sub["Std_Max"].iloc[0]

# =====================
# NG FLAGS
# =====================
sub["NG_LAB"] = (
    (sub["Hardness_LAB"] < lo) |
    (sub["Hardness_LAB"] > hi)
)

sub["NG_LINE"] = (
    (sub["Hardness_LINE"] < lo) |
    (sub["Hardness_LINE"] > hi)
)

n_coils = len(sub)

# =====================
# VIEW MODE
# =====================
view_mode = st.radio(
    "View Mode",
    [
        "📋 View 1 – Data Table",
        "📈 View 2 – Trend",
        "📊 View 3 – Distribution",
        "📐 View 4 – Hardness Safety Analysis",
    ],
    horizontal=True
)

# =====================
# VIEW 1 – DATA TABLE
# =====================
if view_mode == "📋 View 1 – Data Table":

    if n_coils < 30:
        st.warning("⚠️ View 1 requires ≥ 30 coils")
    else:
        st.subheader("📋 Data Table (Hardness Control)")

        st.dataframe(
            sub[
                [
                    "COIL_NO",
                    "Hardness_LAB",
                    "Hardness_LINE",
                    "Std_Min",
                    "Std_Max",
                    "NG_LAB",
                    "NG_LINE",
                ]
            ],
            use_container_width=True
        )

# =====================
# VIEW 2 – TREND
# =====================
elif view_mode == "📈 View 2 – Trend":

    if n_coils < 30:
        st.warning("⚠️ View 2 requires ≥ 30 coils")
    else:
        st.subheader("📈 Hardness Trend")

        fig, ax = plt.subplots(figsize=(10, 4))
        ax.plot(
            sub.index + 1,
            sub["Hardness_LAB"],
            marker="o",
            label="LAB"
        )
        ax.plot(
            sub.index + 1,
            sub["Hardness_LINE"],
            marker="s",
            label="LINE"
        )

        ax.axhline(lo, linestyle="--", label="Std Min")
        ax.axhline(hi, linestyle="--", label="Std Max")

        ax.set_xlabel("Coil Order")
        ax.set_ylabel("Hardness (HRB)")
        ax.legend()
        ax.grid(alpha=0.3)

        st.pyplot(fig)

# =====================
# VIEW 3 – DISTRIBUTION
# =====================
elif view_mode == "📊 View 3 – Distribution":

    if n_coils < 30:
        st.warning("⚠️ View 3 requires ≥ 30 coils")
    else:
        st.subheader("📊 Hardness Distribution (LAB)")

        hr = sub["Hardness_LAB"].dropna()

        fig, ax = plt.subplots(figsize=(6, 4))
        ax.hist(hr, bins=10)
        ax.axvline(lo, linestyle="--")
        ax.axvline(hi, linestyle="--")

        ax.set_xlabel("Hardness (HRB)")
        ax.set_ylabel("Count")
        ax.grid(alpha=0.3)

        st.pyplot(fig)

        # ===== AUTO DECISION =====
        if ((hr < lo) | (hr > hi)).any():
            decision = "🔴 RISK – NG coils detected"
        elif ((hr == lo) | (hr == hi)).any():
            decision = "🟡 WARNING – On spec edge"
        else:
            decision = "🟢 SAFE – All coils within spec"

        st.info(f"📌 Decision: **{decision}**")

# =====================
# VIEW 4 – SAFETY ANALYSIS
# =====================
elif view_mode == "📐 View 4 – Hardness Safety Analysis":

    st.subheader("📐 Hardness Safety Analysis (Independent View)")

    hr = sub["Hardness_LAB"].dropna()

    if len(hr) < 5:
        st.warning("⚠️ Not enough data for safety analysis")
    else:
        hr_bin = hr.round().astype(int)
        bin_df = hr_bin.value_counts().sort_index()

        fig, ax = plt.subplots(figsize=(6, 4))
        ax.bar(bin_df.index, bin_df.values)

        ax.axvline(lo, linestyle="--")
        ax.axvline(hi, linestyle="--")

        ax.set_xlabel("Hardness (HRB)")
        ax.set_ylabel("Coil Count")
        ax.grid(alpha=0.3)

        st.pyplot(fig)

        safe_bins = bin_df[
            (bin_df.index >= lo) &
            (bin_df.index <= hi)
        ]

        if not safe_bins.empty:
            st.success(
                f"✅ Observed stable hardness range: "
                f"{safe_bins.index.min()} – {safe_bins.index.max()} HRB"
            )
        else:
            st.error("❌ No stable hardness zone observed")
