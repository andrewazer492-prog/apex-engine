# ==============================================================================
# APEX HUMAN PERFORMANCE & BIOMETRIC OPERATING SYSTEM — V3.0 ENTERPRISE
# pages/5_Predictive_ML_Studio.py
# ------------------------------------------------------------------------------
# Interactive scikit-learn studio. Aggregates all five relational tables into a
# single date-indexed feature matrix, then fits Random Forest + Linear Regression
# pipelines against court-performance targets and renders feature-importance
# analytics so the athlete can see which protocols actually move performance.
# ==============================================================================

from datetime import date

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

from state_manager import (
    apply_theme,
    compute_gerc,
    get_df,
    init_global_state,
    render_sidebar_profile,
    style_fig,
    to_bool,
)

# Scikit-learn is imported defensively so the page degrades gracefully if the
# dependency is missing from the deployed environment.
SKLEARN_OK = True
SKLEARN_ERR = ""
try:
    from sklearn.ensemble import RandomForestRegressor
    from sklearn.linear_model import LinearRegression
    from sklearn.preprocessing import StandardScaler
    from sklearn.metrics import r2_score, mean_absolute_error
    from sklearn.model_selection import cross_val_score, KFold
except Exception as _exc:  # pragma: no cover
    SKLEARN_OK = False
    SKLEARN_ERR = str(_exc)

