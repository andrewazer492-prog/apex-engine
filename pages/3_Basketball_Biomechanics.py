# ==============================================================================
# APEX HUMAN PERFORMANCE & BIOMETRIC OPERATING SYSTEM — V3.0 ENTERPRISE
# pages/3_Basketball_Biomechanics.py
# ------------------------------------------------------------------------------
# Acceleration physics (F = ma), Sayers relative-power index, weight-drop
# vertical-jump projection, Reactive Strength Index (RSI) analyzer, and a
# cumulative tendon-loading tracker for early jumper's-knee risk detection.
# ==============================================================================

from datetime import date

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from state_manager import (
    ATHLETE_PROFILE,
    apply_theme,
    chartable,
    compute_rsi,
    day_count,
    get_df,
    get_row_by_date,
    init_global_state,
    num_or,
    render_sidebar_profile,
    safe_div,
    style_fig,
    upsert_by_date,
)

st.set_page_config(
    page_title="APEX OS | Basketball Biomechanics",
    page_icon="🏀",
    layout="wide",
    initial_sidebar_state="expanded",
)

init_global_state()
apply_theme()

# ------------------------------------------------------------------------------
# PHYSICS CONSTANTS & MODELS
# ------------------------------------------------------------------------------

G = 9.81                # gravitational acceleration (m/s^2)
LB_TO_KG = 0.45359237
IN_TO_M = 0.0254
M_TO_IN = 1.0 / IN_TO_M


def lbs_to_kg(lbs: float) -> float:
    return num_or(lbs, 0.0) * LB_TO_KG


def jump_height_from_flight(flight_ms: float) -> float:
    """Flight-time method: h = g * t^2 / 8 (t in seconds). Returns inches."""
    t = num_or(flight_ms, 0.0) / 1000.0
    h_m = G * t * t / 8.0
    return h_m * M_TO_IN


def sayers_peak_power(jump_in: float, mass_lbs: float) -> float:
    """Sayers (1999) peak-power estimate (Watts) from CMJ height + body mass."""
    jump_cm = num_or(jump_in, 0.0) * 2.54
    mass_kg = lbs_to_kg(mass_lbs)
    return 60.7 * jump_cm + 45.3 * mass_kg - 2055.0


def relative_power(jump_in: float, mass_lbs: float) -> float:
    """Relative Force Production Quotient = peak power per kg body mass (W/kg)."""
    mass_kg = lbs_to_kg(mass_lbs)
    return safe_div(sayers_peak_power(jump_in, mass_lbs), mass_kg, 0.0)


def project_vertical(mass_cur_lbs: float, jump_cur_in: float,
                     mass_new_lbs: float, pushoff_m: float) -> float:
    """
    Impulse-momentum projection holding propulsive force capacity constant.
    Work-energy over the push-off distance d gives:
        h = (m_cur / m_new) * (d + h_cur) - d
    As mass falls (force preserved), take-off velocity and jump height rise.
    """
    h_cur_m = num_or(jump_cur_in, 0.0) * IN_TO_M
    ratio = safe_div(mass_cur_lbs, mass_new_lbs, 1.0)
    h_new_m = ratio * (pushoff_m + h_cur_m) - pushoff_m
    return max(0.0, h_new_m) * M_TO_IN


def first_step_gain(mass_cur_lbs: float, mass_new_lbs: float) -> float:
    """
    First-step acceleration scales as a = F/m (Newton's 2nd law) with horizontal
    force held constant, so the relative acceleration gain is m_cur / m_new.
    Returned as a percentage improvement.
    """
    return (safe_div(mass_cur_lbs, mass_new_lbs, 1.0) - 1.0) * 100.0

# ------------------------------------------------------------------------------
# SIDEBAR
# ------------------------------------------------------------------------------

with st.sidebar:
    st.markdown("### 🏀 Basketball Biomechanics")
    render_sidebar_profile()
    sel_date = st.date_input("📅 Session Date", value=date.today())
    d_iso = sel_date.isoformat()
    pushoff_cm = st.slider("Push-off range (cm)", 25, 50, 40, 1,
                           help="Countermovement leg-extension distance used by the "
                                "impulse projection model. ~35–45 cm is typical.")
    st.caption("Push-off range calibrates the weight-drop jump projection.")

