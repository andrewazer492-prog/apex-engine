# ==============================================================================
# APEX HUMAN PERFORMANCE & BIOMETRIC OPERATING SYSTEM — V3.0 ENTERPRISE
# pages/1_Metabolic_Engine.py
# ------------------------------------------------------------------------------
# Component-level macro tracker · 7-restaurant enterprise database ·
# custom food creator · 6:00 PM pre-workout kinetic evaluator (GERC).
# ==============================================================================

from datetime import date, datetime

import pandas as pd
import plotly.express as px
import streamlit as st

from state_manager import (
    ATHLETE_PROFILE,
    append_row,
    apply_theme,
    compute_gerc,
    get_df,
    init_global_state,
    num_or,
    render_sidebar_profile,
    set_df,
    style_fig,
    to_bool,
)

st.set_page_config(
    page_title="APEX OS | Metabolic Engine",
    page_icon="🍽️",
    layout="wide",
    initial_sidebar_state="expanded",
)

init_global_state()
apply_theme()

# ------------------------------------------------------------------------------
# ENTERPRISE RESTAURANT DATABASE — component-level macros per standard serving.
# Each entry: {cal, p, c, f, fib} = calories, protein, carbs, fat, fiber (grams).
# Values sourced from published restaurant nutrition data; edit freely here.
# ------------------------------------------------------------------------------

