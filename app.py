# ==============================================================================
# APEX ENGINE — Athletic Performance & Human Optimization Dashboard
# ==============================================================================
# Single-file Streamlit application. Zero local configuration required.
#
# DEPLOYMENT (Streamlit Community Cloud):
#   1. Push app.py + requirements.txt to a GitHub repository.
#   2. Go to share.streamlit.io -> "New app" -> point it at the repo -> Deploy.
#
# requirements.txt contents:
#   streamlit>=1.32
#   pandas>=2.0
#   plotly>=5.18
#
# OPTIONAL (recommended) — add .streamlit/config.toml to the repo for native
# dark chrome on every widget:
#   [theme]
#   base = "dark"
#   primaryColor = "#00E5A0"
#   backgroundColor = "#0B0F19"
#   secondaryBackgroundColor = "#141A26"
#   textColor = "#E6E9F0"
#
# Persistence model: all entries accumulate in st.session_state DataFrames.
# Serverless containers reset, so the Data Management tab provides CSV
# download (export) and upload (restore) to carry history across sessions.
# ==============================================================================

import warnings
from datetime import date, datetime

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# Pandas emits a benign FutureWarning when concatenating a partially-NA new row
# (e.g., logging CNS data before nutrition data on a given date). Silence it.
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

# ------------------------------------------------------------------------------
# PAGE CONFIG + GLOBAL DARK THEME STYLING
# ------------------------------------------------------------------------------

