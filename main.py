# ==============================================================================
# APEX HUMAN PERFORMANCE & BIOMETRIC OPERATING SYSTEM — V3.0 ENTERPRISE
# main.py — core entry point, unified styling, master landing dashboard
# ------------------------------------------------------------------------------
# DEPLOYMENT (Streamlit Community Cloud):
#   Repo layout:
#     main.py
#     state_manager.py
#     requirements.txt
#     pages/1_Metabolic_Engine.py
#     pages/2_Fitbit_Air_Intelligence.py
#     pages/3_Basketball_Biomechanics.py
#     pages/4_Neuro_Academic_Habit_Tracker.py
#     pages/5_Predictive_ML_Studio.py
#   Set the app's "Main file path" to main.py — Streamlit auto-discovers pages/.
# ==============================================================================

from datetime import date

import pandas as pd
import plotly.express as px
import streamlit as st

from state_manager import (
    APP_NAME,
    APP_VERSION,
    ATHLETE_PROFILE,
    SCHEMAS,
    SHEET_NAMES,
    apply_theme,
    chartable,
    day_count,
    flag_from_score,
    get_df,
    init_global_state,
    latest_value,
    num_or,
    render_master_backup_panel,
    render_sidebar_profile,
    style_fig,
)

# ------------------------------------------------------------------------------
# SYSTEMIC UI INITIALIZATION
# ------------------------------------------------------------------------------

st.set_page_config(
    page_title="APEX OS | Human Performance Operating System",
    page_icon="🏀",
    layout="wide",
    initial_sidebar_state="expanded",
)

init_global_state()
apply_theme()

# ------------------------------------------------------------------------------
# SIDEBAR — GLOBAL CONFIGURATION
# ------------------------------------------------------------------------------

