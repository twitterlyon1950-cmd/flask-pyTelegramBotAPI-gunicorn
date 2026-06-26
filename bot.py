import os
import requests
from flask import Flask, request

TOKEN = os.environ["BOT_TOKEN"]
PUBLIC_URL = os.environ["PUBLIC_URL"]
ADMIN_GROUP_ID = os.environ.get("ADMIN_GROUP_ID")

API = f"https://api.telegram.org/bot{TOKEN}"
app = Flask(__name__)

user_steps = {}

def send_message(chat_id, text):
    requests.post(f"{API}/sendMessage", json={
        "chat_id": chat_id,
        "text": text
    })

@app.route("/")
def home():
    return "Bot actif ✅"

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json()
    print("UPDATE REÇU :", data, flush=True)

    message = data.get("message")
    if not message:
        return "OK", 200

    chat = message["chat"]
    chat_id = chat["id"]
    chat_type = chat["type"]
    text = message.get("text", "")
    user = message.get("from", {})
    user_id = user["id"]

    if text == "/connect" and chat_type in ["group", "supergroup"]:
        send_message(chat_id, f"✅ Groupe détecté.\n\nADMIN_GROUP_ID :\n{chat_id}")
        return "OK", 200

    if chat_type != "private":
        return "OK", 200

    if text == "/start":
        user_steps[user_id] = {"step": "nom"}
        send_message(chat_id, "👋 Bonjour !\n\nQuel est ton NOM ?")
        return "OK", 200

    if user_id not in user_steps:
        user_steps[user_id] = {"step": "nom"}
        send_message(chat_id, "Quel est ton NOM ?")
        return "OK", 200

    step = user_steps[user_id]["step"]

    if step == "nom":
        user_steps[user_id]["nom"] = text.strip()
        user_steps[user_id]["step"] = "prenom"
        send_message(chat_id, "Quel est ton PRÉNOM ?")
        return "OK", 200

    if step == "prenom":
        user_steps[user_id]["prenom"] = text.strip()
        user_steps[user_id]["step"] = "numero"
        send_message(chat_id, "Quel est ton NUMÉRO D’ADHÉSION ?")
        return "OK", 200

    if step == "numero":
        user_steps[user_id]["numero"] = text.strip()

        username = f"@{user.get('username')}" if user.get("username") else "Aucun username"
        tg_name = f"{user.get('first_name', '')} {user.get('last_name', '')}".strip()

        admin_message = f"""📩 Nouvelle demande d’adhésion

Nom : {user_steps[user_id]["nom"]}
Prénom : {user_steps[user_id]["prenom"]}
N° adhésion : {user_steps[user_id]["numero"]}

Telegram :
Nom Telegram : {tg_name}
Username : {username}
ID Telegram : {user_id}
"""

        if ADMIN_GROUP_ID:
            send_message(ADMIN_GROUP_ID, admin_message)

        send_message(chat_id, "✅ Merci ! Ta demande a bien été transmise aux administrateurs.")
        del user_steps[user_id]

    return "OK", 200

requests.get(f"{API}/setWebhook", params={"url": f"{PUBLIC_URL}/webhook"})
print("Webhook configuré", flush=True)
