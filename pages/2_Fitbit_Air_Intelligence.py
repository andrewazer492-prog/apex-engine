# ==============================================================================
# APEX HUMAN PERFORMANCE & BIOMETRIC OPERATING SYSTEM — V3.0 ENTERPRISE
# pages/2_Fitbit_Air_Intelligence.py
# ------------------------------------------------------------------------------
# Ingestion hub for the screenless Fitbit Air tracker. Manual entry or bulk
# CSV paste from the Google Health ecosystem feeds the Autonomic Recovery Matrix,
# which derives a unified CNS Readiness Rating and operational training flags.
# ==============================================================================

from datetime import date
from io import StringIO

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from state_manager import (
    apply_theme,
    chartable,
    clamp,
    day_count,
    flag_from_score,
    get_df,
    get_row_by_date,
    init_global_state,
    minmax_scale,
    num_or,
    render_flag_banner,
    render_sidebar_profile,
    rolling_std,
    set_df,
    style_fig,
    upsert_by_date,
)

st.set_page_config(
    page_title="APEX OS | Fitbit Air Intelligence",
    page_icon="📡",
    layout="wide",
    initial_sidebar_state="expanded",
)

init_global_state()
apply_theme()

# ------------------------------------------------------------------------------
# AUTONOMIC RECOVERY ALGORITHM
# ------------------------------------------------------------------------------
# Unified CNS Readiness Rating (0–100) blends five autonomic/recovery channels:
#   Fitbit Air Daily Readiness   35%  (device's own composite, trusted anchor)
#   HRV rMSSD vs. baseline        25%  (parasympathetic reserve; higher = better)
#   Resting HR vs. baseline       15%  (sympathetic load; lower = better)
#   Sleep architecture            15%  (deep + REM minutes vs. targets)
#   Autonomic stability           10%  (inverse of rolling 7-day HRV/RHR volatility)
# The stability term is what the rolling standard deviations feed: a nervous
# system swinging widely day-to-day is dysregulated even if today's point looks ok.
# ------------------------------------------------------------------------------

W_READINESS = 0.35
W_HRV = 0.25
W_RHR = 0.15
W_SLEEP = 0.15
W_STABILITY = 0.10

DEEP_TARGET_MINS = 90.0   # ~1.5 h deep sleep target
REM_TARGET_MINS = 110.0   # ~1.8 h REM target


def sleep_subscore(deep_mins: float, rem_mins: float) -> float:
    deep = minmax_scale(num_or(deep_mins, 0.0), 0.0, DEEP_TARGET_MINS)
    rem = minmax_scale(num_or(rem_mins, 0.0), 0.0, REM_TARGET_MINS)
    return 100.0 * (0.5 * deep + 0.5 * rem)


def hrv_subscore(hrv: float, baseline: float) -> float:
    """100 at/above baseline, scaling down to 0 at half-baseline."""
    hrv = num_or(hrv, np.nan)
    if np.isnan(hrv):
        return np.nan
    ratio = hrv / max(baseline, 1.0)
    return 100.0 * clamp((ratio - 0.5) / 0.5, 0.0, 1.0)


def rhr_subscore(rhr: float, baseline: float) -> float:
    """100 at/below baseline; each bpm above baseline costs ~5 points."""
    rhr = num_or(rhr, np.nan)
    if np.isnan(rhr):
        return np.nan
    deviation = rhr - baseline
    if deviation <= 0:
        return 100.0
    return clamp(100.0 - 5.0 * deviation, 0.0, 100.0)


def stability_subscore(hrv_std: float, rhr_std: float, hrv_base: float, rhr_base: float) -> float:
    """Inverse volatility: a coefficient-of-variation-style penalty on swings."""
    if (hrv_std is None or np.isnan(hrv_std)) and (rhr_std is None or np.isnan(rhr_std)):
        return np.nan
    hrv_cv = (num_or(hrv_std, 0.0) / max(hrv_base, 1.0)) if hrv_std is not None else 0.0
    rhr_cv = (num_or(rhr_std, 0.0) / max(rhr_base, 1.0)) if rhr_std is not None else 0.0
    penalty = 100.0 * (0.6 * hrv_cv + 0.4 * rhr_cv) * 2.0
    return clamp(100.0 - penalty, 0.0, 100.0)


