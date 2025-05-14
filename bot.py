# bot.py
import logging
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
from yt_music_search import search_youtube_music # Import the search function
from yt_downloader import download_and_send_track # Import the download function

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Get bot token from user input (replace with the actual token provided)
BOT_TOKEN = "8038965253:AAEsvhBncVp6-cMuyTWzmH5Jzxh0RNweURg" # IMPORTANT: Replace with your REAL bot token

# PROXY CONFIGURATION - IMPORTANT: SET THIS TO YOUR PROXY OR None
# Example: PROXY_CONFIG = "http://user:pass@your_proxy_host:port"
# Example: PROXY_CONFIG = "http://123.45.67.89:8080"
# If you don't have a proxy or don't want to use one, set it to None
PROXY_CONFIG = None # <--- SET YOUR PROXY HERE OR LEAVE AS None

if PROXY_CONFIG:
    logger.info(f"Using proxy: {PROXY_CONFIG}")
else:
    logger.info("No proxy configured. Running without proxy.")

# --- Command Handlers ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sends a welcome message when the /start command is issued."""
    user = update.effective_user
    await update.message.reply_html(
        rf"Hi {user.mention_html()}!",
        reply_markup=None, # No keyboard for now
    )
    await update.message.reply_text(
        "Enter the artist or track name, or even some lyrics, and I'll search YouTube Music for you!"
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sends a help message when the /help command is issued."""
    await update.message.reply_text(
        "How to use the bot:\n"
        "- Send any text message to search for tracks on YouTube Music.\n"
        "- I'll show you the top results.\n"
        "- Click the button next to a track to start the download.\n\n"
        "Features:\n"
        "- Searches YouTube Music (including lyrics) using ytmusicapi with yt-dlp fallback.\n"
        "- Provides high-quality MP3 audio (converted from best audio source).\n"
        "- Supports proxy usage for improved anti-blocking."
    )

# --- Message Handler ---
async def handle_search_query(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles text messages as search queries."""
    query = update.message.text
    logger.info(f"Received search query: {query}")
    processing_message = await update.message.reply_text(f"Searching for \'{query}\' on YouTube Music...", quote=True)

    try:
        # Pass the PROXY_CONFIG to the search function
        search_results = search_youtube_music(query, max_results=5, proxy_config=PROXY_CONFIG)

        if not search_results:
            await processing_message.edit_text("Sorry, I couldn't find any tracks matching your query.")
            return

        keyboard = []
        response_text = "Here's what I found:"
        for i, track in enumerate(search_results):
            duration_min = int(track.get('duration', 0) // 60)
            duration_sec = int(track.get('duration', 0) % 60)
            duration_str = f"{duration_min:02d}:{duration_sec:02d}"
            title = str(track.get('title', 'Unknown Title'))
            artist = str(track.get('artist', 'Unknown Artist'))
            video_id = str(track.get('id', ''))

            if video_id:
                callback_data = f"dl_{video_id}"
                button_text = f"🎧 {title} - {artist} ({duration_str})"
                keyboard.append([InlineKeyboardButton(button_text, callback_data=callback_data)])
            else:
                logger.warning(f"Track \'{title}\' missing video ID, cannot create download button.")

        if not keyboard: # If no valid tracks with IDs were found to make buttons
            await processing_message.edit_text("Found some results, but couldn't prepare download links. Please try a different search.")
            return
            
        reply_markup = InlineKeyboardMarkup(keyboard)
        await processing_message.edit_text(response_text, reply_markup=reply_markup, parse_mode='Markdown')

    except Exception as e:
        logger.error(f"Error handling search query \'{query}\': {e}", exc_info=True)
        await processing_message.edit_text("An error occurred while searching. Please try again later.")


# --- Callback Query Handler (for button presses) ---
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Parses the CallbackQuery and handles the download request."""
    query = update.callback_query
    await query.answer() 

    callback_data = query.data
    logger.info(f"Callback received: {callback_data}")

    if callback_data.startswith("dl_"):
        video_id = callback_data.split("_", 1)[1]
        await query.edit_message_text(text=f"Request received for track ID: {video_id}. Preparing download...", reply_markup=None)
        # Pass the PROXY_CONFIG to the download function
        await download_and_send_track(video_id, query.message.chat_id, context, message_to_edit=query.message, proxy_config=PROXY_CONFIG)
    else:
        await query.edit_message_text(text=f"Unknown action: {callback_data}")


# --- Main Function ---
def main() -> None:
    """Start the bot."""
    if not BOT_TOKEN or BOT_TOKEN == "YOUR_TELEGRAM_BOT_TOKEN_HERE": # Added a check for placeholder token
        logger.error("Telegram Bot Token not found or not configured! Please set it in bot.py.")
        return
        
    application = Application.builder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_search_query))
    application.add_handler(CallbackQueryHandler(button_callback))

    logger.info("Starting bot polling...")
    application.run_polling()

if __name__ == "__main__":
    main()



