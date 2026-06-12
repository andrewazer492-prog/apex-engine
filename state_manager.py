# ==============================================================================
# APEX HUMAN PERFORMANCE & BIOMETRIC OPERATING SYSTEM — V3.0 ENTERPRISE
# state_manager.py
# ------------------------------------------------------------------------------
# Relational session-state schema layer, global mathematical wrappers, and the
# consolidated master backup/restore data pipeline (multi-tab XLSX + JSON).
# Imported by main.py and every script under pages/.
# ==============================================================================

import io
import json
import warnings
from datetime import date, datetime

import numpy as np
import pandas as pd
import streamlit as st

warnings.filterwarnings(
    "ignore",
    message=".*concatenation with empty or all-NA entries.*",
    category=FutureWarning,
)
warnings.filterwarnings(
    "ignore",
    message=".*incompatible dtype.*",
    category=FutureWarning,
)

APP_NAME = "APEX OS"
APP_VERSION = "3.0"

# ------------------------------------------------------------------------------
# ATHLETE PROFILE (baked into the architecture) + GLOBAL DEFAULT SETTINGS
# ------------------------------------------------------------------------------

ATHLETE_PROFILE = {
    "height": "5'6\"",
    "current_weight_lbs": 167.0,
    "target_low_lbs": 145.0,
    "target_high_lbs": 155.0,
    "role": "Point Guard / Sharpshooter",
    "split": "4-Day Athletic Upper/Lower + 3x/wk Plyometrics & Core",
    "meal_time": "6:00 PM",
    "train_time": "7:30 PM",
    "digestion_window_mins": 90,
}

DEFAULT_SETTINGS = {
    "t_cal": 2100,            # daily calorie target (kcal)
    "t_pro": 165,             # daily protein target (g)
    "t_carb": 225,            # daily carbohydrate target (g)
    "t_fat": 60,              # daily fat target (g)
    "baseline_rhr": 55,       # resting heart rate baseline (bpm)
    "baseline_hrv": 65,       # HRV rMSSD baseline (ms)
    "gerc_threshold": 2.0,    # minimum acceptable Gastric Emptying Rate Coefficient
    "fat_limit_g": 15.0,      # pre-workout fat ceiling (g)
    "fiber_limit_g": 8.0,     # pre-workout fiber ceiling (g)
    "carb_floor_g": 40.0,     # pre-workout carbohydrate floor (g)
    "carb_ceil_g": 60.0,      # pre-workout carbohydrate ceiling (g)
    "protein_floor_g": 30.0,  # pre-workout protein floor (g)
}

# ------------------------------------------------------------------------------
# RELATIONAL SCHEMA REGISTRY — five decoupled DataFrames
# ------------------------------------------------------------------------------

SCHEMAS = {
    "df_nutrition": {
        "columns": [
            "Date", "Timestamp", "Source", "Item_Name", "Calories",
            "Protein", "Carbs", "Fats", "Fiber", "Digestion_Window_Mins",
        ],
        "numeric": ["Calories", "Protein", "Carbs", "Fats", "Fiber", "Digestion_Window_Mins"],
        "bool": [],
        "text": ["Timestamp", "Source", "Item_Name"],
    },
    "df_fitbit_air": {
        "columns": [
            "Date", "Daily_Readiness_Score", "Cardio_Load", "HRV_rMSSD",
            "Resting_Heart_Rate", "Deep_Sleep_Mins", "REM_Sleep_Mins", "Total_Steps",
        ],
        "numeric": [
            "Daily_Readiness_Score", "Cardio_Load", "HRV_rMSSD",
            "Resting_Heart_Rate", "Deep_Sleep_Mins", "REM_Sleep_Mins", "Total_Steps",
        ],
        "bool": [],
        "text": [],
    },
    "df_biomechanics": {
        "columns": [
            "Date", "Body_Weight", "Vertical_Jump_Inches", "Flight_Time_Ms",
            "Ground_Contact_Time_Ms", "Lateral_Shuttle_Sec", "Squat_1RM_Lbs",
        ],
        "numeric": [
            "Body_Weight", "Vertical_Jump_Inches", "Flight_Time_Ms",
            "Ground_Contact_Time_Ms", "Lateral_Shuttle_Sec", "Squat_1RM_Lbs",
        ],
        "bool": [],
        "text": [],
    },
    "df_cognitive_habits": {
        "columns": [
            "Date", "Focus_Blocks_Completed", "Anki_Retention_Rate",
            "Peptide_Adherence_Bool", "Sunlight_Exposure_Bool", "Skincare_Adherence_Bool",
        ],
        "numeric": ["Focus_Blocks_Completed", "Anki_Retention_Rate"],
        "bool": ["Peptide_Adherence_Bool", "Sunlight_Exposure_Bool", "Skincare_Adherence_Bool"],
        "text": [],
    },
    "df_custom_foods": {
        "columns": ["Item_Name", "Calories", "Protein", "Carbs", "Fats", "Fiber"],
        "numeric": ["Calories", "Protein", "Carbs", "Fats", "Fiber"],
        "bool": [],
        "text": ["Item_Name"],
    },
}

