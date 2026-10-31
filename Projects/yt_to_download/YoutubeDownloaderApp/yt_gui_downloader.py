import os
import sys
import subprocess

# Prevent ffmpeg/node from flashing console windows in a --noconsole build.
# Must run before yt_dlp is imported.
if sys.platform == "win32":
    _orig_popen = subprocess.Popen

    class _NoWindowPopen(_orig_popen):
        def __init__(self, *a, **kw):
            kw["creationflags"] = kw.get("creationflags", 0) | 0x08000000  # CREATE_NO_WINDOW
            super().__init__(*a, **kw)

    subprocess.Popen = _NoWindowPopen

import shutil
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import yt_dlp
from yt_dlp.postprocessor import PostProcessor

# External programs the user must install separately (must be on PATH)
REQUIRED_TOOLS = {
    "ffmpeg": "winget install Gyan.FFmpeg      (or https://ffmpeg.org/download.html)",
    "ffprobe": "installed together with FFmpeg",
    "node": "winget install OpenJS.NodeJS.LTS  (or https://nodejs.org)",
}


def find_tools():
    """Return (found, missing) where found maps tool name -> full path."""
    found, missing = {}, []
    for name in REQUIRED_TOOLS:
        path = shutil.which(name)
        if path:
            found[name] = path
        else:
            missing.append(name)
    return found, missing


class CustomMetadataPP(PostProcessor):
    """Custom postprocessor to inject user-defined artist and album metadata."""
    def __init__(self, downloader=None, artist=None, album=None):
        super().__init__(downloader)
        self.artist = artist
        self.album = album

    def run(self, info):
        if self.artist:
            info['artist'] = self.artist
            info['uploader'] = self.artist
        if self.album:
            info['album'] = self.album
        return [], info


class GuiLogger:
    """Sends yt-dlp's own messages to the status box instead of the console."""
    def __init__(self, log):
        self.log = log

    def debug(self, msg):
        if not msg.startswith("[debug]"):
            self.log(msg)

    def info(self, msg):
        self.log(msg)

    def warning(self, msg):
        self.log(f"⚠️ {msg}")

    def error(self, msg):
        self.log(f"❌ {msg}")


