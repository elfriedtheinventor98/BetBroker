import streamlit as st
import requests
import numpy as np
from scipy.stats import poisson

# === Configuration API ===
API_KEY = "votre_cle_api"
BASE_URL = "https://api.football-data.org/v4/"

# === Recherche d’équipe ===
def get_team_id_by_name(team_name):
    headers = {"X-Auth-Token": API_KEY}
    response = requests.get(f"{BASE_URL}/teams", headers=headers)
    teams = response.json().get("teams", [])
    for team in teams:
        if team_name.lower() in team["name"].lower():
            return team["id"]
    return None

# === Fonctions d’analyse ===
def get_team_data(team_id):
    headers = {"X-Auth-Token": API_KEY}
    response = requests.get(f"{BASE_URL}/teams/{team_id}/matches?limit=10", headers=headers)
    return response.json()["matches"]

def calculate_key_metrics(matches, team_id):
    goals_scored = []
    goals_conceded = []
    results = []

    for match in matches:
        if match["homeTeam"]["id"] == team_id:
            goals_scored.append(match["score"]["fullTime"]["home"])
            goals_conceded.append(match["score"]["fullTime"]["away"])
            results.append("win" if match["score"]["fullTime"]["home"] > match["score"]["fullTime"]["away"]
                           else "draw" if match["score"]["fullTime"]["home"] == match["score"]["fullTime"]["away"]
                           else "loss")
        else:
            goals_scored.append(match["score"]["fullTime"]["away"])
            goals_conceded.append(match["score"]["fullTime"]["home"])
            results.append("win" if match["score"]["fullTime"]["away"] > match["score"]["fullTime"]["home"]
                           else "draw" if match["score"]["fullTime"]["away"] == match["score"]["fullTime"]["home"]
                           else "loss")

    return {
        "avg_goals_scored": np.mean(goals_scored),
        "avg_goals_conceded": np.mean(goals_conceded),
        "win_rate": results.count("win") / len(results),
        "draw_rate": results.count("draw") / len(results),
        "loss_rate": results.count("loss") / len(results),
        "dc_success_rate": (results.count("win") + results.count("draw")) / len(results)
    }

def identify_favorite(team1_data, team2_data):
    team1_strength = team1_data["win_rate"] * 0.7 + team1_data["dc_success_rate"] * 0.3
    team2_strength = team2_data["win_rate"] * 0.7 + team2_data["dc_success_rate"] * 0.3
    if abs(team1_strength - team2_strength) < 0.15:
        return None, "Équipes trop proches"
    return ("team1", team1_data) if team1_strength > team2_strength else ("team2", team2_data)

def calculate_poisson_probability(avg_goals):
    return 1 - poisson.pmf(0, avg_goals)

def sophisticated_prediction(team1_id, team2_id):
    team1_matches = get_team_data(team1_id)
    team2_matches = get_team_data(team2_id)

    team1_data = calculate_key_metrics(team1_matches, team1_id)
    team2_data = calculate_key_metrics(team2_matches, team2_id)

    favorite, fav_data = identify_favorite(team1_data, team2_data)
    if not favorite:
        return "Aucun favori clair - Recommandation: +0.5 but global"
    
    underdog_data = team2_data if favorite == "team1" else team1_data
    underdog = "Équipe 2" if favorite == "team1" else "Équipe 1"

    udg_score_prob = calculate_poisson_probability(
        underdog_data["avg_goals_scored"] * (1 + fav_data["avg_goals_conceded"])
    )
    udg_dc_prob = underdog_data["dc_success_rate"]

    if udg_score_prob > 0.65 and udg_dc_prob > 0.55:
        return f"🔥 Valeur détectée ! Double Chance {underdog}"
    elif udg_score_prob > 0.60:
        return f"💡 Opportunité : +0.5 but pour {underdog} (Probabilité : {udg_score_prob:.2%})"
    elif udg_dc_prob > 0.60:
        return f"🛡️ Double Chance {underdog} (Probabilité : {udg_dc_prob:.2%})"
    elif (1 - udg_score_prob) > 0.70:
        return f"✅ Le favori domine - Double Chance {favorite} recommandé"
    else:
        return "⚖️ Option conservative : +0.5 but global"

# === Interface Streamlit stylisée ===
st.set_page_config(page_title="Prédiction Football ⚽", page_icon="⚽", layout="centered")

st.markdown("""
    <div style='text-align: center;'>
        <img src="https://upload.wikimedia.org/wikipedia/commons/6/6e/Football_Logo.png" width="120">
        <h1 style='color: #1e90ff;'>🔮 Prédiction de Match de Football</h1>
        <p style='font-size: 18px;'>Entrez les noms de deux équipes pour obtenir une prédiction intelligente basée sur les données récentes.</p>
    </div>
""", unsafe_allow_html=True)

team1_name = st.text_input("⚽ Nom de l'équipe 1")
team2_name = st.text_input("⚽ Nom de l'équipe 2")

if st.button("Lancer la prédiction 🚀"):
    if team1_name and team2_name:
        team1_id = get_team_id_by_name(team1_name)
        team2_id = get_team_id_by_name(team2_name)

        if not team1_id or not team2_id:
            st.error("❌ Impossible de trouver l'une des équipes. Vérifiez les noms.")
        else:
            with st.spinner("🔍 Analyse en cours..."):
                try:
                    result = sophisticated_prediction(team1_id, team2_id)
                    st.success(result)
                except Exception as e:
                    st.error(f"⚠️ Erreur lors de la prédiction: {e}")
    else:
        st.warning("Veuillez remplir les deux champs.")
