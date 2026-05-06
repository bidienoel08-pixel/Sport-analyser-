import os
import re
import requests
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
import anthropic

# Configuration
TELEGRAM_TOKEN = "8603580790:AAG93jkHy5ZvXpKIhgjWR50HaFBp4Kz5IDE"
ANTHROPIC_API_KEY = "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"
RAPIDAPI_KEY = "49f8aff7abmshda9d17505b6aa72p16c975jsn7d1b979f0506"

# Client Claude
claude = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

def get_team_id(team_name):
    url = "https://api-football-v1.p.rapidapi.com/v3/teams"
    headers = {
        "X-RapidAPI-Key": RAPIDAPI_KEY,
        "X-RapidAPI-Host": "api-football-v1.p.rapidapi.com"
    }
    params = {"search": team_name}
    response = requests.get(url, headers=headers, params=params)
    data = response.json()
    if data["results"] > 0:
        teams = data["response"]
        return teams
    return None

def get_team_stats(team_id, league_id, season):
    url = "https://api-football-v1.p.rapidapi.com/v3/teams/statistics"
    headers = {
        "X-RapidAPI-Key": RAPIDAPI_KEY,
        "X-RapidAPI-Host": "api-football-v1.p.rapidapi.com"
    }
    params = {"team": team_id, "league": league_id, "season": season}
    response = requests.get(url, headers=headers, params=params)
    return response.json()

def get_h2h(team1_id, team2_id):
    url = "https://api-football-v1.p.rapidapi.com/v3/fixtures/headtohead"
    headers = {
        "X-RapidAPI-Key": RAPIDAPI_KEY,
        "X-RapidAPI-Host": "api-football-v1.p.rapidapi.com"
    }
    params = {"h2h": f"{team1_id}-{team2_id}", "last": 5}
    response = requests.get(url, headers=headers, params=params)
    return response.json()

def get_last_matches(team_id):
    url = "https://api-football-v1.p.rapidapi.com/v3/fixtures"
    headers = {
        "X-RapidAPI-Key": RAPIDAPI_KEY,
        "X-RapidAPI-Host": "api-football-v1.p.rapidapi.com"
    }
    params = {"team": team_id, "last": 5}
    response = requests.get(url, headers=headers, params=params)
    return response.json()

def analyze_with_claude(team1, team2, last1, last2, h2h):
    prompt = f"""Tu es un expert en analyse de matchs de football.

Voici les données du match {team1} vs {team2} :

FORME RECENTE {team1} (5 derniers matchs) :
{last1}

FORME RECENTE {team2} (5 derniers matchs) :
{last2}

HEAD TO HEAD (5 dernières confrontations) :
{h2h}

Fais une analyse complète et donne un pronostic clair pour ces 6 options :

1️⃣ 1X2 (Victoire équipe 1 / Nul / Victoire équipe 2)
2️⃣ Double Chance
3️⃣ Total buts (Plus ou moins de 2.5)
4️⃣ BTTS - Les deux équipes marquent (Oui ou Non)
5️⃣ Total buts équipe 1 (Plus ou moins de 1.5)
6️⃣ Total buts équipe 2 (Plus ou moins de 1.5)

Pour chaque option indique le niveau de confiance :
🟢 Haute confiance
🟡 Confiance moyenne
🔴 Risqué
"""
    message = claude.messages.create(
        model="claude-opus-4-6",
        max_tokens=1500,
        messages=[{"role": "user", "content": prompt}]
    )
    return message.content[0].text

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "⚽ Bienvenue sur Sport Analyse Bot!\n\n"
        "Commandes disponibles :\n"
        "/analyse Equipe1 vs Equipe2\n"
        "/aide - Voir l'aide\n\n"
        "Exemple : /analyse PSG vs Real Madrid"
    )

async def aide(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📖 AIDE\n\n"
        "Pour analyser un match :\n"
        "/analyse Equipe1 vs Equipe2\n\n"
        "Exemple :\n"
        "/analyse PSG vs Real Madrid\n"
        "/analyse Liverpool vs Arsenal"
    )

async def analyse(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = " ".join(context.args)

    if "vs" not in text.lower():
        await update.message.reply_text(
            "❌ Format incorrect!\n"
            "Utilise : /analyse Equipe1 vs Equipe2"
        )
        return

    parts = re.split(r'\s+vs\s+', text, flags=re.IGNORECASE)
    team1 = parts[0].strip()
    team2 = parts[1].strip()

    await update.message.reply_text(
        f"⏳ Analyse en cours...\n"
        f"🔍 Recherche des données pour {team1} vs {team2}\n"
        f"Patiente 20-30 secondes..."
    )

    try:
        teams1 = get_team_id(team1)
        teams2 = get_team_id(team2)

        if not teams1 or not teams2:
            await update.message.reply_text("❌ Équipe(s) non trouvée(s). Vérifie les noms.")
            return

        if len(teams1) > 1:
            liste = "\n".join([f"{i+1}. {t['team']['name']} ({t['team']['country']})"
                              for i, t in enumerate(teams1[:4])])
            await update.message.reply_text(
                f"Plusieurs équipes trouvées pour '{team1}':\n{liste}\n\n"
                f"Relance avec le nom exact."
            )
            return

        t1_id = teams1[0]["team"]["id"]
        t2_id = teams2[0]["team"]["id"]
        t1_name = teams1[0]["team"]["name"]
        t2_name = teams2[0]["team"]["name"]

        last1 = get_last_matches(t1_id)
        last2 = get_last_matches(t2_id)
        h2h = get_h2h(t1_id, t2_id)

        last1_text = format_matches(last1)
        last2_text = format_matches(last2)
        h2h_text = format_h2h(h2h)

        analyse_text = analyze_with_claude(t1_name, t2_name, last1_text, last2_text, h2h_text)

        header = f"⚽ ANALYSE : {t1_name} vs {t2_name}\n{'='*35}\n\n"
        await update.message.reply_text(header + analyse_text)

    except Exception as e:
        await update.message.reply_text(f"❌ Erreur : {str(e)}")

def format_matches(data):
    if not data or data.get("results", 0) == 0:
        return "Données non disponibles"
    result = ""
    for match in data["response"][:5]:
        home = match["teams"]["home"]["name"]
        away = match["teams"]["away"]["name"]
        gh = match["goals"]["home"]
        ga = match["goals"]["away"]
        result += f"{home} {gh} - {ga} {away}\n"
    return result

def format_h2h(data):
    if not data or data.get("results", 0) == 0:
        return "Pas d'historique disponible"
    result = ""
    for match in data["response"][:5]:
        home = match["teams"]["home"]["name"]
        away = match["teams"]["away"]["name"]
        gh = match["goals"]["home"]
        ga = match["goals"]["away"]
        result += f"{home} {gh} - {ga} {away}\n"
    return result

def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("aide", aide))
    app.add_handler(CommandHandler("analyse", analyse))
    print("Bot démarré !")
    app.run_polling()

if __name__ == "__main__":
    main()