# YouTube Music Telegram Bot

This Telegram bot allows you to search for music on YouTube Music and download tracks as MP3 files directly within Telegram.

## Features

*   **Music Search**: Searches YouTube Music for tracks using artist name, track title, or lyrics.
    *   Primarily uses `ytmusicapi` for robust searching.
    *   Falls back to `yt-dlp` if `ytmusicapi` encounters issues or yields no results.
*   **MP3 Download**: Downloads the selected track and converts it to an MP3 file (128kbps).
*   **Telegram Integration**: Sends the downloaded MP3 file directly to the user in the Telegram chat.
*   **Caching**: Caches successfully downloaded tracks to provide them instantly for subsequent requests of the same track.
*   **Proxy Support (Optional)**: Includes the capability to route requests through a proxy server to help mitigate blocking by YouTube. (See Configuration section).

## Setup and Installation

1.  **Prerequisites**:
    *   Python 3.9 or higher is recommended.
    *   FFmpeg: This is required by `yt-dlp` for audio conversion. Ensure FFmpeg is installed on the system where the bot will run and is accessible in the system's PATH.

2.  **Clone or Download Files**:
    *   Place `bot.py`, `yt_music_search.py`, and `yt_downloader.py` in the same directory.
    *   If you have a `cookies.txt` file from `yt-dlp` (for potentially helping with some restricted content, though not a primary anti-blocking measure here), place it in the same directory.

3.  **Install Dependencies**:
    Open your terminal or command prompt and navigate to the bot's directory. Install the required Python libraries:
    ```bash
    pip install python-telegram-bot ytmusicapi yt-dlp requests
    ```
    (Use `pip3` if `pip` on your system points to an older Python version).

4.  **Configure Bot Token**:
    *   Open the `bot.py` file.
    *   Find the line: `BOT_TOKEN = "YOUR_TELEGRAM_BOT_TOKEN_HERE"` (or the existing placeholder).
    *   Replace `"YOUR_TELEGRAM_BOT_TOKEN_HERE"` with your actual Telegram Bot token. You can get a token by creating a new bot with BotFather on Telegram.

5.  **Proxy Configuration (Optional - Read Carefully)**:
    *   Open the `bot.py` file.
    *   Find the line: `PROXY_CONFIG = None`
    *   **If you have a proxy server and want to use it**: Change `None` to your proxy string. 
        *   Example without authentication: `PROXY_CONFIG = "http://YOUR_PROXY_IP:PORT"`
        *   Example with authentication: `PROXY_CONFIG = "http://USERNAME:PASSWORD@YOUR_PROXY_IP:PORT"`
    *   **If you do NOT want to use a proxy**: Leave this line as `PROXY_CONFIG = None`.

## Running the Bot

1.  Navigate to the bot's directory in your terminal.
2.  Run the bot using the command:
    ```bash
    python bot.py
    ```
    (Or `python3 bot.py` if needed).
3.  The bot should start polling for messages. You can interact with it on Telegram.

## How to Use

1.  Start a chat with your bot on Telegram.
2.  Send the `/start` command for a welcome message.
3.  Send any text message (e.g., song name, artist, lyrics) to search for music.
4.  The bot will reply with a list of search results as buttons.
5.  Click the button next to the desired track to start the download.
6.  The bot will send a message indicating the download is in progress and then send the MP3 file once ready.

## Important: YouTube Blocking and Proxies

*   **Without a Proxy (`PROXY_CONFIG = None`)**: YouTube actively tries to block automated downloads. If you run the bot without a proxy:
    *   The first download attempt *might* work, especially if your server's IP address hasn't made many recent requests to YouTube.
    *   **Subsequent download attempts are highly likely to fail** with errors like "403 Forbidden" or timeouts. This is because YouTube will quickly identify and block repeated download activity from a single IP address.
    *   The bot's reliability for continuous use will be very limited.
*   **With a Proxy**: Using a good quality, working proxy server (especially residential or mobile proxies) significantly increases the chances of bypassing YouTube's blocks and allows for more reliable, repeated use. However, even proxies can sometimes be detected or rate-limited.

## Cache

The bot creates a `./cache` directory in its working folder to store downloaded MP3s and their metadata. This allows for faster delivery if the same track is requested again.

## Troubleshooting

*   **"Import telegram could not be resolved"**: Ensure `python-telegram-bot` is installed correctly in your Python environment.
*   **403 Forbidden errors during download**: This almost always means YouTube is blocking your IP address (if not using a proxy) or your proxy's IP address. Try a different, reliable proxy.
*   **Timeouts**: Can be related to network issues, slow proxy servers, or YouTube blocking leading to prolonged attempts. If using a proxy, ensure it's fast and stable.
*   **FFmpeg not found**: Make sure FFmpeg is installed and accessible in your system's PATH.
*   **Check logs**: The bot logs information to the console, which can be helpful for diagnosing issues.

This README provides a basic guide. Remember that bypassing YouTube's anti-bot measures is an ongoing challenge.
