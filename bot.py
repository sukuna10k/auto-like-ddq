import os
import random
from datetime import datetime, timedelta
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, LabeledPrice
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    filters,
    CallbackContext
)

# Initialisation du logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Liste des réactions possibles
EMOJIS = ["👍", "🔥", "🎉", "❤️‍🔥", "😁", "🤩", "🥰", "😍", "👏", "👌", "🏆", "💯", "🆒", "🙏", "🤪", "😎", "🤣", "😍", "🤗"]

# Tokens et configuration
# Il est recommandé d'utiliser des variables d'environnement pour ces valeurs
BOT_TOKEN = os.environ.get("BOT_TOKEN", "7676682325:AAHk4PUptjQZREL4Tac9atHEtW1jv18OuMg")
PAYMENT_PROVIDER_TOKEN = os.environ.get("PAYMENT_PROVIDER_TOKEN", "1877036958:TEST:70ed92f6b6f72b26f8565751c21551d42220f0fb")

# Stockage en mémoire
users = {}            # {user_id: {name, username, joined_at}}
user_reactions = {}   # {chat_id: [emojis]}
logs = []             # Historique des actions
config = {}           # Configuration dynamique (clé: valeur)
mute_list = {}        # {user_id: mute_expiry (datetime)}

# Gestion des admins
MAIN_ADMIN_ID = 1687928453  # Administrateur principal (à modifier)
admin_ids = {MAIN_ADMIN_ID}  # Ensemble des IDs administrateurs

# Pour le ConversationHandler de la diffusion
BROADCAST_MESSAGE = 1

# Fonction pour ajouter une entrée dans les logs
def log_action(action: str):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    logs.append(f"[{timestamp}] {action}")
    logging.info(action)

# Vérifie si l'utilisateur est admin
def is_admin(update: Update) -> bool:
    if update.message and update.message.from_user:
        return update.message.from_user.id in admin_ids
    elif update.callback_query and update.callback_query.from_user:
        return update.callback_query.from_user.id in admin_ids
    return False

# --- Fonctions de base du bot ---

