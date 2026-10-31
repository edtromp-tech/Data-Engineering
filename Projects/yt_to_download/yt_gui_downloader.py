import os
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import yt_dlp
from yt_dlp.postprocessor import PostProcessor

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

class YouTubeDownloaderApp:
    def __init__(self, root):
        self.root = root
        self.root.title("YouTube Audio Downloader")
        self.root.geometry("660x500")
        self.root.minsize(600, 450)

        # Default downloads folder
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

    def browse_directory(self):
        dir_selected = filedialog.askdirectory(initialdir=self.dir_entry.get())
        if dir_selected:
            self.dir_entry.delete(0, tk.END)
            self.dir_entry.insert(0, dir_selected)

    def log(self, message):
        self.status_box.config(state="normal")
        self.status_box.insert(tk.END, message + "\n")
        self.status_box.see(tk.END)
        self.status_box.config(state="disabled")

    def start_download(self):
        url = self.url_entry.get().strip()
        if not url:
            messagebox.showerror("Error", "Please enter a valid YouTube URL.")
            return

        self.download_btn.config(state="disabled")
        self.log("Initializing download task...")

        # Run in a background thread so the window stays responsive
        threading.Thread(target=self.run_download_process, args=(url,), daemon=True).start()

    def run_download_process(self, url):
        download_path = self.dir_entry.get().strip()
        artist = self.artist_entry.get().strip()
        album = self.album_entry.get().strip()

        output_template = os.path.join(download_path, "%(title)s.%(ext)s")

        ydl_opts = {
            'format': 'bestaudio/best',
            'noplaylist': False,
            'js_runtimes': {'node': {}},
            'writethumbnail': True,
            'outtmpl': output_template,
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'progress_hooks': [self.yt_progress_hook],
            'postprocessors': [
                {
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '320',
                },
                {
                    'key': 'FFmpegMetadata',
                    'add_metadata': True,
                },
                {
                    'key': 'EmbedThumbnail',
                }
            ],
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # Safely register custom metadata override if user provided input
                if artist or album:
                    ydl.add_post_processor(CustomMetadataPP(artist=artist, album=album))
                
                ydl.download([url])

            self.log("✅ Download(s) complete successfully!")
        except Exception as e:
            self.log(f"❌ Error: {str(e)}")
            messagebox.showerror("Download Error", str(e))
        finally:
            self.download_btn.config(state="normal")

    def yt_progress_hook(self, d):
        if d['status'] == 'downloading':
            p = d.get('_percent_str', '0.0%').strip()
            eta = d.get('_eta_str', 'unknown').strip()
            filename = os.path.basename(d.get('filename', ''))
            self.log(f"Downloading {filename}: {p} (ETA: {eta})")
        elif d['status'] == 'finished':
            self.log(f"Finished downloading, embedding metadata & artwork: {os.path.basename(d.get('filename', ''))}")

if __name__ == "__main__":
    root = tk.Tk()
    app = YouTubeDownloaderApp(root)
    root.mainloop()