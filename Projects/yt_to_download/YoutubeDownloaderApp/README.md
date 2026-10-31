# YouTube Audio Downloader

[Download File](./dist)

A simple Windows app that downloads audio from YouTube videos or playlists as 320 kbps MP3 files, with the thumbnail embedded as cover art. You can optionally set the artist and album name for the downloaded tracks.

## What you need to download

The app needs two free programs installed on your computer. You only have to do this once.

| Program | Why it's needed | Includes |
|---|---|---|
| **FFmpeg** | Converts audio to MP3 and embeds metadata and cover art | `ffmpeg` and `ffprobe` |
| **Node.js (LTS)** | Lets the downloader solve YouTube's JavaScript checks | `node` |

You do **not** need to install Python.

### Option 1: Install with winget (easiest)

Open **Command Prompt** or **PowerShell** and run:

```
winget install Gyan.FFmpeg
winget install OpenJS.NodeJS.LTS
```

Then **close and reopen the app** (or restart your PC if it still doesn't work).

### Option 2: Install manually

**Node.js**

1. Go to https://nodejs.org and download the **LTS** installer.
2. Run it and keep the default options (this adds Node to your PATH automatically).

**FFmpeg**

1. Go to https://ffmpeg.org/download.html, choose **Windows builds**, and download a **release** build (the `.zip` or `.7z`).
2. Extract it somewhere permanent, for example `C:\ffmpeg`.
3. Make sure the extracted folder contains `bin\ffmpeg.exe` and `bin\ffprobe.exe`.
4. Add the `bin` folder to your PATH:
   - Press the Windows key, type **Edit the system environment variables**, and open it.
   - Click **Environment Variables**.
   - Under **User variables**, select **Path**, click **Edit**, then **New**, and enter `C:\ffmpeg\bin` (adjust to match where you extracted it).
   - Click **OK** on every window.
5. Close and reopen the app.

### Check that everything is installed

Open a **new** Command Prompt window and run each of these. Each should print a version number rather than an error:

```
ffmpeg -version
ffprobe -version
node --version
```

## How to use

1. Start the app.
2. Paste a YouTube video or playlist link into the URL box.
3. *(Optional)* Enter an artist name and/or album name. These override the tags in the downloaded files. Leave them blank to keep the video's own details.
4. Choose a download folder (the default is your `Downloads` folder).
5. Click **Start Download** and watch the progress in the status log.

Playlists download every video in the list, so large playlists can take a while.

## Troubleshooting

**A "Missing required software" message appears when the app starts**
The app can't find one or more of the tools listed in the message. Install them using the steps above, then close and fully reopen the app. Programs only see PATH changes if they start after the install.

**The tools are installed but the app still can't find them**
Run the check commands above in a *new* Command Prompt. If a command isn't recognised, its folder isn't on your PATH. For FFmpeg, re-check step 4 of the manual install. Restarting your PC also fixes most PATH issues.

**Downloads suddenly stop working or show errors about extracting data**
YouTube changes its site often, and the downloader inside the app can become outdated. Download the latest version of the app to get an updated downloader.

**The cover art is missing from some files**
Some videos have thumbnails that can't be embedded. The audio and tags are still saved normally.

**Windows SmartScreen or antivirus warns about the app**
Unsigned apps built with PyInstaller are sometimes flagged incorrectly. If you trust where you got the file, choose **More info → Run anyway**, or add an exception in your antivirus.

## Building from source (for developers)

You need Python 3.9 or newer.

```
pip install -U pyinstaller "yt-dlp[default]"
pyinstaller --clean --onefile --noconsole --collect-all yt_dlp --collect-all yt_dlp_ejs --name "YouTube Audio Downloader" yt_gui_downloader.py
```

The exe is created in the `dist` folder. FFmpeg and Node.js are deliberately **not** bundled, so users install them separately as described above. To run directly from source instead:

```
python yt_gui_downloader.py
```

Rebuild the exe after upgrading `yt-dlp` so that users get the newer downloader.

## Legal notice

This software is provided "as is", without warranty of any kind, express or implied, including but not limited to warranties of merchantability, fitness for a particular purpose, or non-infringement.

This tool is intended only for downloading content that you own, that is in the public domain, or that you otherwise have permission to download. You are solely responsible for how you use it and for making sure your use complies with copyright law, YouTube's Terms of Service, and any other laws or agreements that apply to you.

To the fullest extent permitted by law, the author is not liable for any claim, damages, or other liability arising from the use of this software or from any content downloaded with it, including but not limited to copyright infringement, account restrictions, data loss, or damage to your computer. This software is not affiliated with, endorsed by, or sponsored by YouTube or Google.

By using this software, you agree to these terms.
## Credits

Built with [yt-dlp](https://github.com/yt-dlp/yt-dlp), [FFmpeg](https://ffmpeg.org), and [Node.js](https://nodejs.org).