async def start(update: Update, context: CallbackContext):
    if update.message and update.message.from_user:
        user = update.message.from_user
        user_id = user.id
        if user_id not in users:
            users[user_id] = {
                "name": user.full_name,
                "username": user.username,
                "joined_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            log_action(f"Nouvel utilisateur enregistré: {user.full_name} ({user_id})")
    # Message de bienvenue
    welcome_message = (
        "👋 Bienvenue sur le bot des réactions !\n\n"
        "Je suis un bot qui réagit à vos messages avec des emojis.\n"
        "Voici comment utiliser ce bot :\n\n"
        "1. Pour me demander de réagir à un message, envoie simplement un message et je réagirai avec un emoji !\n"
        "2. Pour personnaliser les emojis que j'utilise, utilise la commande /reaction pour sélectionner tes emojis préférés.\n\n"
        "🔗 Vous pouvez ajouter ce bot à un groupe ou un canal, et tous les messages envoyés seront automatiquement réagi avec un emoji.\n"
        "⚠️ *Attention* :\n"
        " - Dans un groupe, le bot réagira à tous les messages.\n"
        " - Dans un canal, le bot ne peut réagir que si le canal est lié à un groupe. Assurez-vous de lier votre canal à un groupe et que le bot soit administrateur dans les 2 pour que cela fonctionne.\n\n"
        "Amuse-toi bien ! 😄"
    )
    # Boutons pour ajouter le bot et faire une donation
    keyboard = [
        [InlineKeyboardButton("➕Add to Channel➕", url="https://t.me/Like1MBot?startchannel=botstart")],
        [InlineKeyboardButton("➕Add to Group➕", url="https://t.me/Like1MBot?startgroup=botstart")],
        [InlineKeyboardButton("🎁DONATE💝", callback_data="donate")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(welcome_message, reply_markup=reply_markup)

async def reaction(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id

    if not context.args:
        allowed_emojis_str = " ".join(EMOJIS)  # Convertit la liste en chaîne de caractères
        await update.message.reply_text(
            f"⚠️ Aucun emoji fourni. Utilise /reaction suivi des emojis souhaités parmi ceux disponibles :\n\n{allowed_emojis_str}\n\nExemple : /reaction 👍 🔥 🎉"
        )
        return
    chosen_emojis = [emoji for emoji in context.args if emoji in EMOJIS]
    if not chosen_emojis:
        await update.message.reply_text("⚠️ Aucun emoji valide n'a été fourni. Voici les emojis disponibles: " + ", ".join(EMOJIS))
    else:
        user_reactions[chat_id] = chosen_emojis
        await update.message.reply_text("✅ Réaction(s) mise(s) à jour: " + " ".join(chosen_emojis))
        log_action(f"Réactions mises à jour pour le chat {chat_id}: {chosen_emojis}")

async def add_reaction(update: Update, context: CallbackContext):
    # Ignorer les commandes afin de ne pas interférer avec d'autres handlers
    if update.message and update.message.text and update.message.text.startswith("/"):
        return
    if update.message:
        user_id = update.message.from_user.id
        # Vérification du mute
        if user_id in mute_list:
            if datetime.now() < mute_list[user_id]:
                return
            else:
                del mute_list[user_id]
        chat_id = update.effective_chat.id
        message_id = update.message.message_id
        reaction_list = user_reactions.get(chat_id, EMOJIS)
        reaction = random.choice(reaction_list)
        try:
            # Remarque : La méthode set_message_reaction n'est pas officiellement supportée.
            # Vous pouvez envisager d'envoyer un message en réponse ou utiliser une autre approche.
            await context.bot.set_message_reaction(
                chat_id=chat_id,
                message_id=message_id,
                reaction=[reaction]
            )
        except Exception as e:
            logging.error(f"Erreur de réaction: {e}")

async def donate(update: Update, context: CallbackContext):
    if update.callback_query:
        query = update.callback_query
        await query.answer()
        prices = [LabeledPrice("1 Étoile", 100)]
        await context.bot.send_invoice(
            chat_id=query.message.chat.id,
            title="Donation 1 Étoile",
            description="Faites un don pour offrir une étoile au bot !",
            payload="donation_payload",
            provider_token=PAYMENT_PROVIDER_TOKEN,
            start_parameter="star_donation",
            currency="USD",
            prices=prices,
            need_shipping_address=False,
            is_flexible=False
        )

async def successful_payment(update: Update, context: CallbackContext):
    await update.message.reply_text("Merci pour ta donation ! 🎉")
    log_action(f"Paiement réussi de l'utilisateur {update.message.from_user.id}")

# --- Fonctions d'administration ---

async def admin_stats(update: Update, context: CallbackContext):
    if not is_admin(update):
        await update.message.reply_text("Accès refusé.")
        return
    total_users = len(users)
    stats_message = f"👥 Total utilisateurs: {total_users}\n\nDétails:\n"
    for uid, info in users.items():
        stats_message += f"{info['name']} (@{info.get('username', 'N/A')}) - Rejoint: {info['joined_at']}\n"
    await update.message.reply_text(stats_message)

# ConversationHandler pour la diffusion
async def start_broadcast(update: Update, context: CallbackContext) -> int:
    if update.effective_user.id != MAIN_ADMIN_ID:
        await update.message.reply_text("🚫 Accès refusé.")
        return ConversationHandler.END
    await update.message.reply_text("Envoyez-moi le message à diffuser. Il peut contenir du texte, une photo, des boutons, etc.")
    return BROADCAST_MESSAGE

async def broadcast_message(update: Update, context: CallbackContext) -> int:
    """
    Copie le message envoyé par l'administrateur vers tous les utilisateurs enregistrés.
    """
    message = update.message
    failed_users = []

    for user_id in users.keys():
        try:
            await context.bot.copy_message(
                chat_id=user_id,
                from_chat_id=message.chat_id,
                message_id=message.message_id
            )
        except Exception as e:
            logging.error(f"Erreur en envoyant le message à {user_id} : {e}")
            failed_users.append(str(user_id))
    if failed_users:
        await update.message.reply_text("Le message n'a pas pu être envoyé aux utilisateurs suivants : " + ", ".join(failed_users))
    else:
        await update.message.reply_text("Message diffusé avec succès.")
    return ConversationHandler.END

async def cancel_broadcast(update: Update, context: CallbackContext) -> int:
    await update.message.reply_text("Diffusion annulée.")
    return ConversationHandler.END

async def admin_ban_user(update: Update, context: CallbackContext):
    if not is_admin(update):
        await update.message.reply_text("Accès refusé.")
        return
    try:
        user_id_to_ban = int(context.args[0])
        if user_id_to_ban in users:
            del users[user_id_to_ban]
            await update.message.reply_text(f"Utilisateur {user_id_to_ban} banni.")
            log_action(f"Utilisateur banni: {user_id_to_ban}")
        else:
            await update.message.reply_text("Utilisateur non trouvé.")
    except (IndexError, ValueError):
        await update.message.reply_text("Utilisation: /admin_ban_user <user_id>")

async def admin_help(update: Update, context: CallbackContext):
    if not is_admin(update):
        await update.message.reply_text("Accès refusé.")
        return
    help_text = (
        "🛠️ Commandes d'administration:\n"
        "/admin_stats - Statistiques utilisateurs\n"
        "/admin_send_message - Diffuser un message (mode interactif)\n"
        "/admin_ban_user <user_id> - Bannir un utilisateur\n"
        "/add_admin <user_id> - Ajouter un admin (seul le main admin)\n"
        "/remove_admin <user_id> - Supprimer un admin (seul le main admin)\n"
        "/schedule_notification <sec> <message> - Planifier une notification\n"
        "/set_config <clé> <valeur> - Mettre à jour une config\n"
        "/get_config <clé> - Obtenir la valeur d'une config\n"
        "/view_logs - Voir les logs\n"
        "/mute_user <user_id> <sec> - Muter un utilisateur\n"
        "/unmute_user <user_id> - Démuter un utilisateur\n"
    )
    await update.message.reply_text(help_text)

async def add_admin(update: Update, context: CallbackContext):
    if update.message.from_user.id != MAIN_ADMIN_ID:
        await update.message.reply_text("Accès refusé.")
        return
    try:
        new_admin_id = int(context.args[0])
        admin_ids.add(new_admin_id)
        await update.message.reply_text(f"Admin ajouté: {new_admin_id}")
        log_action(f"Admin ajouté: {new_admin_id}")
    except (IndexError, ValueError):
        await update.message.reply_text("Utilisation: /add_admin <user_id>")

async def remove_admin(update: Update, context: CallbackContext):
    if update.message.from_user.id != MAIN_ADMIN_ID:
        await update.message.reply_text("Accès refusé.")
        return
    try:
        rem_admin_id = int(context.args[0])
        if rem_admin_id in admin_ids:
            admin_ids.remove(rem_admin_id)
            await update.message.reply_text(f"Admin retiré: {rem_admin_id}")
            log_action(f"Admin retiré: {rem_admin_id}")
        else:
            await update.message.reply_text("Cet utilisateur n'est pas admin.")
    except (IndexError, ValueError):
        await update.message.reply_text("Utilisation: /remove_admin <user_id>")

async def schedule_notification(update: Update, context: CallbackContext):
    if not is_admin(update):
        await update.message.reply_text("Accès refusé.")
        return
    try:
        delay = int(context.args[0])
        message = ' '.join(context.args[1:])
        if not message:
            await update.message.reply_text("Utilisation: /schedule_notification <sec> <message>")
            return
        context.job_queue.run_once(send_scheduled_notification, delay, context=message)
        await update.message.reply_text(f"Notification planifiée dans {delay} secondes.")
        log_action(f"Notification planifiée dans {delay}s: {message}")
    except (IndexError, ValueError):
        await update.message.reply_text("Utilisation: /schedule_notification <sec> <message>")

async def send_scheduled_notification(context: CallbackContext):
    message = context.job.context
    for uid in users:
        try:
            await context.bot.send_message(chat_id=uid, text=f"🔔 Notification: {message}")
        except Exception as e:
            logging.error(f"Erreur lors de l'envoi de la notification à {uid}: {e}")
    log_action(f"Notification envoyée: {message}")

async def set_config(update: Update, context: CallbackContext):
    if not is_admin(update):
        await update.message.reply_text("Accès refusé.")
        return
    try:
        key = context.args[0]
        value = ' '.join(context.args[1:])
        config[key] = value
        await update.message.reply_text(f"Config mise à jour: {key} = {value}")
        log_action(f"Config mise à jour: {key} = {value}")
    except IndexError:
        await update.message.reply_text("Utilisation: /set_config <clé> <valeur>")

async def get_config(update: Update, context: CallbackContext):
    if not is_admin(update):
        await update.message.reply_text("Accès refusé.")
        return
    try:
        key = context.args[0]
        value = config.get(key, "Non défini")
        await update.message.reply_text(f"{key} = {value}")
    except IndexError:
        await update.message.reply_text("Utilisation: /get_config <clé>")

async def view_logs(update: Update, context: CallbackContext):
    if not is_admin(update):
        await update.message.reply_text("Accès refusé.")
        return
    if logs:
        await update.message.reply_text("\n".join(logs[-20:]))
    else:
        await update.message.reply_text("Aucun log disponible.")

async def mute_user(update: Update, context: CallbackContext):
    if not is_admin(update):
        await update.message.reply_text("Accès refusé.")
        return
    try:
        user_id = int(context.args[0])
        duration = int(context.args[1])
        mute_until = datetime.now() + timedelta(seconds=duration)
        mute_list[user_id] = mute_until
        await update.message.reply_text(f"Utilisateur {user_id} muté pendant {duration} secondes.")
        log_action(f"Utilisateur {user_id} muté jusqu'à {mute_until}")
    except (IndexError, ValueError):
        await update.message.reply_text("Utilisation: /mute_user <user_id> <sec>")

async def unmute_user(update: Update, context: CallbackContext):
    if not is_admin(update):
        await update.message.reply_text("Accès refusé.")
        return
    try:
        user_id = int(context.args[0])
        if user_id in mute_list:
            del mute_list[user_id]
            await update.message.reply_text(f"Utilisateur {user_id} démute.")
            log_action(f"Utilisateur {user_id} démute.")
        else:
            await update.message.reply_text("Cet utilisateur n'est pas muté.")
    except (IndexError, ValueError):
        await update.message.reply_text("Utilisation: /unmute_user <user_id>")

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    
    # Commandes de base
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("reaction", reaction))
    app.add_handler(CommandHandler("donate", donate))
    app.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment))
    
    # IMPORTANT : Ajout du ConversationHandler pour la diffusion AVANT le handler général de réactions
    broadcast_conv_handler = ConversationHandler(
        entry_points=[CommandHandler("admin_send_message", start_broadcast)],
        states={
            BROADCAST_MESSAGE: [MessageHandler(filters.ALL, broadcast_message)]
        },
        fallbacks=[CommandHandler("cancel", cancel_broadcast)]
    )
    app.add_handler(broadcast_conv_handler)
    
    # Handler pour les messages non commandes (réactions automatiques)
    app.add_handler(MessageHandler(~filters.COMMAND, add_reaction))
    
    # Commandes d'administration classiques
    app.add_handler(CommandHandler("admin_stats", admin_stats))
    app.add_handler(CommandHandler("admin_ban_user", admin_ban_user))
    app.add_handler(CommandHandler("admin_help", admin_help))
    app.add_handler(CommandHandler("add_admin", add_admin))
    app.add_handler(CommandHandler("remove_admin", remove_admin))
    app.add_handler(CommandHandler("schedule_notification", schedule_notification))
    app.add_handler(CommandHandler("set_config", set_config))
    app.add_handler(CommandHandler("get_config", get_config))
    app.add_handler(CommandHandler("view_logs", view_logs))
    app.add_handler(CommandHandler("mute_user", mute_user))
    app.add_handler(CommandHandler("unmute_user", unmute_user))
    app.add_handler(CallbackQueryHandler(donate, pattern="^donate$"))
    
    # Récupération du port et de l'URL de webhook depuis les variables d'environnement
    port = int(os.environ.get("PORT", "8080"))
    webhook_url = os.environ.get("WEBHOOK_URL")
    if not webhook_url:
        logging.error("WEBHOOK_URL non défini dans les variables d'environnement.")
        return
    # Chemin du webhook (ajouté à l'URL publique)
    webhook_path = "/webhook"
    logging.info(f"Démarrage du webhook sur le port {port} à l'URL: {webhook_url + webhook_path}")
    
    app.run_webhook(listen="0.0.0.0", port=port, url_path=webhook_path, webhook_url=webhook_url + webhook_path)

if __name__ == "__main__":
    main()
