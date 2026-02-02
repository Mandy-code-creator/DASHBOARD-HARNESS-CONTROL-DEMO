# ===== PREPARE X AXIS =====
sub = sub.sort_values("COIL_NO").reset_index(drop=True)
sub["X"] = sub.index + 1

# ===== REMOVE ZERO HARDNESS (KHÔNG VẼ) =====
lab_df  = sub[sub["Hardness_LAB"]  > 0].copy()
line_df = sub[sub["Hardness_LINE"] > 0].copy()

# ===== SPLIT OK / NG =====
lab_ok  = lab_df[~lab_df["NG_LAB"]]
lab_ng  = lab_df[lab_df["NG_LAB"]]

line_ok = line_df[~line_df["NG_LINE"]]
line_ng = line_df[line_df["NG_LINE"]]

# ===== COMMON Y SCALE =====
y_min = int(np.floor(min(lo, lab_df["Hardness_LAB"].min(), line_df["Hardness_LINE"].min())))
y_max = int(np.ceil (max(hi, lab_df["Hardness_LAB"].max(), line_df["Hardness_LINE"].max())))

# =========================
# CHART 1 — HARDNESS LAB
# =========================
fig_lab, ax_lab = plt.subplots(figsize=(8, 3))

ax_lab.plot(
    lab_ok["X"],
    lab_ok["Hardness_LAB"],
    marker="o",
    linewidth=2,
    label="LAB OK",
    zorder=2
)

ax_lab.scatter(
    lab_ng["X"],
    lab_ng["Hardness_LAB"],
    s=60,
    label="LAB NG",
    zorder=3
)

ax_lab.axhline(lo, linestyle="--", linewidth=1, label="LSL")
ax_lab.axhline(hi, linestyle="--", linewidth=1, label="USL")

ax_lab.set_ylabel("Hardness LAB (HRB)")
ax_lab.set_xlabel("Coil Order (sorted by COIL_NO)")
ax_lab.set_title(f"{spec} | Hardness LAB (QA Reference)")

ax_lab.set_ylim(y_min, y_max)
ax_lab.set_yticks(range(y_min, y_max + 1))

ax_lab.legend(
    loc="center left",
    bbox_to_anchor=(1.02, 0.5),
    frameon=False
)

ax_lab.grid(alpha=0.3)

st.pyplot(fig_lab)


# =========================
# CHART 2 — HARDNESS LINE
# =========================
fig_line, ax_line = plt.subplots(figsize=(8, 3))

ax_line.plot(
    line_ok["X"],
    line_ok["Hardness_LINE"],
    marker="o",
    linewidth=2,
    label="LINE OK",
    zorder=2
)

ax_line.scatter(
    line_ng["X"],
    line_ng["Hardness_LINE"],
    s=60,
    label="LINE NG",
    zorder=3
)

ax_line.axhline(lo, linestyle="--", linewidth=1, label="LSL")
ax_line.axhline(hi, linestyle="--", linewidth=1, label="USL")

ax_line.set_ylabel("Hardness LINE (HRB)")
ax_line.set_xlabel("Coil Order (sorted by COIL_NO)")
ax_line.set_title(f"{spec} | Hardness LINE (Process Control)")

ax_line.set_ylim(y_min, y_max)
ax_line.set_yticks(range(y_min, y_max + 1))

ax_line.legend(
    loc="center left",
    bbox_to_anchor=(1.02, 0.5),
    frameon=False
)

ax_line.grid(alpha=0.3)

st.pyplot(fig_line)