pushoff_m = pushoff_cm / 100.0

st.markdown(
    f"""
    <div style="padding:2px 0 4px 0;">
        <h1 style="margin-bottom:0;">🏀 Basketball Biomechanics</h1>
        <p style="color:#8FA1BF;letter-spacing:.13em;font-size:.78rem;margin-top:2px;">
            FORCE PRODUCTION · WEIGHT-DROP PROJECTION · RSI · TENDON LOAD · {d_iso}
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

tab_power, tab_rsi, tab_tendon = st.tabs([
    "⚡ Relative Power & Projection",
    "🦿 RSI Analyzer",
    "🩹 Tendon Loading Tracker",
])

# ==============================================================================
# TAB 1 — RELATIVE POWER FRAMEWORK & WEIGHT-DROP PROJECTION
# ==============================================================================

with tab_power:
    st.subheader("Relative Power Framework")
    st.caption(
        "Logs body weight and vertical jump, derives Sayers peak power and the "
        "Relative Force Production Quotient (W/kg), and projects how shedding mass "
        "toward the 145–155 lb prime zone mechanically unlocks vertical and first step."
    )

    existing = get_row_by_date("df_biomechanics", d_iso)

    def _ev(col, default):
        if existing is None or col not in existing.index or pd.isna(existing[col]):
            return default
        return existing[col]

    pc1, pc2 = st.columns([5, 7], gap="large")
    with pc1:
        with st.form("power_form"):
            st.markdown("##### Log Session Metrics")
            bw = st.number_input("Body Weight (lbs)", 100.0, 260.0,
                                 float(num_or(_ev("Body_Weight",
                                       ATHLETE_PROFILE["current_weight_lbs"]),
                                       ATHLETE_PROFILE["current_weight_lbs"])), 0.2)
            vj = st.number_input("Vertical Jump (inches)", 6.0, 50.0,
                                 float(num_or(_ev("Vertical_Jump_Inches", 24.0), 24.0)), 0.5)
            shuttle = st.number_input("Lateral Shuttle (sec, lower is faster)", 2.0, 12.0,
                                      float(num_or(_ev("Lateral_Shuttle_Sec", 4.8), 4.8)), 0.05)
            squat = st.number_input("Squat 1RM (lbs)", 0.0, 700.0,
                                    float(num_or(_ev("Squat_1RM_Lbs", 245.0), 245.0)), 5.0)
            saved = st.form_submit_button("💾 Save Biomechanics", type="primary",
                                          use_container_width=True)
        if saved:
            upsert_by_date("df_biomechanics", d_iso, {
                "Body_Weight": float(bw),
                "Vertical_Jump_Inches": float(vj),
                "Lateral_Shuttle_Sec": float(shuttle),
                "Squat_1RM_Lbs": float(squat),
            })
            st.toast(f"Biomechanics saved for {d_iso}.", icon="💾")
            st.rerun()

    with pc2:
        peak_w = sayers_peak_power(vj, bw)
        rel_w = relative_power(vj, bw)
        st.markdown("##### Current Output")
        mc = st.columns(3)
        mc[0].metric("Sayers Peak Power", f"{peak_w:,.0f} W")
        mc[1].metric("Relative Power (RFPQ)", f"{rel_w:,.1f} W/kg")
        mc[2].metric("Flight-eq. Hang", f"{(2*np.sqrt(2*G*vj*IN_TO_M)/G)*1000:,.0f} ms",
                     help="Theoretical flight time for the logged vertical.")

        st.markdown(
            f"""
            <div class="apex-card">
                <span class="apex-pill"
                      style="background:rgba(0,229,160,.12);color:#00E5A0;border:1px solid #00E5A0;">
                    NEWTON'S SECOND LAW · a = F / m
                </span>
                <p style="margin:8px 0 0 0;font-size:.86rem;line-height:1.6;color:#C9D2E3;">
                    Your propulsive force capacity is the numerator; body mass is the
                    denominator. Holding force constant while dropping mass raises both
                    take-off velocity (vertical) and horizontal acceleration (first step)
                    in direct proportion to the mass ratio.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.divider()
    st.markdown("##### Weight-Drop Vertical Projection")
    st.caption(
        "Impulse-momentum model holding force capacity constant: "
        "h(m) = (m_current / m_target) · (d + h_current) − d. Idealized — assumes the "
        "weight lost is non-contractile mass and force output is preserved."
    )

    try:
        weights = np.arange(140.0, float(bw) + 0.0001, 1.0)
        if weights.size < 2:
            weights = np.array([140.0, float(bw)])
        proj_in = [project_vertical(bw, vj, w, pushoff_m) for w in weights]
        proj_df = pd.DataFrame({"Body Weight (lbs)": weights, "Projected Vertical (in)": proj_in})

        fig = px.line(proj_df, x="Body Weight (lbs)", y="Projected Vertical (in)",
                      title="Projected Vertical vs. Body Weight")
        fig.update_traces(line=dict(color="#00E5A0", width=3))
        fig.add_vrect(x0=ATHLETE_PROFILE["target_low_lbs"], x1=ATHLETE_PROFILE["target_high_lbs"],
                      fillcolor="#00B4D8", opacity=0.14, line_width=0,
                      annotation_text="PRIME ZONE", annotation_font_color="#00B4D8")
        fig.add_trace(go.Scatter(x=[bw], y=[vj], mode="markers",
                                 marker=dict(size=14, color="#FF4D4F"), name="Current"))
        fig.update_xaxes(autorange="reversed")  # lighter = further right toward gains
        st.plotly_chart(style_fig(fig, 360), use_container_width=True)

        proj_low = project_vertical(bw, vj, ATHLETE_PROFILE["target_high_lbs"], pushoff_m)
        proj_high = project_vertical(bw, vj, ATHLETE_PROFILE["target_low_lbs"], pushoff_m)
        step_low = first_step_gain(bw, ATHLETE_PROFILE["target_high_lbs"])
        step_high = first_step_gain(bw, ATHLETE_PROFILE["target_low_lbs"])

        rcol = st.columns(3)
        rcol[0].metric("Vertical @ 155 lb", f"{proj_low:.1f} in", f"{proj_low - vj:+.1f} in",
                       delta_color="normal")
        rcol[1].metric("Vertical @ 145 lb", f"{proj_high:.1f} in", f"{proj_high - vj:+.1f} in",
                       delta_color="normal")
        rcol[2].metric("First-step accel gain", f"+{step_low:.1f}–{step_high:.1f}%",
                       "at prime weight", delta_color="off")

        rim_clear = 0.0
        st.markdown(
            f"""
            <div class="apex-card">
                <p style="margin:0;font-size:.88rem;line-height:1.65;color:#C9D2E3;">
                    Dropping from <b style="color:#F2F5FA;">{bw:.0f} lb</b> into the prime zone
                    projects a vertical of
                    <b style="color:#00E5A0;">{proj_low:.1f}–{proj_high:.1f} in</b>
                    (a <b style="color:#00E5A0;">{proj_low - vj:+.1f} to {proj_high - vj:+.1f} in</b>
                    gain) and a <b style="color:#00B4D8;">{step_low:.1f}–{step_high:.1f}%</b>
                    faster first step — the mechanical payoff of a better power-to-weight ratio
                    for rim-snapping and lateral closeouts.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )
    except Exception as exc:
        st.info(f"Projection temporarily unavailable ({exc}). Log a body weight and "
                "vertical jump to generate the curve.")

    # Historical vertical / relative-power trend
    bm = chartable("df_biomechanics")
    if day_count("df_biomechanics") >= 2:
        try:
            hist = bm.dropna(subset=["Vertical_Jump_Inches", "Body_Weight"], how="all").copy()
            hist["Rel_Power"] = hist.apply(
                lambda r: relative_power(r["Vertical_Jump_Inches"], r["Body_Weight"]), axis=1)
            fig_h = go.Figure()
            fig_h.add_trace(go.Scatter(x=hist["Date_dt"], y=hist["Vertical_Jump_Inches"],
                                       mode="lines+markers", name="Vertical (in)",
                                       line=dict(color="#00E5A0", width=3)))
            fig_h.add_trace(go.Scatter(x=hist["Date_dt"], y=hist["Rel_Power"],
                                       mode="lines+markers", name="Rel. Power (W/kg)",
                                       line=dict(color="#B388FF", width=2, dash="dot"),
                                       yaxis="y2"))
            fig_h.update_layout(title="Vertical & Relative Power Over Time",
                                yaxis=dict(title="Vertical (in)"),
                                yaxis2=dict(title="W/kg", overlaying="y", side="right",
                                            showgrid=False))
            st.plotly_chart(style_fig(fig_h, 330), use_container_width=True)
        except Exception as exc:
            st.info(f"Trend rendering unavailable ({exc}).")
    else:
        st.info("🔒 **Vertical & relative-power trend** unlocks after 2 logged biomechanics days.")

# ==============================================================================
# TAB 2 — REACTIVE STRENGTH INDEX (RSI) ANALYZER
# ==============================================================================

with tab_rsi:
    st.subheader("Reactive Strength Index Analyzer")
    st.caption(
        "RSI = Flight Time ÷ Ground Contact Time — the core plyometric quality, "
        "quantifying how much elastic return you generate per unit of ground time. "
        "Higher RSI = stiffer, springier, faster-reacting lower limb."
    )

    existing = get_row_by_date("df_biomechanics", d_iso)

    def _ev2(col, default):
        if existing is None or col not in existing.index or pd.isna(existing[col]):
            return default
        return existing[col]

    rc1, rc2 = st.columns([5, 7], gap="large")
    with rc1:
        with st.form("rsi_form"):
            st.markdown("##### Drop / Rebound Jump Inputs")
            flight = st.number_input("Flight Time (ms)", 100.0, 1200.0,
                                     float(num_or(_ev2("Flight_Time_Ms", 540.0), 540.0)), 5.0)
            contact = st.number_input("Ground Contact Time (ms)", 80.0, 1000.0,
                                      float(num_or(_ev2("Ground_Contact_Time_Ms", 210.0), 210.0)), 5.0)
            saved = st.form_submit_button("💾 Save RSI Inputs", type="primary",
                                          use_container_width=True)
        if saved:
            upsert_by_date("df_biomechanics", d_iso, {
                "Flight_Time_Ms": float(flight),
                "Ground_Contact_Time_Ms": float(contact),
            })
            st.toast("RSI inputs saved.", icon="💾")
            st.rerun()

    with rc2:
        rsi = compute_rsi(flight, contact)
        jh = jump_height_from_flight(flight)
        st.markdown("##### Computed Reactive Quality")
        rm = st.columns(3)
        rm[0].metric("RSI", f"{rsi:.2f}", "flight ÷ contact", delta_color="off")
        rm[1].metric("Jump Height (flight method)", f"{jh:.1f} in")
        rm[2].metric("Contact Time", f"{contact:.0f} ms")

        if rsi >= 2.5:
            band = ("#00E5A0", "ELITE", "Elite reactive stiffness — true plyometric "
                    "athlete range. Train depth jumps and high-intensity rebound work.")
        elif rsi >= 1.5:
            band = ("#FAAD14", "DEVELOPING", "Solid, developing reactivity. Emphasize "
                    "short ground-contact drills (pogos, low hurdle hops) to push stiffness.")
        else:
            band = ("#FF4D4F", "FOUNDATIONAL", "Foundational range — ground contacts are "
                    "long. Build ankle/Achilles stiffness with submaximal pogos before "
                    "loading high-intensity depth jumps.")
        st.markdown(
            f"""
            <div class="apex-card" style="border-color:{band[0]};">
                <span class="apex-pill"
                      style="background:rgba(0,0,0,.25);color:{band[0]};border:1px solid {band[0]};">
                    {band[1]} · RSI {rsi:.2f}
                </span>
                <p style="margin:8px 0 0 0;font-size:.86rem;line-height:1.6;color:#C9D2E3;">
                    {band[2]}
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.divider()
    bm = chartable("df_biomechanics")
    if day_count("df_biomechanics") >= 2:
        try:
            rdf = bm.dropna(subset=["Flight_Time_Ms", "Ground_Contact_Time_Ms"]).copy()
            if len(rdf) >= 2:
                rdf["RSI"] = rdf.apply(
                    lambda r: compute_rsi(r["Flight_Time_Ms"], r["Ground_Contact_Time_Ms"]), axis=1)
                fig_rsi = px.line(rdf, x="Date_dt", y="RSI", markers=True,
                                  title="Reactive Strength Index Over Time")
                fig_rsi.update_traces(line=dict(color="#00E5A0", width=3),
                                      marker=dict(size=9, color="#00B4D8"))
                fig_rsi.add_hrect(y0=0, y1=1.5, fillcolor="#FF4D4F", opacity=0.07, line_width=0)
                fig_rsi.add_hrect(y0=1.5, y1=2.5, fillcolor="#FAAD14", opacity=0.07, line_width=0)
                fig_rsi.add_hrect(y0=2.5, y1=4.0, fillcolor="#00E5A0", opacity=0.07, line_width=0)
                st.plotly_chart(style_fig(fig_rsi, 330), use_container_width=True)
            else:
                st.info("🔒 **RSI trend** needs 2+ days with both flight and contact times logged.")
        except Exception as exc:
            st.info(f"RSI trend unavailable ({exc}).")
    else:
        st.info("🔒 **RSI trend** unlocks after 2 logged biomechanics days.")

# ==============================================================================
# TAB 3 — TENDON LOADING TRACKER
# ==============================================================================

with tab_tendon:
    st.subheader("Tendon Loading Tracker")
    st.caption(
        "Cumulative lower-body impact = Foot Contacts × Drill-Intensity Modifier, "
        "mapped against reported patellar/Achilles soreness to surface jumper's-knee "
        "risk before inflammation patterns manifest. Logged here and exportable as CSV."
    )

    # Page-local persistence (kept separate from the five master tables; the
    # df_biomechanics schema has no foot-contact/soreness fields). Export below.
    if "tendon_log" not in st.session_state:
        st.session_state["tendon_log"] = pd.DataFrame(
            columns=["Date", "Foot_Contacts", "Intensity_Modifier",
                     "Session_Load", "Tendon_Soreness"])

    INTENSITY_MAP = {
        "Pogo / low-amplitude hops (0.8×)": 0.8,
        "Box / broad jumps (1.0×)": 1.0,
        "Bounding / single-leg (1.3×)": 1.3,
        "Depth jumps / shock (1.6×)": 1.6,
        "Max rim-test / reactive (2.0×)": 2.0,
    }

    tc1, tc2 = st.columns([5, 7], gap="large")
    with tc1:
        with st.form("tendon_form"):
            st.markdown("##### Log Plyometric Session")
            contacts = st.number_input("Foot Contacts (total)", 0, 600, 80, 5)
            intensity_label = st.selectbox("Drill Intensity", list(INTENSITY_MAP.keys()))
            soreness = st.slider("Tendon Soreness (1 fresh · 10 severe)", 1, 10, 3)
            saved = st.form_submit_button("💾 Log Tendon Load", type="primary",
                                          use_container_width=True)
        if saved:
            modifier = INTENSITY_MAP[intensity_label]
            load = contacts * modifier
            tl = st.session_state["tendon_log"]
            new = pd.DataFrame([{
                "Date": d_iso, "Foot_Contacts": contacts,
                "Intensity_Modifier": modifier, "Session_Load": load,
                "Tendon_Soreness": soreness}])
            st.session_state["tendon_log"] = (new if tl.empty
                                              else pd.concat([tl, new], ignore_index=True))
            st.toast(f"Logged tendon load {load:.0f} units.", icon="🩹")
            st.rerun()

    tl = st.session_state["tendon_log"]
    with tc2:
        st.markdown("##### Loading Status")
        if tl.empty:
            st.info("No plyometric sessions logged yet. Log one to begin tracking "
                    "cumulative tendon load and soreness.")
        else:
            tl_sorted = tl.copy()
            tl_sorted["Date_dt"] = pd.to_datetime(tl_sorted["Date"], errors="coerce")
            tl_sorted = tl_sorted.sort_values("Date_dt")
            recent7 = tl_sorted[tl_sorted["Date_dt"] >=
                                (pd.Timestamp(d_iso) - pd.Timedelta(days=7))]
            cum7 = float(pd.to_numeric(recent7["Session_Load"], errors="coerce").fillna(0).sum())
            latest_sore = float(pd.to_numeric(tl_sorted["Tendon_Soreness"],
                                              errors="coerce").fillna(0).iloc[-1])
            sm_cols = st.columns(3)
            sm_cols[0].metric("7-Day Cumulative Load", f"{cum7:,.0f}")
            sm_cols[1].metric("Latest Soreness", f"{latest_sore:.0f}/10")
            sm_cols[2].metric("Sessions Logged", f"{len(tl_sorted)}")

            # Jumper's-knee composite risk: high volume AND rising soreness.
            load_risk = min(cum7 / 1200.0, 1.0)            # 1200+ units = saturated
            sore_risk = max(0.0, (latest_sore - 3.0) / 7.0)
            risk = round(100.0 * (0.55 * load_risk + 0.45 * sore_risk), 0)
            if risk >= 66 or latest_sore >= 8:
                st.error(
                    f"🔴 JUMPER'S-KNEE RISK: HIGH ({risk:.0f}%). Cumulative patellar/Achilles "
                    "load is elevated while soreness is climbing — the classic pre-tendinopathy "
                    "signature. Deload plyometric volume ~50%, drop to ≤0.8× intensity (pogos "
                    "only), add isometric Spanish-squat holds, and reassess before any depth jumps.")
            elif risk >= 33:
                st.warning(
                    f"🟡 JUMPER'S-KNEE RISK: MODERATE ({risk:.0f}%). Tissue is absorbing real "
                    "load. Hold volume flat, prioritize eccentric tempo and isometrics, and avoid "
                    "stacking max-intensity reactive sessions on consecutive days.")
            else:
                st.success(
                    f"🟢 JUMPER'S-KNEE RISK: LOW ({risk:.0f}%). Tendon load and soreness are in a "
                    "well-managed adaptive window — clear to progress reactive volume sensibly.")

    if not tl.empty:
        st.divider()
        try:
            tl_plot = tl.copy()
            tl_plot["Date_dt"] = pd.to_datetime(tl_plot["Date"], errors="coerce")
            tl_plot = tl_plot.sort_values("Date_dt")
            tl_plot["Cumulative_Load"] = pd.to_numeric(
                tl_plot["Session_Load"], errors="coerce").fillna(0).cumsum()
            fig_t = go.Figure()
            fig_t.add_trace(go.Bar(x=tl_plot["Date_dt"], y=tl_plot["Session_Load"],
                                   name="Session Load", marker_color="#00B4D8"))
            fig_t.add_trace(go.Scatter(x=tl_plot["Date_dt"], y=tl_plot["Tendon_Soreness"],
                                       mode="lines+markers", name="Soreness (1–10)",
                                       line=dict(color="#FF4D4F", width=3), yaxis="y2"))
            fig_t.update_layout(title="Tendon Load vs. Reported Soreness",
                                yaxis=dict(title="Session Load"),
                                yaxis2=dict(title="Soreness", overlaying="y", side="right",
                                            range=[0, 10], showgrid=False))
            st.plotly_chart(style_fig(fig_t, 330), use_container_width=True)
        except Exception as exc:
            st.info(f"Tendon chart unavailable ({exc}).")

        exp1, exp2 = st.columns([3, 7])
        csv = tl.to_csv(index=False).encode("utf-8")
        exp1.download_button("⬇️ Export Tendon Log (CSV)", data=csv,
                             file_name=f"apex_tendon_log_{date.today().isoformat()}.csv",
                             mime="text/csv", use_container_width=True)
        if exp2.button("🗑️ Clear tendon log", use_container_width=True):
            st.session_state["tendon_log"] = st.session_state["tendon_log"].iloc[0:0]
            st.rerun()
