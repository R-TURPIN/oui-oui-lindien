import streamlit as st
import pandas as pd
import numpy as np
import requests
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os
import math
from datetime import datetime, timedelta

# Les trendlines Plotly (ols/lowess) nécessitent statsmodels — fallback propre si absent
try:
    import statsmodels.api  # noqa: F401
    TRENDLINE_OLS    = "ols"
    TRENDLINE_LOWESS = "lowess"
except ImportError:
    TRENDLINE_OLS    = None
    TRENDLINE_LOWESS = None

# ─────────────────────────────────────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Kikimeter Analytique",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ─────────────────────────────────────────────────────────────────────────────
# VARIABLES ENVIRONNEMENT
# ─────────────────────────────────────────────────────────────────────────────
CLIENT_ID     = os.environ.get("STRAVA_CLIENT_ID")
CLIENT_SECRET = os.environ.get("STRAVA_CLIENT_SECRET")
APP_URL       = os.environ.get("APP_URL", "http://localhost:8501")

# ─────────────────────────────────────────────────────────────────────────────
# CSS CUSTOM — DARK ULTRA-SPORT
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
  /* ── Base ── */
  @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;400;500;600;700&family=Space+Mono:wght@400;700&display=swap');

  html, body, [class*="css"] {
    font-family: 'Space Grotesk', sans-serif;
    background-color: #0a0a0f;
    color: #e8e8f0;
  }
  .stApp { background-color: #0a0a0f; }
  .block-container { padding: 1.5rem 2rem 3rem; max-width: 1600px; }

  /* ── Sidebar ── */
  [data-testid="stSidebar"] {
    background-color: #0f0f1a;
    border-right: 1px solid #1e1e30;
  }
  [data-testid="stSidebar"] * { color: #c8c8e0 !important; }

  /* ── Metric cards ── */
  [data-testid="stMetricValue"] {
    font-family: 'Space Mono', monospace !important;
    font-size: 1.8rem !important;
    font-weight: 700 !important;
    color: #ff4d00 !important;
  }
  [data-testid="stMetricLabel"] {
    font-size: 0.72rem !important;
    letter-spacing: 0.12em !important;
    text-transform: uppercase !important;
    color: #6868a0 !important;
  }
  [data-testid="metric-container"] {
    background: #13131f;
    border: 1px solid #1e1e30;
    border-radius: 8px;
    padding: 1.1rem 1.3rem !important;
    transition: border-color 0.2s;
  }
  [data-testid="metric-container"]:hover { border-color: #ff4d00; }

  /* ── Section headers ── */
  .kiki-header {
    font-family: 'Space Mono', monospace;
    font-size: 0.7rem;
    letter-spacing: 0.25em;
    text-transform: uppercase;
    color: #ff4d00;
    margin: 2.2rem 0 0.8rem;
    border-left: 2px solid #ff4d00;
    padding-left: 0.8rem;
  }
  .kiki-sub {
    font-size: 0.8rem;
    color: #5555a0;
    margin-top: -0.5rem;
    margin-bottom: 1.2rem;
    padding-left: 1.1rem;
  }

  /* ── Badge chips ── */
  .badge-wrap { display: flex; flex-wrap: wrap; gap: 0.5rem; margin: 0.5rem 0 1rem; }
  .badge {
    display: inline-flex; align-items: center; gap: 0.3rem;
    padding: 0.35rem 0.75rem;
    border-radius: 999px;
    font-size: 0.75rem; font-weight: 600;
    border: 1px solid;
    letter-spacing: 0.04em;
  }
  .badge-orange { background: #1a0a00; border-color: #ff4d00; color: #ff7040; }
  .badge-blue   { background: #000a1a; border-color: #0080ff; color: #4db3ff; }
  .badge-green  { background: #001a08; border-color: #00d264; color: #33ff99; }
  .badge-purple { background: #0d001a; border-color: #9900ff; color: #cc66ff; }
  .badge-yellow { background: #1a1400; border-color: #ffcc00; color: #ffe066; }

  /* ── Hall of Fame ── */
  .record-card {
    background: #13131f;
    border: 1px solid #1e1e30;
    border-radius: 8px;
    padding: 0.9rem 1.1rem;
    margin-bottom: 0.5rem;
    display: flex; justify-content: space-between; align-items: center;
    transition: border-color 0.2s;
  }
  .record-card:hover { border-color: #ff4d00; }
  .record-label { font-size: 0.72rem; color: #6868a0; text-transform: uppercase; letter-spacing: 0.1em; }
  .record-value { font-family: 'Space Mono', monospace; font-size: 1.05rem; color: #ff4d00; font-weight: 700; }
  .record-name  { font-size: 0.78rem; color: #9898c0; max-width: 200px; text-align: right; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }

  /* ── Divider ── */
  hr { border-color: #1e1e30 !important; }

  /* ── Dataframe ── */
  [data-testid="stDataFrame"] { border-radius: 8px; overflow: hidden; }

  /* ── Title block ── */
  .hero-title {
    font-family: 'Space Mono', monospace;
    font-size: 2.2rem; font-weight: 700;
    letter-spacing: -0.02em;
    background: linear-gradient(135deg, #ff4d00 0%, #ff0080 100%);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    margin-bottom: 0;
  }
  .hero-sub {
    font-size: 0.85rem; color: #5555a0;
    letter-spacing: 0.15em; text-transform: uppercase;
    margin-top: 0.2rem;
  }

  /* ── Info box ── */
  .stAlert { background: #13131f !important; border: 1px solid #1e1e30 !important; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# FONCTIONS UTILITAIRES
# ─────────────────────────────────────────────────────────────────────────────

def fmt_pace(speed_ms):
    """Convertit m/s en pace min/km (string)."""
    if not speed_ms or speed_ms <= 0:
        return "N/A"
    pace_s = 1000 / speed_ms
    return f"{int(pace_s // 60)}:{int(pace_s % 60):02d} /km"


def fmt_duration(seconds):
    """Formate des secondes en hh:mm:ss."""
    if pd.isna(seconds) or seconds <= 0:
        return "—"
    h, rem = divmod(int(seconds), 3600)
    m, s   = divmod(rem, 60)
    return f"{h}h{m:02d}" if h else f"{m}min{s:02d}"


def safe_div(a, b, default=0):
    try:
        return a / b if b and b != 0 else default
    except Exception:
        return default


# ─────────────────────────────────────────────────────────────────────────────
# CALCULS PHYSIOLOGIQUES
# ─────────────────────────────────────────────────────────────────────────────

def calc_trimp(row, fc_repos, fc_max):
    """TRIMP d'Edward basé sur la FC de réserve."""
    try:
        avg_hr = row.get("average_heartrate")
        if pd.isna(avg_hr) or avg_hr <= 0:
            return 0.0
        hrr = (avg_hr - fc_repos) / max(fc_max - fc_repos, 1)
        hrr = float(np.clip(hrr, 0.0, 1.0))
        return row["durée_min"] * hrr * 0.64 * math.exp(1.92 * hrr)
    except Exception:
        return 0.0


def calc_vam(row):
    """Vitesse Ascensionnelle Moyenne en m/h."""
    try:
        if row.get("moving_time", 0) > 0 and row.get("total_elevation_gain", 0) > 0:
            return row["total_elevation_gain"] / (row["moving_time"] / 3600)
        return 0.0
    except Exception:
        return 0.0


def calc_gradient(row):
    """Gradient moyen en %."""
    try:
        d = row.get("distance", 0)
        e = row.get("total_elevation_gain", 0)
        return (e / d * 100) if d > 0 else 0.0
    except Exception:
        return 0.0


def estimate_power_no_sensor(row, poids_kg, Crr=0.004, Cd=0.9, A=0.45, rho=1.225, eta=0.97):
    """
    Estimation de la puissance cycliste (W) sans capteur.
    Modèle aérodynamique + résistance au roulement + gravité.
    """
    try:
        v   = float(row.get("average_speed", 0))       # m/s
        gr  = float(row.get("total_elevation_gain", 0))
        d   = float(row.get("distance", 1))
        pct = gr / d if d > 0 else 0                   # pente fractionnaire
        g   = 9.81

        F_aero   = 0.5 * Cd * A * rho * v**2
        F_roulement = Crr * poids_kg * g * math.cos(math.atan(pct))
        F_gravite   = poids_kg * g * math.sin(math.atan(pct))
        P = (F_aero + F_roulement + F_gravite) * v / eta
        return max(0.0, P)
    except Exception:
        return 0.0


def calc_efficiency_index(row):
    """
    Efficiency Index (EI) = vitesse (m/s) / FC_moy.
    Indicateur d'économie de course.
    """
    try:
        v  = float(row.get("average_speed", 0))
        hr = float(row.get("average_heartrate", 0))
        return (v / hr * 100) if hr > 0 else 0.0
    except Exception:
        return 0.0


def calc_acwr(df_sorted):
    """
    Acute:Chronic Workload Ratio (ACWR).
    Acute  = moyenne TRIMP sur 7 jours
    Chronic = moyenne TRIMP sur 28 jours
    Retourne une colonne acwr dans df.
    """
    try:
        df_sorted = df_sorted.copy()
        df_sorted["date_dt"] = pd.to_datetime(df_sorted["date"])
        df_sorted = df_sorted.sort_values("date_dt").reset_index(drop=True)

        acwr_vals = []
        for i, row in df_sorted.iterrows():
            d = row["date_dt"]
            acute  = df_sorted[(df_sorted["date_dt"] >= d - timedelta(days=7))  & (df_sorted["date_dt"] <= d)]["trimp"].mean()
            chronic = df_sorted[(df_sorted["date_dt"] >= d - timedelta(days=28)) & (df_sorted["date_dt"] <= d)]["trimp"].mean()
            acwr_vals.append(safe_div(acute, chronic, default=np.nan))

        df_sorted["acwr"] = acwr_vals
        return df_sorted
    except Exception:
        df_sorted["acwr"] = np.nan
        return df_sorted


def estimate_vo2max_running(df):
    """
    Estimation VO2max dynamique sur les meilleures sorties de course.
    Méthode Jack Daniels : VO2 = vitesse(m/min) * 0.2 + 3.5
    Ajustée par %VO2 estimé via la FC de réserve.
    Retourne un float ou None.
    """
    try:
        runs = df[df["type"].str.lower().isin(["run", "virtualrun", "trailrun"])].copy()
        runs = runs[runs["average_speed"] > 0]
        if runs.empty:
            return None
        # Prendre les 5 meilleures sorties par rapport vitesse/FC si dispo
        if "average_heartrate" in runs.columns and runs["average_heartrate"].notnull().any():
            runs = runs.dropna(subset=["average_heartrate"])
            runs["vo2_est"] = (runs["average_speed"] * 60 * 0.2 + 3.5)  # VO2 à cet effort
            # Retourner le percentile 90 des estimations (efforts durs → meilleure estimation)
            return runs["vo2_est"].quantile(0.9)
        else:
            # Fallback : meilleure vitesse sur les longues sorties
            long_runs = runs[runs["distance"] > 5000]
            if not long_runs.empty:
                best_speed = long_runs["average_speed"].max()
                return best_speed * 60 * 0.2 + 3.5
        return None
    except Exception:
        return None


def assign_badges(df, df_run, df_ride, poids):
    """Génère une liste de badges selon le profil de l'athlète."""
    badges = []
    try:
        total_km       = df["distance_km"].sum()
        total_dplus    = df["total_elevation_gain"].sum()
        ratio_dkm      = safe_div(total_dplus, total_km)
        max_speed_kmh  = df["vitesse_moy_kmh"].max()
        total_hours    = df["durée_min"].sum() / 60
        avg_trimp      = df["trimp"].mean()
        nb_runs        = len(df_run)
        nb_rides       = len(df_ride)

        if ratio_dkm > 18:
            badges.append(("🏔️ Grimpeur Pur", "badge-orange"))
        if max_speed_kmh > 55:
            badges.append(("⚡ Sprinteur Explosif", "badge-yellow"))
        if total_hours > 80:
            badges.append(("🔩 Machine d'Endurance", "badge-green"))
        if avg_trimp > 80:
            badges.append(("💀 Masochiste Certifié", "badge-purple"))
        if nb_runs > nb_rides and nb_runs > 20:
            badges.append(("👟 Runner Acharné", "badge-blue"))
        if nb_rides > nb_runs and nb_rides > 20:
            badges.append(("🚴 Cycliste Dédié", "badge-blue"))
        if total_dplus > 30000:
            badges.append(("🗻 Avaleur de Cols", "badge-orange"))
        if total_km > 1500:
            badges.append(("📍 Explorateur de Bornes", "badge-green"))
        if df["trimp"].max() > 200:
            badges.append(("☢️ Séance Nucléaire", "badge-purple"))
        if not badges:
            badges.append(("🌱 En Construction", "badge-blue"))
    except Exception:
        badges.append(("⚡ Athlète", "badge-orange"))
    return badges


# ─────────────────────────────────────────────────────────────────────────────
# COULEURS ZONES FC
# ─────────────────────────────────────────────────────────────────────────────
ZONE_COLORS = {
    "Z1 - Récup":      "#3a6fff",
    "Z2 - Aérobie":    "#00d264",
    "Z3 - Tempo":      "#ffcc00",
    "Z4 - Seuil":      "#ff7040",
    "Z5 - VO2Max":     "#ff0040",
}
PLOTLY_DARK = "plotly_dark"

# ─────────────────────────────────────────────────────────────────────────────
# HEADER HERO
# ─────────────────────────────────────────────────────────────────────────────
st.markdown('<p class="hero-title">⚡ KIKIMETER ANALYTIQUE</p>', unsafe_allow_html=True)
st.markdown('<p class="hero-sub">Autopsie Physiologique · Strava Data Intelligence</p>', unsafe_allow_html=True)
st.markdown("---")

# ─────────────────────────────────────────────────────────────────────────────
# SIDEBAR — PROFIL ATHLÈTE
# ─────────────────────────────────────────────────────────────────────────────
st.sidebar.markdown("## ⚙️ Profil Athlète")
poids    = st.sidebar.number_input("Poids (kg)",            min_value=40,  max_value=150, value=70, step=1)
fc_max   = st.sidebar.number_input("FC Max (BPM)",          min_value=140, max_value=220, value=190)
fc_repos = st.sidebar.number_input("FC Repos (BPM)",        min_value=35,  max_value=90,  value=55)
age      = st.sidebar.number_input("Âge",                   min_value=15,  max_value=80,  value=30)
ftp      = st.sidebar.number_input("FTP Vélo (W) — optionnel", min_value=0, max_value=600, value=0, step=5)

st.sidebar.markdown("---")
st.sidebar.markdown("##### 🏆 Objectifs & Contexte")
sport_focus = st.sidebar.selectbox("Sport principal", ["Course à pied", "Cyclisme", "Triathlon", "Polyvalent"])

# ─────────────────────────────────────────────────────────────────────────────
# OAUTH2 STRAVA
# ─────────────────────────────────────────────────────────────────────────────
if "strava_token" not in st.session_state:
    query_params = st.query_params
    if "code" in query_params:
        auth_code = query_params["code"]
        res = requests.post("https://www.strava.com/oauth/token", data={
            "client_id":     CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "code":          auth_code,
            "grant_type":    "authorization_code"
        })
        if res.status_code == 200:
            st.session_state["strava_token"] = res.json()["access_token"]
            st.rerun()
        else:
            st.error(f"❌ Échec du token Strava ({res.status_code}). Vérifie CLIENT_ID / CLIENT_SECRET.")
    else:
        col_l, col_c, col_r = st.columns([1, 2, 1])
        with col_c:
            st.markdown("""
            <div style="text-align:center; padding: 3rem 2rem; background:#13131f;
                        border:1px solid #1e1e30; border-radius:12px;">
              <div style="font-size:3.5rem; margin-bottom:1rem;">🔗</div>
              <p style="font-family:'Space Mono',monospace; font-size:1.1rem; color:#e8e8f0; margin-bottom:0.5rem;">
                Connecte ton compte Strava
              </p>
              <p style="font-size:0.8rem; color:#5555a0; margin-bottom:1.8rem;">
                100 dernières activités · Analyse complète en quelques secondes
              </p>
            </div>
            """, unsafe_allow_html=True)
            authorize_url = (
                f"https://www.strava.com/oauth/authorize"
                f"?client_id={CLIENT_ID}"
                f"&redirect_uri={APP_URL}"
                f"&response_type=code"
                f"&scope=activity:read_all"
            )
            st.markdown(f"""
            <div style="text-align:center; margin-top:1.2rem;">
              <a href="{authorize_url}" target="_self">
                <button style="background:#FC4C02;color:#fff;border:none;padding:14px 36px;
                               font-size:1rem;border-radius:6px;cursor:pointer;font-weight:700;
                               font-family:'Space Grotesk',sans-serif;letter-spacing:0.05em;
                               transition:background 0.2s;">
                  🚀 Se connecter avec Strava
                </button>
              </a>
            </div>
            """, unsafe_allow_html=True)
    st.stop()


# ─────────────────────────────────────────────────────────────────────────────
# RÉCUPÉRATION DES DONNÉES STRAVA
# ─────────────────────────────────────────────────────────────────────────────
if st.sidebar.button("🔴 Déconnecter"):
    del st.session_state["strava_token"]
    st.rerun()

token   = st.session_state["strava_token"]
headers = {"Authorization": f"Bearer {token}"}

with st.spinner("⚡ Aspiration des données Strava..."):
    response = requests.get(
        "https://www.strava.com/api/v3/athlete/activities?per_page=100",
        headers=headers
    )

if response.status_code != 200:
    st.error(f"❌ Erreur API Strava {response.status_code}")
    st.stop()

raw = response.json()
if not raw:
    st.warning("Aucune activité trouvée sur ce compte.")
    st.stop()


# ─────────────────────────────────────────────────────────────────────────────
# PRÉ-TRAITEMENT DU DATAFRAME
# ─────────────────────────────────────────────────────────────────────────────
df = pd.DataFrame(raw)

# Colonnes numériques de base
for col in ["distance", "moving_time", "elapsed_time", "total_elevation_gain",
            "average_speed", "max_speed", "average_heartrate", "max_heartrate",
            "average_watts", "max_watts", "kilojoules", "suffer_score"]:
    if col not in df.columns:
        df[col] = np.nan
    else:
        df[col] = pd.to_numeric(df[col], errors="coerce")

df["distance_km"]      = df["distance"] / 1000
df["durée_min"]        = df["moving_time"] / 60
df["vitesse_moy_kmh"]  = df["average_speed"] * 3.6
df["vitesse_max_kmh"]  = df["max_speed"] * 3.6
df["date"]             = pd.to_datetime(df["start_date_local"]).dt.date
df["date_dt"]          = pd.to_datetime(df["start_date_local"])
df["semaine"]          = df["date_dt"].dt.isocalendar().week
df["mois"]             = df["date_dt"].dt.to_period("M").astype(str)
df["type"]             = df["type"].fillna("Unknown")
df["name"]             = df["name"].fillna("Sans nom")

# ─── Métriques physiologiques ───
df["vam"]         = df.apply(calc_vam, axis=1)
df["gradient"]    = df.apply(calc_gradient, axis=1)
df["trimp"]       = df.apply(lambda r: calc_trimp(r, fc_repos, fc_max), axis=1)
df["eff_index"]   = df.apply(calc_efficiency_index, axis=1)

# ─── Puissance (capteur OU estimation) ───
has_power = "device_watts" in df.columns and df["device_watts"].any()
if has_power:
    df["watts_final"] = df.apply(
        lambda r: r["average_watts"] if r.get("device_watts") and pd.notnull(r["average_watts"])
                  else estimate_power_no_sensor(r, poids),
        axis=1
    )
else:
    df["watts_final"] = df.apply(lambda r: estimate_power_no_sensor(r, poids), axis=1)

df["w_kg"]          = df.apply(lambda r: safe_div(r["watts_final"], poids), axis=1)
df["joules_est"]    = df["watts_final"] * df["moving_time"]
df["kcal_utiles"]   = df["joules_est"] / 4184

# ─── VO2max dynamique ───
vo2max_dynamique = estimate_vo2max_running(df)
vo2max_basale    = 15.3 * (fc_max / max(fc_repos, 1))

# ─── ACWR ───
df = calc_acwr(df)

# ─── Sous-DataFrames par sport ───
df_run   = df[df["type"].str.lower().isin(["run", "virtualrun", "trailrun"])].copy()
df_ride  = df[df["type"].str.lower().isin(["ride", "virtualride", "ebikeride"])].copy()
df_swim  = df[df["type"].str.lower().isin(["swim"])].copy()

# ─── Pace / allure ───
df["pace_str"] = df["average_speed"].apply(fmt_pace)


# ─────────────────────────────────────────────────────────────────────────────
# PROFIL ATHLÈTE & BADGES
# ─────────────────────────────────────────────────────────────────────────────
badges     = assign_badges(df, df_run, df_ride, poids)
athlete_vo2 = vo2max_dynamique or vo2max_basale

# Récupération infos athlete si dispo
try:
    ath_info = requests.get("https://www.strava.com/api/v3/athlete", headers=headers).json()
    ath_name = f"{ath_info.get('firstname', '')} {ath_info.get('lastname', '')}".strip() or "Athlète"
except Exception:
    ath_name = "Athlète"

# ─────────────────────────────────────────────────────────────────────────────
# SECTION 1 — KPIs GLOBAUX
# ─────────────────────────────────────────────────────────────────────────────
st.markdown(f'<p class="kiki-header">📊 KPIs Globaux — {ath_name}</p>', unsafe_allow_html=True)
st.markdown('<p class="kiki-sub">100 dernières activités · Toutes disciplines</p>', unsafe_allow_html=True)

# Badges
badge_html = '<div class="badge-wrap">'
for label, cls in badges:
    badge_html += f'<span class="badge {cls}">{label}</span>'
badge_html += '</div>'
st.markdown(badge_html, unsafe_allow_html=True)

k = st.columns(5)
k[0].metric("VO₂Max Estimé",        f"{athlete_vo2:.1f} ml/kg/min")
k[1].metric("Volume Total",          f"{df['distance_km'].sum():,.0f} km")
k[2].metric("Dénivelé Cumulé",       f"{df['total_elevation_gain'].sum():,.0f} m+")
k[3].metric("Temps de Mouvement",    fmt_duration(df["moving_time"].sum()))
k[4].metric("Activités Analysées",   f"{len(df)}")

k2 = st.columns(5)
k2[0].metric("TRIMP Total",          f"{df['trimp'].sum():.0f} pts")
k2[1].metric("TRIMP Max (Séance)",   f"{df['trimp'].max():.0f} pts")
k2[2].metric("Énergie Totale",       f"{df['kcal_utiles'].sum():,.0f} kcal")
k2[3].metric("VAM Max",              f"{df['vam'].max():.0f} m/h")
k2[4].metric("W/kg Peak",            f"{df['w_kg'].max():.2f} W/kg")

st.markdown("---")


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 2 — HALL OF FAME
# ─────────────────────────────────────────────────────────────────────────────
st.markdown('<p class="kiki-header">🏆 Hall of Fame — Records Personnels</p>', unsafe_allow_html=True)
st.markdown('<p class="kiki-sub">Les meilleures performances de l\'historique</p>', unsafe_allow_html=True)

col_hof1, col_hof2, col_hof3 = st.columns(3)

def record_card_html(label, value, name=""):
    return f"""
    <div class="record-card">
      <div>
        <div class="record-label">{label}</div>
        <div class="record-value">{value}</div>
      </div>
      <div class="record-name">{name}</div>
    </div>
    """

with col_hof1:
    # Meilleure sortie run distance
    if not df_run.empty:
        best_run_dist = df_run.loc[df_run["distance_km"].idxmax()]
        st.markdown(record_card_html("🏃 Plus longue sortie run",
                                     f"{best_run_dist['distance_km']:.1f} km",
                                     best_run_dist["name"]), unsafe_allow_html=True)

        best_run_speed = df_run.loc[df_run["vitesse_moy_kmh"].idxmax()]
        st.markdown(record_card_html("🚀 Vitesse Moyenne Max (Run)",
                                     f"{best_run_speed['vitesse_moy_kmh']:.1f} km/h",
                                     best_run_speed["name"]), unsafe_allow_html=True)

    # VAM max
    best_vam_row = df[df["vam"] > 0]
    if not best_vam_row.empty:
        best_vam = best_vam_row.loc[best_vam_row["vam"].idxmax()]
        st.markdown(record_card_html("🏔️ VAM Maximale",
                                     f"{best_vam['vam']:.0f} m/h",
                                     best_vam["name"]), unsafe_allow_html=True)

with col_hof2:
    # Plus grand dénivelé
    best_elev = df.loc[df["total_elevation_gain"].idxmax()]
    st.markdown(record_card_html("⛰️ Dénivelé max sur une sortie",
                                 f"{best_elev['total_elevation_gain']:.0f} m+",
                                 best_elev["name"]), unsafe_allow_html=True)

    # TRIMP max
    best_trimp = df.loc[df["trimp"].idxmax()]
    st.markdown(record_card_html("☠️ Séance la plus dure (TRIMP)",
                                 f"{best_trimp['trimp']:.0f} pts",
                                 best_trimp["name"]), unsafe_allow_html=True)

    # Sortie la plus longue en durée
    best_dur = df.loc[df["moving_time"].idxmax()]
    st.markdown(record_card_html("⏱️ Sortie la plus longue",
                                 fmt_duration(best_dur["moving_time"]),
                                 best_dur["name"]), unsafe_allow_html=True)

with col_hof3:
    if not df_ride.empty:
        best_ride_dist = df_ride.loc[df_ride["distance_km"].idxmax()]
        st.markdown(record_card_html("🚴 Plus long ride",
                                     f"{best_ride_dist['distance_km']:.1f} km",
                                     best_ride_dist["name"]), unsafe_allow_html=True)

        best_w = df_ride.loc[df_ride["watts_final"].idxmax()]
        st.markdown(record_card_html("⚡ Puissance Max (Vélo)",
                                     f"{best_w['watts_final']:.0f} W",
                                     best_w["name"]), unsafe_allow_html=True)

    # Meilleure vitesse max
    best_speed_max = df.loc[df["vitesse_max_kmh"].idxmax()]
    st.markdown(record_card_html("💥 Pic de Vitesse Absolue",
                                 f"{best_speed_max['vitesse_max_kmh']:.1f} km/h",
                                 best_speed_max["name"]), unsafe_allow_html=True)

st.markdown("---")


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 3 — CHARGE D'ENTRAÎNEMENT (TRIMP + ACWR)
# ─────────────────────────────────────────────────────────────────────────────
st.markdown('<p class="kiki-header">📈 Charge d\'Entraînement & Risque de Blessure</p>', unsafe_allow_html=True)
st.markdown('<p class="kiki-sub">TRIMP par séance · ACWR (Acute:Chronic Workload Ratio) · Zones de risque</p>', unsafe_allow_html=True)

col_c1, col_c2 = st.columns([3, 2])

with col_c1:
    # TRIMP barchart + ACWR line
    df_sorted = df.sort_values("date_dt").reset_index(drop=True)

    fig_load = make_subplots(specs=[[{"secondary_y": True}]])
    fig_load.add_trace(
        go.Bar(x=df_sorted["date_dt"], y=df_sorted["trimp"],
               name="TRIMP", marker_color="#ff4d00", opacity=0.75),
        secondary_y=False
    )
    if "acwr" in df_sorted.columns and df_sorted["acwr"].notnull().any():
        fig_load.add_trace(
            go.Scatter(x=df_sorted["date_dt"], y=df_sorted["acwr"],
                       name="ACWR", line=dict(color="#ffcc00", width=2),
                       mode="lines+markers", marker_size=4),
            secondary_y=True
        )
        # Zones de risque ACWR
        fig_load.add_hrect(y0=1.3, y1=2.5, secondary_y=True,
                           fillcolor="#ff0040", opacity=0.08,
                           annotation_text="Zone Rouge (blessure)", annotation_position="top left",
                           annotation_font_color="#ff0040")
        fig_load.add_hrect(y0=0.8, y1=1.3, secondary_y=True,
                           fillcolor="#00d264", opacity=0.05,
                           annotation_text="Zone Verte (optimal)", annotation_position="bottom right",
                           annotation_font_color="#00d264")

    fig_load.update_layout(
        template=PLOTLY_DARK, paper_bgcolor="#13131f", plot_bgcolor="#13131f",
        title="Charge d'entraînement (TRIMP) & Ratio Aiguë/Chronique (ACWR)",
        legend=dict(orientation="h", y=-0.15),
        height=380, margin=dict(l=20, r=20, t=40, b=20)
    )
    fig_load.update_yaxes(title_text="TRIMP", secondary_y=False, gridcolor="#1e1e30")
    fig_load.update_yaxes(title_text="ACWR Ratio", secondary_y=True, gridcolor="#1e1e30")
    st.plotly_chart(fig_load, use_container_width=True)

with col_c2:
    # Stats ACWR
    acwr_last = df_sorted["acwr"].dropna().iloc[-1] if "acwr" in df_sorted.columns and df_sorted["acwr"].notnull().any() else None
    acute_7j   = df_sorted[df_sorted["date_dt"] >= df_sorted["date_dt"].max() - timedelta(days=7)]["trimp"].mean()
    chronic_28j = df_sorted[df_sorted["date_dt"] >= df_sorted["date_dt"].max() - timedelta(days=28)]["trimp"].mean()

    st.metric("Charge Aiguë (7j)",    f"{acute_7j:.1f} TRIMP/sortie")
    st.metric("Charge Chronique (28j)", f"{chronic_28j:.1f} TRIMP/sortie")
    if acwr_last:
        status = "🟢 Optimal" if 0.8 <= acwr_last <= 1.3 else ("🔴 Danger !" if acwr_last > 1.3 else "🟡 Sous-charge")
        st.metric("ACWR Actuel", f"{acwr_last:.2f} — {status}")

    st.markdown("""
    <div style="background:#1a0a00;border:1px solid #ff4d0040;border-radius:8px;padding:0.8rem 1rem;margin-top:0.8rem;">
      <p style="font-size:0.72rem;color:#ff7040;font-weight:600;margin:0 0 0.4rem;">⚠️ Lecture ACWR</p>
      <p style="font-size:0.75rem;color:#9898c0;margin:0;">
        <b style="color:#00d264;">0.8 – 1.3</b> → Zone optimale<br>
        <b style="color:#ff7040;">&gt; 1.3</b> → Risque de blessure élevé<br>
        <b style="color:#ffcc00;">&lt; 0.8</b> → Sous-charge, désentraînement
      </p>
    </div>
    """, unsafe_allow_html=True)

st.markdown("---")


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 4 — ANALYSE CARDIAQUE & ZONES
# ─────────────────────────────────────────────────────────────────────────────
st.markdown('<p class="kiki-header">❤️ Analyse Cardiaque & Zones FC</p>', unsafe_allow_html=True)
st.markdown('<p class="kiki-sub">Distribution par zones · Efficacité · FC de réserve</p>', unsafe_allow_html=True)

# Calcul des zones FC (méthode Karvonen)
def fc_zone_label(hrr_pct):
    if hrr_pct < 0.60: return "Z1 - Récup"
    if hrr_pct < 0.70: return "Z2 - Aérobie"
    if hrr_pct < 0.80: return "Z3 - Tempo"
    if hrr_pct < 0.90: return "Z4 - Seuil"
    return "Z5 - VO2Max"

has_hr = "average_heartrate" in df.columns and df["average_heartrate"].notnull().any()

if has_hr:
    df_hr = df.dropna(subset=["average_heartrate"]).copy()
    df_hr["hrr_pct"] = ((df_hr["average_heartrate"] - fc_repos) / max(fc_max - fc_repos, 1)).clip(0, 1)
    df_hr["zone"]    = df_hr["hrr_pct"].apply(fc_zone_label)

    col_z1, col_z2 = st.columns(2)

    with col_z1:
        zone_counts = df_hr.groupby("zone")["durée_min"].sum().reset_index()
        zone_counts["zone"] = pd.Categorical(zone_counts["zone"], categories=list(ZONE_COLORS.keys()), ordered=True)
        zone_counts = zone_counts.sort_values("zone")
        fig_zones = px.bar(zone_counts, x="zone", y="durée_min",
                           color="zone",
                           color_discrete_map=ZONE_COLORS,
                           labels={"durée_min": "Temps total (min)", "zone": "Zone"},
                           title="Temps passé dans chaque zone FC (méthode Karvonen)")
        fig_zones.update_layout(template=PLOTLY_DARK, paper_bgcolor="#13131f",
                                 plot_bgcolor="#13131f", showlegend=False,
                                 height=320, margin=dict(l=20, r=20, t=40, b=20))
        fig_zones.update_xaxes(gridcolor="#1e1e30")
        fig_zones.update_yaxes(gridcolor="#1e1e30")
        st.plotly_chart(fig_zones, use_container_width=True)

    with col_z2:
        # FC moyenne par type d'activité
        hr_by_type = df_hr.groupby("type")["average_heartrate"].mean().reset_index().sort_values("average_heartrate", ascending=False)
        fig_hr_type = px.bar(hr_by_type, x="average_heartrate", y="type",
                              orientation="h",
                              color="average_heartrate",
                              color_continuous_scale=["#3a6fff", "#ff4d00"],
                              labels={"average_heartrate": "FC Moyenne (BPM)", "type": ""},
                              title="Intensité cardiaque moyenne par discipline")
        fig_hr_type.update_layout(template=PLOTLY_DARK, paper_bgcolor="#13131f",
                                   plot_bgcolor="#13131f", coloraxis_showscale=False,
                                   height=320, margin=dict(l=20, r=20, t=40, b=20))
        fig_hr_type.update_xaxes(gridcolor="#1e1e30")
        st.plotly_chart(fig_hr_type, use_container_width=True)

    # Efficiency Index scatter
    df_ei = df_hr[df_hr["eff_index"] > 0].copy()
    if not df_ei.empty:
        fig_ei = px.scatter(df_ei.sort_values("date_dt"), x="date_dt", y="eff_index",
                             size="distance_km", color="trimp",
                             hover_name="name",
                             color_continuous_scale="RdYlGn",
                             labels={"eff_index": "Efficiency Index (v/FC×100)",
                                     "date_dt": "Date", "trimp": "Stress TRIMP"},
                             title="Efficiency Index dans le temps (↑ = meilleure économie de course)")
        # Tendance (uniquement si statsmodels dispo)
        if TRENDLINE_LOWESS:
            try:
                fig_ei.add_traces(px.scatter(df_ei.sort_values("date_dt"), x="date_dt", y="eff_index",
                                              trendline=TRENDLINE_LOWESS).data[1])
            except Exception:
                pass
        fig_ei.update_layout(template=PLOTLY_DARK, paper_bgcolor="#13131f",
                              plot_bgcolor="#13131f", height=300,
                              margin=dict(l=20, r=20, t=40, b=20))
        fig_ei.update_xaxes(gridcolor="#1e1e30")
        fig_ei.update_yaxes(gridcolor="#1e1e30")
        st.plotly_chart(fig_ei, use_container_width=True)
else:
    st.info("⚠️ Pas de données cardiaques sur les activités récentes. Connecte une ceinture cardio pour débloquer cette section.")

st.markdown("---")


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 5 — PUISSANCE & ÉNERGIE
# ─────────────────────────────────────────────────────────────────────────────
st.markdown('<p class="kiki-header">⚡ Puissance & Énergie Mécanique</p>', unsafe_allow_html=True)
st.markdown('<p class="kiki-sub">W/kg · Joules · FTP estimation · Modèle aérodynamique si pas de capteur</p>', unsafe_allow_html=True)

col_p1, col_p2, col_p3 = st.columns(3)
df_power = df[df["watts_final"] > 10].copy()

with col_p1:
    if not df_power.empty:
        fig_wkg = px.line(df_power.sort_values("date_dt"), x="date_dt", y="w_kg",
                           markers=True, line_shape="spline",
                           color="type",
                           labels={"w_kg": "W/kg", "date_dt": "Date"},
                           title="Évolution du ratio Watts/kg")
        if ftp > 0:
            fig_wkg.add_hline(y=ftp / poids, line_dash="dash",
                               line_color="#ffcc00",
                               annotation_text=f"FTP: {ftp/poids:.2f} W/kg",
                               annotation_font_color="#ffcc00")
        fig_wkg.update_layout(template=PLOTLY_DARK, paper_bgcolor="#13131f",
                               plot_bgcolor="#13131f", height=300,
                               margin=dict(l=20, r=20, t=40, b=20))
        fig_wkg.update_xaxes(gridcolor="#1e1e30")
        fig_wkg.update_yaxes(gridcolor="#1e1e30")
        st.plotly_chart(fig_wkg, use_container_width=True)
    else:
        st.info("Données de puissance insuffisantes.")

with col_p2:
    # Distribution kcal par mois
    df_kcal = df.groupby("mois")["kcal_utiles"].sum().reset_index().sort_values("mois")
    if not df_kcal.empty:
        fig_kcal = px.bar(df_kcal, x="mois", y="kcal_utiles",
                           color="kcal_utiles",
                           color_continuous_scale=["#1e1e30", "#ff4d00"],
                           labels={"kcal_utiles": "kcal", "mois": "Mois"},
                           title="Énergie dépensée par mois (kcal mécaniques)")
        fig_kcal.update_layout(template=PLOTLY_DARK, paper_bgcolor="#13131f",
                                plot_bgcolor="#13131f", coloraxis_showscale=False,
                                height=300, margin=dict(l=20, r=20, t=40, b=20))
        fig_kcal.update_xaxes(gridcolor="#1e1e30", tickangle=45)
        fig_kcal.update_yaxes(gridcolor="#1e1e30")
        st.plotly_chart(fig_kcal, use_container_width=True)

with col_p3:
    # Puissance vs gradient (efficacité en pente)
    df_pg = df[(df["gradient"] > 1) & (df["watts_final"] > 10)].copy()
    if not df_pg.empty:
        fig_pg = px.scatter(df_pg, x="gradient", y="watts_final",
                             size="distance_km", hover_name="name",
                             color="w_kg",
                             color_continuous_scale="Viridis",
                             labels={"gradient": "Gradient Moyen (%)",
                                     "watts_final": "Puissance (W)", "w_kg": "W/kg"},
                             title="Puissance vs Pente (efficacité en montée)")
        fig_pg.update_layout(template=PLOTLY_DARK, paper_bgcolor="#13131f",
                              plot_bgcolor="#13131f", height=300,
                              margin=dict(l=20, r=20, t=40, b=20))
        st.plotly_chart(fig_pg, use_container_width=True)
    else:
        st.info("Pas assez de données puissance + dénivelé.")

# ─── Niveaux W/kg de référence ───
avg_wkg = df_power["w_kg"].mean() if not df_power.empty else 0
st.markdown(f"""
<div style="background:#0f0f1a;border:1px solid #1e1e30;border-radius:8px;padding:1rem 1.5rem;margin-top:0.5rem;">
  <p style="font-family:'Space Mono',monospace;font-size:0.7rem;color:#5555a0;letter-spacing:0.2em;margin:0 0 0.6rem;">
    ⚡ NIVEAUX DE RÉFÉRENCE W/KG (CYCLISME)
  </p>
  <div style="display:flex;gap:2rem;flex-wrap:wrap;">
    {'<span style="color:#3a6fff;font-size:0.78rem;">Débutant: &lt;2.0</span>' if avg_wkg < 2 else '<span style="color:#3a6fff;font-size:0.78rem;opacity:0.4;">Débutant: &lt;2.0</span>'}
    {'<span style="color:#00d264;font-size:0.78rem;font-weight:700;">✓ Amateur: 2.0–3.0</span>' if 2 <= avg_wkg < 3 else '<span style="color:#00d264;font-size:0.78rem;opacity:0.4;">Amateur: 2.0–3.0</span>'}
    {'<span style="color:#ffcc00;font-size:0.78rem;font-weight:700;">✓ Avancé: 3.0–4.0</span>' if 3 <= avg_wkg < 4 else '<span style="color:#ffcc00;font-size:0.78rem;opacity:0.4;">Avancé: 3.0–4.0</span>'}
    {'<span style="color:#ff7040;font-size:0.78rem;font-weight:700;">✓ Elite: 4.0–5.0</span>' if 4 <= avg_wkg < 5 else '<span style="color:#ff7040;font-size:0.78rem;opacity:0.4;">Elite: 4.0–5.0</span>'}
    {'<span style="color:#ff0040;font-size:0.78rem;font-weight:700;">✓ Pro: &gt;5.0 🐐</span>' if avg_wkg >= 5 else '<span style="color:#ff0040;font-size:0.78rem;opacity:0.4;">Pro: &gt;5.0 🐐</span>'}
  </div>
  <p style="font-size:0.72rem;color:#9898c0;margin:0.6rem 0 0;">Ton W/kg moyen : <b style="color:#ff4d00;">{avg_wkg:.2f} W/kg</b></p>
</div>
""", unsafe_allow_html=True)

st.markdown("---")


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 6 — VAM & DÉNIVELÉ
# ─────────────────────────────────────────────────────────────────────────────
st.markdown('<p class="kiki-header">🏔️ VAM & Efficacité en Montagne</p>', unsafe_allow_html=True)
st.markdown('<p class="kiki-sub">Vitesse Ascensionnelle Moyenne · Gradient · Répartition du dénivelé</p>', unsafe_allow_html=True)

col_v1, col_v2 = st.columns(2)

with col_v1:
    df_vam = df[df["total_elevation_gain"] > 30].copy()
    if not df_vam.empty:
        fig_vam = px.scatter(df_vam, x="total_elevation_gain", y="vam",
                              size="distance_km", hover_name="name",
                              color="vitesse_moy_kmh",
                              color_continuous_scale="Plasma",
                              trendline=TRENDLINE_OLS,
                              labels={"total_elevation_gain": "D+ (m)",
                                      "vam": "VAM (m/h)", "vitesse_moy_kmh": "Vitesse (km/h)"},
                              title="VAM vs Dénivelé (taille = distance)")
        fig_vam.update_layout(template=PLOTLY_DARK, paper_bgcolor="#13131f",
                               plot_bgcolor="#13131f", height=340,
                               margin=dict(l=20, r=20, t=40, b=20))
        st.plotly_chart(fig_vam, use_container_width=True)
    else:
        st.info("Pas assez de sorties avec dénivelé.")

with col_v2:
    # Top 10 sorties par VAM
    top_vam = df[df["vam"] > 0].nlargest(10, "vam")[["name", "vam", "total_elevation_gain", "date"]]
    top_vam["vam"] = top_vam["vam"].round(0)
    fig_top_vam = px.bar(top_vam, x="vam", y="name", orientation="h",
                          color="vam",
                          color_continuous_scale=["#1e1e30", "#ff4d00"],
                          labels={"vam": "VAM (m/h)", "name": ""},
                          title="Top 10 sorties par VAM")
    fig_top_vam.update_layout(template=PLOTLY_DARK, paper_bgcolor="#13131f",
                               plot_bgcolor="#13131f", coloraxis_showscale=False,
                               height=340, margin=dict(l=20, r=20, t=40, b=20),
                               yaxis=dict(autorange="reversed"))
    st.plotly_chart(fig_top_vam, use_container_width=True)

# VAM par mois
df_vam_month = df[df["vam"] > 0].groupby("mois")["vam"].mean().reset_index().sort_values("mois")
if not df_vam_month.empty:
    fig_vam_m = px.line(df_vam_month, x="mois", y="vam", markers=True,
                         labels={"vam": "VAM Moy (m/h)", "mois": "Mois"},
                         title="Progression de la VAM moyenne mensuelle")
    fig_vam_m.update_traces(line_color="#ff4d00", marker_color="#ff4d00")
    fig_vam_m.update_layout(template=PLOTLY_DARK, paper_bgcolor="#13131f",
                             plot_bgcolor="#13131f", height=250,
                             margin=dict(l=20, r=20, t=40, b=20))
    fig_vam_m.update_xaxes(gridcolor="#1e1e30", tickangle=45)
    fig_vam_m.update_yaxes(gridcolor="#1e1e30")
    st.plotly_chart(fig_vam_m, use_container_width=True)

st.markdown("---")


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 7 — VOLUME & PROGRESSION
# ─────────────────────────────────────────────────────────────────────────────
st.markdown('<p class="kiki-header">📅 Volume & Progression Temporelle</p>', unsafe_allow_html=True)
st.markdown('<p class="kiki-sub">Km par semaine · Charge mensuelle · Distribution des efforts</p>', unsafe_allow_html=True)

col_v1, col_v2 = st.columns(2)

with col_v1:
    # Volume hebdomadaire
    df_weekly = df.groupby(["mois", "semaine"])["distance_km"].sum().reset_index()
    df_weekly["label"] = df_weekly["mois"] + "-S" + df_weekly["semaine"].astype(str)
    fig_weekly = px.bar(df_weekly.tail(20), x="label", y="distance_km",
                         color="distance_km",
                         color_continuous_scale=["#1e1e30", "#ff4d00"],
                         labels={"distance_km": "km", "label": "Semaine"},
                         title="Volume hebdomadaire (20 dernières semaines)")
    fig_weekly.update_layout(template=PLOTLY_DARK, paper_bgcolor="#13131f",
                              plot_bgcolor="#13131f", coloraxis_showscale=False,
                              height=300, margin=dict(l=20, r=20, t=40, b=20))
    fig_weekly.update_xaxes(gridcolor="#1e1e30", tickangle=45)
    fig_weekly.update_yaxes(gridcolor="#1e1e30")
    st.plotly_chart(fig_weekly, use_container_width=True)

with col_v2:
    # Répartition par discipline
    fig_pie = px.pie(df, names="type",
                      title="Répartition des disciplines",
                      color_discrete_sequence=["#ff4d00", "#0080ff", "#00d264",
                                               "#ffcc00", "#9900ff", "#ff0080",
                                               "#00ccff", "#ff6600"])
    fig_pie.update_traces(textposition="inside", textinfo="percent+label",
                           textfont_size=11)
    fig_pie.update_layout(template=PLOTLY_DARK, paper_bgcolor="#13131f",
                           plot_bgcolor="#13131f", showlegend=False,
                           height=300, margin=dict(l=20, r=20, t=40, b=20))
    st.plotly_chart(fig_pie, use_container_width=True)

# Distance cumulée dans le temps
df_cum = df.sort_values("date_dt").copy()
df_cum["km_cumul"] = df_cum["distance_km"].cumsum()
df_cum["dplus_cumul"] = df_cum["total_elevation_gain"].cumsum()

fig_cum = make_subplots(specs=[[{"secondary_y": True}]])
fig_cum.add_trace(
    go.Scatter(x=df_cum["date_dt"], y=df_cum["km_cumul"],
               name="Km cumulés", fill="tozeroy",
               line=dict(color="#ff4d00"), fillcolor="rgba(255,77,0,0.15)"),
    secondary_y=False
)
fig_cum.add_trace(
    go.Scatter(x=df_cum["date_dt"], y=df_cum["dplus_cumul"],
               name="D+ cumulé", line=dict(color="#0080ff", dash="dot")),
    secondary_y=True
)
fig_cum.update_layout(
    template=PLOTLY_DARK, paper_bgcolor="#13131f", plot_bgcolor="#13131f",
    title="Distance et dénivelé cumulés (progression globale)",
    height=280, margin=dict(l=20, r=20, t=40, b=20),
    legend=dict(orientation="h", y=-0.2)
)
fig_cum.update_yaxes(title_text="Km cumulés", secondary_y=False, gridcolor="#1e1e30")
fig_cum.update_yaxes(title_text="D+ cumulé (m)", secondary_y=True, gridcolor="#1e1e30")
st.plotly_chart(fig_cum, use_container_width=True)

st.markdown("---")


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 8 — PROFIL VO2MAX & PHYSIOLOGIE
# ─────────────────────────────────────────────────────────────────────────────
st.markdown('<p class="kiki-header">🫁 Profil VO₂Max & Capacité Aérobie</p>', unsafe_allow_html=True)
st.markdown('<p class="kiki-sub">Estimation multi-méthodes · Niveaux de référence · Zones d\'intensité</p>', unsafe_allow_html=True)

col_ph1, col_ph2 = st.columns([2, 1])

with col_ph1:
    # Radar profil athlète (métriques normalisées)
    categories = ["Volume (km)", "Dénivelé D+", "Intensité TRIMP", "Efficacité VAM", "Puissance W/kg"]
    # Normalisation sur 100
    max_km    = 2000
    max_dplus = 50000
    max_trimp = 3000
    max_vam   = 1500
    max_wkg   = 6

    vals = [
        min(df["distance_km"].sum() / max_km * 100, 100),
        min(df["total_elevation_gain"].sum() / max_dplus * 100, 100),
        min(df["trimp"].sum() / max_trimp * 100, 100),
        min(df["vam"].max() / max_vam * 100, 100),
        min(df["w_kg"].max() / max_wkg * 100, 100),
    ]

    fig_radar = go.Figure()
    fig_radar.add_trace(go.Scatterpolar(
        r=vals + [vals[0]],
        theta=categories + [categories[0]],
        fill="toself",
        fillcolor="rgba(255,77,0,0.2)",
        line=dict(color="#ff4d00", width=2),
        name=ath_name
    ))
    fig_radar.update_layout(
        polar=dict(
            radialaxis=dict(visible=True, range=[0, 100], gridcolor="#1e1e30",
                            tickfont=dict(color="#5555a0", size=9)),
            angularaxis=dict(gridcolor="#1e1e30", tickfont=dict(color="#9898c0", size=11)),
            bgcolor="#13131f"
        ),
        showlegend=False,
        template=PLOTLY_DARK,
        paper_bgcolor="#13131f",
        title="Profil Athlète (score sur 100 vs niveaux référence)",
        height=380, margin=dict(l=20, r=20, t=50, b=20)
    )
    st.plotly_chart(fig_radar, use_container_width=True)

with col_ph2:
    # VO2 max estimations
    st.markdown(f"""
    <div style="background:#13131f;border:1px solid #ff4d00;border-radius:8px;padding:1.2rem;margin-bottom:0.8rem;">
      <p style="font-family:'Space Mono',monospace;font-size:0.65rem;color:#ff4d00;letter-spacing:0.2em;margin:0 0 0.8rem;">VO₂MAX ESTIMATIONS</p>
      <p style="font-size:0.75rem;color:#9898c0;margin:0 0 0.3rem;">Méthode Uth-Sørensen (FC):</p>
      <p style="font-family:'Space Mono',monospace;font-size:1.4rem;color:#ff4d00;font-weight:700;margin:0 0 0.8rem;">{vo2max_basale:.1f} ml/kg/min</p>
      {"<p style='font-size:0.75rem;color:#9898c0;margin:0 0 0.3rem;'>Méthode Jack Daniels (vitesse/run):</p><p style='font-family:Space Mono,monospace;font-size:1.4rem;color:#00d264;font-weight:700;margin:0 0 0.8rem;'>" + f"{vo2max_dynamique:.1f} ml/kg/min</p>" if vo2max_dynamique else ""}
    </div>
    """, unsafe_allow_html=True)

    # Tableau niveaux VO2
    vo2_ref = [
        ("Mauvais", "< 35", "#ff0040"),
        ("Passable", "35–45", "#ff7040"),
        ("Bon", "45–55", "#ffcc00"),
        ("Très bon", "55–65", "#00d264"),
        ("Excellent", "> 65", "#3a6fff"),
    ]
    for level, range_str, color in vo2_ref:
        is_current = False
        try:
            lo = float(range_str.split("–")[0].replace("<", "0").replace(">", ""))
            hi = float(range_str.split("–")[-1].replace("<", "35").replace(">", "999").replace("65", "65"))
            is_current = lo <= athlete_vo2 < hi
        except Exception:
            pass
        bold = "font-weight:700; background:#1a0a00;" if is_current else "opacity:0.55;"
        st.markdown(f"""
        <div style="display:flex;justify-content:space-between;padding:0.3rem 0.5rem;
                    border-left: 2px solid {color if is_current else '#1e1e30'};
                    margin-bottom:2px;{bold}border-radius:4px;">
          <span style="font-size:0.75rem;color:{color};">{level}</span>
          <span style="font-family:'Space Mono',monospace;font-size:0.72rem;color:#9898c0;">{range_str}</span>
        </div>
        """, unsafe_allow_html=True)

st.markdown("---")


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 9 — ANALYSE COURSE À PIED DÉTAILLÉE
# ─────────────────────────────────────────────────────────────────────────────
if not df_run.empty:
    st.markdown('<p class="kiki-header">👟 Analyse Course à Pied</p>', unsafe_allow_html=True)
    st.markdown('<p class="kiki-sub">Allure · Cadence · Évolution · Meilleures sorties</p>', unsafe_allow_html=True)

    col_r1, col_r2 = st.columns(2)

    with col_r1:
        # Allure dans le temps
        df_run_s = df_run[df_run["average_speed"] > 0].sort_values("date_dt")
        df_run_s["allure_minkm"] = 1000 / df_run_s["average_speed"] / 60
        fig_allure = px.scatter(df_run_s, x="date_dt", y="allure_minkm",
                                 size="distance_km",
                                 color="total_elevation_gain",
                                 color_continuous_scale="Burg",
                                 hover_name="name",
                                 trendline=TRENDLINE_LOWESS,
                                 labels={"allure_minkm": "Allure (min/km)", "date_dt": "Date"},
                                 title="Évolution de l'allure (↓ = plus rapide)")
        fig_allure.update_yaxes(autorange="reversed")
        fig_allure.update_layout(template=PLOTLY_DARK, paper_bgcolor="#13131f",
                                  plot_bgcolor="#13131f", height=320,
                                  margin=dict(l=20, r=20, t=40, b=20))
        st.plotly_chart(fig_allure, use_container_width=True)

    with col_r2:
        # Distance vs élévation scatter
        fig_run_perf = px.scatter(df_run, x="distance_km", y="vitesse_moy_kmh",
                                   size="durée_min",
                                   color="trimp",
                                   color_continuous_scale="Hot",
                                   hover_name="name",
                                   labels={"distance_km": "Distance (km)",
                                           "vitesse_moy_kmh": "Vitesse Moy (km/h)",
                                           "trimp": "Stress TRIMP"},
                                   title="Vitesse moyenne selon la distance")
        fig_run_perf.update_layout(template=PLOTLY_DARK, paper_bgcolor="#13131f",
                                    plot_bgcolor="#13131f", height=320,
                                    margin=dict(l=20, r=20, t=40, b=20))
        st.plotly_chart(fig_run_perf, use_container_width=True)

    # Stats résumé run
    cr1, cr2, cr3, cr4 = st.columns(4)
    cr1.metric("Km Run Total",       f"{df_run['distance_km'].sum():.0f} km")
    cr2.metric("Allure Médiane",      fmt_pace(df_run["average_speed"].median()))
    cr3.metric("D+ Run Total",        f"{df_run['total_elevation_gain'].sum():.0f} m+")
    cr4.metric("Nb Sorties",          f"{len(df_run)}")

    st.markdown("---")


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 10 — ANALYSE VÉLO DÉTAILLÉE
# ─────────────────────────────────────────────────────────────────────────────
if not df_ride.empty:
    st.markdown('<p class="kiki-header">🚴 Analyse Cyclisme</p>', unsafe_allow_html=True)
    st.markdown('<p class="kiki-sub">Puissance · VAM · Kilomètres · Comparaison avec niveaux UCI</p>', unsafe_allow_html=True)

    col_cy1, col_cy2 = st.columns(2)

    with col_cy1:
        fig_ride_watt = px.scatter(df_ride[df_ride["watts_final"] > 10], x="distance_km", y="watts_final",
                                    color="total_elevation_gain",
                                    color_continuous_scale="Viridis",
                                    size="durée_min",
                                    hover_name="name",
                                    trendline=TRENDLINE_OLS,
                                    labels={"distance_km": "Distance (km)", "watts_final": "Puissance (W)"},
                                    title="Puissance vs Distance (vélo)")
        fig_ride_watt.update_layout(template=PLOTLY_DARK, paper_bgcolor="#13131f",
                                     plot_bgcolor="#13131f", height=320,
                                     margin=dict(l=20, r=20, t=40, b=20))
        st.plotly_chart(fig_ride_watt, use_container_width=True)

    with col_cy2:
        fig_ride_speed = px.histogram(df_ride, x="vitesse_moy_kmh",
                                       nbins=20,
                                       color_discrete_sequence=["#ff4d00"],
                                       labels={"vitesse_moy_kmh": "Vitesse (km/h)"},
                                       title="Distribution des vitesses moyennes (vélo)")
        fig_ride_speed.update_layout(template=PLOTLY_DARK, paper_bgcolor="#13131f",
                                      plot_bgcolor="#13131f", height=320,
                                      margin=dict(l=20, r=20, t=40, b=20))
        fig_ride_speed.update_xaxes(gridcolor="#1e1e30")
        fig_ride_speed.update_yaxes(gridcolor="#1e1e30")
        st.plotly_chart(fig_ride_speed, use_container_width=True)

    cy1, cy2, cy3, cy4 = st.columns(4)
    cy1.metric("Km Vélo Total",     f"{df_ride['distance_km'].sum():.0f} km")
    cy2.metric("Vitesse Moy Ride",  f"{df_ride['vitesse_moy_kmh'].mean():.1f} km/h")
    cy3.metric("Puissance Moy",     f"{df_ride['watts_final'].mean():.0f} W")
    cy4.metric("D+ Vélo Total",     f"{df_ride['total_elevation_gain'].sum():.0f} m+")

    st.markdown("---")


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 11 — FICHE DE STATS "PARTAGER AVEC TES POTES"
# ─────────────────────────────────────────────────────────────────────────────
st.markdown('<p class="kiki-header">📋 Fiche Stats — Compare avec tes Potes</p>', unsafe_allow_html=True)
st.markdown('<p class="kiki-sub">Ton profil en un coup d\'œil · Ready to flex</p>', unsafe_allow_html=True)

fiche_cols = st.columns(3)

with fiche_cols[0]:
    st.markdown(f"""
    <div style="background:#13131f;border:1px solid #1e1e30;border-radius:10px;padding:1.2rem;height:100%;">
      <p style="font-family:'Space Mono',monospace;font-size:0.65rem;color:#6868a0;letter-spacing:0.2em;margin:0 0 1rem;">🏃 RUNNING</p>
      {'<p style="font-size:0.75rem;color:#9898c0;margin:0.15rem 0;">Km parcourus : <b style="color:#e8e8f0;font-family:Space Mono,monospace;">' + f"{df_run['distance_km'].sum():.0f} km</b></p>" if not df_run.empty else "<p style='color:#5555a0;font-size:0.75rem;'>Aucun run détecté</p>"}
      {'<p style="font-size:0.75rem;color:#9898c0;margin:0.15rem 0;">Allure médiane : <b style="color:#e8e8f0;font-family:Space Mono,monospace;">' + fmt_pace(df_run["average_speed"].median()) + "</b></p>" if not df_run.empty else ""}
      {'<p style="font-size:0.75rem;color:#9898c0;margin:0.15rem 0;">Vitesse max sortie : <b style="color:#ff4d00;font-family:Space Mono,monospace;">' + f"{df_run['vitesse_moy_kmh'].max():.1f} km/h</b></p>" if not df_run.empty else ""}
      {'<p style="font-size:0.75rem;color:#9898c0;margin:0.15rem 0;">Nb sorties run : <b style="color:#e8e8f0;font-family:Space Mono,monospace;">' + f"{len(df_run)}</b></p>" if not df_run.empty else ""}
    </div>
    """, unsafe_allow_html=True)

with fiche_cols[1]:
    st.markdown(f"""
    <div style="background:#13131f;border:1px solid #1e1e30;border-radius:10px;padding:1.2rem;height:100%;">
      <p style="font-family:'Space Mono',monospace;font-size:0.65rem;color:#6868a0;letter-spacing:0.2em;margin:0 0 1rem;">🚴 CYCLISME</p>
      {'<p style="font-size:0.75rem;color:#9898c0;margin:0.15rem 0;">Km parcourus : <b style="color:#e8e8f0;font-family:Space Mono,monospace;">' + f"{df_ride['distance_km'].sum():.0f} km</b></p>" if not df_ride.empty else "<p style='color:#5555a0;font-size:0.75rem;'>Aucun ride détecté</p>"}
      {'<p style="font-size:0.75rem;color:#9898c0;margin:0.15rem 0;">W/kg moyen : <b style="color:#ff4d00;font-family:Space Mono,monospace;">' + f"{df_ride['w_kg'].mean():.2f} W/kg</b></p>" if not df_ride.empty else ""}
      {'<p style="font-size:0.75rem;color:#9898c0;margin:0.15rem 0;">Vitesse moy ride : <b style="color:#e8e8f0;font-family:Space Mono,monospace;">' + f"{df_ride['vitesse_moy_kmh'].mean():.1f} km/h</b></p>" if not df_ride.empty else ""}
      {'<p style="font-size:0.75rem;color:#9898c0;margin:0.15rem 0;">Nb sorties vélo : <b style="color:#e8e8f0;font-family:Space Mono,monospace;">' + f"{len(df_ride)}</b></p>" if not df_ride.empty else ""}
    </div>
    """, unsafe_allow_html=True)

with fiche_cols[2]:
    st.markdown(f"""
    <div style="background:#13131f;border:1px solid #ff4d00;border-radius:10px;padding:1.2rem;height:100%;">
      <p style="font-family:'Space Mono',monospace;font-size:0.65rem;color:#ff4d00;letter-spacing:0.2em;margin:0 0 1rem;">⚡ GLOBAL</p>
      <p style="font-size:0.75rem;color:#9898c0;margin:0.15rem 0;">VO₂max estimé : <b style="color:#ff4d00;font-family:Space Mono,monospace;">{athlete_vo2:.1f} ml/kg/min</b></p>
      <p style="font-size:0.75rem;color:#9898c0;margin:0.15rem 0;">Volume total : <b style="color:#e8e8f0;font-family:Space Mono,monospace;">{df['distance_km'].sum():.0f} km</b></p>
      <p style="font-size:0.75rem;color:#9898c0;margin:0.15rem 0;">D+ total : <b style="color:#e8e8f0;font-family:Space Mono,monospace;">{df['total_elevation_gain'].sum():.0f} m+</b></p>
      <p style="font-size:0.75rem;color:#9898c0;margin:0.15rem 0;">Charge totale : <b style="color:#e8e8f0;font-family:Space Mono,monospace;">{df['trimp'].sum():.0f} TRIMP</b></p>
      <p style="font-size:0.75rem;color:#9898c0;margin:0.15rem 0;">Heures d'effort : <b style="color:#e8e8f0;font-family:Space Mono,monospace;">{df['durée_min'].sum()/60:.0f}h</b></p>
    </div>
    """, unsafe_allow_html=True)

st.markdown("---")


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 12 — EXTRACTION DATA RAW
# ─────────────────────────────────────────────────────────────────────────────
st.markdown('<p class="kiki-header">🔬 Extraction Chirurgicale des Données</p>', unsafe_allow_html=True)
st.markdown('<p class="kiki-sub">Toutes les activités · Tri personnalisable</p>', unsafe_allow_html=True)

cols_show = ["date", "name", "type", "distance_km", "durée_min", "vitesse_moy_kmh",
             "total_elevation_gain", "gradient", "vam", "trimp", "watts_final", "w_kg",
             "kcal_utiles", "eff_index", "acwr"]
existing_cols = [c for c in cols_show if c in df.columns]

df_display = df[existing_cols].sort_values("date", ascending=False).copy()
# Arrondir les floats pour la lisibilité
float_cols = ["distance_km", "durée_min", "vitesse_moy_kmh", "gradient",
              "vam", "trimp", "watts_final", "w_kg", "kcal_utiles", "eff_index", "acwr"]
for c in float_cols:
    if c in df_display.columns:
        df_display[c] = df_display[c].round(2)

st.dataframe(df_display, use_container_width=True, height=420)

# ─────────────────────────────────────────────────────────────────────────────
# FOOTER
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("""
<div style="margin-top:3rem; text-align:center; padding:1.5rem;
            border-top: 1px solid #1e1e30;">
  <p style="font-family:'Space Mono',monospace;font-size:0.65rem;
            color:#333355;letter-spacing:0.2em;">
    ⚡ KIKIMETER ANALYTIQUE · POWERED BY STRAVA API · FORMULES : TRIMP EDWARD · KARVONEN · JACK DANIELS · MODÈLE AÉRODYNAMIQUE
  </p>
</div>
""", unsafe_allow_html=True)