with st.sidebar:
    st.markdown(
        f"""
        <div style="padding:4px 0 8px 0;">
            <h2 style="margin:0;">🏀 {APP_NAME}</h2>
            <p style="color:#7E8FAD;font-size:.72rem;letter-spacing:.12em;margin:2px 0 0 0;">
                HUMAN PERFORMANCE OPERATING SYSTEM · V{APP_VERSION}
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    render_sidebar_profile()

    st.markdown("#### 🎯 Global Macro Targets")
    st.number_input("Calories (kcal)", min_value=1200, max_value=6000, step=50, key="t_cal")
    gc1, gc2, gc3 = st.columns(3)
    gc1.number_input("Protein (g)", min_value=50, max_value=400, step=5, key="t_pro")
    gc2.number_input("Carbs (g)", min_value=50, max_value=600, step=5, key="t_carb")
    gc3.number_input("Fat (g)", min_value=20, max_value=250, step=5, key="t_fat")

    st.markdown("#### ❤️ Autonomic Baselines")
    st.number_input("Baseline RHR (bpm)", min_value=35, max_value=100, step=1, key="baseline_rhr")
    st.number_input("Baseline HRV rMSSD (ms)", min_value=10, max_value=200, step=1, key="baseline_hrv")

    st.caption(f"{APP_NAME} v{APP_VERSION} · session data lives in memory — "
               "use the Master Backup panel below to persist it.")

# ------------------------------------------------------------------------------
# MASTER LANDING DASHBOARD
# ------------------------------------------------------------------------------

st.markdown(
    f"""
    <div style="padding:2px 0 4px 0;">
        <h1 style="margin-bottom:0;">🏀 {APP_NAME} · MISSION CONTROL</h1>
        <p style="color:#8FA1BF;letter-spacing:.13em;font-size:.78rem;margin-top:2px;">
            HUMAN PERFORMANCE & BIOMETRIC OPERATING SYSTEM ·
            {ATHLETE_PROFILE['role'].upper()} BUILD · {date.today().isoformat()}
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

# ---- KPI command row ---------------------------------------------------------

today_iso = date.today().isoformat()
nut = get_df("df_nutrition")
today_kcal = 0.0
if not nut.empty:
    today_rows = nut[nut["Date"] == today_iso]
    if not today_rows.empty:
        today_kcal = float(pd.to_numeric(today_rows["Calories"], errors="coerce").fillna(0).sum())

readiness = latest_value("df_fitbit_air", "Daily_Readiness_Score")
body_weight = latest_value("df_biomechanics", "Body_Weight")
vertical = latest_value("df_biomechanics", "Vertical_Jump_Inches")
focus_blocks = latest_value("df_cognitive_habits", "Focus_Blocks_Completed")

k1, k2, k3, k4, k5 = st.columns(5)

if readiness is None:
    k1.metric("Readiness", "—", "no telemetry yet", delta_color="off")
else:
    r = num_or(readiness, 0.0)
    k1.metric("Readiness", f"{r:.0f}%", flag_from_score(r), delta_color="off")

if body_weight is None:
    k2.metric("Body Weight", "—", "log biomechanics", delta_color="off")
else:
    bw = num_or(body_weight, ATHLETE_PROFILE["current_weight_lbs"])
    delta_lbs = bw - ATHLETE_PROFILE["current_weight_lbs"]
    k2.metric("Body Weight", f"{bw:.1f} lb", f"{delta_lbs:+.1f} vs 167 start",
              delta_color="inverse")

if vertical is None:
    k3.metric("Vertical Jump", "—", "log jump data", delta_color="off")
else:
    k3.metric("Vertical Jump", f"{num_or(vertical, 0):.1f} in", "latest measured",
              delta_color="off")

k4.metric("Fuel Today", f"{today_kcal:,.0f} kcal",
          f"target {int(st.session_state.t_cal):,}", delta_color="off")

if focus_blocks is None:
    k5.metric("Focus Blocks", "—", "log cognitive day", delta_color="off")
else:
    k5.metric("Focus Blocks", f"{num_or(focus_blocks, 0):.0f}", "latest logged day",
              delta_color="off")

st.divider()

# ---- Module navigation grid --------------------------------------------------

st.subheader("🗂️ System Modules")

MODULES = [
    ("pages/1_Metabolic_Engine.py", "🍽️ Metabolic Engine",
     "7-restaurant macro database, custom food creator, and the 6:00 PM "
     "pre-workout kinetic evaluator (GERC).", "df_nutrition"),
    ("pages/2_Fitbit_Air_Intelligence.py", "📡 Fitbit Air Intelligence",
     "Passive telemetry ingestion — readiness, HRV, RHR, sleep architecture — "
     "feeding the Autonomic Recovery Matrix.", "df_fitbit_air"),
    ("pages/3_Basketball_Biomechanics.py", "🏀 Basketball Biomechanics",
     "Relative force production, weight-drop jump projection, RSI analyzer, "
     "and tendon loading risk tracking.", "df_biomechanics"),
    ("pages/4_Neuro_Academic_Habit_Tracker.py", "🧠 Neuro-Academic Habit Tracker",
     "Cognitive load, Anki retention, optimization checklist, and "
     "neuro-athletic fatigue mapping.", "df_cognitive_habits"),
    ("pages/5_Predictive_ML_Studio.py", "🤖 Predictive ML Studio",
     "Random Forest + Linear Regression feature-importance engine across all "
     "aggregated health metrics.", "df_fitbit_air"),
]

grid_row_1 = st.columns(3)
grid_row_2 = st.columns(3)
slots = list(grid_row_1) + list(grid_row_2)

for slot, (path, label, desc, df_key) in zip(slots, MODULES):
    with slot:
        with st.container(border=True):
            st.markdown(f"**{label}**")
            st.caption(desc)
            st.caption(f"📅 {day_count(df_key)} day(s) of data logged")
            try:
                st.page_link(path, label=f"Open {label.split(' ', 1)[1]} →")
            except Exception:
                st.caption("Module file pending installation.")

with slots[5]:
    with st.container(border=True):
        st.markdown("**💾 Data Integrity**")
        total_rows = sum(len(get_df(k)) for k in SCHEMAS)
        st.caption("All five relational tables bundle into one master backup "
                   "workbook below.")
        st.caption(f"🗃️ {total_rows} total rows across {len(SCHEMAS)} tables")

st.divider()

# ---- Command-center trend snapshots ------------------------------------------

st.subheader("📈 Command-Center Trends")

trend_left, trend_right = st.columns(2, gap="medium")

with trend_left:
    try:
        fb = chartable("df_fitbit_air")
        fb_valid = fb.dropna(subset=["Daily_Readiness_Score"]) if not fb.empty else fb
        if fb_valid.empty or len(fb_valid) < 2:
            st.info(
                "🔒 **Readiness trendline** unlocks after 2 logged days of Fitbit Air "
                f"telemetry ({0 if fb_valid.empty else len(fb_valid)} logged so far). "
                "Open the Fitbit Air Intelligence module to start syncing."
            )
        else:
            fig_r = px.line(
                fb_valid, x="Date_dt", y="Daily_Readiness_Score", markers=True,
                title="Daily Readiness Score",
                labels={"Date_dt": "Date", "Daily_Readiness_Score": "Readiness (%)"},
            )
            fig_r.update_traces(line_color="#00E5A0", marker=dict(size=9, color="#00B4D8"))
            fig_r.add_hrect(y0=0, y1=50, fillcolor="#FF4D4F", opacity=0.08, line_width=0)
            fig_r.add_hrect(y0=50, y1=80, fillcolor="#FAAD14", opacity=0.08, line_width=0)
            fig_r.add_hrect(y0=80, y1=100, fillcolor="#00E5A0", opacity=0.08, line_width=0)
            fig_r.update_yaxes(range=[0, 105], title="Readiness (%)")
            st.plotly_chart(style_fig(fig_r, 330), use_container_width=True)
    except Exception as exc:
        st.info(f"Readiness trendline is temporarily unavailable ({exc}). "
                "Log more Fitbit Air days to rebuild it.")

with trend_right:
    try:
        bm = chartable("df_biomechanics")
        bm_valid = bm.dropna(subset=["Body_Weight"]) if not bm.empty else bm
        if bm_valid.empty or len(bm_valid) < 2:
            st.info(
                "🔒 **Weight-cut trajectory** unlocks after 2 logged days of body-weight "
                f"data ({0 if bm_valid.empty else len(bm_valid)} logged so far). "
                "Open the Basketball Biomechanics module to start logging."
            )
        else:
            fig_w = px.line(
                bm_valid, x="Date_dt", y="Body_Weight", markers=True,
                title="Body Weight vs. Prime Basketball Zone",
                labels={"Date_dt": "Date", "Body_Weight": "lbs"},
            )
            fig_w.update_traces(line_color="#00B4D8", marker=dict(size=9))
            fig_w.add_hrect(
                y0=ATHLETE_PROFILE["target_low_lbs"],
                y1=ATHLETE_PROFILE["target_high_lbs"],
                fillcolor="#00E5A0", opacity=0.12, line_width=0,
                annotation_text="PRIME ZONE 145–155",
                annotation_font_color="#00E5A0",
            )
            fig_w.update_yaxes(title="Body Weight (lbs)")
            st.plotly_chart(style_fig(fig_w, 330), use_container_width=True)
    except Exception as exc:
        st.info(f"Weight trajectory is temporarily unavailable ({exc}). "
                "Log more biomechanics days to rebuild it.")

st.divider()

# ---- Master backup / restore pipeline ----------------------------------------

with st.container(border=True):
    render_master_backup_panel()

st.markdown(
    f"""
    <p style="text-align:center;color:#42506B;font-size:.72rem;letter-spacing:.1em;margin-top:28px;">
        {APP_NAME} V{APP_VERSION} ENTERPRISE · FEED 6:00 PM → TRAIN 7:30 PM · BUILT FOR THE RIM
    </p>
    """,
    unsafe_allow_html=True,
)