# DataFrames keyed one-row-per-Date (merge/upsert semantics use the Date column)
DAILY_KEYED = {"df_fitbit_air", "df_biomechanics", "df_cognitive_habits"}

SHEET_NAMES = {
    "df_nutrition": "Nutrition",
    "df_fitbit_air": "Fitbit_Air",
    "df_biomechanics": "Biomechanics",
    "df_cognitive_habits": "Cognitive_Habits",
    "df_custom_foods": "Custom_Foods",
}

# ------------------------------------------------------------------------------
# STATE INITIALIZATION + ACCESSORS
# ------------------------------------------------------------------------------


def _blank_df(key: str) -> pd.DataFrame:
    return pd.DataFrame(columns=SCHEMAS[key]["columns"])


def init_global_state():
    """Idempotent systemic initialization. Call at the top of every page."""
    for key in SCHEMAS:
        if key not in st.session_state:
            st.session_state[key] = _blank_df(key)
    for setting, default in DEFAULT_SETTINGS.items():
        st.session_state.setdefault(setting, default)


def get_df(key: str) -> pd.DataFrame:
    init_global_state()
    return st.session_state[key]


def set_df(key: str, df: pd.DataFrame):
    st.session_state[key] = df.reset_index(drop=True)


def append_row(key: str, row: dict):
    """Append a single record, aligning to the registered schema."""
    df = get_df(key)
    full = {c: row.get(c, pd.NA) for c in SCHEMAS[key]["columns"]}
    addition = pd.DataFrame([full])
    if df.empty:
        set_df(key, addition)
    else:
        set_df(key, pd.concat([df, addition], ignore_index=True))


def upsert_by_date(key: str, date_iso: str, updates: dict):
    """One-row-per-day write for daily-keyed DataFrames."""
    df = get_df(key)
    mask = df["Date"] == date_iso
    if mask.any():
        idx = df.index[mask][0]
        for col, val in updates.items():
            if col in df.columns:
                df.loc[idx, col] = val
        set_df(key, df)
    else:
        row = {c: pd.NA for c in SCHEMAS[key]["columns"]}
        row["Date"] = date_iso
        row.update({k: v for k, v in updates.items() if k in row})
        addition = pd.DataFrame([row])
        if df.empty:
            set_df(key, addition)
        else:
            set_df(key, pd.concat([df, addition], ignore_index=True))


def delete_rows(key: str, index_list):
    df = get_df(key)
    set_df(key, df.drop(index=[i for i in index_list if i in df.index]))


def get_row_by_date(key: str, date_iso: str):
    df = get_df(key)
    if df.empty:
        return None
    hits = df[df["Date"] == date_iso]
    return None if hits.empty else hits.iloc[-1]


def day_count(key: str) -> int:
    df = get_df(key)
    if df.empty or "Date" not in df.columns:
        return 0
    return int(df["Date"].dropna().nunique())


