import streamlit as st
import pandas as pd
import requests
import plotly.express as px
import os
import math

# Configuration de la page Streamlit
st.set_page_config(page_title="Kikimeter Sportif - Analyser", page_icon="⚡", layout="wide")

# Récupération des variables d'environnement (Coolify)
CLIENT_ID = os.environ.get("STRAVA_CLIENT_ID")
CLIENT_SECRET = os.environ.get("STRAVA_CLIENT_SECRET")
# L'URL de ton application (ex: https://stats.tondomaine.com)
APP_URL = os.environ.get("APP_URL", "http://localhost:8501")

st.title("⚡ Le Kikimeter Analytique")
st.subheader("Importation Strava en 1 clic & Autopsie des performances")

# --- SIDEBAR : PARAMÈTRES PHYSIOLOGIQUES ---
st.sidebar.header("🏃‍♂️ Profil de l'Athlète")
poids = st.sidebar.number_input("Poids (kg)", min_value=40, max_value=150, value=64, step=1)
fc_max = st.sidebar.number_input("Fréquence Cardiaque Max (BPM)", min_value=140, max_value=220, value=190)
fc_repos = st.sidebar.number_input("Fréquence Cardiaque Repos (BPM)", min_value=35, max_value=90, value=55)

# --- LOGIQUE D'AUTHENTIFICATION OAUTH2 STRAVA ---
if "strava_token" not in st.session_state:
    # Récupération du code dans l'URL après redirection Strava
    query_params = st.query_params
    if "code" in query_params:
        auth_code = query_params["code"]
        # Échange du code contre un Access Token
        token_url = "https://www.strava.com/oauth/token"
        payload = {
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "code": auth_code,
            "grant_type": "authorization_code"
        }
        res = requests.post(token_url, data=payload)
        if res.status_code == 200:
            st.session_state["strava_token"] = res.json()["access_token"]
            st.rerun()
        else:
            st.error("Échec de la récupération du token Strava. Vérifie tes clés API.")
    else:
        # Affichage du bouton de connexion initial
        st.info("Aucune donnée importée. Connecte un compte pour lancer l'analyse.")
        authorize_url = f"https://www.strava.com/oauth/authorize?client_id={CLIENT_ID}&redirect_uri={APP_URL}&response_type=code&scope=activity:read_all"
        st.markdown(f'<a href="{authorize_url}" target="_self"><button style="background-color: #FC4C02; color: white; border: none; padding: 12px 24px; font-size: 16px; border-radius: 4px; cursor: pointer; font-weight: bold;">🔗 Se connecter avec Strava</button></a>', unsafe_allowed_html=True)