def compute_cns_rating(row: dict, hrv_std, rhr_std, hrv_base: float, rhr_base: float) -> dict:
    """Returns the composite rating plus the contributing subscores."""
    readiness = num_or(row.get("Daily_Readiness_Score"), np.nan)
    hrv_s = hrv_subscore(row.get("HRV_rMSSD"), hrv_base)
    rhr_s = rhr_subscore(row.get("Resting_Heart_Rate"), rhr_base)
    sleep_s = sleep_subscore(row.get("Deep_Sleep_Mins"), row.get("REM_Sleep_Mins"))
    stab_s = stability_subscore(hrv_std, rhr_std, hrv_base, rhr_base)

    parts = [
        (readiness, W_READINESS),
        (hrv_s, W_HRV),
        (rhr_s, W_RHR),
        (sleep_s, W_SLEEP),
        (stab_s, W_STABILITY),
    ]
    num, den = 0.0, 0.0
    for value, weight in parts:
        if value is not None and not np.isnan(value):
            num += value * weight
            den += weight
    rating = round(clamp(num / den, 0.0, 100.0), 1) if den > 0 else np.nan
    return {
        "rating": rating,
        "readiness": readiness,
        "hrv_s": hrv_s,
        "rhr_s": rhr_s,
        "sleep_s": sleep_s,
        "stab_s": stab_s,
    }

# ------------------------------------------------------------------------------
# SIDEBAR
# ------------------------------------------------------------------------------

with st.sidebar:
    st.markdown("### 📡 Fitbit Air Intelligence")
    render_sidebar_profile()
    sel_date = st.date_input("📅 Telemetry Date", value=date.today())
    d_iso = sel_date.isoformat()
    st.number_input("Baseline RHR (bpm)", min_value=35, max_value=100, step=1, key="baseline_rhr")
    st.number_input("Baseline HRV rMSSD (ms)", min_value=10, max_value=200, step=1, key="baseline_hrv")
    st.caption("Baselines anchor the HRV/RHR deviation subscores in the recovery matrix.")

hrv_base = float(st.session_state.baseline_hrv)
rhr_base = float(st.session_state.baseline_rhr)

