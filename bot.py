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


def answer_callback(callback_id):
    requests.post(f"{API}/answerCallbackQuery", json={
        "callback_query_id": callback_id
    })


def approve_join_request(user_id):
    if not CHANNEL_ID:
        raise Exception("CHANNEL_ID manquant dans Render.")

    response = requests.post(f"{API}/approveChatJoinRequest", json={
        "chat_id": CHANNEL_ID,
        "user_id": user_id
    })

    data = response.json()
    if not data.get("ok"):
        raise Exception(data)


def decline_join_request(user_id):
    if not CHANNEL_ID:
        raise Exception("CHANNEL_ID manquant dans Render.")

    response = requests.post(f"{API}/declineChatJoinRequest", json={
        "chat_id": CHANNEL_ID,
        "user_id": user_id
    })

    data = response.json()
    if not data.get("ok"):
        raise Exception(data)


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

    message = data.get("message") or data.get("channel_post")

    if not message:
        return "OK", 200

    chat = message["chat"]
    chat_id = chat["id"]
    chat_type = chat["type"]
    text = message.get("text", "")
    user = message.get("from", {})
    user_id = user.get("id")

    if chat_type == "channel":
        print("CHANNEL_ID =", chat_id, flush=True)
        return "OK", 200

    if text == "/connect" and chat_type in ["group", "supergroup"]:
        send_message(chat_id, f"✅ Groupe détecté.\n\nADMIN_GROUP_ID :\n{chat_id}")
        return "OK", 200

    if text == "/channelid":
        send_message(chat_id, f"ID de ce chat :\n{chat_id}")
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
            approve_join_request(user_id)

            send_message(user_id, """✅ Votre demande a été validée.

Vous avez maintenant accès au canal Telegram Lyon 1950.""")

            edit_message(
                chat_id,
                message_id,
                original_text + f"\n\n🟢 VALIDÉ par {admin_name}"
            )

        except Exception as e:
            send_message(chat_id, f"❌ Erreur lors de la validation :\n{e}")

    if action == "reject":
        try:
            decline_join_request(user_id)

            send_message(
                user_id,
                "❌ Votre demande d’accès au canal Lyon 1950 n’a pas été validée."
            )

            edit_message(
                chat_id,
                message_id,
                original_text + f"\n\n🔴 REFUSÉ par {admin_name}"
            )

        except Exception as e:
            send_message(chat_id, f"❌ Erreur lors du refus :\n{e}")

    answer_callback(callback["id"])


requests.get(f"{API}/setWebhook", params={
    "url": f"{PUBLIC_URL}/webhook",
    "allowed_updates": ["message", "channel_post", "callback_query"]
})

print("Webhook configuré", flush=True)