# --- TRAITEMENT ET AFFICHAGE DES DONNÉES ---
if "strava_token" in st.session_state:
    token = st.session_state["strava_token"]
    
    # Bouton pour clear la session si besoin de changer de compte
    if st.sidebar.button("🔴 Déconnecter le compte"):
        del st.session_state["strava_token"]
        st.rerun()

    # Récupération des 100 dernières activités
    with st.spinner("Aspiration des données Strava..."):
        headers = {"Authorization": f"Bearer {token}"}
        activities_url = "https://www.strava.com/api/v3/athlete/activities?per_page=100"
        response = requests.get(activities_url, headers=headers)
        
    if response.status_code == 200:
        data = response.json()
        if not data:
            st.warning("Aucune activité trouvée sur ce compte Strava.")
        else:
            df = pd.DataFrame(data)

            # --- NETTOYAGE & CONVERSIONS BRUTES ---
            df["distance_km"] = df["distance"] / 1000
            df["durée_min"] = df["moving_time"] / 60
            df["vitesse_moy_kmh"] = df["average_speed"] * 3.6
            df["date"] = pd.to_datetime(df["start_date_local"]).dt.date

            # --- APPLICATION DES FORMULES PHYSIOLOGIQUES ---
            # 1. Estimation VO2 Max (Formule Uth-Sørensen-Overgaard-Pedersen)
            vo2_max_est = 15.3 * (fc_max / fc_repos)

            # 2. VAM (Vitesse Ascensionnelle Moyenne en m/h)
            df["vam"] = df.apply(lambda row: (row["total_elevation_gain"] / (row["moving_time"] / 3600)) if row["moving_time"] > 0 else 0, axis=1)

            # 3. TRIMP (Training Impulse - Charge de stress cardiaque)
            def calc_trimp(row):
                if "average_heartrate" in row and pd.notnull(row["average_heartrate"]):
                    # Calcul de la Fréquence Cardiaque de Réserve (HRR)
                    hrr = (row["average_heartrate"] - fc_repos) / (fc_max - fc_repos)
                    hrr = max(0, min(1, hrr)) # Clamping entre 0 et 1
                    # Formule TRIMP d'Edward
                    factor = 0.64 * math.exp(1.92 * hrr)
                    return row["durée_min"] * hrr * factor
                return 0

            df["trimp"] = df.apply(calc_trimp, axis=1)

            # 4. Ratio Puissance / Poids (W/kg)
            if "device_watts" in df.columns:
                df["w_kg"] = df.apply(lambda row: (row["average_watts"] / poids) if row["device_watts"] and "average_watts" in row else 0, axis=1)
            else:
                df["w_kg"] = 0

            # --- AFFICHAGE DES METRICS GLOBALES (KPIs) ---
            st.markdown("### 📊 Tableau des Scores")
            kpi1, kpi2, kpi3, kpi4 = st.columns(4)
            kpi1.metric(label="Estimation VO2 Max Basale", value=f"{vo2_max_est:.1f} ml/kg/min")
            kpi2.metric(label="Volume Total Analysé", value=f"{df['distance_km'].sum():.1f} Km")
            kpi3.metric(label="Dénivelé Cumulé", value=f"{df['total_elevation_gain'].sum():.0f} m+")
            kpi4.metric(label="Mine la plus violente (Max TRIMP)", value=f"{df['trimp'].max():.0f} pts")

            st.markdown("---")

            # --- SECTIONS GRAPHIQUES ---
            col1, col2 = st.columns(2)

            with col1:
                st.markdown("#### ⚡ Intensité Cardiaque & Stress (TRIMP) par Sortie")
                if "average_heartrate" in df.columns and df["average_heartrate"].notnull().any():
                    fig_trimp = px.bar(df, x="date", y="trimp", color="trimp",
                                       labels={"trimp": "Score TRIMP (Stress)"},
                                       title="Évolution de la charge d'entraînement (Plus c'est haut, plus ça a souffert)",
                                       color_continuous_scale="Reds")
                    st.plotly_chart(fig_trimp, use_container_width=True)
                else:
                    st.info("Données cardiaques indisponibles sur les dernières sorties pour calculer le TRIMP.")

            with col2:
                st.markdown("#### 🏔️ Analyse VAM (Vitesse Ascensionnelle Moyenne)")
                fig_vam = px.scatter(df[df["total_elevation_gain"] > 20], x="total_elevation_gain", y="vam", 
                                     size="distance_km", hover_name="name",
                                     labels={"total_elevation_gain": "Dénivelé Positif (m)", "vam": "VAM (m/h)"},
                                     title="Efficacité en montée (VAM) vs Dénivelé de la sortie",
                                     color="vitesse_moy_kmh", color_continuous_scale="Viridis")
                st.plotly_chart(fig_vam, use_container_width=True)

            col3, col4 = st.columns(2)

            with col3:
                st.markdown("#### 🚴‍♂️ Rapport Puissance / Poids Élitiste")
                if "w_kg" in df.columns and df["w_kg"].max() > 0:
                    fig_watts = px.line(df[df["w_kg"] > 0], x="date", y="w_kg", markers=True,
                                        labels={"w_kg": "Watts / kg"},
                                        title="Évolution du ratio Watts/Kg moyen sur les sorties",
                                        line_shape="spline")
                    st.plotly_chart(fig_watts, use_container_width=True)
                else:
                    st.info("Aucun capteur de puissance (Watts) détecté sur les activités récentes.")

            with col4:
                st.markdown("#### 📊 Distribution des types d'efforts")
                fig_pie = px.pie(df, names="type", title="Répartition des disciplines importées")
                st.plotly_chart(fig_pie, use_container_width=True)

            # --- TABLEAU DE DONNÉES RAW BRUTAL ---
            st.markdown("### 🔍 Extraction chirurgicale des données")
            cols_to_show = ["date", "name", "type", "distance_km", "durée_min", "vitesse_moy_kmh", "total_elevation_gain", "vam", "trimp", "w_kg"]
            # Filtrer uniquement les colonnes existantes pour éviter les crashs
            existing_cols = [c for c in cols_to_show if c in df.columns]
            st.dataframe(df[existing_cols].sort_values(by="date", ascending=False), use_container_width=True)

    else:
        st.error(f"Erreur API Strava: {response.status_code}. Impossible de récupérer les activités.")