st.markdown(
    f"""
    <div style="padding:2px 0 4px 0;">
        <h1 style="margin-bottom:0;">📡 Fitbit Air Intelligence</h1>
        <p style="color:#8FA1BF;letter-spacing:.13em;font-size:.78rem;margin-top:2px;">
            SCREENLESS WEARABLE TELEMETRY · AUTONOMIC RECOVERY MATRIX · {d_iso}
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

tab_log, tab_matrix, tab_trends, tab_bulk = st.tabs([
    "🛰️ Telemetry Logging",
    "🧮 Autonomic Recovery Matrix",
    "📈 Trends & Volatility",
    "📥 Bulk CSV Sync",
])

# ==============================================================================
# TAB 1 — TELEMETRY LOGGING PANEL
# ==============================================================================

with tab_log:
    st.subheader("Telemetry Logging Panel")
    st.caption(
        "The Fitbit Air is screenless — pull these numbers from the Fitbit / Google "
        "Health app and log them here, or paste a structured CSV on the Bulk Sync tab."
    )

    existing = get_row_by_date("df_fitbit_air", d_iso)

    def _ev(col, default):
        if existing is None or col not in existing.index or pd.isna(existing[col]):
            return default
        return existing[col]

    with st.form("fitbit_form"):
        c1, c2 = st.columns(2)
        with c1:
            readiness = st.slider("Daily Readiness Score (0–100)", 0, 100,
                                  int(num_or(_ev("Daily_Readiness_Score", 70), 70)))
            cardio_load = st.slider("Cardio Load (training-impulse units)", 0, 300,
                                    int(num_or(_ev("Cardio_Load", 40), 40)))
            hrv = st.slider("HRV rMSSD (ms)", 5, 200,
                            int(num_or(_ev("HRV_rMSSD", hrv_base), hrv_base)))
            rhr = st.slider("Resting Heart Rate (bpm)", 35, 110,
                            int(num_or(_ev("Resting_Heart_Rate", rhr_base), rhr_base)))
        with c2:
            deep = st.slider("Deep Sleep (mins)", 0, 240,
                             int(num_or(_ev("Deep_Sleep_Mins", 80), 80)))
            rem = st.slider("REM Sleep (mins)", 0, 240,
                            int(num_or(_ev("REM_Sleep_Mins", 95), 95)))
            steps = st.number_input("Total Steps", min_value=0, max_value=60000, step=250,
                                    value=int(num_or(_ev("Total_Steps", 8000), 8000)))
        submitted = st.form_submit_button("🛰️ Save Telemetry", type="primary",
                                          use_container_width=True)

    if submitted:
        upsert_by_date("df_fitbit_air", d_iso, {
            "Daily_Readiness_Score": float(readiness),
            "Cardio_Load": float(cardio_load),
            "HRV_rMSSD": float(hrv),
            "Resting_Heart_Rate": float(rhr),
            "Deep_Sleep_Mins": float(deep),
            "REM_Sleep_Mins": float(rem),
            "Total_Steps": float(steps),
        })
        st.toast(f"Telemetry saved for {d_iso}.", icon="🛰️")
        st.rerun()

    if existing is not None:
        st.markdown("##### Logged Snapshot")
        sc = st.columns(4)
        sc[0].metric("Readiness", f"{num_or(_ev('Daily_Readiness_Score', 0), 0):.0f}")
        sc[1].metric("HRV rMSSD", f"{num_or(_ev('HRV_rMSSD', 0), 0):.0f} ms")
        sc[2].metric("Resting HR", f"{num_or(_ev('Resting_Heart_Rate', 0), 0):.0f} bpm")
        sc[3].metric("Steps", f"{num_or(_ev('Total_Steps', 0), 0):,.0f}")

# ==============================================================================
# TAB 2 — AUTONOMIC RECOVERY MATRIX
# ==============================================================================

with tab_matrix:
    st.subheader("Autonomic Recovery Matrix")
    st.caption(
        "Blends Fitbit Air readiness (35%), HRV-vs-baseline (25%), RHR-vs-baseline "
        "(15%), sleep architecture (15%), and 7-day autonomic stability (10%) into a "
        "unified CNS Readiness Rating that gates today's training."
    )

    fb = chartable("df_fitbit_air")
    row = get_row_by_date("df_fitbit_air", d_iso)

    if row is None:
        st.info(
            "No telemetry logged for this date yet. Save today's numbers on the "
            "Telemetry Logging tab to compute the CNS Readiness Rating."
        )
    else:
        # Rolling 7-day std up to and including the selected date.
        hrv_std = rhr_std = np.nan
        if not fb.empty:
            upto = fb[fb["Date"] <= d_iso]
            if len(upto) >= 2:
                hrv_std = rolling_std(upto["HRV_rMSSD"], 7).iloc[-1]
                rhr_std = rolling_std(upto["Resting_Heart_Rate"], 7).iloc[-1]

        row_dict = {c: row[c] for c in row.index}
        res = compute_cns_rating(row_dict, hrv_std, rhr_std, hrv_base, rhr_base)
        rating = res["rating"]

        if rating is None or np.isnan(rating):
            st.info("Not enough channels logged on this date to compute a rating.")
        else:
            gcol = ("#00E5A0" if rating >= 80 else "#FAAD14" if rating >= 50 else "#FF4D4F")
            gauge = go.Figure(go.Indicator(
                mode="gauge+number",
                value=rating,
                number={"suffix": "%", "font": {"color": "#F2F5FA", "size": 44}},
                title={"text": f"CNS READINESS · {d_iso}", "font": {"color": "#8FA1BF", "size": 13}},
                gauge={
                    "axis": {"range": [0, 100], "tickcolor": "#5A6B8C"},
                    "bar": {"color": gcol, "thickness": 0.32},
                    "bgcolor": "rgba(0,0,0,0)", "borderwidth": 0,
                    "steps": [
                        {"range": [0, 50], "color": "rgba(255,77,79,0.18)"},
                        {"range": [50, 80], "color": "rgba(250,173,20,0.18)"},
                        {"range": [80, 100], "color": "rgba(0,229,160,0.18)"},
                    ],
                },
            ))
            gauge.update_layout(height=250, margin=dict(t=44, b=6, l=36, r=36),
                                paper_bgcolor="rgba(0,0,0,0)", font={"color": "#E6E9F0"})

            gleft, gright = st.columns([5, 7], gap="large")
            with gleft:
                st.plotly_chart(gauge, use_container_width=True)
            with gright:
                render_flag_banner(rating)
                st.markdown("###### Subscore Contributions")

                def fmt(v):
                    return "—" if v is None or np.isnan(v) else f"{v:.0f}"

                sub = st.columns(3)
                sub[0].metric("Fitbit Readiness (35%)", fmt(res["readiness"]))
                sub[1].metric("HRV vs base (25%)", fmt(res["hrv_s"]),
                              f"{num_or(row_dict.get('HRV_rMSSD'),0):.0f} / {hrv_base:.0f} ms",
                              delta_color="off")
                sub[2].metric("RHR vs base (15%)", fmt(res["rhr_s"]),
                              f"{num_or(row_dict.get('Resting_Heart_Rate'),0):.0f} / {rhr_base:.0f} bpm",
                              delta_color="off")
                sub2 = st.columns(3)
                sub2[0].metric("Sleep arch. (15%)", fmt(res["sleep_s"]))
                sub2[1].metric("Stability (10%)", fmt(res["stab_s"]))
                if not (hrv_std is None or np.isnan(hrv_std)):
                    sub2[2].metric("7-day HRV σ", f"{hrv_std:.1f} ms", delta_color="off")
                else:
                    sub2[2].metric("7-day HRV σ", "—", "need 2+ days", delta_color="off")

            st.markdown(
                f"""
                <div class="apex-card">
                    <span class="apex-pill"
                          style="background:rgba(0,180,216,.12);color:#00B4D8;border:1px solid #00B4D8;">
                        AUTONOMIC STABILITY READ
                    </span>
                    <p style="margin:8px 0 0 0;font-size:.86rem;line-height:1.6;color:#C9D2E3;">
                        Rolling 7-day standard deviation —
                        <b>HRV σ = {('n/a' if hrv_std is None or np.isnan(hrv_std) else f'{hrv_std:.1f} ms')}</b>,
                        <b>RHR σ = {('n/a' if rhr_std is None or np.isnan(rhr_std) else f'{rhr_std:.1f} bpm')}</b>.
                        Wide day-to-day swings signal an autonomic system that has not settled,
                        which suppresses the stability term even when today's point values look
                        acceptable. Tight, low-variance HRV is the signature of a fully adapted,
                        plyometric-ready nervous system.
                    </p>
                </div>
                """,
                unsafe_allow_html=True,
            )

# ==============================================================================
# TAB 3 — TRENDS & VOLATILITY
# ==============================================================================

with tab_trends:
    st.subheader("Trends & Volatility")
    fb = chartable("df_fitbit_air")
    days = day_count("df_fitbit_air")

    if days < 2:
        st.info(
            f"🔒 **Trend charts** unlock after 2 logged telemetry days ({days} logged "
            "so far). Keep syncing the Fitbit Air daily to activate volatility tracking."
        )
    else:
        try:
            fb = fb.sort_values("Date_dt").reset_index(drop=True)
            fb["HRV_roll_std"] = rolling_std(fb["HRV_rMSSD"], 7)
            fb["RHR_roll_std"] = rolling_std(fb["Resting_Heart_Rate"], 7)

            t1, t2 = st.columns(2, gap="medium")
            with t1:
                fig_hrv = go.Figure()
                fig_hrv.add_trace(go.Scatter(
                    x=fb["Date_dt"], y=fb["HRV_rMSSD"], mode="lines+markers",
                    name="HRV rMSSD", line=dict(color="#00E5A0", width=3)))
                fig_hrv.add_trace(go.Scatter(
                    x=fb["Date_dt"], y=fb["HRV_roll_std"], mode="lines",
                    name="7-day σ", line=dict(color="#B388FF", width=2, dash="dot"),
                    yaxis="y2"))
                fig_hrv.update_layout(
                    title="HRV rMSSD + 7-Day Volatility",
                    yaxis=dict(title="HRV (ms)"),
                    yaxis2=dict(title="σ", overlaying="y", side="right", showgrid=False))
                st.plotly_chart(style_fig(fig_hrv, 340), use_container_width=True)
            with t2:
                fig_rhr = go.Figure()
                fig_rhr.add_trace(go.Scatter(
                    x=fb["Date_dt"], y=fb["Resting_Heart_Rate"], mode="lines+markers",
                    name="Resting HR", line=dict(color="#00B4D8", width=3)))
                fig_rhr.add_trace(go.Scatter(
                    x=fb["Date_dt"], y=fb["RHR_roll_std"], mode="lines",
                    name="7-day σ", line=dict(color="#FAAD14", width=2, dash="dot"),
                    yaxis="y2"))
                fig_rhr.update_layout(
                    title="Resting HR + 7-Day Volatility",
                    yaxis=dict(title="RHR (bpm)"),
                    yaxis2=dict(title="σ", overlaying="y", side="right", showgrid=False))
                st.plotly_chart(style_fig(fig_rhr, 340), use_container_width=True)

            s1, s2 = st.columns(2, gap="medium")
            with s1:
                sleep_long = fb.melt(
                    id_vars="Date_dt", value_vars=["Deep_Sleep_Mins", "REM_Sleep_Mins"],
                    var_name="Stage", value_name="Mins").dropna(subset=["Mins"])
                sleep_long["Stage"] = sleep_long["Stage"].map(
                    {"Deep_Sleep_Mins": "Deep", "REM_Sleep_Mins": "REM"})
                fig_sleep = px.area(
                    sleep_long, x="Date_dt", y="Mins", color="Stage",
                    title="Sleep Architecture (Deep + REM)",
                    color_discrete_map={"Deep": "#00B4D8", "REM": "#B388FF"})
                st.plotly_chart(style_fig(fig_sleep, 320), use_container_width=True)
            with s2:
                fig_rd = px.line(
                    fb.dropna(subset=["Daily_Readiness_Score"]),
                    x="Date_dt", y="Daily_Readiness_Score", markers=True,
                    title="Fitbit Air Daily Readiness")
                fig_rd.update_traces(line_color="#00E5A0", marker=dict(size=8))
                fig_rd.add_hrect(y0=0, y1=50, fillcolor="#FF4D4F", opacity=0.08, line_width=0)
                fig_rd.add_hrect(y0=50, y1=80, fillcolor="#FAAD14", opacity=0.08, line_width=0)
                fig_rd.add_hrect(y0=80, y1=100, fillcolor="#00E5A0", opacity=0.08, line_width=0)
                fig_rd.update_yaxes(range=[0, 105])
                st.plotly_chart(style_fig(fig_rd, 320), use_container_width=True)
        except Exception as exc:
            st.info(f"Trend rendering is temporarily unavailable ({exc}). "
                    "Log additional telemetry days to rebuild the charts.")

# ==============================================================================
# TAB 4 — BULK CSV SYNC
# ==============================================================================

with tab_bulk:
    st.subheader("Bulk CSV Sync")
    st.caption(
        "Paste rows exported from the Google Health / Fitbit ecosystem. Expected "
        "columns (header row required): Date, Daily_Readiness_Score, Cardio_Load, "
        "HRV_rMSSD, Resting_Heart_Rate, Deep_Sleep_Mins, REM_Sleep_Mins, Total_Steps. "
        "Missing columns are tolerated and filled as blanks."
    )

    sample = ("Date,Daily_Readiness_Score,Cardio_Load,HRV_rMSSD,Resting_Heart_Rate,"
              "Deep_Sleep_Mins,REM_Sleep_Mins,Total_Steps\n"
              "2026-06-10,82,45,68,53,95,110,9800\n"
              "2026-06-11,74,52,61,56,80,98,11200\n")
    with st.expander("📋 Show expected format / sample"):
        st.code(sample, language="csv")

    pasted = st.text_area("Paste CSV rows here", height=180, key="fb_bulk_paste")
    bcol1, bcol2 = st.columns([3, 7])
    bulk_mode = bcol2.radio("Apply mode", ["Merge (upsert by date)", "Replace all telemetry"],
                            horizontal=True, key="fb_bulk_mode")
    if bcol1.button("📥 Ingest Pasted CSV", type="primary", use_container_width=True):
        if not pasted.strip():
            st.error("Paste some CSV rows first.")
        else:
            try:
                incoming = pd.read_csv(StringIO(pasted))
                cols = ["Date", "Daily_Readiness_Score", "Cardio_Load", "HRV_rMSSD",
                        "Resting_Heart_Rate", "Deep_Sleep_Mins", "REM_Sleep_Mins", "Total_Steps"]
                incoming.columns = [str(c).strip() for c in incoming.columns]
                for c in cols:
                    if c not in incoming.columns:
                        incoming[c] = pd.NA
                incoming = incoming[cols]
                parsed = pd.to_datetime(incoming["Date"], errors="coerce")
                incoming = incoming[parsed.notna()].copy()
                incoming["Date"] = parsed[parsed.notna()].dt.date.astype(str)
                for c in cols[1:]:
                    incoming[c] = pd.to_numeric(incoming[c], errors="coerce")
                if incoming.empty:
                    st.error("No valid dated rows found. Check the Date column format (YYYY-MM-DD).")
                else:
                    if bulk_mode.startswith("Replace"):
                        set_df("df_fitbit_air", incoming.drop_duplicates(
                            subset="Date", keep="last").sort_values("Date"))
                    else:
                        for _, r in incoming.iterrows():
                            upsert_by_date("df_fitbit_air", r["Date"],
                                           {c: r[c] for c in cols[1:] if not pd.isna(r[c])})
                    st.toast(f"Ingested {len(incoming)} telemetry row(s).", icon="📥")
                    st.rerun()
            except Exception as exc:
                st.error(f"Could not parse that CSV: {exc}")

    st.divider()
    st.markdown("##### Current Telemetry Table")
    fb_now = get_df("df_fitbit_air")
    if fb_now.empty:
        st.info("No telemetry logged yet.")
    else:
        st.dataframe(fb_now.sort_values("Date", ascending=False),
                     use_container_width=True, hide_index=True)