def latest_value(key: str, col: str, default=None):
    df = get_df(key)
    if df.empty or col not in df.columns:
        return default
    sub = df.dropna(subset=[col])
    if sub.empty:
        return default
    if "Date" in sub.columns:
        sub = sub.sort_values("Date")
    return sub.iloc[-1][col]


def chartable(key: str) -> pd.DataFrame:
    """Typed, date-sorted copy of a DataFrame ready for Plotly rendering."""
    df = get_df(key).copy()
    if df.empty:
        return df
    schema = SCHEMAS[key]
    if "Date" in df.columns:
        df["Date_dt"] = pd.to_datetime(df["Date"], errors="coerce")
        df = df.dropna(subset=["Date_dt"]).sort_values("Date_dt").reset_index(drop=True)
    for col in schema["numeric"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    for col in schema["bool"]:
        df[col] = df[col].map(to_bool)
    return df

# ------------------------------------------------------------------------------
# GLOBAL MATHEMATICAL WRAPPERS
# ------------------------------------------------------------------------------


def to_bool(v) -> bool:
    return str(v).strip().lower() in ("true", "1", "1.0", "yes", "y")


def safe_div(numerator: float, denominator: float, default: float = 0.0) -> float:
    try:
        n, d = float(numerator), float(denominator)
        if d == 0 or np.isnan(d) or np.isnan(n):
            return default
        return n / d
    except (TypeError, ValueError):
        return default


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def num_or(value, default: float = np.nan) -> float:
    try:
        out = float(value)
        return default if np.isnan(out) else out
    except (TypeError, ValueError):
        return default


def compute_gerc(carbs_g: float, fats_g: float, fiber_g: float) -> float:
    """Gastric Emptying Rate Coefficient: Carbs / (Fats*1.5 + Fiber*2.0 + 1)."""
    carbs = max(0.0, num_or(carbs_g, 0.0))
    fats = max(0.0, num_or(fats_g, 0.0))
    fiber = max(0.0, num_or(fiber_g, 0.0))
    return round(safe_div(carbs, fats * 1.5 + fiber * 2.0 + 1.0, 0.0), 2)


def compute_rsi(flight_time_ms: float, ground_contact_ms: float) -> float:
    """Reactive Strength Index = Flight Time / Ground Contact Time."""
    return round(safe_div(num_or(flight_time_ms, 0.0), num_or(ground_contact_ms, 0.0), 0.0), 3)


def rolling_mean(series: pd.Series, window: int = 7) -> pd.Series:
    s = pd.to_numeric(series, errors="coerce")
    return s.rolling(window=window, min_periods=max(2, window // 2)).mean()


def rolling_std(series: pd.Series, window: int = 7) -> pd.Series:
    s = pd.to_numeric(series, errors="coerce")
    return s.rolling(window=window, min_periods=max(2, window // 2)).std()


def last_finite(series: pd.Series, default=None):
    s = pd.to_numeric(series, errors="coerce").dropna()
    return default if s.empty else float(s.iloc[-1])


def minmax_scale(value: float, low: float, high: float) -> float:
    if high <= low:
        return 0.0
    return clamp((value - low) / (high - low), 0.0, 1.0)


FLAG_MESSAGES = {
    "GREEN": ("🟢 GREEN FLAG", "CNS Fully Potentiated. Clear for maximum-effort "
              "plyometrics, vertical rim-testing, and explosive acceleration."),
    "YELLOW": ("🟡 YELLOW FLAG", "CNS Moderately Fatigued. Reduce plyometric volume "
               "by 30%. Focus heavily on dynamic joint stiffness and deceleration mechanics."),
    "RED": ("🔴 RED FLAG", "CNS Depleted / High Injury Risk. HALT all explosive training "
            "and heavy compound lifting. Shift entirely to active recovery, mobility, "
            "or light spot-shooting."),
}


def flag_from_score(score: float) -> str:
    if score >= 80:
        return "GREEN"
    if score >= 50:
        return "YELLOW"
    return "RED"


def render_flag_banner(score: float):
    label = flag_from_score(score)
    title, body = FLAG_MESSAGES[label]
    text = f"{title} ({score:.0f}%) — {body}"
    if label == "GREEN":
        st.success(text)
    elif label == "YELLOW":
        st.warning(text)
    else:
        st.error(text)

# ------------------------------------------------------------------------------
# TYPED COERCION FOR RESTORED DATA
# ------------------------------------------------------------------------------


def _coerce_df(key: str, raw: pd.DataFrame) -> pd.DataFrame:
    schema = SCHEMAS[key]
    df = raw.copy()
    df.columns = [str(c).strip() for c in df.columns]
    for col in schema["columns"]:
        if col not in df.columns:
            df[col] = pd.NA
    df = df[schema["columns"]]
    if "Date" in df.columns:
        parsed = pd.to_datetime(df["Date"], errors="coerce")
        df = df[parsed.notna()].copy()
        df["Date"] = parsed[parsed.notna()].dt.date.astype(str)
    for col in schema["numeric"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    for col in schema["bool"]:
        df[col] = df[col].map(lambda v: to_bool(v) if not pd.isna(v) else pd.NA)
    for col in schema["text"]:
        df[col] = df[col].astype("object").where(df[col].notna(), pd.NA)
    return df.reset_index(drop=True)


def _apply_restore(key: str, incoming: pd.DataFrame, mode: str) -> int:
    if mode.lower().startswith("merge"):
        merged = pd.concat([get_df(key), incoming], ignore_index=True)
    else:
        merged = incoming
    if key in DAILY_KEYED:
        merged = merged.drop_duplicates(subset="Date", keep="last").sort_values("Date")
    elif key == "df_custom_foods":
        merged = merged.drop_duplicates(subset="Item_Name", keep="last")
    else:
        merged = merged.drop_duplicates(keep="last")
        if "Date" in merged.columns:
            merged = merged.sort_values("Date")
    set_df(key, merged[SCHEMAS[key]["columns"]])
    return len(incoming)

# ------------------------------------------------------------------------------
# MASTER BACKUP UTILITY — multi-tab XLSX + JSON bundles
# ------------------------------------------------------------------------------


def build_master_backup_xlsx() -> bytes:
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        meta = pd.DataFrame([{
            "app": APP_NAME,
            "version": APP_VERSION,
            "exported_utc": datetime.utcnow().isoformat(timespec="seconds"),
        }])
        meta.to_excel(writer, sheet_name="_meta", index=False)
        for key, sheet in SHEET_NAMES.items():
            get_df(key).to_excel(writer, sheet_name=sheet, index=False)
    return buffer.getvalue()


def restore_master_backup_xlsx(uploaded_file, mode: str) -> dict:
    workbook = pd.read_excel(uploaded_file, sheet_name=None)
    counts = {}
    for key, sheet in SHEET_NAMES.items():
        if sheet in workbook:
            counts[key] = _apply_restore(key, _coerce_df(key, workbook[sheet]), mode)
    return counts


def build_master_backup_json() -> str:
    payload = {
        "app": APP_NAME,
        "version": APP_VERSION,
        "exported_utc": datetime.utcnow().isoformat(timespec="seconds"),
        "tables": {
            key: get_df(key).where(get_df(key).notna(), None).to_dict(orient="records")
            for key in SCHEMAS
        },
    }
    return json.dumps(payload, default=str, indent=2)


def restore_master_backup_json(uploaded_file, mode: str) -> dict:
    payload = json.load(uploaded_file)
    tables = payload.get("tables", {})
    counts = {}
    for key in SCHEMAS:
        if key in tables:
            counts[key] = _apply_restore(key, _coerce_df(key, pd.DataFrame(tables[key])), mode)
    return counts


def render_master_backup_panel():
    """Full save/restore UI block. Rendered on the main.py landing dashboard."""
    st.markdown("##### 💾 Master Backup — Export Full Database State")
    st.caption(
        "Bundles all five relational tables (Nutrition, Fitbit Air, Biomechanics, "
        "Cognitive/Habits, Custom Foods) into a single multi-tab workbook. Streamlit "
        "Community Cloud containers reset on sleep — export after every logging session."
    )
    stamp = date.today().isoformat()
    exp1, exp2 = st.columns(2)
    with exp1:
        try:
            xlsx_bytes = build_master_backup_xlsx()
            st.download_button(
                "⬇️ Download Master Backup (.xlsx — 5 tabs)",
                data=xlsx_bytes,
                file_name=f"apex_os_master_backup_{stamp}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
                type="primary",
            )
        except Exception as exc:
            st.error(f"XLSX engine unavailable: {exc}")
    with exp2:
        st.download_button(
            "⬇️ Download Master Backup (.json)",
            data=build_master_backup_json().encode("utf-8"),
            file_name=f"apex_os_master_backup_{stamp}.json",
            mime="application/json",
            use_container_width=True,
        )

    st.markdown("##### ♻️ Restore Full Database State")
    mode = st.radio(
        "Restore mode",
        ["Replace current session", "Merge with current session"],
        horizontal=True,
        key="apex_restore_mode",
    )
    uploaded = st.file_uploader(
        "Upload a previously exported master backup (.xlsx or .json)",
        type=["xlsx", "json"],
        key="apex_master_restore",
    )
    if uploaded is not None:
        if st.button("♻️ Restore Master Backup", use_container_width=True, key="apex_restore_btn"):
            try:
                if uploaded.name.lower().endswith(".json"):
                    counts = restore_master_backup_json(uploaded, mode)
                else:
                    counts = restore_master_backup_xlsx(uploaded, mode)
                if not counts:
                    st.error("No recognizable APEX OS tables found in that file.")
                else:
                    summary = " · ".join(
                        f"{SHEET_NAMES[k]}: {v} rows" for k, v in counts.items()
                    )
                    st.toast(f"Restored — {summary}", icon="♻️")
                    st.rerun()
            except Exception as exc:
                st.error(f"Restore failed — file could not be parsed: {exc}")

    with st.expander("🔍 Inspect current table row counts"):
        counts_df = pd.DataFrame(
            [{"Table": SHEET_NAMES[k], "Rows": len(get_df(k)), "Days": day_count(k)}
             for k in SCHEMAS]
        )
        st.dataframe(counts_df, use_container_width=True, hide_index=True)

# ------------------------------------------------------------------------------
# UNIFIED DARK THEME + PLOTLY STYLER (shared by main.py and all pages)
# ------------------------------------------------------------------------------

APEX_CSS = """
<style>
.stApp {
    background: radial-gradient(1100px 520px at 18% -8%, #13203A 0%, #0B0F19 55%) fixed;
    background-color: #0B0F19;
}
[data-testid="stHeader"] { background: rgba(0,0,0,0); }
[data-testid="stSidebar"] { background: #070A11; border-right: 1px solid #1C2536; }
[data-testid="stSidebar"] .stMarkdown p, [data-testid="stSidebar"] label { color: #C9D2E3; }
h1, h2, h3, h4 { color: #F2F5FA !important; letter-spacing: .01em; }
.stMarkdown p, .stMarkdown li, label, [data-testid="stWidgetLabel"] p { color: #C9D2E3; }
[data-testid="stCaptionContainer"] p { color: #7E8FAD !important; }
[data-testid="stMetric"] {
    background: linear-gradient(160deg, #121A2B, #0E1422);
    border: 1px solid #22304A; border-radius: 14px;
    padding: 12px 16px; box-shadow: 0 6px 18px rgba(0,0,0,.35);
}
[data-testid="stMetricLabel"] p {
    color: #8FA1BF !important; text-transform: uppercase;
    font-size: .70rem !important; letter-spacing: .08em; font-weight: 700;
}
[data-testid="stMetricValue"] { color: #00E5A0; }
.stProgress > div > div > div > div {
    background: linear-gradient(90deg, #00E5A0, #00B4D8);
}
div[data-testid="stExpander"] {
    background: #0E1422; border: 1px solid #1F2B42; border-radius: 12px;
}
[data-testid="stForm"] {
    background: #0E1422; border: 1px solid #1F2B42;
    border-radius: 14px; padding: 18px;
}
button[data-baseweb="tab"] p { color: #8FA1BF; font-weight: 700; letter-spacing: .02em; }
button[data-baseweb="tab"][aria-selected="true"] p { color: #00E5A0; }
[data-baseweb="tab-highlight"] { background-color: #00E5A0; }
.stNumberInput input, .stTextInput input, .stDateInput input {
    background: #101727 !important; color: #E6E9F0 !important; border-radius: 8px;
}
div[data-baseweb="select"] > div { background: #101727; color: #E6E9F0; }
.stButton > button, .stDownloadButton > button, .stFormSubmitButton > button {
    border-radius: 10px; border: 1px solid #2A3A58;
    background: linear-gradient(160deg, #16203A, #101727);
    color: #E6E9F0; font-weight: 700;
}
.stButton > button:hover, .stDownloadButton > button:hover,
.stFormSubmitButton > button:hover { border-color: #00E5A0; color: #00E5A0; }
.apex-card {
    background: linear-gradient(160deg, #121A2B, #0D1320);
    border: 1px solid #22304A; border-radius: 14px;
    padding: 16px 18px; margin-bottom: 12px;
}
.apex-pill {
    display: inline-block; padding: 3px 12px; border-radius: 999px;
    font-size: .70rem; font-weight: 800; letter-spacing: .07em;
}
a[data-testid="stPageLink-NavLink"] p { color: #C9D2E3; font-weight: 700; }
a[data-testid="stPageLink-NavLink"]:hover p { color: #00E5A0; }
</style>
"""


def apply_theme():
    st.markdown(APEX_CSS, unsafe_allow_html=True)


def style_fig(fig, height: int = 360):
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(10,13,20,0.55)",
        height=height,
        margin=dict(t=48, b=8, l=8, r=8),
        font=dict(color="#E6E9F0", size=12),
        legend=dict(orientation="h", yanchor="bottom", y=-0.28, x=0),
        xaxis_title=None,
    )
    return fig


def render_sidebar_profile():
    """Shared athlete-profile card for every page sidebar."""
    st.markdown(
        f"""
        <div class="apex-card">
            <span class="apex-pill"
                  style="background:rgba(0,229,160,.12);color:#00E5A0;border:1px solid #00E5A0;">
                ATHLETE PROFILE
            </span>
            <p style="margin:10px 0 0 0;font-size:.84rem;line-height:1.65;color:#C9D2E3;">
                <b style="color:#F2F5FA;">{ATHLETE_PROFILE['role']}</b><br>
                Height {ATHLETE_PROFILE['height']} ·
                {ATHLETE_PROFILE['current_weight_lbs']:.0f} lbs baseline<br>
                Prime zone: <b style="color:#00E5A0;">
                {ATHLETE_PROFILE['target_low_lbs']:.0f}–{ATHLETE_PROFILE['target_high_lbs']:.0f} lbs</b><br>
                {ATHLETE_PROFILE['split']}<br>
                Feed {ATHLETE_PROFILE['meal_time']} → Train {ATHLETE_PROFILE['train_time']}
                ({ATHLETE_PROFILE['digestion_window_mins']}-min window)
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def data_gate(required_days: int, available_days: int, feature_name: str) -> bool:
    """Robust data-availability gate. Renders an st.info callout when locked."""
    if available_days >= required_days:
        return True
    remaining = required_days - available_days
    st.info(
        f"🔒 **{feature_name}** unlocks after {required_days} logged days "
        f"({available_days} logged so far — {remaining} more to go). "
        f"Keep logging daily entries to activate this analysis."
    )
    return False