st.set_page_config(
    page_title="APEX OS | Predictive ML Studio",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

init_global_state()
apply_theme()

# ------------------------------------------------------------------------------
# FEATURE-MATRIX AGGREGATION
# ------------------------------------------------------------------------------

TARGET_SPECS = {
    "Vertical Jump (in)": {"col": "Vertical_Jump_Inches", "higher_better": True},
    "Reactive Strength Index": {"col": "RSI", "higher_better": True},
    "Lateral Speed (shuttle, s)": {"col": "Lateral_Shuttle_Sec", "higher_better": False},
}

FEATURE_LABELS = {
    "Readiness": "Fitbit Air Daily Readiness",
    "HRV_rMSSD": "HRV rMSSD (parasympathetic reserve)",
    "Resting_HR": "Resting Heart Rate",
    "Deep_Sleep_Mins": "Deep Sleep (mins)",
    "REM_Sleep_Mins": "REM Sleep (mins)",
    "Total_Steps": "Daily Steps (NEAT)",
    "Cardio_Load": "Cardio Training Load",
    "Caloric_Deficit": "Caloric Deficit Size",
    "Preworkout_GERC": "Pre-workout GERC (digestion)",
    "Peptide_Adherence": "Peptide Adherence",
    "Sunlight": "Morning Sunlight",
    "Skincare": "Skincare Adherence",
    "Focus_Blocks": "Cognitive Focus Blocks",
    "Body_Weight": "Body Weight (lbs)",
}


def _per_date_nutrition(target_cal: float):
    """Return per-date (caloric deficit, pre-workout GERC) maps."""
    nut = get_df("df_nutrition")
    deficit_map, gerc_map = {}, {}
    if nut.empty:
        return deficit_map, gerc_map
    nut = nut.copy()
    for c in ["Calories", "Carbs", "Fats", "Fiber", "Digestion_Window_Mins"]:
        nut[c] = pd.to_numeric(nut[c], errors="coerce").fillna(0.0)
    for d, grp in nut.groupby("Date"):
        consumed = float(grp["Calories"].sum())
        deficit_map[d] = target_cal - consumed
        pw = grp[grp["Digestion_Window_Mins"] > 0]
        basis = pw if not pw.empty else grp
        gerc_map[d] = compute_gerc(basis["Carbs"].sum(), basis["Fats"].sum(),
                                   basis["Fiber"].sum())
    return deficit_map, gerc_map


def build_feature_matrix(target_cal: float) -> pd.DataFrame:
    """Date-indexed join of all five relational tables + engineered features."""
    fb = get_df("df_fitbit_air").copy()
    bm = get_df("df_biomechanics").copy()
    ch = get_df("df_cognitive_habits").copy()

    # Collect the universe of logged dates from the tables that carry signal.
    date_set = set()
    for frame in (fb, bm, ch):
        if not frame.empty and "Date" in frame.columns:
            date_set.update(frame["Date"].dropna().astype(str).tolist())
    if not date_set:
        return pd.DataFrame()

    base = pd.DataFrame({"Date": sorted(date_set)})

    def _num(frame, col):
        if frame.empty or col not in frame.columns:
            return {}
        f = frame.copy()
        f[col] = pd.to_numeric(f[col], errors="coerce")
        return dict(zip(f["Date"].astype(str), f[col]))

    def _boolmap(frame, col):
        if frame.empty or col not in frame.columns:
            return {}
        return {str(d): (1.0 if to_bool(v) else 0.0)
                for d, v in zip(frame["Date"], frame[col])}

    base["Readiness"] = base["Date"].map(_num(fb, "Daily_Readiness_Score"))
    base["HRV_rMSSD"] = base["Date"].map(_num(fb, "HRV_rMSSD"))
    base["Resting_HR"] = base["Date"].map(_num(fb, "Resting_Heart_Rate"))
    base["Deep_Sleep_Mins"] = base["Date"].map(_num(fb, "Deep_Sleep_Mins"))
    base["REM_Sleep_Mins"] = base["Date"].map(_num(fb, "REM_Sleep_Mins"))
    base["Total_Steps"] = base["Date"].map(_num(fb, "Total_Steps"))
    base["Cardio_Load"] = base["Date"].map(_num(fb, "Cardio_Load"))

    base["Body_Weight"] = base["Date"].map(_num(bm, "Body_Weight"))
    base["Focus_Blocks"] = base["Date"].map(_num(ch, "Focus_Blocks_Completed"))
    base["Peptide_Adherence"] = base["Date"].map(_boolmap(ch, "Peptide_Adherence_Bool"))
    base["Sunlight"] = base["Date"].map(_boolmap(ch, "Sunlight_Exposure_Bool"))
    base["Skincare"] = base["Date"].map(_boolmap(ch, "Skincare_Adherence_Bool"))

    deficit_map, gerc_map = _per_date_nutrition(target_cal)
    base["Caloric_Deficit"] = base["Date"].map(deficit_map)
    base["Preworkout_GERC"] = base["Date"].map(gerc_map)

    # Targets
    base["Vertical_Jump_Inches"] = base["Date"].map(_num(bm, "Vertical_Jump_Inches"))
    base["Lateral_Shuttle_Sec"] = base["Date"].map(_num(bm, "Lateral_Shuttle_Sec"))
    flight = _num(bm, "Flight_Time_Ms")
    contact = _num(bm, "Ground_Contact_Time_Ms")
    rsi = {}
    for d in base["Date"]:
        f, c = flight.get(d, np.nan), contact.get(d, np.nan)
        if not (pd.isna(f) or pd.isna(c) or c == 0):
            rsi[d] = f / c
    base["RSI"] = base["Date"].map(rsi)
    return base

# ------------------------------------------------------------------------------
# SIDEBAR
# ------------------------------------------------------------------------------

with st.sidebar:
    st.markdown("### 🤖 Predictive ML Studio")
    render_sidebar_profile()
    st.number_input("Daily calorie target (deficit basis)", min_value=1200, max_value=6000,
                    step=50, key="t_cal")
    st.caption("The calorie target anchors the engineered Caloric Deficit feature.")

st.markdown(
    """
    <div style="padding:2px 0 4px 0;">
        <h1 style="margin-bottom:0;">🤖 Predictive ML Studio</h1>
        <p style="color:#8FA1BF;letter-spacing:.13em;font-size:.78rem;margin-top:2px;">
            SCIKIT-LEARN FEATURE-IMPORTANCE ENGINE · RANDOM FOREST + LINEAR REGRESSION
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

if not SKLEARN_OK:
    st.error(
        "scikit-learn is not available in this environment, so the modeling engine "
        f"cannot run ({SKLEARN_ERR}). Confirm `scikit-learn>=1.4` is in requirements.txt "
        "and redeploy. The rest of APEX OS is unaffected."
    )
    st.stop()

target_cal = float(st.session_state.t_cal)
matrix = build_feature_matrix(target_cal)

tab_matrix, tab_model, tab_explore = st.tabs([
    "🧮 Aggregated Feature Matrix",
    "🌲 Model Studio & Importance",
    "🔍 Single-Feature Explorer",
])

# ==============================================================================
# TAB 1 — AGGREGATED FEATURE MATRIX
# ==============================================================================

with tab_matrix:
    st.subheader("Aggregated Feature Matrix")
    st.caption(
        "Every logged date joined across all five relational tables, with engineered "
        "features (Caloric Deficit, Pre-workout GERC, RSI). This is the single dataset "
        "the models learn from."
    )
    if matrix.empty:
        st.info(
            "🔒 **No data yet.** Log telemetry, biomechanics, nutrition, and habits across "
            "the other modules — once dates accumulate, the unified matrix builds here."
        )
    else:
        st.caption(f"{len(matrix)} logged date(s) in the matrix.")
        show = matrix.copy()
        for c in show.columns:
            if c != "Date":
                show[c] = pd.to_numeric(show[c], errors="coerce").round(2)
        st.dataframe(show.sort_values("Date", ascending=False),
                     use_container_width=True, hide_index=True)
        with st.expander("ℹ️ Feature dictionary"):
            st.dataframe(
                pd.DataFrame([{"Feature": k, "Meaning": v} for k, v in FEATURE_LABELS.items()]),
                use_container_width=True, hide_index=True)

# ==============================================================================
# TAB 2 — MODEL STUDIO & FEATURE IMPORTANCE
# ==============================================================================

with tab_model:
    st.subheader("Model Studio & Feature Importance")
    st.caption(
        "Fit a Random Forest Regressor and a Linear Regression against a chosen "
        "performance target. Feature importance reveals which lifestyle protocols "
        "carry the strongest empirical signal for court output."
    )

    mc1, mc2, mc3 = st.columns([4, 4, 4])
    target_label = mc1.selectbox("Target variable", list(TARGET_SPECS.keys()))
    n_estimators = mc2.slider("Random Forest trees", 50, 500, 200, 50)
    max_depth = mc3.slider("Max tree depth", 2, 12, 5, 1)

    target_col = TARGET_SPECS[target_label]["col"]
    feature_cols = list(FEATURE_LABELS.keys())

    if matrix.empty or target_col not in matrix.columns:
        st.info("🔒 The modeling engine unlocks once the feature matrix has data. "
                "Log entries in the other modules first.")
    else:
        work = matrix.copy()
        work[target_col] = pd.to_numeric(work[target_col], errors="coerce")
        work = work.dropna(subset=[target_col])

        # Keep only features that carry at least some non-null signal.
        usable = []
        for c in feature_cols:
            col = pd.to_numeric(work.get(c), errors="coerce")
            if col.notna().sum() >= max(2, int(0.4 * len(work))):
                usable.append(c)

        n_samples = len(work)
        MIN_SAMPLES = 6

        if n_samples < MIN_SAMPLES:
            st.info(
                f"🔒 **Modeling unlocks at {MIN_SAMPLES} dated samples for this target** "
                f"({n_samples} usable so far — {MIN_SAMPLES - n_samples} more needed). "
                f"Log more days that include **{target_label}** plus supporting metrics. "
                "Tree ensembles need a minimum sample base to produce trustworthy importances."
            )
        elif len(usable) < 2:
            st.info(
                "🔒 At least 2 features with sufficient coverage are required. Log more "
                "telemetry/nutrition/habit data alongside your performance metrics."
            )
        else:
            try:
                X = work[usable].apply(pd.to_numeric, errors="coerce")
                X = X.fillna(X.median(numeric_only=True))
                # Drop any feature still fully null after imputation (all-NaN column).
                X = X.dropna(axis=1, how="all")
                usable = list(X.columns)
                y = pd.to_numeric(work[target_col], errors="coerce").values

                # Guard against zero-variance feature columns for the linear model.
                variances = X.var(axis=0)
                nonconstant = variances[variances > 1e-12].index.tolist()
                X_lin = X[nonconstant] if nonconstant else X

                # ---- Random Forest ----
                rf = RandomForestRegressor(
                    n_estimators=n_estimators, max_depth=max_depth,
                    random_state=42, n_jobs=-1)
                rf.fit(X, y)
                rf_pred = rf.predict(X)
                rf_r2 = r2_score(y, rf_pred)
                rf_mae = mean_absolute_error(y, rf_pred)
                rf_imp = pd.DataFrame({
                    "Feature": [FEATURE_LABELS[c] for c in usable],
                    "Importance": rf.feature_importances_,
                }).sort_values("Importance", ascending=True)

                # ---- Linear Regression on standardized features ----
                scaler = StandardScaler()
                Xs = scaler.fit_transform(X_lin)
                lin = LinearRegression()
                lin.fit(Xs, y)
                lin_pred = lin.predict(Xs)
                lin_r2 = r2_score(y, lin_pred)
                lin_imp = pd.DataFrame({
                    "Feature": [FEATURE_LABELS[c] for c in nonconstant] if nonconstant
                    else [FEATURE_LABELS[c] for c in usable],
                    "Coefficient": lin.coef_,
                })
                lin_imp["AbsCoef"] = lin_imp["Coefficient"].abs()
                lin_imp = lin_imp.sort_values("AbsCoef", ascending=True)

                # ---- Cross-validated R² when sample base allows ----
                cv_note = ""
                if n_samples >= 8:
                    try:
                        folds = min(5, n_samples)
                        cv = cross_val_score(
                            RandomForestRegressor(n_estimators=n_estimators,
                                                  max_depth=max_depth, random_state=42),
                            X, y, cv=KFold(n_splits=folds, shuffle=True, random_state=42),
                            scoring="r2")
                        cv_note = f"{np.mean(cv):+.2f} (mean {folds}-fold CV R²)"
                    except Exception:
                        cv_note = "n/a"

                sc = st.columns(4)
                sc[0].metric("Samples", f"{n_samples}")
                sc[1].metric("RF in-sample R²", f"{rf_r2:.2f}")
                sc[2].metric("RF MAE", f"{rf_mae:.2f}")
                sc[3].metric("Linear R²", f"{lin_r2:.2f}")
                if cv_note:
                    st.caption(f"Cross-validated generalization: {cv_note}. "
                               "In-sample R² will look optimistic on small datasets — trust the CV figure.")
                if n_samples < 12:
                    st.warning(
                        "⚠️ Small-sample regime: with fewer than ~12 dated samples these "
                        "importances are directional, not definitive. Keep logging — the "
                        "signal sharpens as the matrix grows.")

                g1, g2 = st.columns(2, gap="large")
                with g1:
                    fig_rf = px.bar(
                        rf_imp, x="Importance", y="Feature", orientation="h",
                        title="Random Forest — Feature Importance")
                    fig_rf.update_traces(marker_color="#00E5A0")
                    st.plotly_chart(style_fig(fig_rf, 420), use_container_width=True)
                with g2:
                    fig_lin = px.bar(
                        lin_imp, x="Coefficient", y="Feature", orientation="h",
                        title="Linear Regression — Standardized Coefficients",
                        color="Coefficient",
                        color_continuous_scale=["#FF4D4F", "#0B0F19", "#00E5A0"])
                    st.plotly_chart(style_fig(fig_lin, 420), use_container_width=True)

                top_feat = rf_imp.iloc[-1]["Feature"]
                direction = "higher" if TARGET_SPECS[target_label]["higher_better"] else "lower"
                st.markdown(
                    f"""
                    <div class="apex-card">
                        <span class="apex-pill"
                              style="background:rgba(0,229,160,.12);color:#00E5A0;border:1px solid #00E5A0;">
                            EMPIRICAL READOUT
                        </span>
                        <p style="margin:8px 0 0 0;font-size:.88rem;line-height:1.65;color:#C9D2E3;">
                            For <b>{target_label}</b> ({direction} = better), the Random Forest
                            ranks <b style="color:#00E5A0;">{top_feat}</b> as the single
                            highest-signal driver in your logged history. The linear model's
                            signed coefficients show direction: green bars push the target up,
                            red bars pull it down. Use this to prioritize the protocols that
                            empirically move your court output — then verify by holding them
                            constant and re-checking as more data accrues.
                        </p>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            except Exception as exc:
                st.info(f"Model fitting was interrupted ({exc}). This usually means a target "
                        "or feature column needs more logged variance. Add more dated entries "
                        "and re-run.")

# ==============================================================================
# TAB 3 — SINGLE-FEATURE EXPLORER
# ==============================================================================

with tab_explore:
    st.subheader("Single-Feature Explorer")
    st.caption(
        "Scatter any one feature against a target with an ordinary-least-squares trend "
        "line to eyeball the raw bivariate relationship behind the model importances."
    )
    if matrix.empty:
        st.info("🔒 Log data across the modules to unlock the explorer.")
    else:
        ec1, ec2 = st.columns(2)
        x_feat = ec1.selectbox("Feature (X)", list(FEATURE_LABELS.keys()),
                               format_func=lambda c: FEATURE_LABELS[c])
        y_target = ec2.selectbox("Target (Y)", list(TARGET_SPECS.keys()), key="explore_target")
        y_col = TARGET_SPECS[y_target]["col"]

        sub = matrix.copy()
        if y_col not in sub.columns:
            st.info("That target has no logged values yet.")
        else:
            sub[x_feat] = pd.to_numeric(sub.get(x_feat), errors="coerce")
            sub[y_col] = pd.to_numeric(sub[y_col], errors="coerce")
            sub = sub.dropna(subset=[x_feat, y_col])
            if len(sub) < 3:
                st.info(
                    f"🔒 Need 3+ dates with both **{FEATURE_LABELS[x_feat]}** and "
                    f"**{y_target}** logged ({len(sub)} so far).")
            else:
                try:
                    trend = "ols" if sub[x_feat].std() > 1e-9 else None
                    fig = px.scatter(
                        sub, x=x_feat, y=y_col, trendline=trend,
                        labels={x_feat: FEATURE_LABELS[x_feat], y_col: y_target},
                        title=f"{FEATURE_LABELS[x_feat]} vs. {y_target}")
                    fig.update_traces(marker=dict(size=12, color="#00E5A0",
                                                  line=dict(width=1, color="#0B0F19")))
                    st.plotly_chart(style_fig(fig, 380), use_container_width=True)
                    if sub[x_feat].std() > 1e-9 and sub[y_col].std() > 1e-9:
                        r = float(np.corrcoef(sub[x_feat], sub[y_col])[0, 1])
                        st.caption(f"Pearson r = {r:+.2f} across {len(sub)} dates.")
                except Exception as exc:
                    st.info(f"Explorer plot unavailable ({exc}). The OLS trendline needs the "
                            "statsmodels package; the scatter still conveys the relationship.")
