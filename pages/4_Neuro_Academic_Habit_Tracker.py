# ==============================================================================
# APEX HUMAN PERFORMANCE & BIOMETRIC OPERATING SYSTEM — V3.0 ENTERPRISE
# pages/4_Neuro_Academic_Habit_Tracker.py
# ------------------------------------------------------------------------------
# Cognitive load logging (study/focus blocks + recall accuracy), the human-
# optimization adherence matrix (sunlight, peptides, Tretinoin/Minoxidil
# skincare), and dual-axis neuro-athletic fatigue mapping that overlays physical
# training load against cognitive output to expose fatigue-driven recall decay.
# ==============================================================================

from datetime import date

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from state_manager import (
    apply_theme,
    chartable,
    day_count,
    get_df,
    get_row_by_date,
    init_global_state,
    num_or,
    render_sidebar_profile,
    style_fig,
    to_bool,
    upsert_by_date,
)

st.set_page_config(
    page_title="APEX OS | Neuro-Academic Habit Tracker",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)

init_global_state()
apply_theme()

# ------------------------------------------------------------------------------
# SIDEBAR
# ------------------------------------------------------------------------------

with st.sidebar:
    st.markdown("### 🧠 Neuro-Academic Tracker")
    render_sidebar_profile()
    sel_date = st.date_input("📅 Entry Date", value=date.today())
    d_iso = sel_date.isoformat()
    st.caption("Cognitive output + optimization adherence persist in the master backup.")

