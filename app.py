import numpy as np
import matplotlib.pyplot as plt
import streamlit as st

# =========================================================
# TASK: QA STRICT + CHART (LAB / LINE SEPARATE)
# =========================================================
if task == "QA Strict + Chart":

    st.subheader("📊 QA Strict Spec Check with Visualization")

    # ===== LOOP BY VALID SPEC CONDITIONS =====
    for _, cond in valid_conditions.iterrows():

        spec  = cond["Product_Spec"]
        mat   = cond["HR_STEEL_GRADE"]
        coat  = cond["COATMASS"]
        gauge = cond["ORDER_GAUGE"]
        lo    = cond["Std_Min"]
        hi    = cond["Std_Max"]

        # ===== FILTER DATA =====
        sub = df[
            (df["Product_Spec"] == spec) &
            (df["HR_STEEL_GRADE"] == mat) &
            (df["COATMASS"] == coat) &
            (df["ORDER_GAUGE"] == gauge)
        ].copy()

        if sub.empty:
            continue

        # ===== SORT & X AXIS =====
        sub = sub.sort_values("COIL_NO").reset_index(drop=True)
        sub["X"] = sub.index + 1

        # ===== STRICT QA JUDGEMENT =====
        sub["NG_LAB"]  = (sub["Hardness_LAB"]  < lo) | (sub["Hardness_LAB"]  > hi)
        sub["NG_LINE"] = (sub["Hardness_LINE"] < lo) | (sub["Hardness_LINE"] > hi)
        sub["COIL_NG"] = sub["NG_LAB"] | sub["NG_LINE"]

        n_total = sub["COIL_NO"].nunique()
        n_out   = sub[sub["COIL_NG"]]["COIL_NO"].nunique()
        qa_result = "FAIL" if n_out > 0 else "PASS"

        # ===== HEADER =====
        st.markdown(
            f"""
            **Product Spec:** {spec}  
            **Material:** {mat} | **Coatmass:** {coat} | **Gauge:** {gauge}  
            **n = {n_total} coils**  
            ❌ **n_out = {n_out} coils out of spec**  
            🧪 **QA Result:** `{qa_result}`
            """
        )

        # ===== REMOVE ZERO HARDNESS =====
        lab_df  = sub[sub["Hardness_LAB"]  > 0].copy()
        line_df = sub[sub["Hardness_LINE"] > 0].copy()

        # ===== SPLIT OK / NG =====
        lab_ok  = lab_df[~lab_df["NG_LAB"]]
        lab_ng  = lab_df[ lab_df["NG_LAB"]]

        line_ok = line_df[~line_df["NG_LINE"]]
        line_ng = line_df[ line_df["NG_LINE"]]

        # ===== COMMON Y SCALE (INTEGER) =====
        y_min = int(np.floor(min(lo,
                                 lab_df["Hardness_LAB"].min(),
                                 line_df["Hardness_LINE"].min())))
        y_max = int(np.ceil (max(hi,
                                 lab_df["Hardness_LAB"].max(),
                                 line_df["Hardness_LINE"].max())))

        yticks = list(range(y_min, y_max + 1))

        # =====================================================
        # LAB CHART
        # =====================================================
        fig_lab, ax_lab = plt.subplots(figsize=(7, 3))

        ax_lab.scatter(
            lab_ok["X"], lab_ok["Hardness_LAB"],
            label="LAB OK", s=28, alpha=0.8
        )
        ax_lab.scatter(
            lab_ng["X"], lab_ng["Hardness_LAB"],
            label="LAB NG", s=45, marker="x"
        )

        ax_lab.axhline(lo, linestyle="--", linewidth=1)
        ax_lab.axhline(hi, linestyle="--", linewidth=1)

        ax_lab.set_title("LAB Hardness")
        ax_lab.set_xlabel("Coil Order (after filter)")
        ax_lab.set_ylabel("HRB")
        ax_lab.set_ylim(y_min, y_max)
        ax_lab.set_yticks(yticks)
        ax_lab.legend(loc="upper left", bbox_to_anchor=(1.02, 1))

        st.pyplot(fig_lab)

        # =====================================================
        # LINE CHART
        # =====================================================
        fig_line, ax_line = plt.subplots(figsize=(7, 3))

        ax_line.scatter(
            line_ok["X"], line_ok["Hardness_LINE"],
            label="LINE OK", s=28, alpha=0.8
        )
        ax_line.scatter(
            line_ng["X"], line_ng["Hardness_LINE"],
            label="LINE NG", s=45, marker="x"
        )

        ax_line.axhline(lo, linestyle="--", linewidth=1)
        ax_line.axhline(hi, linestyle="--", linewidth=1)

        ax_line.set_title("LINE Hardness")
        ax_line.set_xlabel("Coil Order (after filter)")
        ax_line.set_ylabel("HRB")
        ax_line.set_ylim(y_min, y_max)
        ax_line.set_yticks(yticks)
        ax_line.legend(loc="upper left", bbox_to_anchor=(1.02, 1))

        st.pyplot(fig_line)
