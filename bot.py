import os
import telebot
from flask import Flask, request

TOKEN = os.environ["BOT_TOKEN"]
PUBLIC_URL = os.environ["PUBLIC_URL"]
ADMIN_GROUP_ID = os.environ.get("ADMIN_GROUP_ID")

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

user_steps = {}

@app.route("/")
def home():
    return "Bot actif ✅"

@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        json_data = request.get_data().decode("utf-8")
        print("UPDATE REÇU :", json_data)
        update = telebot.types.Update.de_json(json_data)
        bot.process_new_updates([update])
        return "OK", 200
    except Exception as e:
        print("ERREUR WEBHOOK :", e)
        return "ERROR", 500

@bot.message_handler(commands=["start"])
def start(message):
    print("START REÇU")
    user_steps[message.from_user.id] = {"step": "nom"}
    bot.send_message(message.chat.id, "👋 Bonjour !\n\nQuel est ton NOM ?")

@bot.message_handler(commands=["connect"])
def connect(message):
    print("CONNECT REÇU")
    bot.reply_to(message, f"✅ Groupe détecté.\n\nADMIN_GROUP_ID :\n{message.chat.id}")

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    print("MESSAGE REÇU :", message.text)

    if message.chat.type != "private":
        return

    user_id = message.from_user.id

    if user_id not in user_steps:
        user_steps[user_id] = {"step": "nom"}
        bot.send_message(message.chat.id, "Quel est ton NOM ?")
        return

    data = user_steps[user_id]
    step = data["step"]

    if step == "nom":
        data["nom"] = message.text.strip()
        data["step"] = "prenom"
        bot.send_message(message.chat.id, "Quel est ton PRÉNOM ?")
        return

    if step == "prenom":
        data["prenom"] = message.text.strip()
        data["step"] = "numero"
        bot.send_message(message.chat.id, "Quel est ton NUMÉRO D’ADHÉSION ?")
        return

    if step == "numero":
        data["numero"] = message.text.strip()

        username = f"@{message.from_user.username}" if message.from_user.username else "Aucun username"
        tg_name = f"{message.from_user.first_name or ''} {message.from_user.last_name or ''}".strip()

        admin_message = f"""📩 Nouvelle demande d’adhésion

Nom : {data["nom"]}
Prénom : {data["prenom"]}
N° adhésion : {data["numero"]}

Telegram :
Nom Telegram : {tg_name}
Username : {username}
ID Telegram : {user_id}
"""

        if ADMIN_GROUP_ID:
            bot.send_message(ADMIN_GROUP_ID, admin_message)

        bot.send_message(message.chat.id, "✅ Merci ! Ta demande a bien été transmise aux administrateurs.")
        del user_steps[user_id]

bot.remove_webhook()
bot.set_webhook(url=f"{PUBLIC_URL}/webhook")
print("Webhook configuré :", f"{PUBLIC_URL}/webhook")
