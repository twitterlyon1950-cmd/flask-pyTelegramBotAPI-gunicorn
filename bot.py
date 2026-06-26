import os
import telebot
from flask import Flask, request

TOKEN = os.environ["BOT_TOKEN"]
PUBLIC_URL = os.environ["PUBLIC_URL"]
ADMIN_GROUP_ID = os.environ.get("ADMIN_GROUP_ID")

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

user_steps = {}

@app.route("/", methods=["GET"])
def home():
    return "Bot actif ✅"

@app.route("/webhook", methods=["POST"])
def webhook():
    update = telebot.types.Update.de_json(request.get_data().decode("utf-8"))
    bot.process_new_updates([update])
    return "OK", 200

@bot.message_handler(commands=["start"])
def start(message):
    if message.chat.type != "private":
        return

    user_steps[message.from_user.id] = {"step": "nom"}
    bot.send_message(
        message.chat.id,
        "👋 Bonjour !\n\nPour demander l’accès au canal, réponds aux questions.\n\nQuel est ton NOM ?"
    )

@bot.message_handler(commands=["connect"])
def connect(message):
    if message.chat.type in ["group", "supergroup"]:
        bot.reply_to(
            message,
            f"✅ Groupe détecté.\n\nCopie cet ID dans Render comme ADMIN_GROUP_ID :\n{message.chat.id}"
        )

@bot.message_handler(func=lambda message: message.chat.type == "private")
def handle_private(message):
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
        else:
            bot.send_message(message.chat.id, "✅ Demande reçue, mais le groupe admin n’est pas encore connecté.")

        del user_steps[user_id]

bot.remove_webhook()
bot.set_webhook(url=f"{PUBLIC_URL}/webhook")