st.markdown(
    f"""
    <div style="padding:2px 0 4px 0;">
        <h1 style="margin-bottom:0;">🧠 Neuro-Academic Habit Tracker</h1>
        <p style="color:#8FA1BF;letter-spacing:.13em;font-size:.78rem;margin-top:2px;">
            COGNITIVE LOAD · OPTIMIZATION ADHERENCE · NEURO-ATHLETIC FATIGUE · {d_iso}
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

tab_log, tab_matrix, tab_fatigue = st.tabs([
    "📚 Cognitive Load & Protocols",
    "✅ Adherence Consistency Matrix",
    "🔀 Neuro-Athletic Fatigue Mapping",
])

# ==============================================================================
# TAB 1 — COGNITIVE LOAD INTERFACE + OPTIMIZATION CHECKLIST
# ==============================================================================

with tab_log:
    st.subheader("Cognitive Load Interface")
    st.caption(
        "Log study/focus blocks and recall accuracy (Anki flashcard retention + active "
        "recall drills), then toggle the day's human-optimization protocols. Everything "
        "here persists in the five-table master backup."
    )

    existing = get_row_by_date("df_cognitive_habits", d_iso)

    def _ev(col, default):
        if existing is None or col not in existing.index or pd.isna(existing[col]):
            return default
        return existing[col]

    cl, cr = st.columns([5, 7], gap="large")

    with cl:
        with st.form("cognitive_form"):
            st.markdown("##### Cognitive Output")
            focus = st.slider("Study / Focus Blocks Completed", 0, 16,
                              int(num_or(_ev("Focus_Blocks_Completed", 4), 4)),
                              help="Deep-work blocks (~25–50 min each) completed today.")
            recall = st.slider("Recall Accuracy — Anki + active recall (%)", 0, 100,
                               int(num_or(_ev("Anki_Retention_Rate", 85), 85)),
                               help="Unified retention metric: flashcard retention rate and "
                                    "active-recall drill accuracy.")
            st.markdown("##### Human-Optimization Protocols")
            sun = st.toggle("☀️ Morning Sunlight Exposure",
                            value=to_bool(_ev("Sunlight_Exposure_Bool", False)))
            pep = st.toggle("🧬 Peptide Protocol Adherence",
                            value=to_bool(_ev("Peptide_Adherence_Bool", False)))
            skin = st.toggle("🧴 Skincare Regimen (Tretinoin + Minoxidil)",
                             value=to_bool(_ev("Skincare_Adherence_Bool", False)))
            saved = st.form_submit_button("💾 Save Cognitive Day", type="primary",
                                          use_container_width=True)
        if saved:
            upsert_by_date("df_cognitive_habits", d_iso, {
                "Focus_Blocks_Completed": float(focus),
                "Anki_Retention_Rate": float(recall),
                "Peptide_Adherence_Bool": bool(pep),
                "Sunlight_Exposure_Bool": bool(sun),
                "Skincare_Adherence_Bool": bool(skin),
            })
            st.toast(f"Cognitive day saved for {d_iso}.", icon="🧠")
            st.rerun()

    with cr:
        st.markdown("##### Today's Snapshot")
        adherence = (int(sun) + int(pep) + int(skin)) / 3.0 * 100.0
        sn = st.columns(3)
        sn[0].metric("Focus Blocks", f"{focus}")
        sn[1].metric("Recall Accuracy", f"{recall}%")
        sn[2].metric("Protocol Adherence", f"{adherence:.0f}%")

        cognitive_load_index = focus * (recall / 100.0)
        st.markdown(
            f"""
            <div class="apex-card">
                <span class="apex-pill"
                      style="background:rgba(179,136,255,.14);color:#B388FF;border:1px solid #B388FF;">
                    EFFECTIVE COGNITIVE THROUGHPUT
                </span>
                <p style="margin:8px 0 0 0;font-size:.86rem;line-height:1.6;color:#C9D2E3;">
                    Throughput index = focus blocks × recall accuracy =
                    <b style="color:#B388FF;">{cognitive_load_index:.1f}</b>.
                    This weights raw study volume by how much actually stuck — the metric the
                    Fatigue Mapping tab plots against physical training load to find the point
                    where lifting/plyometric fatigue starts eroding retention.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # 7-day adherence streak read
        ch = chartable("df_cognitive_habits")
        if not ch.empty:
            recent = ch[ch["Date"] <= d_iso].tail(7)
            if not recent.empty:
                rate = recent[["Sunlight_Exposure_Bool", "Peptide_Adherence_Bool",
                               "Skincare_Adherence_Bool"]].apply(
                    lambda s: s.map(to_bool)).mean(axis=1).mean() * 100.0
                st.caption(f"Rolling 7-day protocol adherence: {rate:.0f}%")

# ==============================================================================
# TAB 2 — ADHERENCE CONSISTENCY MATRIX
# ==============================================================================

with tab_matrix:
    st.subheader("Optimization Adherence Consistency Matrix")
    st.caption(
        "Day-by-day adherence grid for the three keystone protocols. Green = done, "
        "slate = missed. Consistency — not intensity — is what compounds for circadian "
        "alignment, tissue recovery, and Tretinoin/Minoxidil efficacy."
    )

    ch = chartable("df_cognitive_habits")
    if ch.empty:
        st.info("🔒 **Consistency matrix** unlocks after your first logged cognitive day.")
    else:
        try:
            grid = ch.sort_values("Date_dt").tail(30).copy()
            labels = {
                "Sunlight_Exposure_Bool": "Sunlight",
                "Peptide_Adherence_Bool": "Peptides",
                "Skincare_Adherence_Bool": "Skincare",
            }
            mat = []
            for col in labels:
                mat.append([1 if to_bool(v) else 0 for v in grid[col]])
            date_labels = grid["Date_dt"].dt.strftime("%m-%d").tolist()
            fig = go.Figure(go.Heatmap(
                z=mat,
                x=date_labels,
                y=list(labels.values()),
                colorscale=[[0, "#1B2433"], [1, "#00E5A0"]],
                showscale=False,
                xgap=3, ygap=6,
                hovertemplate="%{y} · %{x}: %{z}<extra></extra>",
            ))
            fig.update_layout(
                title="Protocol Adherence — Last 30 Logged Days",
                template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)", height=240,
                margin=dict(t=46, b=8, l=8, r=8), font=dict(color="#E6E9F0"))
            st.plotly_chart(fig, use_container_width=True)

            st.markdown("##### Adherence Rates")
            rates = st.columns(3)
            for i, (col, lab) in enumerate(labels.items()):
                series = grid[col].map(to_bool)
                pct = series.mean() * 100.0 if len(series) else 0.0
                # current streak
                streak = 0
                for v in reversed(series.tolist()):
                    if v:
                        streak += 1
                    else:
                        break
                rates[i].metric(lab, f"{pct:.0f}%", f"{streak}-day streak", delta_color="off")

            cdf = ch.sort_values("Date_dt").copy()
            cdf["Adherence_%"] = cdf[list(labels.keys())].apply(
                lambda r: np.mean([1 if to_bool(v) else 0 for v in r]) * 100.0, axis=1)
            fig_line = px.line(cdf, x="Date_dt", y="Adherence_%", markers=True,
                               title="Composite Daily Adherence (%)")
            fig_line.update_traces(line_color="#00E5A0", marker=dict(size=8, color="#00B4D8"))
            fig_line.update_yaxes(range=[0, 105])
            st.plotly_chart(style_fig(fig_line, 300), use_container_width=True)
        except Exception as exc:
            st.info(f"Matrix rendering temporarily unavailable ({exc}). Log more days to rebuild it.")

# ==============================================================================
# TAB 3 — NEURO-ATHLETIC FATIGUE MAPPING
# ==============================================================================