FOOD_DB = {
    "Chipotle": {
        "White Rice (4 oz)":                 {"cal": 210, "p": 4.0,  "c": 40.0, "f": 4.0,  "fib": 1.0},
        "Brown Rice (4 oz)":                 {"cal": 210, "p": 4.0,  "c": 36.0, "f": 6.0,  "fib": 2.0},
        "Black Beans (4 oz)":                {"cal": 130, "p": 8.0,  "c": 22.0, "f": 1.5,  "fib": 7.0},
        "Pinto Beans (4 oz)":                {"cal": 130, "p": 8.0,  "c": 21.0, "f": 1.5,  "fib": 8.0},
        "Chicken (4 oz)":                    {"cal": 180, "p": 32.0, "c": 0.0,  "f": 7.0,  "fib": 0.0},
        "Steak (4 oz)":                      {"cal": 150, "p": 21.0, "c": 1.0,  "f": 6.0,  "fib": 0.0},
        "Barbacoa (4 oz)":                   {"cal": 170, "p": 24.0, "c": 2.0,  "f": 7.0,  "fib": 1.0},
        "Carnitas (4 oz)":                   {"cal": 210, "p": 23.0, "c": 0.0,  "f": 12.0, "fib": 0.0},
        "Fajita Veggies (2.5 oz)":           {"cal": 20,  "p": 1.0,  "c": 5.0,  "f": 0.0,  "fib": 1.0},
        "Fresh Tomato Salsa (3.5 oz)":       {"cal": 25,  "p": 0.0,  "c": 5.0,  "f": 0.0,  "fib": 1.0},
        "Tomatillo-Green Chili Salsa (2 oz)":{"cal": 15,  "p": 1.0,  "c": 4.0,  "f": 0.0,  "fib": 1.0},
        "Tomatillo-Red Chili Salsa (2 oz)":  {"cal": 30,  "p": 1.0,  "c": 4.0,  "f": 1.0,  "fib": 1.0},
        "Sour Cream (2 oz)":                 {"cal": 110, "p": 2.0,  "c": 2.0,  "f": 9.0,  "fib": 0.0},
        "Cheese (1 oz)":                     {"cal": 110, "p": 6.0,  "c": 1.0,  "f": 8.0,  "fib": 0.0},
        "Guacamole (4 oz)":                  {"cal": 230, "p": 2.0,  "c": 8.0,  "f": 22.0, "fib": 6.0},
        "Romaine Lettuce (1 oz)":            {"cal": 5,   "p": 0.0,  "c": 1.0,  "f": 0.0,  "fib": 1.0},
    },
    "Chick-fil-A": {
        "Grilled Nuggets (8-ct)":            {"cal": 130, "p": 25.0, "c": 1.0,  "f": 3.0,  "fib": 0.0},
        "Grilled Nuggets (12-ct)":           {"cal": 200, "p": 38.0, "c": 2.0,  "f": 4.5,  "fib": 0.0},
        "Regular Nuggets (8-ct)":            {"cal": 250, "p": 27.0, "c": 11.0, "f": 11.0, "fib": 0.0},
        "Regular Nuggets (12-ct)":           {"cal": 380, "p": 40.0, "c": 16.0, "f": 17.0, "fib": 1.0},
        "Grilled Chicken Sandwich":          {"cal": 390, "p": 28.0, "c": 44.0, "f": 12.0, "fib": 3.0},
        "Spicy Chicken Sandwich":            {"cal": 450, "p": 28.0, "c": 45.0, "f": 19.0, "fib": 3.0},
        "Waffle Fries (Small)":              {"cal": 320, "p": 4.0,  "c": 34.0, "f": 19.0, "fib": 4.0},
        "Waffle Fries (Medium)":             {"cal": 420, "p": 5.0,  "c": 45.0, "f": 24.0, "fib": 5.0},
        "Waffle Fries (Large)":              {"cal": 520, "p": 7.0,  "c": 57.0, "f": 29.0, "fib": 6.0},
        "Fruit Cup (Medium)":                {"cal": 60,  "p": 1.0,  "c": 15.0, "f": 0.0,  "fib": 2.0},
        "Chick-fil-A Sauce (1 packet)":      {"cal": 140, "p": 0.0,  "c": 6.0,  "f": 13.0, "fib": 0.0},
        "Polynesian Sauce (1 packet)":       {"cal": 110, "p": 0.0,  "c": 13.0, "f": 6.0,  "fib": 0.0},
        "Honey Roasted BBQ (1 packet)":      {"cal": 60,  "p": 0.0,  "c": 4.0,  "f": 5.0,  "fib": 0.0},
    },
    "Whataburger": {
        "Beef Patty (4\" / quarter-lb)":     {"cal": 230, "p": 19.0, "c": 0.0,  "f": 17.0, "fib": 0.0},
        "Beef Patty (5\" / large)":          {"cal": 310, "p": 25.0, "c": 0.0,  "f": 23.0, "fib": 0.0},
        "Brioche Bun":                       {"cal": 220, "p": 7.0,  "c": 38.0, "f": 5.0,  "fib": 1.0},
        "Texas Toast (2 slices)":            {"cal": 220, "p": 6.0,  "c": 30.0, "f": 9.0,  "fib": 1.0},
        "Sweet & Spicy Pepper Sauce (1 oz)": {"cal": 90,  "p": 0.0,  "c": 18.0, "f": 2.0,  "fib": 0.0},
        "Bacon Strip (each)":                {"cal": 45,  "p": 3.0,  "c": 0.0,  "f": 4.0,  "fib": 0.0},
        "American Cheese (slice)":           {"cal": 90,  "p": 5.0,  "c": 1.0,  "f": 7.0,  "fib": 0.0},
        "Monterey Jack Cheese (slice)":      {"cal": 100, "p": 6.0,  "c": 1.0,  "f": 8.0,  "fib": 0.0},
        "Grilled Onions (1 oz)":             {"cal": 30,  "p": 0.0,  "c": 4.0,  "f": 1.5,  "fib": 1.0},
        "French Fries (Small)":              {"cal": 270, "p": 3.0,  "c": 34.0, "f": 13.0, "fib": 3.0},
        "French Fries (Medium)":             {"cal": 410, "p": 5.0,  "c": 51.0, "f": 20.0, "fib": 4.0},
        "French Fries (Large)":              {"cal": 530, "p": 7.0,  "c": 66.0, "f": 26.0, "fib": 5.0},
    },
    "Taco Bell": {
        "Crunchy Taco":                      {"cal": 170, "p": 8.0,  "c": 13.0, "f": 10.0, "fib": 3.0},
        "Soft Taco":                         {"cal": 180, "p": 9.0,  "c": 18.0, "f": 9.0,  "fib": 3.0},
        "Chicken Quesadilla":                {"cal": 510, "p": 26.0, "c": 37.0, "f": 28.0, "fib": 4.0},
        "Cheesy Bean and Rice Burrito":      {"cal": 420, "p": 11.0, "c": 56.0, "f": 16.0, "fib": 7.0},
        "Beefy 5-Layer Burrito":             {"cal": 490, "p": 18.0, "c": 60.0, "f": 19.0, "fib": 8.0},
        "Black Beans and Rice":              {"cal": 170, "p": 5.0,  "c": 30.0, "f": 4.0,  "fib": 4.0},
    },
    "McDonald's": {
        "Quarter Pounder Beef Patty":        {"cal": 230, "p": 20.0, "c": 0.0,  "f": 16.0, "fib": 0.0},
        "McChicken Filet":                   {"cal": 350, "p": 14.0, "c": 33.0, "f": 18.0, "fib": 2.0},
        "Big Mac Sauce (1 oz)":              {"cal": 90,  "p": 0.0,  "c": 4.0,  "f": 9.0,  "fib": 0.0},
        "Artisan Roll":                      {"cal": 200, "p": 7.0,  "c": 38.0, "f": 3.0,  "fib": 2.0},
        "Large Fries":                       {"cal": 480, "p": 7.0,  "c": 66.0, "f": 22.0, "fib": 5.0},
        "Egg McMuffin":                      {"cal": 310, "p": 17.0, "c": 30.0, "f": 13.0, "fib": 2.0},
    },
    "Panda Express": {
        "Grilled Teriyaki Chicken":          {"cal": 300, "p": 36.0, "c": 8.0,  "f": 13.0, "fib": 0.0},
        "Orange Chicken":                    {"cal": 490, "p": 25.0, "c": 51.0, "f": 23.0, "fib": 2.0},
        "Beijing Beef":                      {"cal": 470, "p": 14.0, "c": 46.0, "f": 26.0, "fib": 2.0},
        "Kung Pao Chicken":                  {"cal": 290, "p": 16.0, "c": 14.0, "f": 19.0, "fib": 3.0},
        "Chow Mein":                         {"cal": 510, "p": 13.0, "c": 80.0, "f": 16.0, "fib": 6.0},
        "Fried Rice":                        {"cal": 520, "p": 11.0, "c": 85.0, "f": 16.0, "fib": 4.0},
        "Super Greens":                      {"cal": 90,  "p": 6.0,  "c": 10.0, "f": 3.0,  "fib": 4.0},
    },
    "Wingstop": {
        "Traditional Wing — Lemon Pepper (each)":   {"cal": 100, "p": 6.0, "c": 1.0, "f": 8.0,  "fib": 0.0},
        "Traditional Wing — Garlic Parmesan (each)":{"cal": 105, "p": 7.0, "c": 1.0, "f": 8.0,  "fib": 0.0},
        "Traditional Wing — Louisiana Rub (each)":  {"cal": 90,  "p": 6.0, "c": 1.0, "f": 7.0,  "fib": 0.0},
        "Traditional Wing — Mango Habanero (each)": {"cal": 110, "p": 6.0, "c": 4.0, "f": 8.0,  "fib": 0.0},
        "Boneless Wing (each)":                     {"cal": 70,  "p": 4.0, "c": 5.0, "f": 4.0,  "fib": 0.0},
        "Voodoo Fries (regular)":                   {"cal": 690, "p": 14.0,"c": 80.0,"f": 36.0, "fib": 6.0},
    },
}

