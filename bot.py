import os
import requests
from flask import Flask, request

TOKEN = os.environ["BOT_TOKEN"]
PUBLIC_URL = os.environ["PUBLIC_URL"]
ADMIN_GROUP_ID = os.environ.get("ADMIN_GROUP_ID")
CHANNEL_ID = os.environ.get("CHANNEL_ID")

API = f"https://api.telegram.org/bot{TOKEN}"
app = Flask(__name__)

user_steps = {}


def send_message(chat_id, text, reply_markup=None):
    payload = {"chat_id": chat_id, "text": text}
    if reply_markup:
        payload["reply_markup"] = reply_markup
    requests.post(f"{API}/sendMessage", json=payload)


def edit_message(chat_id, message_id, text):
    requests.post(f"{API}/editMessageText", json={
        "chat_id": chat_id,
        "message_id": message_id,
        "text": text
    })


def create_unique_invite_link():
    response = requests.post(f"{API}/createChatInviteLink", json={
        "chat_id": CHANNEL_ID,
        "member_limit": 1,
        "name": "Invitation adhésion validée"
    })
    data = response.json()
    if not data.get("ok"):
        raise Exception(data)
    return data["result"]["invite_link"]


@app.route("/")
def home():
    return "Bot actif ✅"


@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json()
    print("UPDATE REÇU :", data, flush=True)

    if "callback_query" in data:
        handle_callback(data["callback_query"])
        return "OK", 200

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

    if text == "/channelid":
        send_message(chat_id, f"ID de ce chat/canal :\n{chat_id}")
        return "OK", 200

    if chat_type != "private":
        return "OK", 200

    if text == "/start":
        user_steps[user_id] = {"step": "nom"}
        send_message(chat_id, """👋 Bienvenue !

Ce bot vous permet de demander l'accès au canal Telegram Lyon 1950 pour la saison 2026/2027.

Afin de vérifier votre adhésion, merci de renseigner :

• votre nom
• votre prénom
• votre numéro d'adhésion

⏳ Votre demande sera examinée par un administrateur. Une fois validée, vous recevrez l'accès au canal.

⚠️ Merci de saisir les informations exactement comme elles figurent sur votre adhésion.

➡️ Quel est votre NOM ?""")
        return "OK", 200

    if user_id not in user_steps:
        user_steps[user_id] = {"step": "nom"}
        send_message(chat_id, "➡️ Quel est votre NOM ?")
        return "OK", 200

    step = user_steps[user_id]["step"]

    if step == "nom":
        user_steps[user_id]["nom"] = text.strip()
        user_steps[user_id]["step"] = "prenom"
        send_message(chat_id, "Quel est votre PRÉNOM ?")
        return "OK", 200

    if step == "prenom":
        user_steps[user_id]["prenom"] = text.strip()
        user_steps[user_id]["step"] = "numero"
        send_message(chat_id, "Quel est votre NUMÉRO D’ADHÉSION ?")
        return "OK", 200

    if step == "numero":
        user_steps[user_id]["numero"] = text.strip()

        username = f"@{user.get('username')}" if user.get("username") else "Aucun username"
        tg_name = f"{user.get('first_name', '')} {user.get('last_name', '')}".strip()

        admin_message = f"""📩 Nouvelle demande d’adhésion

👤 Nom : {user_steps[user_id]["nom"]}
👤 Prénom : {user_steps[user_id]["prenom"]}
🎫 N° adhésion : {user_steps[user_id]["numero"]}

📱 Telegram :
Nom Telegram : {tg_name}
Username : {username}
ID Telegram : {user_id}

⏳ En attente de validation"""

        keyboard = {
            "inline_keyboard": [[
                {"text": "✅ Valider", "callback_data": f"approve:{user_id}"},
                {"text": "❌ Refuser", "callback_data": f"reject:{user_id}"}
            ]]
        }

        if ADMIN_GROUP_ID:
            send_message(ADMIN_GROUP_ID, admin_message, keyboard)

        send_message(chat_id, "✅ Merci ! Votre demande a bien été transmise aux administrateurs.")
        del user_steps[user_id]

    return "OK", 200


def handle_callback(callback):
    data = callback["data"]
    admin = callback["from"]
    message = callback["message"]

    admin_name = admin.get("first_name", "Admin")
    chat_id = message["chat"]["id"]
    message_id = message["message_id"]
    original_text = message.get("text", "")

    action, user_id = data.split(":")
    user_id = int(user_id)

    if action == "approve":
        try:
            invite_link = create_unique_invite_link()
            send_message(user_id, f"""✅ Votre demande a été validée.

Voici votre lien d’accès unique au canal Lyon 1950 :

{invite_link}

⚠️ Ce lien est personnel et utilisable une seule fois.""")
            edit_message(chat_id, message_id, original_text + f"\n\n🟢 VALIDÉ par {admin_name}")
        except Exception as e:
            send_message(chat_id, f"❌ Erreur lors de la création du lien :\n{e}")

    if action == "reject":
        send_message(user_id, "❌ Votre demande d’accès au canal Lyon 1950 n’a pas été validée.")
        edit_message(chat_id, message_id, original_text + f"\n\n🔴 REFUSÉ par {admin_name}")

    requests.post(f"{API}/answerCallbackQuery", json={
        "callback_query_id": callback["id"]
    })


requests.get(f"{API}/setWebhook", params={"url": f"{PUBLIC_URL}/webhook"})
print("Webhook configuré", flush=True)