class YouTubeDownloaderApp:
    def __init__(self, root):
        self.root = root
        self.root.title("YouTube Audio Downloader")
        self.root.geometry("660x500")
        self.root.minsize(600, 450)
        self._last_pct = -1

        default_downloads = os.path.join(os.path.expanduser("~"), "Downloads")
        padding = {'padx': 10, 'pady': 6}

        # --- URL Section ---
        url_frame = ttk.LabelFrame(root, text="YouTube URL (Single Video or Playlist)")
        url_frame.pack(fill="x", **padding)
        self.url_entry = ttk.Entry(url_frame, font=("Arial", 10))
        self.url_entry.pack(fill="x", expand=True, padx=8, pady=8)

        # --- Metadata Section ---
        meta_frame = ttk.LabelFrame(root, text="Metadata Overrides (Optional)")
        meta_frame.pack(fill="x", **padding)
        ttk.Label(meta_frame, text="Artist Name:").grid(row=0, column=0, sticky="w", padx=8, pady=5)
        self.artist_entry = ttk.Entry(meta_frame, font=("Arial", 10))
        self.artist_entry.grid(row=0, column=1, sticky="ew", padx=8, pady=5)
        ttk.Label(meta_frame, text="Album Name:").grid(row=1, column=0, sticky="w", padx=8, pady=5)
        self.album_entry = ttk.Entry(meta_frame, font=("Arial", 10))
        self.album_entry.grid(row=1, column=1, sticky="ew", padx=8, pady=5)
        meta_frame.columnconfigure(1, weight=1)

        # --- Directory Section ---
        dir_frame = ttk.LabelFrame(root, text="Download Location")
        dir_frame.pack(fill="x", **padding)
        self.dir_entry = ttk.Entry(dir_frame, font=("Arial", 10))
        self.dir_entry.insert(0, default_downloads)
        self.dir_entry.pack(side="left", fill="x", expand=True, padx=8, pady=8)
        browse_btn = ttk.Button(dir_frame, text="Browse...", command=self.browse_directory)
        browse_btn.pack(side="right", padx=8, pady=8)

        # --- Action Button ---
        action_frame = ttk.Frame(root)
        action_frame.pack(fill="x", **padding)
        self.download_btn = ttk.Button(action_frame, text="Start Download", command=self.start_download)
        self.download_btn.pack(side="right", padx=8, pady=5)

        # --- Status Log Box ---
        status_frame = ttk.LabelFrame(root, text="Status Log")
        status_frame.pack(fill="both", expand=True, **padding)
        self.status_box = tk.Text(status_frame, height=8, wrap="word", font=("Consolas", 9), state="disabled")
        self.status_box.pack(fill="both", expand=True, padx=8, pady=8)

        self.check_tools_on_startup()

    # ---------- tool check ----------
    def check_tools_on_startup(self):
        found, missing = find_tools()
        for name, path in found.items():
            self.log(f"Found {name}: {path}")
        if missing:
            lines = [f"  • {n}: {REQUIRED_TOOLS[n]}" for n in missing]
            text = (
                "These required programs were not found on your PATH:\n\n"
                + "\n".join(lines)
                + "\n\nInstall them, then close and reopen this app "
                  "(a restart is needed so Windows picks up the new PATH)."
            )
            self.log("❌ Missing tools: " + ", ".join(missing))
            self.download_btn.config(state="disabled")
            messagebox.showwarning("Missing required software", text)

    # ---------- UI helpers ----------
    def browse_directory(self):
        dir_selected = filedialog.askdirectory(initialdir=self.dir_entry.get())
        if dir_selected:
            self.dir_entry.delete(0, tk.END)
            self.dir_entry.insert(0, dir_selected)

    def log(self, message):
        # Safe to call from any thread
        self.root.after(0, self._log, message)

    def _log(self, message):
        self.status_box.config(state="normal")
        self.status_box.insert(tk.END, message + "\n")
        self.status_box.see(tk.END)
        self.status_box.config(state="disabled")

    # ---------- download ----------
    def start_download(self):
        url = self.url_entry.get().strip()
        if not url:
            messagebox.showerror("Error", "Please enter a valid YouTube URL.")
            return

        self.download_btn.config(state="disabled")
        self.log("Initializing download task...")
        threading.Thread(target=self.run_download_process, args=(url,), daemon=True).start()

    def run_download_process(self, url):
        download_path = self.dir_entry.get().strip()
        artist = self.artist_entry.get().strip()
        album = self.album_entry.get().strip()
        output_template = os.path.join(download_path, "%(title)s.%(ext)s")

        try:
            found, missing = find_tools()
            if missing:
                raise FileNotFoundError("Missing required software: " + ", ".join(missing))

            ydl_opts = {
                'format': 'bestaudio/best',
                'noplaylist': False,
                'ffmpeg_location': os.path.dirname(found["ffmpeg"]),
                'js_runtimes': {'node': {'path': found["node"]}},
                'writethumbnail': True,
                'outtmpl': output_template,
                'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'progress_hooks': [self.yt_progress_hook],
                'logger': GuiLogger(self.log),
                'quiet': True,
                'noprogress': True,
                'postprocessors': [
                    {'key': 'FFmpegThumbnailsConvertor', 'format': 'jpg', 'when': 'before_dl'},
                    {'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '320'},
                    {'key': 'FFmpegMetadata', 'add_metadata': True},
                    {'key': 'EmbedThumbnail'},
                ],
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                if artist or album:
                    ydl.add_post_processor(CustomMetadataPP(artist=artist, album=album), when='pre_process')
                ydl.download([url])

            self.log("✅ Download(s) complete successfully!")
        except Exception as e:
            msg = str(e)
            self.log(f"❌ Error: {msg}")
            self.root.after(0, lambda m=msg: messagebox.showerror("Download Error", m))
        finally:
            self.root.after(0, lambda: self.download_btn.config(state="normal"))

    def yt_progress_hook(self, d):
        if d['status'] == 'downloading':
            total = d.get('total_bytes') or d.get('total_bytes_estimate')
            if total:
                pct = int(d.get('downloaded_bytes', 0) / total * 100)
                if pct // 10 != self._last_pct:
                    self._last_pct = pct // 10
                    name = os.path.basename(d.get('filename', ''))
                    self.log(f"Downloading {name}: {pct}%")
        elif d['status'] == 'finished':
            self._last_pct = -1
            self.log(f"Finished downloading, converting & tagging: {os.path.basename(d.get('filename', ''))}")


if __name__ == "__main__":
    root = tk.Tk()
    app = YouTubeDownloaderApp(root)
    root.mainloop()