st.set_page_config(
    page_title="APEX ENGINE | Human Optimization Dashboard",
    page_icon="🏀",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
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
    </style>
    """,
    unsafe_allow_html=True,
)

# ------------------------------------------------------------------------------
# HARDCODED ATHLETE PROFILE (baked into the architecture)
# ------------------------------------------------------------------------------

PROFILE = {
    "height": "5'6\"",
    "current_weight": 167.0,
    "target_low": 145.0,
    "target_high": 155.0,
    "role": "Point Guard / Sharpshooter",
    "split": "4-Day Athletic Upper/Lower + 3x/wk Plyometrics & Core",
    "meal_time": "6:00 PM",
    "train_time": "7:30 PM",
    "window_min": 90,
}

# Pre-workout validation thresholds (Rules A / B / C)
CARB_FLOOR, CARB_CEIL = 40.0, 60.0
FAT_LIMIT, FIBER_LIMIT = 15.0, 8.0
PROTEIN_FLOOR, PROTEIN_CEIL = 30.0, 40.0

MSG_GREEN = ("CNS Fully Potentiated. Clear for maximum-effort plyometrics, "
             "depth jumps, and vertical rim-testing.")
MSG_YELLOW = ("CNS Moderately Fatigued. Consider reducing plyometric volume by 30%. "
              "Focus heavily on dynamic warm-ups and joint stiffness.")
MSG_RED = ("CNS System Depleted / High Injury Risk. HALT all plyometric and heavy "
           "bilateral lifting. Shift entirely to active recovery, mobility, or "
           "light spot-shooting mechanics.")

# ------------------------------------------------------------------------------
# HARDCODED FAST-FOOD NUTRITIONAL DATABASE
# Macro profiles per standard serving, based on published restaurant nutrition
# data (cal / protein g / carb g / fat g / fiber g). Edit values here anytime.
# ------------------------------------------------------------------------------

FOOD_DB = {
    "Chipotle": {
        "Chicken (4 oz serving)":                    {"cal": 180, "p": 32.0, "c": 0.0,  "f": 7.0,  "fib": 0.0},
        "Steak (4 oz serving)":                      {"cal": 150, "p": 21.0, "c": 1.0,  "f": 6.0,  "fib": 0.0},
        "White Rice (4 oz serving)":                 {"cal": 210, "p": 4.0,  "c": 40.0, "f": 4.0,  "fib": 1.0},
        "Black Beans (4 oz serving)":                {"cal": 130, "p": 8.0,  "c": 22.0, "f": 1.5,  "fib": 7.0},
        "Fajita Veggies (2.5 oz serving)":           {"cal": 20,  "p": 1.0,  "c": 5.0,  "f": 0.0,  "fib": 1.0},
        "Guacamole (4 oz serving)":                  {"cal": 230, "p": 2.0,  "c": 8.0,  "f": 22.0, "fib": 6.0},
        "Cheese (1 oz serving)":                     {"cal": 110, "p": 6.0,  "c": 1.0,  "f": 8.0,  "fib": 0.0},
        "Fresh Tomato Salsa (4 oz serving)":         {"cal": 25,  "p": 0.0,  "c": 5.0,  "f": 0.0,  "fib": 1.0},
        "BOWL: Chicken + White Rice + Fajita Veg":   {"cal": 410, "p": 37.0, "c": 45.0, "f": 11.0, "fib": 2.0},
        "BOWL: Chicken + Rice + Beans + Veggies":    {"cal": 540, "p": 45.0, "c": 67.0, "f": 12.5, "fib": 9.0},
        "BOWL: Steak + White Rice + Fajita Veg":     {"cal": 380, "p": 26.0, "c": 46.0, "f": 10.0, "fib": 2.0},
    },
    "Chick-fil-A": {
        "Grilled Nuggets (8-count)":                 {"cal": 130, "p": 25.0, "c": 1.0,  "f": 3.0,  "fib": 0.0},
        "Grilled Nuggets (12-count)":                {"cal": 200, "p": 38.0, "c": 2.0,  "f": 4.5,  "fib": 0.0},
        "Fried Nuggets (8-count)":                   {"cal": 250, "p": 27.0, "c": 11.0, "f": 11.0, "fib": 0.0},
        "Fried Nuggets (12-count)":                  {"cal": 380, "p": 40.0, "c": 16.0, "f": 17.0, "fib": 1.0},
        "Grilled Chicken Sandwich":                  {"cal": 390, "p": 28.0, "c": 44.0, "f": 12.0, "fib": 3.0},
        "Grilled Chicken Club (w/ cheese & bacon)":  {"cal": 520, "p": 38.0, "c": 44.0, "f": 22.0, "fib": 3.0},
        "Waffle Fries (Small)":                      {"cal": 320, "p": 4.0,  "c": 34.0, "f": 19.0, "fib": 4.0},
        "Waffle Fries (Medium)":                     {"cal": 420, "p": 5.0,  "c": 45.0, "f": 24.0, "fib": 5.0},
        "Chick-fil-A Sauce (1 packet)":              {"cal": 140, "p": 0.0,  "c": 6.0,  "f": 13.0, "fib": 0.0},
        "Polynesian Sauce (1 packet)":               {"cal": 110, "p": 0.0,  "c": 13.0, "f": 6.0,  "fib": 0.0},
        "Garden Herb Ranch Sauce (1 packet)":        {"cal": 140, "p": 1.0,  "c": 1.0,  "f": 15.0, "fib": 0.0},
        "Zesty Buffalo Sauce (1 packet)":            {"cal": 25,  "p": 0.0,  "c": 1.0,  "f": 2.5,  "fib": 0.0},
        "Barbeque Sauce (1 packet)":                 {"cal": 45,  "p": 0.0,  "c": 11.0, "f": 0.0,  "fib": 0.0},
    },
    "Whataburger": {
        "Sweet & Spicy Bacon Burger":                {"cal": 1080, "p": 53.0, "c": 74.0, "f": 65.0, "fib": 3.0},
        "Whataburger Jr.":                           {"cal": 310,  "p": 14.0, "c": 30.0, "f": 15.0, "fib": 2.0},
        "Grilled Chicken Sandwich":                  {"cal": 420,  "p": 33.0, "c": 46.0, "f": 12.0, "fib": 3.0},
        "French Fries (Small)":                      {"cal": 270,  "p": 3.0,  "c": 34.0, "f": 13.0, "fib": 3.0},
        "French Fries (Medium)":                     {"cal": 410,  "p": 5.0,  "c": 51.0, "f": 20.0, "fib": 4.0},
    },
}

CUSTOM_LABEL = "Custom / Manual Entry"

# ------------------------------------------------------------------------------
# DATA SCHEMAS + SESSION STATE INITIALIZATION
# ------------------------------------------------------------------------------

DAILY_COLUMNS = [
    "date", "sleep_quality", "soreness", "resting_hr", "cns_score", "cns_flag",
    "sunlight", "peptides", "skincare",
    "body_weight_lbs", "vertical_elasticity", "barbell_output", "adherence_pct",
]
MEAL_COLUMNS = [
    "date", "restaurant", "item", "portion",
    "calories", "protein_g", "carbs_g", "fat_g", "fiber_g", "preworkout",
]
DAILY_NUM_COLS = [
    "sleep_quality", "soreness", "resting_hr", "cns_score",
    "body_weight_lbs", "vertical_elasticity", "barbell_output", "adherence_pct",
]
DAILY_BOOL_COLS = ["sunlight", "peptides", "skincare"]
MEAL_NUM_COLS = ["portion", "calories", "protein_g", "carbs_g", "fat_g", "fiber_g"]


def init_state():
    if "daily_df" not in st.session_state:
        st.session_state.daily_df = pd.DataFrame(columns=DAILY_COLUMNS)
    if "meal_log" not in st.session_state:
        st.session_state.meal_log = pd.DataFrame(columns=MEAL_COLUMNS)
    st.session_state.setdefault("t_cal", 2100)
    st.session_state.setdefault("t_pro", 165)
    st.session_state.setdefault("t_carb", 225)
    st.session_state.setdefault("t_fat", 60)
    st.session_state.setdefault("baseline_rhr", 55)


init_state()

# ------------------------------------------------------------------------------
# HELPER FUNCTIONS
# ------------------------------------------------------------------------------


def to_bool(v) -> bool:
    """Robust truthiness for values that survived a CSV round-trip."""
    return str(v).strip().lower() in ("true", "1", "yes", "y", "1.0")


def gv(row, key, default=None):
    """Safe getter for a value in a daily-log Series (handles None/NaN)."""
    if row is None or key not in row.index:
        return default
    val = row[key]
    if pd.isna(val):
        return default
    return val


def get_daily_row(d_iso: str):
    df = st.session_state.daily_df
    hits = df[df["date"] == d_iso]
    if hits.empty:
        return None
    return hits.iloc[-1]


def upsert_daily(d_iso: str, updates: dict):
    df = st.session_state.daily_df
    mask = df["date"] == d_iso
    if mask.any():
        idx = df.index[mask][0]
        for k, v in updates.items():
            df.loc[idx, k] = v
        st.session_state.daily_df = df
    else:
        new_row = {c: pd.NA for c in DAILY_COLUMNS}
        new_row["date"] = d_iso
        new_row.update(updates)
        addition = pd.DataFrame([new_row])
        if df.empty:
            st.session_state.daily_df = addition
        else:
            st.session_state.daily_df = pd.concat([df, addition], ignore_index=True)


def day_meal_slice(d_iso: str) -> pd.DataFrame:
    ml = st.session_state.meal_log
    if ml.empty:
        return ml
    return ml[ml["date"] == d_iso]


def macro_totals(meals: pd.DataFrame) -> dict:
    if meals.empty:
        return {"calories": 0.0, "protein_g": 0.0, "carbs_g": 0.0, "fat_g": 0.0, "fiber_g": 0.0}
    return {
        "calories": float(pd.to_numeric(meals["calories"], errors="coerce").fillna(0).sum()),
        "protein_g": float(pd.to_numeric(meals["protein_g"], errors="coerce").fillna(0).sum()),
        "carbs_g": float(pd.to_numeric(meals["carbs_g"], errors="coerce").fillna(0).sum()),
        "fat_g": float(pd.to_numeric(meals["fat_g"], errors="coerce").fillna(0).sum()),
        "fiber_g": float(pd.to_numeric(meals["fiber_g"], errors="coerce").fillna(0).sum()),
    }


def cns_components(sleep: float, soreness: float, rhr: float, baseline: float):
    """Weighted CNS readiness components: sleep 40% | soreness 30% | RHR 30%."""
    sleep_pts = ((sleep - 1.0) / 9.0) * 40.0
    sore_pts = ((10.0 - soreness) / 9.0) * 30.0
    deviation = rhr - baseline
    if deviation <= 0:
        rhr_pts = 30.0
    else:
        rhr_pts = max(0.0, 30.0 - 3.0 * deviation)
    return round(sleep_pts, 1), round(sore_pts, 1), round(rhr_pts, 1)


def calc_cns(sleep: float, soreness: float, rhr: float, baseline: float) -> float:
    a, b, c = cns_components(sleep, soreness, rhr, baseline)
    return round(min(100.0, max(0.0, a + b + c)), 1)


def cns_flag_label(score: float) -> str:
    if score >= 80:
        return "GREEN"
    if score >= 50:
        return "YELLOW"
    return "RED"


def render_cns_banner(score: float):
    if score >= 80:
        st.success(f"🟢 GREEN FLAG ({score:.0f}%) — {MSG_GREEN}")
    elif score >= 50:
        st.warning(f"🟡 YELLOW FLAG ({score:.0f}%) — {MSG_YELLOW}")
    else:
        st.error(f"🔴 RED FLAG ({score:.0f}%) — {MSG_RED}")


def validate_preworkout(p: float, c: float, f: float, fib: float):
    """Rules A/B/C for the 6:00 PM meal feeding the 7:30 PM session."""
    checks = []
    if c < CARB_FLOOR:
        checks.append(("error",
            f"RULE A · CARBOHYDRATE THRESHOLD — FAILED: only {c:.0f} g of carbohydrate logged. "
            f"A minimum of {CARB_FLOOR:.0f}–{CARB_CEIL:.0f} g of highly bioavailable, low-fiber "
            f"carbohydrate (white rice, sandwich bun, fruit) is required to saturate muscle "
            f"glycogen stores for the 7:30 PM session. Add at least {CARB_FLOOR - c:.0f} g more."))
    elif c <= CARB_CEIL:
        checks.append(("success",
            f"RULE A · CARBOHYDRATE THRESHOLD — PASSED: {c:.0f} g sits inside the "
            f"{CARB_FLOOR:.0f}–{CARB_CEIL:.0f} g glycogen-saturation band for the 7:30 PM session."))
    else:
        checks.append(("info",
            f"RULE A · CARBOHYDRATE THRESHOLD — PASSED (HIGH): {c:.0f} g exceeds the "
            f"{CARB_CEIL:.0f} g target ceiling. Glycogen is fully covered; trim portions if this "
            f"threatens the daily caloric deficit."))

    bottlenecks = []
    if f > FAT_LIMIT:
        bottlenecks.append(f"fat at {f:.0f} g (limit {FAT_LIMIT:.0f} g)")
    if fib > FIBER_LIMIT:
        bottlenecks.append(f"fiber at {fib:.0f} g (limit {FIBER_LIMIT:.0f} g)")
    if bottlenecks:
        checks.append(("warning",
            "RULE B · FAT/FIBER BOTTLENECK — FLAGGED: " + " and ".join(bottlenecks) + ". "
            "Elevated fat and fiber delay gastric emptying, meaning this meal will still be "
            "sitting in the gut at 7:30 PM — expect sluggishness, heaviness, or cramping during "
            "high-velocity plyometrics. Strip guacamole, fried items, and heavy sauces from this "
            "meal, or move them to the post-workout window."))
    else:
        checks.append(("success",
            f"RULE B · FAT/FIBER BOTTLENECK — CLEAR: fat {f:.0f} g (≤{FAT_LIMIT:.0f} g) and "
            f"fiber {fib:.0f} g (≤{FIBER_LIMIT:.0f} g). Gastric emptying will complete inside "
            f"the 90-minute metabolic window."))

    if p < PROTEIN_FLOOR:
        checks.append(("error",
            f"RULE C · PROTEIN PROTECTION — FAILED: only {p:.0f} g of protein logged. "
            f"A minimum of {PROTEIN_FLOOR:.0f}–{PROTEIN_CEIL:.0f} g of rapid-absorbing lean protein "
            f"(grilled chicken, steak) is required to prevent muscular catabolism during a training "
            f"bout performed in a caloric deficit. Add at least {PROTEIN_FLOOR - p:.0f} g more."))
    elif p <= PROTEIN_CEIL:
        checks.append(("success",
            f"RULE C · PROTEIN PROTECTION — PASSED: {p:.0f} g of lean protein shields muscle "
            f"tissue through the deficit-state session."))
    else:
        checks.append(("info",
            f"RULE C · PROTEIN PROTECTION — PASSED (HIGH): {p:.0f} g exceeds the "
            f"{PROTEIN_CEIL:.0f} g band. Anti-catabolic coverage is total, though digestion rate "
            f"slows marginally above this range."))
    return checks


def style_fig(fig, height=340):
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


def build_chart_df() -> pd.DataFrame:
    df = st.session_state.daily_df.copy()
    if df.empty:
        return df
    df["date_dt"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date_dt"]).sort_values("date_dt").reset_index(drop=True)
    for col in DAILY_NUM_COLS:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    for col in DAILY_BOOL_COLS:
        df[col + "_b"] = df[col].map(to_bool)
    df["adherence_calc"] = df[[c + "_b" for c in DAILY_BOOL_COLS]].mean(axis=1) * 100.0
    return df


def normalize_daily_import(raw: pd.DataFrame) -> pd.DataFrame:
    df = raw.copy()
    df.columns = [str(c).strip() for c in df.columns]
    for col in DAILY_COLUMNS:
        if col not in df.columns:
            df[col] = pd.NA
    df = df[DAILY_COLUMNS]
    parsed = pd.to_datetime(df["date"], errors="coerce")
    df = df[parsed.notna()].copy()
    df["date"] = parsed[parsed.notna()].dt.date.astype(str)
    for col in DAILY_NUM_COLS:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    for col in DAILY_BOOL_COLS:
        df[col] = df[col].map(lambda v: to_bool(v) if not pd.isna(v) else pd.NA)
    return df.reset_index(drop=True)


def normalize_meal_import(raw: pd.DataFrame) -> pd.DataFrame:
    df = raw.copy()
    df.columns = [str(c).strip() for c in df.columns]
    for col in MEAL_COLUMNS:
        if col not in df.columns:
            df[col] = pd.NA
    df = df[MEAL_COLUMNS]
    parsed = pd.to_datetime(df["date"], errors="coerce")
    df = df[parsed.notna()].copy()
    df["date"] = parsed[parsed.notna()].dt.date.astype(str)
    for col in MEAL_NUM_COLS:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)
    df["preworkout"] = df["preworkout"].map(to_bool)
    df["restaurant"] = df["restaurant"].fillna("Unknown").astype(str)
    df["item"] = df["item"].fillna("Unknown item").astype(str)
    return df.reset_index(drop=True)


# ------------------------------------------------------------------------------
# SIDEBAR — BRANDING, PROFILE, ENTRY DATE, TARGETS, BASELINES
# ------------------------------------------------------------------------------

with st.sidebar:
    st.markdown(
        """
        <div style="padding:4px 0 8px 0;">
            <h2 style="margin:0;">🏀 APEX ENGINE</h2>
            <p style="color:#7E8FAD;font-size:.72rem;letter-spacing:.12em;margin:2px 0 0 0;">
                HUMAN OPTIMIZATION SYSTEM
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        f"""
        <div class="apex-card">
            <span class="apex-pill" style="background:rgba(0,229,160,.12);color:#00E5A0;border:1px solid #00E5A0;">ATHLETE PROFILE</span>
            <p style="margin:10px 0 0 0;font-size:.84rem;line-height:1.65;color:#C9D2E3;">
                <b style="color:#F2F5FA;">{PROFILE['role']}</b><br>
                Height {PROFILE['height']} · {PROFILE['current_weight']:.0f} lbs current<br>
                Prime zone: <b style="color:#00E5A0;">{PROFILE['target_low']:.0f}–{PROFILE['target_high']:.0f} lbs</b><br>
                {PROFILE['split']}<br>
                Feed {PROFILE['meal_time']} → Train {PROFILE['train_time']}
                ({PROFILE['window_min']}-min window)
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    sel_date = st.date_input("📅 Entry Date", value=date.today())
    d_iso = sel_date.isoformat()

    st.markdown("#### 🎯 Daily Macro Targets")
    st.number_input("Calories (kcal)", min_value=1200, max_value=6000, step=50, key="t_cal")
    tc1, tc2, tc3 = st.columns(3)
    tc1.number_input("Protein (g)", min_value=50, max_value=400, step=5, key="t_pro")
    tc2.number_input("Carbs (g)", min_value=50, max_value=600, step=5, key="t_carb")
    tc3.number_input("Fat (g)", min_value=20, max_value=250, step=5, key="t_fat")

    st.markdown("#### ❤️ Recovery Baseline")
    st.number_input("Baseline Resting HR (bpm)", min_value=35, max_value=100, step=1, key="baseline_rhr")

    snapshot = build_chart_df()
    if not snapshot.empty:
        st.markdown("#### ⚡ Latest Snapshot")
        s1, s2 = st.columns(2)
        last_cns = snapshot["cns_score"].dropna()
        last_wt = snapshot["body_weight_lbs"].dropna()
        s1.metric("CNS Score", f"{last_cns.iloc[-1]:.0f}%" if not last_cns.empty else "—")
        s2.metric("Body Wt", f"{last_wt.iloc[-1]:.1f} lb" if not last_wt.empty else "—")

# ------------------------------------------------------------------------------
# MAIN HEADER + TABS
# ------------------------------------------------------------------------------

st.markdown(
    f"""
    <div style="padding:2px 0 4px 0;">
        <h1 style="margin-bottom:0;">🏀 APEX ENGINE</h1>
        <p style="color:#8FA1BF;letter-spacing:.13em;font-size:.78rem;margin-top:2px;">
            ATHLETIC PERFORMANCE & BIOMETRIC DASHBOARD · {PROFILE['role'].upper()} BUILD ·
            ENTRY DATE: {d_iso}
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

tab_fuel, tab_cns, tab_opt, tab_data = st.tabs([
    "🍔 Nutrition Engine",
    "⚡ CNS Readiness",
    "📊 Optimization Correlator",
    "💾 Data Management",
])

# ==============================================================================
# MODULE 1 — FAST-FOOD MACRO & NUTRIENT TIMING ENGINE
# ==============================================================================

with tab_fuel:
    st.subheader("Fast-Food Macro & Nutrient Timing Engine")
    st.caption(
        "Log meals from the hardcoded restaurant database, track Consumed vs. Remaining "
        "against your daily targets, and validate the critical 6:00 PM pre-workout feeding window."
    )

    col_logger, col_budget = st.columns([6, 5], gap="large")

    with col_logger:
        st.markdown("##### 🧾 Fuel Logger")
        restaurant = st.selectbox(
            "Establishment", list(FOOD_DB.keys()) + [CUSTOM_LABEL], key="rest_sel"
        )

        if restaurant == CUSTOM_LABEL:
            item_label = st.text_input("Food name", value="Custom meal", key="cust_name")
            cc1, cc2, cc3 = st.columns(3)
            cust_cal = cc1.number_input("Calories", 0.0, 3000.0, 500.0, 10.0, key="cust_cal")
            cust_p = cc2.number_input("Protein (g)", 0.0, 250.0, 35.0, 1.0, key="cust_p")
            cust_c = cc3.number_input("Carbs (g)", 0.0, 400.0, 50.0, 1.0, key="cust_c")
            cc4, cc5 = st.columns(2)
            cust_f = cc4.number_input("Fat (g)", 0.0, 200.0, 12.0, 1.0, key="cust_f")
            cust_fib = cc5.number_input("Fiber (g)", 0.0, 60.0, 3.0, 1.0, key="cust_fib")
            portion = 1.0
            base = {"cal": cust_cal, "p": cust_p, "c": cust_c, "f": cust_f, "fib": cust_fib}
        else:
            item_label = st.selectbox(
                "Menu item", list(FOOD_DB[restaurant].keys()), key=f"item_{restaurant}"
            )
            portion = st.slider(
                "Serving weight multiplier (e.g., double meat = 2.0×)",
                0.25, 3.0, 1.0, 0.25, key="portion_mult",
            )
            base = FOOD_DB[restaurant][item_label]

        scaled = {k: float(base[k]) * portion for k in ("cal", "p", "c", "f", "fib")}

        pv1, pv2, pv3, pv4, pv5 = st.columns(5)
        pv1.metric("kcal", f"{scaled['cal']:.0f}")
        pv2.metric("Protein", f"{scaled['p']:.0f} g")
        pv3.metric("Carbs", f"{scaled['c']:.0f} g")
        pv4.metric("Fat", f"{scaled['f']:.0f} g")
        pv5.metric("Fiber", f"{scaled['fib']:.0f} g")

        pw_flag = st.toggle(
            "⏱️ Count toward the 6:00 PM pre-workout meal", value=False, key="pw_flag"
        )

        if st.button("➕ Add to Daily Log", use_container_width=True, type="primary"):
            new_meal = {
                "date": d_iso,
                "restaurant": restaurant,
                "item": str(item_label) if item_label else "Custom meal",
                "portion": portion,
                "calories": scaled["cal"],
                "protein_g": scaled["p"],
                "carbs_g": scaled["c"],
                "fat_g": scaled["f"],
                "fiber_g": scaled["fib"],
                "preworkout": bool(pw_flag),
            }
            meal_addition = pd.DataFrame([new_meal])
            if st.session_state.meal_log.empty:
                st.session_state.meal_log = meal_addition
            else:
                st.session_state.meal_log = pd.concat(
                    [st.session_state.meal_log, meal_addition], ignore_index=True
                )
            st.toast(f"Logged: {new_meal['item']} ({scaled['cal']:.0f} kcal)", icon="✅")
            st.rerun()

        day_meals = day_meal_slice(d_iso)
        st.markdown(f"##### 📋 Logged on {d_iso}")
        if day_meals.empty:
            st.info("No meals logged for this date yet. Add items above to start tracking.")
        else:
            display = day_meals[[
                "restaurant", "item", "portion", "calories",
                "protein_g", "carbs_g", "fat_g", "fiber_g", "preworkout",
            ]].copy()
            for ncol in ["portion", "calories", "protein_g", "carbs_g", "fat_g", "fiber_g"]:
                display[ncol] = pd.to_numeric(display[ncol], errors="coerce").round(1)
            display["preworkout"] = display["preworkout"].map(to_bool)
            display = display.rename(columns={
                "restaurant": "Spot", "item": "Item", "portion": "Servings",
                "calories": "kcal", "protein_g": "P (g)", "carbs_g": "C (g)",
                "fat_g": "F (g)", "fiber_g": "Fiber (g)", "preworkout": "6PM Meal",
            })
            st.dataframe(display, use_container_width=True, hide_index=True)

            remove_options = {
                f"{row['item']} · {pd.to_numeric(pd.Series([row['calories']]), errors='coerce').fillna(0).iloc[0]:.0f} kcal (entry #{idx})": idx
                for idx, row in day_meals.iterrows()
            }
            rm1, rm2 = st.columns([7, 3])
            pick = rm1.selectbox("Remove an entry", list(remove_options.keys()), key="rm_pick")
            if rm2.button("🗑️ Remove", use_container_width=True):
                st.session_state.meal_log = (
                    st.session_state.meal_log.drop(remove_options[pick]).reset_index(drop=True)
                )
                st.rerun()

    with col_budget:
        st.markdown("##### 📊 Consumed vs. Remaining")
        totals = macro_totals(day_meals)
        targets = [
            ("Calories", "calories", float(st.session_state.t_cal), "kcal"),
            ("Protein", "protein_g", float(st.session_state.t_pro), "g"),
            ("Carbohydrate", "carbs_g", float(st.session_state.t_carb), "g"),
            ("Fat", "fat_g", float(st.session_state.t_fat), "g"),
        ]
        for label, key, target, unit in targets:
            consumed = totals[key]
            remaining = target - consumed
            pct = min(consumed / max(target, 1.0), 1.0)
            st.progress(
                pct,
                text=f"{label}: {consumed:,.0f} / {target:,.0f} {unit} consumed · "
                     f"{max(remaining, 0):,.0f} {unit} remaining",
            )
            if remaining < 0:
                st.caption(f"🔺 Over {label.lower()} budget by {abs(remaining):,.0f} {unit}.")
        st.caption(f"Total fiber consumed today: {totals['fiber_g']:.0f} g")

        st.markdown(
            f"""
            <div class="apex-card">
                <span class="apex-pill" style="background:rgba(0,180,216,.12);color:#00B4D8;border:1px solid #00B4D8;">CUT PROTOCOL</span>
                <p style="margin:8px 0 0 0;font-size:.82rem;line-height:1.6;color:#C9D2E3;">
                    Driving from <b style="color:#F2F5FA;">167 lbs</b> to the
                    <b style="color:#00E5A0;">145–155 lb</b> prime basketball zone.
                    Protect protein, time carbohydrate around the 7:30 PM session, and let the
                    deficit come from fat. Intermittent-fasting feed window opens with the
                    6:00 PM pre-workout meal.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.divider()
    st.subheader("⏱️ 6:00 PM Pre-Workout Optimization Window")
    st.caption(
        "Strict 90-minute metabolic window: meal at 6:00 PM → first jump at 7:30 PM. "
        "Items toggled as pre-workout in the Fuel Logger are validated below against Rules A, B, and C."
    )

    if day_meals.empty:
        pw_meals = day_meals
    else:
        pw_meals = day_meals[day_meals["preworkout"].map(to_bool)]

    if pw_meals.empty:
        st.info(
            "No items flagged for the 6:00 PM meal yet. Flip the '⏱️ Count toward the 6:00 PM "
            "pre-workout meal' toggle when logging items to run the optimization validator."
        )
    else:
        pw = macro_totals(pw_meals)
        m1, m2, m3, m4, m5 = st.columns(5)
        m1.metric("Meal kcal", f"{pw['calories']:.0f}")
        m2.metric("Protein", f"{pw['protein_g']:.0f} g")
        m3.metric("Carbs", f"{pw['carbs_g']:.0f} g")
        m4.metric("Fat", f"{pw['fat_g']:.0f} g")
        m5.metric("Fiber", f"{pw['fiber_g']:.0f} g")

        checks = validate_preworkout(pw["protein_g"], pw["carbs_g"], pw["fat_g"], pw["fiber_g"])
        severities = [s for s, _ in checks]

        if "error" in severities:
            st.error(
                "⛔ VERDICT: REBUILD THIS MEAL — one or more hard requirements failed. "
                "Fix the items below before 6:00 PM or the 7:30 PM session will be under-fueled."
            )
        elif "warning" in severities:
            st.warning(
                "🟠 VERDICT: USABLE WITH ADJUSTMENTS — macros clear the floors, but the "
                "fat/fiber bottleneck will compromise gastric emptying inside the 90-minute window."
            )
        else:
            st.success(
                "✅ VERDICT: MEAL CLEARED — optimal glycogen saturation, clean gastric emptying, "
                "and full anti-catabolic protein coverage for the 7:30 PM session."
            )

        for severity, msg in checks:
            if severity == "success":
                st.success(msg)
            elif severity == "warning":
                st.warning(msg)
            elif severity == "error":
                st.error(msg)
            else:
                st.info(msg)

# ==============================================================================
# MODULE 2 — CNS READINESS SCORE TRACKER
# ==============================================================================

with tab_cns:
    st.subheader("Central Nervous System Readiness Tracker")
    st.caption(
        "High-velocity plyometrics load tendons and the CNS hard. Enter the three morning "
        "biomarkers — the algorithm weights sleep 40%, soreness 30%, and RHR deviation 30% — "
        "to gate today's plyometric volume and protect against overtraining and jumper's knee."
    )

    existing = get_daily_row(d_iso)
    col_form, col_result = st.columns([5, 7], gap="large")

    with col_form:
        with st.form("cns_form"):
            st.markdown("##### 🌅 Morning Entry")
            in_sleep = st.slider(
                "Sleep Duration & Quality (1 = terrible · 10 = elite)",
                1, 10, int(float(gv(existing, "sleep_quality", 7))),
                help="Weighted at 40% of the total CNS Readiness Score.",
            )
            in_sore = st.slider(
                "Muscle/Tendon Soreness (1 = fresh · 10 = severe fatigue/pain)",
                1, 10, int(float(gv(existing, "soreness", 3))),
                help="Weighted at 30% of the total CNS Readiness Score.",
            )
            in_rhr = st.number_input(
                "Morning Resting Heart Rate (bpm)",
                min_value=35, max_value=120,
                value=int(float(gv(existing, "resting_hr", st.session_state.baseline_rhr))),
                step=1,
                help=(
                    "Weighted at 30%, scored on deviation from your baseline RHR "
                    f"(currently {st.session_state.baseline_rhr} bpm — set in the sidebar). "
                    "Each bpm above baseline costs 3 points of the RHR component."
                ),
            )
            submitted = st.form_submit_button(
                "⚡ Calculate & Save CNS Readiness", use_container_width=True, type="primary"
            )

        if submitted:
            score = calc_cns(in_sleep, in_sore, in_rhr, float(st.session_state.baseline_rhr))
            upsert_daily(d_iso, {
                "sleep_quality": float(in_sleep),
                "soreness": float(in_sore),
                "resting_hr": float(in_rhr),
                "cns_score": score,
                "cns_flag": cns_flag_label(score),
            })
            st.toast(f"CNS Readiness saved: {score:.0f}%", icon="⚡")
            st.rerun()

    with col_result:
        row = get_daily_row(d_iso)
        saved_score = gv(row, "cns_score", None)
        if saved_score is None:
            st.info(
                "Submit this morning's biomarkers to generate today's CNS Readiness Score "
                "and training clearance flag."
            )
        else:
            score = float(saved_score)
            if score >= 80:
                bar_color = "#00E5A0"
            elif score >= 50:
                bar_color = "#FAAD14"
            else:
                bar_color = "#FF4D4F"

            gauge = go.Figure(go.Indicator(
                mode="gauge+number",
                value=score,
                number={"suffix": "%", "font": {"color": "#F2F5FA", "size": 44}},
                title={"text": f"CNS READINESS · {d_iso}", "font": {"color": "#8FA1BF", "size": 13}},
                gauge={
                    "axis": {"range": [0, 100], "tickcolor": "#5A6B8C"},
                    "bar": {"color": bar_color, "thickness": 0.32},
                    "bgcolor": "rgba(0,0,0,0)",
                    "borderwidth": 0,
                    "steps": [
                        {"range": [0, 50], "color": "rgba(255,77,79,0.18)"},
                        {"range": [50, 80], "color": "rgba(250,173,20,0.18)"},
                        {"range": [80, 100], "color": "rgba(0,229,160,0.18)"},
                    ],
                },
            ))
            gauge.update_layout(
                height=250, margin=dict(t=44, b=6, l=36, r=36),
                paper_bgcolor="rgba(0,0,0,0)", font={"color": "#E6E9F0"},
            )
            st.plotly_chart(gauge, use_container_width=True)
            render_cns_banner(score)

            sl = float(gv(row, "sleep_quality", 7))
            so = float(gv(row, "soreness", 3))
            hr = float(gv(row, "resting_hr", st.session_state.baseline_rhr))
            pts_sleep, pts_sore, pts_rhr = cns_components(
                sl, so, hr, float(st.session_state.baseline_rhr)
            )
            b1, b2, b3 = st.columns(3)
            b1.metric("Sleep (40%)", f"{pts_sleep:.1f} / 40", f"rated {sl:.0f}/10", delta_color="off")
            b2.metric("Soreness (30%)", f"{pts_sore:.1f} / 30", f"rated {so:.0f}/10", delta_color="off")
            b3.metric(
                "RHR (30%)", f"{pts_rhr:.1f} / 30",
                f"{hr:.0f} bpm vs {st.session_state.baseline_rhr} base", delta_color="off",
            )

    st.divider()
    st.markdown("##### 📈 CNS Readiness History")
    hist = build_chart_df()
    hist = hist.dropna(subset=["cns_score"]) if not hist.empty else hist
    if hist.empty:
        st.info("Save at least one morning entry to build the readiness trendline.")
    else:
        fig_cns = px.line(
            hist, x="date_dt", y="cns_score", markers=True,
            labels={"date_dt": "Date", "cns_score": "CNS Score (%)"},
        )
        fig_cns.update_traces(line_color="#00E5A0", marker=dict(size=9, color="#00B4D8"))
        fig_cns.add_hrect(y0=0, y1=50, fillcolor="#FF4D4F", opacity=0.08, line_width=0)
        fig_cns.add_hrect(y0=50, y1=80, fillcolor="#FAAD14", opacity=0.08, line_width=0)
        fig_cns.add_hrect(y0=80, y1=100, fillcolor="#00E5A0", opacity=0.08, line_width=0)
        fig_cns.update_yaxes(range=[0, 105], title="CNS Score (%)")
        st.plotly_chart(style_fig(fig_cns, 330), use_container_width=True)

# ==============================================================================
# MODULE 3 — HUMAN OPTIMIZATION & PROTOCOL CORRELATOR
# ==============================================================================

with tab_opt:
    st.subheader("Human Optimization & Protocol Correlator")
    st.caption(
        "Track daily protocol adherence, log athletic output, and let the correlation engine "
        "map which habits actually move vertical jump elasticity and body weight."
    )

    row = get_daily_row(d_iso)

    st.markdown("##### ✅ Daily Protocol Stack")
    pc1, pc2, pc3 = st.columns(3)
    with pc1:
        in_sun = st.toggle(
            "☀️ Morning Sunlight Exposure",
            value=to_bool(gv(row, "sunlight", False)), key="tg_sun",
        )
        st.caption("Circadian clock alignment & cortisol optimization.")
    with pc2:
        in_pep = st.toggle(
            "🧬 Peptide Protocol Adherence",
            value=to_bool(gv(row, "peptides", False)), key="tg_pep",
        )
        st.caption("Tissue recovery and cellular repair support.")
    with pc3:
        in_skin = st.toggle(
            "🧴 Skincare Regimen Adherence",
            value=to_bool(gv(row, "skincare", False)), key="tg_skin",
        )
        st.caption("Daily application consistency: Tretinoin + Minoxidil.")

    st.markdown("##### 🏋️ Athletic Performance Logger")
    chart_now = build_chart_df()
    last_known_wt = PROFILE["current_weight"]
    if not chart_now.empty:
        wt_series = chart_now["body_weight_lbs"].dropna()
        if not wt_series.empty:
            last_known_wt = float(wt_series.iloc[-1])

    lc1, lc2, lc3 = st.columns(3)
    in_bw = lc1.number_input(
        "Body Weight (lbs)", min_value=100.0, max_value=250.0,
        value=float(gv(row, "body_weight_lbs", last_known_wt)), step=0.2,
    )
    in_vje = lc2.slider(
        "Perceived Vertical Jump Elasticity (1–10)",
        1, 10, int(float(gv(row, "vertical_elasticity", 5))),
        help="How springy and reactive the legs feel — the rim-snapping rating.",
    )
    in_bbs = lc3.slider(
        "Max Barbell Strength / Output (1–10)",
        1, 10, int(float(gv(row, "barbell_output", 5))),
        help="Bar speed and strength output across the 4-day upper/lower split.",
    )

    if st.button("💾 Save Protocols & Performance", type="primary", use_container_width=True):
        adherence = (int(in_sun) + int(in_pep) + int(in_skin)) / 3.0 * 100.0
        upsert_daily(d_iso, {
            "sunlight": bool(in_sun),
            "peptides": bool(in_pep),
            "skincare": bool(in_skin),
            "body_weight_lbs": float(in_bw),
            "vertical_elasticity": float(in_vje),
            "barbell_output": float(in_bbs),
            "adherence_pct": round(adherence, 1),
        })
        st.toast(f"Saved {d_iso}: adherence {adherence:.0f}%", icon="💾")
        st.rerun()

    st.divider()
    st.subheader("📈 Data Visualization & Correlation Matrix")

    cdf = build_chart_df()
    if cdf.empty:
        st.info("Log at least one day of protocols and performance to unlock the correlation engine.")
    else:
        g1, g2 = st.columns(2, gap="medium")

        with g1:
            wdf = cdf.dropna(subset=["body_weight_lbs"])
            if wdf.empty:
                st.info("No body-weight entries yet.")
            else:
                fig_wt = px.line(
                    wdf, x="date_dt", y="body_weight_lbs", markers=True,
                    title="Body Weight vs. Prime Basketball Zone",
                    labels={"date_dt": "Date", "body_weight_lbs": "lbs"},
                )
                fig_wt.update_traces(line_color="#00B4D8", marker=dict(size=9))
                fig_wt.add_hrect(
                    y0=PROFILE["target_low"], y1=PROFILE["target_high"],
                    fillcolor="#00E5A0", opacity=0.12, line_width=0,
                    annotation_text="PRIME ZONE 145–155", annotation_font_color="#00E5A0",
                )
                st.plotly_chart(style_fig(fig_wt), use_container_width=True)

        with g2:
            pdf = cdf.dropna(subset=["vertical_elasticity", "barbell_output"], how="all")
            if pdf.empty:
                st.info("No performance ratings yet.")
            else:
                melted = pdf.melt(
                    id_vars="date_dt",
                    value_vars=["vertical_elasticity", "barbell_output"],
                    var_name="Metric", value_name="Rating",
                ).dropna(subset=["Rating"])
                melted["Metric"] = melted["Metric"].map({
                    "vertical_elasticity": "Vertical Jump Elasticity",
                    "barbell_output": "Barbell Strength Output",
                })
                fig_perf = px.line(
                    melted, x="date_dt", y="Rating", color="Metric", markers=True,
                    title="Explosive Output Ratings Over Time",
                    color_discrete_map={
                        "Vertical Jump Elasticity": "#00E5A0",
                        "Barbell Strength Output": "#B388FF",
                    },
                )
                fig_perf.update_yaxes(range=[0, 10.5])
                st.plotly_chart(style_fig(fig_perf), use_container_width=True)

        g3, g4 = st.columns(2, gap="medium")

        with g3:
            fig_adh = px.bar(
                cdf, x="date_dt", y="adherence_calc",
                title="Daily Protocol Adherence (%)",
                labels={"date_dt": "Date", "adherence_calc": "Adherence %"},
            )
            fig_adh.update_traces(marker_color="#00B4D8", marker_line_width=0)
            fig_adh.update_yaxes(range=[0, 105])
            st.plotly_chart(style_fig(fig_adh), use_container_width=True)

        with g4:
            sdf = cdf.dropna(subset=["vertical_elasticity"])
            if len(sdf) < 2:
                st.info("Need 2+ days with jump-elasticity ratings for the adherence scatter.")
            else:
                fig_sc1 = px.scatter(
                    sdf, x="adherence_calc", y="vertical_elasticity",
                    color="cns_score", size_max=16,
                    title="Protocol Adherence → Vertical Jump Elasticity",
                    labels={
                        "adherence_calc": "Adherence %",
                        "vertical_elasticity": "Jump Elasticity (1–10)",
                        "cns_score": "CNS %",
                    },
                    color_continuous_scale=["#FF4D4F", "#FAAD14", "#00E5A0"],
                    hover_data={"date": True},
                )
                fig_sc1.update_traces(marker=dict(size=13, line=dict(width=1, color="#0B0F19")))
                fig_sc1.update_yaxes(range=[0, 10.5])
                st.plotly_chart(style_fig(fig_sc1), use_container_width=True)

        g5, g6 = st.columns(2, gap="medium")

        with g5:
            swf = cdf.dropna(subset=["body_weight_lbs"])
            if len(swf) < 2:
                st.info("Need 2+ days with body-weight entries for the adherence scatter.")
            else:
                swf = swf.assign(
                    Peptides=swf["peptides_b"].map({True: "Peptides ✓", False: "Peptides ✗"})
                )
                fig_sc2 = px.scatter(
                    swf, x="adherence_calc", y="body_weight_lbs", color="Peptides",
                    title="Protocol Adherence → Body Weight",
                    labels={"adherence_calc": "Adherence %", "body_weight_lbs": "Body Weight (lbs)"},
                    color_discrete_map={"Peptides ✓": "#00E5A0", "Peptides ✗": "#5A6B8C"},
                    hover_data={"date": True},
                )
                fig_sc2.update_traces(marker=dict(size=13, line=dict(width=1, color="#0B0F19")))
                st.plotly_chart(style_fig(fig_sc2), use_container_width=True)

        with g6:
            corr_cols = {
                "adherence_calc": "Adherence %",
                "sleep_quality": "Sleep",
                "soreness": "Soreness",
                "resting_hr": "RHR",
                "cns_score": "CNS Score",
                "body_weight_lbs": "Body Wt",
                "vertical_elasticity": "Vert Elasticity",
                "barbell_output": "Barbell Output",
            }
            sub = cdf[list(corr_cols.keys())].rename(columns=corr_cols)
            sub = sub.apply(pd.to_numeric, errors="coerce")
            if len(sub.dropna(how="all")) < 3:
                st.info("Need 3+ logged days to compute the correlation matrix.")
            else:
                corr = sub.corr().fillna(0).round(2)
                fig_corr = px.imshow(
                    corr, text_auto=True, aspect="auto",
                    zmin=-1, zmax=1,
                    color_continuous_scale=["#FF4D4F", "#0B0F19", "#00E5A0"],
                    title="Protocol ↔ Performance Correlation Matrix",
                )
                st.plotly_chart(style_fig(fig_corr, 380), use_container_width=True)
                st.caption(
                    "Pearson r across all logged days: +1.0 = moves together, "
                    "−1.0 = moves opposite. Pairs with insufficient overlap display 0."
                )

# ==============================================================================
# DATA MANAGEMENT — CSV EXPORT / IMPORT (NO-DATABASE PERSISTENCE)
# ==============================================================================

with tab_data:
    st.subheader("Data Management")
    st.caption(
        "Streamlit Community Cloud containers reset on sleep — your session data lives in memory. "
        "Export CSVs after logging (they download straight to your phone or computer), then "
        "re-upload them next session to fully restore your history."
    )

    cnt1, cnt2 = st.columns(2)
    cnt1.metric("Biometric days logged", f"{len(st.session_state.daily_df)}")
    cnt2.metric("Meal entries logged", f"{len(st.session_state.meal_log)}")

    col_exp, col_imp = st.columns(2, gap="large")

    with col_exp:
        st.markdown("##### ⬇️ Export / Download Biometric Data")
        daily_csv = st.session_state.daily_df.to_csv(index=False).encode("utf-8")
        st.download_button(
            "⬇️ Export / Download Biometric Data",
            data=daily_csv,
            file_name=f"apex_biometric_data_{date.today().isoformat()}.csv",
            mime="text/csv",
            use_container_width=True,
            type="primary",
            disabled=st.session_state.daily_df.empty,
        )
        meal_csv = st.session_state.meal_log.to_csv(index=False).encode("utf-8")
        st.download_button(
            "⬇️ Export / Download Nutrition Log",
            data=meal_csv,
            file_name=f"apex_nutrition_log_{date.today().isoformat()}.csv",
            mime="text/csv",
            use_container_width=True,
            disabled=st.session_state.meal_log.empty,
        )
        st.caption("Tip: export at the end of every logging session — it takes two taps.")

    with col_imp:
        st.markdown("##### ⬆️ Import / Upload Historical Data")
        restore_mode = st.radio(
            "Restore mode",
            ["Merge with current session", "Replace current session"],
            horizontal=True,
            key="restore_mode",
        )

        up_bio = st.file_uploader(
            "Upload biometric data CSV", type=["csv"], key="up_bio"
        )
        if up_bio is not None:
            if st.button("♻️ Restore Biometric Data", use_container_width=True, key="btn_bio"):
                try:
                    incoming = normalize_daily_import(pd.read_csv(up_bio))
                    if incoming.empty:
                        st.error("No valid rows found — check that the file has a 'date' column.")
                    else:
                        if restore_mode.startswith("Merge"):
                            merged = pd.concat(
                                [st.session_state.daily_df, incoming], ignore_index=True
                            )
                        else:
                            merged = incoming
                        merged = (
                            merged.drop_duplicates(subset="date", keep="last")
                            .sort_values("date")
                            .reset_index(drop=True)
                        )
                        st.session_state.daily_df = merged[DAILY_COLUMNS]
                        st.toast(f"Restored {len(incoming)} biometric rows.", icon="♻️")
                        st.rerun()
                except Exception as exc:
                    st.error(f"Could not parse that file as biometric data: {exc}")

        up_meal = st.file_uploader(
            "Upload nutrition log CSV", type=["csv"], key="up_meal"
        )
        if up_meal is not None:
            if st.button("♻️ Restore Nutrition Log", use_container_width=True, key="btn_meal"):
                try:
                    incoming = normalize_meal_import(pd.read_csv(up_meal))
                    if incoming.empty:
                        st.error("No valid rows found — check that the file has a 'date' column.")
                    else:
                        if restore_mode.startswith("Merge"):
                            merged = pd.concat(
                                [st.session_state.meal_log, incoming], ignore_index=True
                            ).drop_duplicates().reset_index(drop=True)
                        else:
                            merged = incoming
                        st.session_state.meal_log = merged[MEAL_COLUMNS]
                        st.toast(f"Restored {len(incoming)} meal entries.", icon="♻️")
                        st.rerun()
                except Exception as exc:
                    st.error(f"Could not parse that file as a nutrition log: {exc}")

    st.divider()
    with st.expander("🔍 Preview current biometric dataset"):
        if st.session_state.daily_df.empty:
            st.info("No biometric rows yet.")
        else:
            st.dataframe(
                st.session_state.daily_df.sort_values("date", ascending=False),
                use_container_width=True, hide_index=True,
            )
    with st.expander("🔍 Preview current nutrition log"):
        if st.session_state.meal_log.empty:
            st.info("No meal entries yet.")
        else:
            st.dataframe(
                st.session_state.meal_log.sort_values("date", ascending=False),
                use_container_width=True, hide_index=True,
            )
    with st.expander("🧨 Danger Zone — wipe session data"):
        confirm = st.checkbox(
            "I understand this permanently clears ALL data in the current session "
            "(exported CSV files are unaffected)."
        )
        if st.button("Clear All Session Data", disabled=not confirm):
            st.session_state.daily_df = pd.DataFrame(columns=DAILY_COLUMNS)
            st.session_state.meal_log = pd.DataFrame(columns=MEAL_COLUMNS)
            st.rerun()

st.markdown(
    """
    <p style="text-align:center;color:#42506B;font-size:.72rem;letter-spacing:.1em;margin-top:28px;">
        APEX ENGINE v1.0 · FEED 6:00 PM → TRAIN 7:30 PM · BUILT FOR THE RIM
    </p>
    """,
    unsafe_allow_html=True,
)
