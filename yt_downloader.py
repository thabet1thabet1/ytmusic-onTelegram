# yt_downloader.py
import yt_dlp
import os
import logging
import random
import json
import asyncio
from telegram import InputFile
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)

CACHE_DIR = "./cache"

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    

    # ask chatgbt or any other AI for other User-Agents 

]

async def download_and_send_track(video_id: str, chat_id: int, context: ContextTypes.DEFAULT_TYPE, message_to_edit=None, proxy_config: str = None):
    """
    Downloads a track from YouTube, converts it to MP3, adds metadata (via yt-dlp),
    caches it with a separate metadata file, and sends it to the user.
    Uses rotating User-Agents, optional proxy, and adds a small delay.
    """
    script_dir = os.path.dirname(os.path.abspath(__file__))
    cookie_file_path = os.path.join(script_dir, "cookies.txt")
    cookie_file_to_use = cookie_file_path if os.path.exists(cookie_file_path) else None

    if not cookie_file_to_use:
        logger.warning(f"[{video_id}] Cookie file not found at {cookie_file_path}. Proceeding without cookies.")

    logger.info(f"[{video_id}] Starting download for chat {chat_id}. Proxy: {proxy_config}")
    final_file_path = os.path.join(CACHE_DIR, f"{video_id}.mp3")
    metadata_file_path = os.path.join(CACHE_DIR, f"{video_id}.json")
    temp_download_path_pattern = os.path.join(CACHE_DIR, f"{video_id}_temp.%(ext)s")
    processed_temp_path = os.path.join(CACHE_DIR, f"{video_id}_temp.mp3")

    selected_user_agent = random.choice(USER_AGENTS)
    http_headers = {
        "User-Agent": selected_user_agent,
        "Accept-Language": "en-US,en;q=0.5",
    }
    logger.info(f"[{video_id}] Using User-Agent: {selected_user_agent}")

    try:
        if os.path.exists(final_file_path) and os.path.exists(metadata_file_path):
            logger.info(f"[{video_id}] Cache hit for audio and metadata.")
            if message_to_edit:
                await message_to_edit.edit_text("Track found in cache! Sending now...")
            try:
                with open(metadata_file_path, "r", encoding="utf-8") as meta_f:
                    cached_metadata = json.load(meta_f)
                title = cached_metadata.get("title", "Unknown Title")
                artist = cached_metadata.get("artist", "Unknown Artist")
                duration = cached_metadata.get("duration", 0)
                caption = f"{title} - {artist}"
                with open(final_file_path, "rb") as audio_file:
                    await context.bot.send_audio(
                        chat_id=chat_id,
                        audio=InputFile(audio_file, filename=f"{title} - {artist}.mp3"),
                        caption=caption, title=title, performer=artist, duration=duration,
                        write_timeout=180, read_timeout=180, connect_timeout=180
                    )
                logger.info(f"[{video_id}] Successfully sent cached file.")
                if message_to_edit: await message_to_edit.delete()
                return
            except Exception as send_error:
                logger.error(f"[{video_id}] Error sending cached file {final_file_path}: {send_error}", exc_info=True)
                if message_to_edit: await message_to_edit.edit_text("Error sending cached file. Will attempt redownload.")

        logger.info(f"[{video_id}] Cache miss or error. Proceeding with download.")
        if message_to_edit: await message_to_edit.edit_text("Downloading and processing track... (this may take a moment)")

        os.makedirs(CACHE_DIR, exist_ok=True)

        base_ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "source_address": "0.0.0.0",
            "http_headers": http_headers,
            "geo_bypass": True,
            "force_ipv4": True,
        }
        if cookie_file_to_use:
            base_ydl_opts["cookiefile"] = cookie_file_to_use
            logger.info(f"[{video_id}] Using cookie file for operations: {cookie_file_to_use}")
        if proxy_config:
            base_ydl_opts["proxy"] = proxy_config
            logger.info(f"[{video_id}] Using proxy for operations: {proxy_config}")

        track_info = None
        video_url = f"https://www.youtube.com/watch?v={video_id}"
        logger.info(f"[{video_id}] Extracting track info from: {video_url}")
        try:
            await asyncio.sleep(random.uniform(0.5, 1.5))
            ydl_info_opts = base_ydl_opts.copy()
            # No download for info extraction
            with yt_dlp.YoutubeDL(ydl_info_opts) as ydl_info:
                track_info = ydl_info.extract_info(video_url, download=False)
            logger.info(f"[{video_id}] Successfully extracted track info.")
        except Exception as info_err:
            logger.error(f"[{video_id}] Failed to extract info: {info_err}", exc_info=True)
            error_message = "Failed to get track information."
            if "authentication" in str(info_err).lower() or "login" in str(info_err).lower():
                error_message += " (Authentication may be required - check cookies)"
            elif "HTTP Error 403" in str(info_err):
                 error_message += " (Blocked by YouTube - 403)"
            if message_to_edit: await message_to_edit.edit_text(error_message)
            return

        if not track_info:
            logger.error(f"[{video_id}] Track info was empty after extraction.")
            if message_to_edit: await message_to_edit.edit_text("Could not retrieve track information.")
            return

        ydl_download_opts = base_ydl_opts.copy()
        ydl_download_opts.update({
            "format": "bestaudio[ext=m4a]/bestaudio[ext=opus]/bestaudio/best",
            "outtmpl": temp_download_path_pattern,
            "force_overwrites": True,
            "noplaylist": True,
            "retries": 3,
            "fragment_retries": 3,
            "retry_sleep": {"http": random.randint(3, 7)}, # Randomized retry sleep
            "addmetadata": True,
            "throttledrate": "1M",
            "sleep_interval_requests": random.uniform(0.5, 1.5),
            "postprocessors": [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "128",
            }],
        })
        
        download_success = False
        logger.info(f"[{video_id}] Starting download and processing for MP3...")
        try:
            delay = random.uniform(1.0, 3.0)
            logger.info(f"[{video_id}] Waiting for {delay:.2f} seconds before download...")
            await asyncio.sleep(delay)
            
            with yt_dlp.YoutubeDL(ydl_download_opts) as ydl:
                download_target_url = track_info.get("webpage_url", video_url)
                logger.info(f"[{video_id}] Passing URL to ydl.download: {download_target_url}")
                error_code = ydl.download([download_target_url])
                if error_code == 0:
                    download_success = True
                    logger.info(f"[{video_id}] yt-dlp download process completed successfully.")
                else:
                    logger.error(f"[{video_id}] yt-dlp download process failed with error code: {error_code}")
        
        except yt_dlp.utils.DownloadError as dl_err:
            logger.error(f"[{video_id}] Download failed (DownloadError): {dl_err}", exc_info=False)
            error_message = "Download failed. "
            is_403 = "HTTP Error 403" in str(dl_err)
            
            # Simplified fallback: if cookies were used and it's a 403, try without cookies if proxy is not already set (or vice-versa)
            # For now, just report the error more clearly.
            if is_403:
                error_message += "YouTube blocked the request (403 Forbidden). "
                if cookie_file_to_use: error_message += "Try updating cookies or using a proxy. "
                elif proxy_config: error_message += "The proxy might be blocked. "
                else: error_message += "Consider using a proxy or cookies. "
            elif "unavailable" in str(dl_err).lower():
                error_message += "The video might be unavailable or region-locked."
            else:
                error_message += "Please try again later."

            if message_to_edit: await message_to_edit.edit_text(error_message)
            # No return here, will be caught by `if not download_success` later for cleanup

        except Exception as dl_err:
            logger.error(f"[{video_id}] Unexpected exception during yt-dlp download/processing: {dl_err}", exc_info=True)
            if message_to_edit: await message_to_edit.edit_text("An unexpected error occurred during download.")
            # No return here, will be caught by `if not download_success` later for cleanup

        if not download_success:
            logger.error(f"[{video_id}] Download/processing ultimately failed.")
            # Ensure message_to_edit is updated if not already by a specific error message
            if message_to_edit and "Download failed" not in message_to_edit.text and "403 Forbidden" not in message_to_edit.text:
                 await message_to_edit.edit_text("Failed to download or process the track after attempts.")
            # Cleanup temp files
            if os.path.exists(processed_temp_path): os.remove(processed_temp_path)
            for ext in ["webm", "opus", "mp4", "mkv", "aac", "m4a", "mp3", "part"]:
                temp_f = os.path.join(CACHE_DIR, f"{video_id}_temp.{ext}")
                if os.path.exists(temp_f): os.remove(temp_f)
            return

        if not os.path.exists(processed_temp_path):
            logger.error(f"[{video_id}] Processed file {processed_temp_path} not found after download.")
            if message_to_edit: await message_to_edit.edit_text("Processing failed: Final audio file not found.")
            return
        
        title = track_info.get("title", "Unknown Title")
        # Attempt to get artist from track_info, fallback to uploader/channel
        artist_detail = track_info.get("artist") or track_info.get("uploader") or track_info.get("channel", "Unknown Artist")
        duration = int(track_info.get("duration", 0))
        metadata_to_save = {"title": title, "artist": artist_detail, "duration": duration, "video_id": video_id}
        try:
            with open(metadata_file_path, "w", encoding="utf-8") as meta_f:
                json.dump(metadata_to_save, meta_f, ensure_ascii=False, indent=4)
            logger.info(f"[{video_id}] Saved metadata to {metadata_file_path}")
        except Exception as json_err:
            logger.error(f"[{video_id}] Failed to save metadata: {json_err}")

        os.rename(processed_temp_path, final_file_path)
        logger.info(f"[{video_id}] Renamed {processed_temp_path} to {final_file_path}")

        if message_to_edit: await message_to_edit.edit_text("Upload starting...")
        try:
            with open(final_file_path, "rb") as audio_file:
                caption = f"{title} - {artist_detail}"
                await context.bot.send_audio(
                    chat_id=chat_id,
                    audio=InputFile(audio_file, filename=f"{title} - {artist_detail}.mp3"),
                    caption=caption, title=title, performer=artist_detail, duration=duration,
                    write_timeout=180, read_timeout=180, connect_timeout=180
                )
            logger.info(f"[{video_id}] Successfully sent audio file.")
            if message_to_edit: await message_to_edit.delete()
        except Exception as send_error:
            logger.error(f"[{video_id}] Error sending file {final_file_path}: {send_error}", exc_info=True)
            if message_to_edit: await message_to_edit.edit_text(f"Error sending the track: {send_error}")
            else: await context.bot.send_message(chat_id=chat_id, text=f"Error sending the track: {send_error}")

    except Exception as e:
        logger.error(f"[{video_id}] An unexpected error in download_and_send_track: {e}", exc_info=True)
        final_error_message = "An unexpected error occurred while processing your request."
        if "403" in str(e): final_error_message = "Request blocked by YouTube (403). Try a proxy or updated cookies."
        if message_to_edit:
            try: await message_to_edit.edit_text(final_error_message)
            except Exception: await context.bot.send_message(chat_id=chat_id, text=final_error_message)
        else:
            await context.bot.send_message(chat_id=chat_id, text=final_error_message)