with tab_fatigue:
    st.subheader("Neuro-Athletic Fatigue Mapping")
    st.caption(
        "Dual-axis overlay of physical training load (Fitbit cardio load + plyometric "
        "impact from the tendon tracker) against cognitive output (focus blocks and "
        "recall accuracy) — pinpointing where physical fatigue begins to erode retention."
    )

    ch = chartable("df_cognitive_habits")
    fb = chartable("df_fitbit_air")

    # Plyometric impact pulled from the Biomechanics page-local tendon log (session-shared).
    tendon = st.session_state.get("tendon_log", pd.DataFrame())
    if isinstance(tendon, pd.DataFrame) and not tendon.empty:
        tload = tendon.copy()
        tload["Date"] = pd.to_datetime(tload["Date"], errors="coerce").dt.date.astype(str)
        plyo_by_date = tload.groupby("Date")["Session_Load"].sum()
    else:
        plyo_by_date = pd.Series(dtype=float)

    cog_days = day_count("df_cognitive_habits")
    if cog_days < 2:
        st.info(
            f"🔒 **Fatigue mapping** unlocks after 2 logged cognitive days ({cog_days} so "
            "far). Log focus blocks + recall daily, and ideally sync Fitbit cardio load and "
            "plyometric sessions, to expose the fatigue-vs-retention relationship."
        )
    else:
        try:
            cog = ch.sort_values("Date_dt").copy()
            cog["Cognitive_Throughput"] = (
                pd.to_numeric(cog["Focus_Blocks_Completed"], errors="coerce").fillna(0) *
                pd.to_numeric(cog["Anki_Retention_Rate"], errors="coerce").fillna(0) / 100.0)

            # Build per-date physical load = Fitbit cardio load + plyometric impact.
            phys = pd.DataFrame({"Date": cog["Date"]})
            cardio_map = {}
            if not fb.empty:
                cardio_map = dict(zip(fb["Date"],
                                      pd.to_numeric(fb["Cardio_Load"], errors="coerce")))
            phys["Cardio_Load"] = phys["Date"].map(cardio_map).fillna(0.0)
            phys["Plyo_Load"] = phys["Date"].map(plyo_by_date).fillna(0.0)
            phys["Physical_Load"] = phys["Cardio_Load"] + phys["Plyo_Load"]

            merged = cog.merge(phys[["Date", "Physical_Load"]], on="Date", how="left")
            merged["Physical_Load"] = merged["Physical_Load"].fillna(0.0)

            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=merged["Date_dt"], y=merged["Physical_Load"],
                name="Physical Training Load", marker_color="rgba(0,180,216,0.55)"))
            fig.add_trace(go.Scatter(
                x=merged["Date_dt"], y=merged["Focus_Blocks_Completed"],
                name="Focus Blocks", mode="lines+markers",
                line=dict(color="#00E5A0", width=3), yaxis="y2"))
            fig.add_trace(go.Scatter(
                x=merged["Date_dt"], y=merged["Anki_Retention_Rate"],
                name="Recall Accuracy (%)", mode="lines+markers",
                line=dict(color="#B388FF", width=3, dash="dot"), yaxis="y2"))
            fig.update_layout(
                title="Physical Load vs. Cognitive Output",
                yaxis=dict(title="Physical Load"),
                yaxis2=dict(title="Focus blocks / Recall %", overlaying="y", side="right",
                            showgrid=False))
            st.plotly_chart(style_fig(fig, 380), use_container_width=True)

            # Correlation read between physical load and recall accuracy.
            corr_df = merged.dropna(subset=["Physical_Load", "Anki_Retention_Rate"])
            if len(corr_df) >= 3 and corr_df["Physical_Load"].std(skipna=True) not in (0, np.nan):
                r = float(np.corrcoef(
                    pd.to_numeric(corr_df["Physical_Load"], errors="coerce"),
                    pd.to_numeric(corr_df["Anki_Retention_Rate"], errors="coerce"))[0, 1])
                if np.isnan(r):
                    st.info("Physical load shows no variance yet — vary training to read the correlation.")
                elif r <= -0.4:
                    st.warning(
                        f"🟠 Physical load ↔ recall correlation r = {r:+.2f}. Higher training "
                        "load is tracking with **lower** recall accuracy — a fatigue-driven "
                        "cognitive cost. Stack heavy sessions away from your highest-yield study "
                        "blocks, and protect sleep on max-effort training days.")
                elif r >= 0.4:
                    st.success(
                        f"🟢 Physical load ↔ recall correlation r = {r:+.2f}. Training and "
                        "retention are rising together — you're in a well-fueled, well-recovered "
                        "window where exercise is priming cognition rather than taxing it.")
                else:
                    st.info(
                        f"⚪ Physical load ↔ recall correlation r = {r:+.2f}. No strong coupling "
                        "yet — keep logging to sharpen the signal.")
            else:
                st.info("Need 3+ overlapping days with physical load + recall to compute the "
                        "fatigue correlation.")
        except Exception as exc:
            st.info(f"Fatigue mapping temporarily unavailable ({exc}). Log more cognitive and "
                    "training days to rebuild it.")
