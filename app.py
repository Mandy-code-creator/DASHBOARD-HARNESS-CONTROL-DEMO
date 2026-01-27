import streamlit as st
import pandas as pd
import numpy as np

st.set_page_config(
    page_title="GI Hardness Dashboard",
    layout="wide"
)

st.title("GI Hardness & Mechanical Property Dashboard")

# =========================
# LOAD DATA FROM GOOGLE SHEET
# =========================
@st.cache_data
def load_data():
    sheet_id = "PUT_YOUR_SHEET_ID_HERE"
    url = f"https://docs.google.com/spreadsheets/d/1GdnY09hJ2qVHuEBAIJ-eU6B5z8ZdgcGf4P7ZjlAt4JI/export?format=csv"
    df = pd.read_csv(url)
    return df

df = load_data()

st.subheader("Raw data preview")
st.dataframe(df.head())

# =========================
# SELECT HARDNESS SOURCE
# =========================
st.sidebar.header("Settings")
hardness_source = st.sidebar.radio(
    "Hardness source",
    ["HARDNESS 冶金", "HARDNESS 鍍鋅線 C"]
)

# =========================
# CREATE ANALYSIS COLUMNS
# =========================
HARDNESS = df[hardness_source]
HMAX = df["Standard Hardness"]

# ΔH to upper spec
df["ΔH_spec"] = HMAX - HARDNESS

# Hardness band
def hardness_band(x):
    if x >= 10:
        return "≥10"
    elif x >= 7:
        return "7–10"
    elif x >= 5:
        return "5–7"
    elif x >= 3:
        return "3–5"
    else:
        return "<3"

df["Hardness_Band"] = df["ΔH_spec"].apply(hardness_band)

# Decision zone
def decision_zone(x):
    if x >= 7:
        return "SAFE"
    elif x >= 5:
        return "WATCH"
    else:
        return "RISK"

df["Zone"] = df["ΔH_spec"].apply(decision_zone)

# =========================
# SHOW RESULT TABLE
# =========================
st.subheader("Analysis table")
st.dataframe(
    df[
        [
            hardness_source,
            "Standard Hardness",
            "ΔH_spec",
            "Hardness_Band",
            "Zone",
            "TENSILE_ELONG",
        ]
    ].head(20)
)
