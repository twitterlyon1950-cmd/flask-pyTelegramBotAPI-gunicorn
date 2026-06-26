import os
import telebot
from flask import Flask, request

TOKEN = os.environ["BOT_TOKEN"]
ADMIN_GROUP_ID = os.environ.get("ADMIN_GROUP_ID")
PUBLIC_URL = os.environ.get("PUBLIC_URL")

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

user_data = {}

@bot.message_handler(commands=["start"])
def start(message):
    user_data[message.from_user.id] = {"step": "nom"}
    bot.send_message(
        message.chat.id,
        "👋 Bonjour !\n\nPour demander l’accès au canal Lyon 1950 26/27, réponds aux questions suivantes.\n\nQuel est ton NOM ?"
    )

@bot.message_handler(func=lambda message: message.chat.type == "private")
def handle_private_message(message):
    user_id = message.from_user.id

    if user_id not in user_data:
        user_data[user_id] = {"step": "nom"}
        bot.send_message(message.chat.id, "Quel est ton NOM ?")
        return

    step = user_data[user_id]["step"]

    if step == "nom":
        user_data[user_id]["nom"] = message.text.strip()
        user_data[user_id]["step"] = "prenom"
        bot.send_message(message.chat.id, "Quel est ton PRÉNOM ?")

    elif step == "prenom":
        user_data[user_id]["prenom"] = message.text.strip()
        user_data[user_id]["step"] = "numero"
        bot.send_message(message.chat.id, "Quel est ton numéro d’adhésion ?")

    elif step == "numero":
        user_data[user_id]["numero"] = message.text.strip()

        username = f"@{message.from_user.username}" if message.from_user.username else "Aucun username"
        telegram_name = f"{message.from_user.first_name or ''} {message.from_user.last_name or ''}".strip()

        admin_message = f"""📩 Nouvelle demande d’adhésion

Nom : {user_data[user_id]["nom"]}
Prénom : {user_data[user_id]["prenom"]}
N° adhésion : {user_data[user_id]["numero"]}

Telegram :
Nom Telegram : {telegram_name}
Username : {username}
ID Telegram : {user_id}
"""

        if ADMIN_GROUP_ID:
            bot.send_message(ADMIN_GROUP_ID, admin_message)
            bot.send_message(message.chat.id, "✅ Merci ! Ta demande a bien été transmise aux administrateurs.")
        else:
            bot.send_message(message.chat.id, "✅ Demande reçue, mais le groupe admin n’est pas encore connecté.")

        del user_data[user_id]

@bot.message_handler(commands=["connect"])
def connect_group(message):
    if message.chat.type in ["group", "supergroup"]:
        bot.reply_to(message, f"✅ Groupe détecté.\nID du groupe : {message.chat.id}")

@app.route("/", methods=["GET"])
def home():
    return "Bot adhésion actif ✅"

@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    update = telebot.types.Update.de_json(request.stream.read().decode("utf-8"))
    bot.process_new_updates([update])
    return "OK", 200

if PUBLIC_URL:
    bot.remove_webhook()
    bot.set_webhook(url=f"{PUBLIC_URL}/{TOKEN}")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
