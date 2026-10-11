# YT Cloud Player

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/Doge-person/yt-cloud/blob/main/yt_cloud_colab.ipynb)

**Quickest way:** click the badge above, then **Runtime → Run all** and paste a link into the player. The rest of this README covers the Codespaces version.

Paste a YouTube link. yt-dlp downloads it at up to 1080p **on a cloud machine** (GitHub Codespaces), and the page plays it back.

## Launch (browser or VS Code)
1. Create a new GitHub repo and upload this folder's contents (keep the `.devcontainer` folder).
2. On the repo page: **Code → Codespaces → Create codespace on main**.
   - In VS Code instead: install the *GitHub Codespaces* extension → "Codespaces: Create New Codespace" → pick the repo.
3. Wait for setup (installs ffmpeg, yt-dlp, deno). The server starts on its own and port 8000 opens in a preview tab.
   - If it doesn't open, use the **Ports** tab → port 8000 → globe icon, or run `python app.py`.

## Notes
- Format choice: H.264 + AAC at 1080p when YouTube offers it (plays in every browser), otherwise the best stream at or below 1080p.
- Files are saved in `downloads/` inside the codespace. Right-click one in the VS Code file explorer → Download to keep a copy.
- **"Sign in to confirm you're not a bot"**: YouTube sometimes blocks cloud IPs. Export your YouTube cookies as `cookies.txt` and upload them from the panel at the bottom of the page.
- If downloads start failing after a while, update yt-dlp: `pip install -U "yt-dlp[default]"`.
- Stop the codespace when done. It counts against your free monthly hours.
- Only download videos you have the right to save. YouTube's terms restrict downloading.