CUSTOM_DB_LABEL = "★ My Custom Foods"
GERC_THRESHOLD = float(st.session_state.get("gerc_threshold", 2.0))
FAT_LIMIT = float(st.session_state.get("fat_limit_g", 15.0))
FIBER_LIMIT = float(st.session_state.get("fiber_limit_g", 8.0))
CARB_FLOOR = float(st.session_state.get("carb_floor_g", 40.0))
CARB_CEIL = float(st.session_state.get("carb_ceil_g", 60.0))
PROTEIN_FLOOR = float(st.session_state.get("protein_floor_g", 30.0))

# ------------------------------------------------------------------------------
# SIDEBAR
# ------------------------------------------------------------------------------

with st.sidebar:
    st.markdown("### 🍽️ Metabolic Engine")
    render_sidebar_profile()
    sel_date = st.date_input("📅 Log Date", value=date.today())
    d_iso = sel_date.isoformat()
    st.caption("Macros scale live with the serving multiplier on the Builder tab.")

st.markdown(
    f"""
    <div style="padding:2px 0 4px 0;">
        <h1 style="margin-bottom:0;">🍽️ Metabolic Engine</h1>
        <p style="color:#8FA1BF;letter-spacing:.13em;font-size:.78rem;margin-top:2px;">
            COMPONENT-LEVEL MACRO TRACKER · CUT TO 145–155 LBS · LOG DATE {d_iso}
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

tab_builder, tab_custom, tab_window, tab_log = st.tabs([
    "🧱 Macro Builder",
    "➕ Custom Food Creator",
    "⏱️ 6:00 PM Kinetic Evaluator",
    "📋 Daily Log & Budget",
])

# ------------------------------------------------------------------------------
# HELPERS
# ------------------------------------------------------------------------------


def custom_food_options() -> dict:
    df = get_df("df_custom_foods")
    out = {}
    if not df.empty:
        for _, r in df.iterrows():
            name = str(r["Item_Name"])
            out[name] = {
                "cal": num_or(r["Calories"], 0.0),
                "p": num_or(r["Protein"], 0.0),
                "c": num_or(r["Carbs"], 0.0),
                "f": num_or(r["Fats"], 0.0),
                "fib": num_or(r["Fiber"], 0.0),
            }
    return out


def day_nutrition(date_iso: str) -> pd.DataFrame:
    df = get_df("df_nutrition")
    if df.empty:
        return df
    return df[df["Date"] == date_iso]


def macro_totals(frame: pd.DataFrame) -> dict:
    if frame.empty:
        return {"Calories": 0.0, "Protein": 0.0, "Carbs": 0.0, "Fats": 0.0, "Fiber": 0.0}
    return {
        col: float(pd.to_numeric(frame[col], errors="coerce").fillna(0).sum())
        for col in ["Calories", "Protein", "Carbs", "Fats", "Fiber"]
    }


def log_item(date_iso: str, source: str, name: str, scaled: dict, window_mins):
    append_row("df_nutrition", {
        "Date": date_iso,
        "Timestamp": datetime.now().strftime("%H:%M"),
        "Source": source,
        "Item_Name": name,
        "Calories": round(scaled["cal"], 1),
        "Protein": round(scaled["p"], 1),
        "Carbs": round(scaled["c"], 1),
        "Fats": round(scaled["f"], 1),
        "Fiber": round(scaled["fib"], 1),
        "Digestion_Window_Mins": window_mins,
    })

# ==============================================================================
# TAB 1 — MACRO BUILDER
# ==============================================================================

with tab_builder:
    st.subheader("Component-Level Macro Builder")
    st.caption(
        "Select an establishment, drill to the exact component, scale the serving, "
        "and log it. Items can be tagged for the 6:00 PM pre-workout window, which "
        "stamps a 90-minute digestion clock and routes them to the Kinetic Evaluator."
    )

    customs = custom_food_options()
    db_sources = list(FOOD_DB.keys())
    if customs:
        db_sources = db_sources + [CUSTOM_DB_LABEL]

    bc1, bc2 = st.columns([5, 7], gap="large")

    with bc1:
        with st.container(border=True):
            source = st.selectbox("Establishment", db_sources, key="me_source")
            if source == CUSTOM_DB_LABEL:
                item_map = customs
            else:
                item_map = FOOD_DB[source]
            item_name = st.selectbox("Component / Item", list(item_map.keys()), key="me_item")
            base = item_map[item_name]

            portion = st.slider(
                "Serving multiplier (e.g., double meat = 2.0×)",
                0.25, 4.0, 1.0, 0.25, key="me_portion",
            )
            is_preworkout = st.toggle(
                "⏱️ Tag as 6:00 PM pre-workout component", value=False, key="me_pw",
            )

            scaled = {k: float(base[k]) * portion for k in ("cal", "p", "c", "f", "fib")}
            window_mins = ATHLETE_PROFILE["digestion_window_mins"] if is_preworkout else 0

            if st.button("➕ Log Component", type="primary", use_container_width=True):
                src_label = "Custom" if source == CUSTOM_DB_LABEL else source
                log_item(d_iso, src_label, item_name, scaled, window_mins)
                st.toast(f"Logged {item_name} ({scaled['cal']:.0f} kcal)", icon="✅")
                st.rerun()

    with bc2:
        st.markdown("##### Scaled Macro Preview")
        pv = st.columns(5)
        pv[0].metric("kcal", f"{scaled['cal']:.0f}")
        pv[1].metric("Protein", f"{scaled['p']:.0f} g")
        pv[2].metric("Carbs", f"{scaled['c']:.0f} g")
        pv[3].metric("Fat", f"{scaled['f']:.0f} g")
        pv[4].metric("Fiber", f"{scaled['fib']:.0f} g")

        gerc_preview = compute_gerc(scaled["c"], scaled["f"], scaled["fib"])
        st.markdown(
            f"""
            <div class="apex-card">
                <span class="apex-pill"
                      style="background:rgba(0,180,216,.12);color:#00B4D8;border:1px solid #00B4D8;">
                    GASTRIC EMPTYING RATE COEFFICIENT
                </span>
                <p style="margin:8px 0 0 0;font-size:.86rem;line-height:1.6;color:#C9D2E3;">
                    This component's <b>GERC = {gerc_preview:.2f}</b>
                    (Carbs / (Fat·1.5 + Fiber·2.0 + 1)). Higher is faster-clearing.
                    The pre-workout floor is <b style="color:#00E5A0;">{GERC_THRESHOLD:.1f}</b> —
                    components below it sit heavy in the gut at tip-off.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if is_preworkout:
            st.info(
                f"Tagged for the 6:00 PM window — a {window_mins}-minute digestion clock "
                f"will be stamped and this component routes into the Kinetic Evaluator."
            )

# ==============================================================================
# TAB 2 — CUSTOM FOOD CREATOR
# ==============================================================================

with tab_custom:
    st.subheader("Custom Food Creator")
    st.caption(
        "Define any arbitrary food with exact macros. Saved items append to your "
        "Custom Food List and become instantly selectable in the Macro Builder."
    )

    cc1, cc2 = st.columns([5, 7], gap="large")

    with cc1:
        with st.form("custom_food_form"):
            st.markdown("##### New Custom Item")
            new_name = st.text_input("Food name", value="", placeholder="e.g., Mom's chicken & rice")
            f1, f2 = st.columns(2)
            new_cal = f1.number_input("Calories", 0.0, 4000.0, 400.0, 10.0)
            new_pro = f2.number_input("Protein (g)", 0.0, 300.0, 30.0, 1.0)
            f3, f4, f5 = st.columns(3)
            new_carb = f3.number_input("Carbs (g)", 0.0, 500.0, 45.0, 1.0)
            new_fat = f4.number_input("Fat (g)", 0.0, 250.0, 12.0, 1.0)
            new_fib = f5.number_input("Fiber (g)", 0.0, 80.0, 4.0, 1.0)
            saved = st.form_submit_button("💾 Save to Custom Food List",
                                          type="primary", use_container_width=True)
        if saved:
            clean = new_name.strip()
            if not clean:
                st.error("Give the food a name before saving.")
            else:
                df = get_df("df_custom_foods")
                if not df.empty and (df["Item_Name"].astype(str) == clean).any():
                    idx = df.index[df["Item_Name"].astype(str) == clean][0]
                    df.loc[idx, ["Calories", "Protein", "Carbs", "Fats", "Fiber"]] = [
                        new_cal, new_pro, new_carb, new_fat, new_fib]
                    set_df("df_custom_foods", df)
                    st.toast(f"Updated '{clean}'.", icon="♻️")
                else:
                    append_row("df_custom_foods", {
                        "Item_Name": clean, "Calories": new_cal, "Protein": new_pro,
                        "Carbs": new_carb, "Fats": new_fat, "Fiber": new_fib})
                    st.toast(f"Saved '{clean}' to Custom Food List.", icon="✅")
                st.rerun()

    with cc2:
        st.markdown("##### Custom Food List")
        cdf = get_df("df_custom_foods")
        if cdf.empty:
            st.info("No custom foods yet. Create one on the left to reuse it in the Builder.")
        else:
            show = cdf.copy()
            for col in ["Calories", "Protein", "Carbs", "Fats", "Fiber"]:
                show[col] = pd.to_numeric(show[col], errors="coerce").round(1)
            st.dataframe(show, use_container_width=True, hide_index=True)
            del_pick = st.selectbox(
                "Remove a custom item",
                ["—"] + cdf["Item_Name"].astype(str).tolist(), key="cust_del")
            if del_pick != "—" and st.button("🗑️ Delete custom item", use_container_width=True):
                keep = cdf[cdf["Item_Name"].astype(str) != del_pick]
                set_df("df_custom_foods", keep)
                st.rerun()

# ==============================================================================
# TAB 3 — 6:00 PM PRE-WORKOUT KINETIC EVALUATOR
# ==============================================================================

with tab_window:
    st.subheader("6:00 PM Pre-Workout Kinetic Evaluator")
    st.caption(
        f"Strict {ATHLETE_PROFILE['digestion_window_mins']}-minute metabolic window: "
        f"feed {ATHLETE_PROFILE['meal_time']} → train {ATHLETE_PROFILE['train_time']}. "
        "Components tagged pre-workout in the Builder aggregate here and are scored by "
        "the Gastric Emptying Rate Coefficient."
    )

    day_df = day_nutrition(d_iso)
    if day_df.empty:
        pw_df = day_df
    else:
        pw_df = day_df[pd.to_numeric(day_df["Digestion_Window_Mins"], errors="coerce").fillna(0) > 0]

    if pw_df.empty:
        st.info(
            "No components tagged for the 6:00 PM window on this date. In the Macro "
            "Builder, flip '⏱️ Tag as 6:00 PM pre-workout component' when logging."
        )
    else:
        pw = macro_totals(pw_df)
        gerc = compute_gerc(pw["Carbs"], pw["Fats"], pw["Fiber"])

        m = st.columns(6)
        m[0].metric("Meal kcal", f"{pw['Calories']:.0f}")
        m[1].metric("Protein", f"{pw['Protein']:.0f} g")
        m[2].metric("Carbs", f"{pw['Carbs']:.0f} g")
        m[3].metric("Fat", f"{pw['Fats']:.0f} g")
        m[4].metric("Fiber", f"{pw['Fiber']:.0f} g")
        m[5].metric("GERC", f"{gerc:.2f}", f"floor {GERC_THRESHOLD:.1f}", delta_color="off")

        bottlenecks = []
        if pw["Fats"] > FAT_LIMIT:
            bottlenecks.append(f"fat {pw['Fats']:.0f} g (limit {FAT_LIMIT:.0f} g)")
        if pw["Fiber"] > FIBER_LIMIT:
            bottlenecks.append(f"fiber {pw['Fiber']:.0f} g (limit {FIBER_LIMIT:.0f} g)")
        gerc_low = gerc < GERC_THRESHOLD

        if bottlenecks or gerc_low:
            reasons = []
            if gerc_low:
                reasons.append(f"the GERC of {gerc:.2f} sits below the {GERC_THRESHOLD:.1f} floor")
            if bottlenecks:
                reasons.append(" and ".join(bottlenecks) + " exceed the pre-workout ceilings")
            st.error(
                "⛔ **KINETIC BOTTLENECK DETECTED** — " + "; ".join(reasons) + ". "
                "A slow-clearing bolus this close to tip-off forces the splanchnic "
                "circulation to divert blood volume toward the gut for digestion, "
                "pulling it away from working skeletal muscle. The downstream cost is "
                "blunted Type IIx fast-twitch motor-unit recruitment, dulled first-step "
                "explosiveness, and a real cramping/heaviness risk during the 7:30 PM "
                "plyometric block. Strip the high-fat/high-fiber components (guacamole, "
                "fried items, heavy sauces, dense bean volume) or push them to the "
                "post-workout window, and re-anchor this meal on lean protein plus "
                "low-fiber, high-glycemic carbohydrate."
            )
        else:
            st.success(
                f"✅ **KINETIC CLEARANCE** — GERC {gerc:.2f} clears the {GERC_THRESHOLD:.1f} "
                f"floor, with fat ({pw['Fats']:.0f} g) and fiber ({pw['Fiber']:.0f} g) under "
                "ceiling. Gastric emptying completes inside the 90-minute window, preserving "
                "central blood volume for Type IIx fast-twitch recruitment at tip-off."
            )

        # Secondary macro-floor checks (protein / carb saturation)
        notes = []
        if pw["Carbs"] < CARB_FLOOR:
            notes.append(("warning", f"Carbohydrate at {pw['Carbs']:.0f} g is below the "
                          f"{CARB_FLOOR:.0f}–{CARB_CEIL:.0f} g glycogen-saturation band — "
                          "add low-fiber, high-glycemic carbohydrate."))
        elif pw["Carbs"] > CARB_CEIL:
            notes.append(("info", f"Carbohydrate at {pw['Carbs']:.0f} g exceeds the "
                          f"{CARB_CEIL:.0f} g ceiling; glycogen is covered — watch the daily deficit."))
        else:
            notes.append(("success", f"Carbohydrate at {pw['Carbs']:.0f} g sits in the "
                          f"{CARB_FLOOR:.0f}–{CARB_CEIL:.0f} g glycogen-saturation band."))
        if pw["Protein"] < PROTEIN_FLOOR:
            notes.append(("warning", f"Protein at {pw['Protein']:.0f} g is below the "
                          f"{PROTEIN_FLOOR:.0f} g anti-catabolic floor for a deficit-state session."))
        else:
            notes.append(("success", f"Protein at {pw['Protein']:.0f} g shields muscle tissue "
                          "through the deficit-state bout."))
        for sev, msg in notes:
            getattr(st, sev)(msg)

        with st.expander("🔬 Pre-workout components on this date"):
            comp = pw_df[["Source", "Item_Name", "Calories", "Protein", "Carbs", "Fats", "Fiber"]].copy()
            for col in ["Calories", "Protein", "Carbs", "Fats", "Fiber"]:
                comp[col] = pd.to_numeric(comp[col], errors="coerce").round(1)
            st.dataframe(comp, use_container_width=True, hide_index=True)

# ==============================================================================
# TAB 4 — DAILY LOG & BUDGET
# ==============================================================================

with tab_log:
    st.subheader("Daily Log & Macro Budget")
    day_df = day_nutrition(d_iso)
    totals = macro_totals(day_df)

    st.markdown("##### Consumed vs. Remaining")
    targets = [
        ("Calories", "Calories", float(st.session_state.t_cal), "kcal"),
        ("Protein", "Protein", float(st.session_state.t_pro), "g"),
        ("Carbohydrate", "Carbs", float(st.session_state.t_carb), "g"),
        ("Fat", "Fats", float(st.session_state.t_fat), "g"),
    ]
    for label, key, target, unit in targets:
        consumed = totals[key]
        remaining = target - consumed
        pct = min(consumed / max(target, 1.0), 1.0)
        st.progress(pct, text=f"{label}: {consumed:,.0f} / {target:,.0f} {unit} consumed · "
                              f"{max(remaining, 0):,.0f} {unit} remaining")
        if remaining < 0:
            st.caption(f"🔺 Over {label.lower()} budget by {abs(remaining):,.0f} {unit}.")
    st.caption(f"Total fiber consumed: {totals['Fiber']:.0f} g")

    st.divider()
    st.markdown(f"##### Components logged on {d_iso}")
    if day_df.empty:
        st.info("No components logged for this date. Use the Macro Builder to start.")
    else:
        show = day_df.copy()
        show["Pre-Wkt"] = pd.to_numeric(show["Digestion_Window_Mins"], errors="coerce").fillna(0) > 0
        disp = show[["Timestamp", "Source", "Item_Name", "Calories", "Protein",
                     "Carbs", "Fats", "Fiber", "Pre-Wkt"]].copy()
        for col in ["Calories", "Protein", "Carbs", "Fats", "Fiber"]:
            disp[col] = pd.to_numeric(disp[col], errors="coerce").round(1)
        disp = disp.rename(columns={"Item_Name": "Item", "Calories": "kcal",
                                    "Protein": "P", "Carbs": "C", "Fats": "F", "Fiber": "Fib"})
        st.dataframe(disp, use_container_width=True, hide_index=True)

        del_opts = {
            f"{row['Item_Name']} · {num_or(row['Calories'], 0):.0f} kcal (#{idx})": idx
            for idx, row in day_df.iterrows()
        }
        dl, dr = st.columns([7, 3])
        pick = dl.selectbox("Remove a logged component", list(del_opts.keys()), key="me_del")
        if dr.button("🗑️ Remove", use_container_width=True):
            full = get_df("df_nutrition")
            set_df("df_nutrition", full.drop(index=del_opts[pick]))
            st.rerun()

        if len(day_df) >= 2:
            src_split = day_df.copy()
            src_split["Calories"] = pd.to_numeric(src_split["Calories"], errors="coerce").fillna(0)
            agg = src_split.groupby("Source", as_index=False)["Calories"].sum()
            fig = px.bar(agg, x="Source", y="Calories", title="Calories by Source (this date)")
            fig.update_traces(marker_color="#00B4D8")
            st.plotly_chart(style_fig(fig, 300), use_container_width=True)
