import random
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, LabeledPrice
from telegram.ext import ApplicationBuilder, MessageHandler, filters, CommandHandler, CallbackContext, CallbackQueryHandler

# Liste des réactions possibles, élargie avec les nouveaux emojis
EMOJIS = ["👍", "🔥", "🎉", "❤️‍🔥", "😁", "🤩", "🥰", "😍", "👏", "👌", "🏆", "💯", "🆒" , "🙏" , "🤪" , "😎" , "🤣" , "😍" , "🤗"]

# Token du bot Telegram
BOT_TOKEN = "7676682325:AAHk4PUptjQZREL4Tac9atHEtW1jv18OuMg"

# Variables de paiement
PAYMENT_PROVIDER_TOKEN = '1877036958:TEST:70ed92f6b6f72b26f8565751c21551d42220f0fb'  # Remplace par le token de ton fournisseur de paiement Telegram

# Dictionnaire pour stocker les réactions personnalisées par utilisateur
user_reactions = {}

# Fonction pour gérer les réactions
async def add_reaction(update: Update, context: CallbackContext):
    """Ajoute une réaction emoji directement au message reçu."""
    if update.message:
        chat_id = update.effective_chat.id
        message_id = update.message.message_id
        # Choisir une réaction au hasard parmi les emojis choisis
        reaction = random.choice(EMOJIS)
        try:
            await context.bot.set_message_reaction(
                chat_id=chat_id,
                message_id=message_id,
                reaction=[reaction]
            )
        except Exception as e:
            print(f"❌ Erreur lors de l'ajout de la réaction : {e}")

# Fonction pour afficher le message de bienvenue
async def start(update: Update, context: CallbackContext):
    """Affiche un message de bienvenue avec des instructions d'utilisation du bot."""
    welcome_message = (
        "👋 Bienvenue sur le bot des réactions !\n\n"
        "Je suis un bot qui réagit à vos messages avec des emojis.\n"
        "Voici comment utiliser ce bot :\n\n"
        "1. Pour me demander de réagir à un message, envoie simplement un message et je réagirai avec un emoji !\n"
        "2. Pour personnaliser les emojis que j'utilise, utilise la commande /reaction pour sélectionner tes emojis préférés.\n\n"
        "🔗 Vous pouvez ajouter ce bot à un groupe ou un canal, et tous les messages envoyés seront automatiquement réagi avec un emoji.\n"
        "⚠️ *Attention* :\n"
        " - Dans un groupe, le bot réagira à tous les messages.\n"
        " - Dans un canal, le bot ne peut réagir que si le canal est lié à un groupe. Assurez-vous de lier votre canal à un groupe et que le soit administrateur dans les 2 pour que cela fonctionne.\n\n"
        "Amuse-toi bien ! 😄"
    )

    # Création des boutons avec des liens
    keyboard = [
        [InlineKeyboardButton("➕Add to Channel➕", url="https://t.me/Like1MBot?startchannel=botstart")],
        [InlineKeyboardButton("➕Add to group➕", url="https://t.me/Like1MBot?startgroup=botstart")],
        [InlineKeyboardButton("🎁DONATE💝", callback_data="donate")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # Envoi du message avec les boutons
    await update.message.reply_text(welcome_message, reply_markup=reply_markup)

# Fonction pour gérer la donation
async def donate(update: Update, context: CallbackContext):
    """Message de remerciement avec un bouton pour confirmer la donation."""
    if update.callback_query:
        query = update.callback_query
        await query.answer()  # Nécessaire pour fermer le popup de notification

        # Créer un bouton de paiement
        prices = [LabeledPrice("1 Étoile", 100)]  # 100 kopecks = 1 étoile, ajuste la devise selon ton paramètre

        # Envoi de l'invoice (facture)
        await context.bot.send_invoice(
            chat_id=query.message.chat.id,
            title="Donation 1 Étoile",
            description="Faites un don pour offrir une étoile au bot !",
            payload="donation_payload",  # Une donnée unique pour identifier cette facture
            provider_token=PAYMENT_PROVIDER_TOKEN,
            start_parameter="star_donation",
            currency="USD",  # Change la devise si nécessaire
            prices=prices,
            need_shipping_address=False,
            is_flexible=False
        )

# Fonction pour traiter la confirmation du paiement
async def successful_payment(update: Update, context: CallbackContext):
    """Cette fonction est appelée après un paiement réussi."""
    await update.message.reply_text("Merci beaucoup pour ta donation ! 🎉 Tu as offert une étoile ⭐ au bot !")
    # Vous pouvez ici ajouter l'étoile au bot ou récompense à l'utilisateur

# Fonction pour gérer les choix des emojis de réaction
async def reaction(update: Update, context: CallbackContext):
    """Permet à l'utilisateur de choisir plusieurs emojis pour les réactions."""
    chat_id = update.effective_chat.id

    if not context.args:
        await update.message.reply_text("⚠️ Tu n'as pas fourni d'emoji. Voici la liste des emojis disponibles :\n\n" + ", ".join(EMOJIS))
        return

    chosen_emojis = [emoji for emoji in context.args if emoji in EMOJIS]

    if not chosen_emojis:
        await update.message.reply_text(f"⚠️ Aucun emoji valide n'a été fourni. Voici les emojis disponibles : {', '.join(EMOJIS)}")
    else:
        user_reactions[chat_id] = chosen_emojis
        await update.message.reply_text(f"✅ Les messages seront maintenant réagi avec : {' '.join(chosen_emojis)}.")

# Fonction pour ajouter une réaction aléatoire parmi celles choisies par l'utilisateur
async def add_reaction(update: Update, context: CallbackContext):
    """Ajoute une réaction emoji au message reçu."""
    if update.message:
        chat_id = update.effective_chat.id
        message_id = update.message.message_id

        # Vérifier si l'utilisateur a défini ses propres emojis, sinon choisir un emoji aléatoire
        reaction_list = user_reactions.get(chat_id, EMOJIS)
        reaction = random.choice(reaction_list)

        try:
            await context.bot.set_message_reaction(
                chat_id=chat_id,
                message_id=message_id,
                reaction=[reaction]
            )
        except Exception as e:
            print(f"❌ Erreur lors de l'ajout de la réaction : {e}")

def main():
    # Initialiser l'application
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Ajouter les gestionnaires de commandes
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("reaction", reaction))
    app.add_handler(CommandHandler("donate", donate))

    # Ajouter le gestionnaire de pré-validation de paiement
    app.add_handler(CallbackQueryHandler(donate, pattern="^donate$"))

    # Ajouter le gestionnaire de confirmation de paiement réussi
    app.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment))

    # Ajouter le gestionnaire des messages pour les réactions
    app.add_handler(MessageHandler(filters.ALL, add_reaction))

    print("🤖 Bot lancé ! Il réagit à tous les messages, quel que soit le type...")
    app.run_polling()

if __name__ == "__main__":
    main()
