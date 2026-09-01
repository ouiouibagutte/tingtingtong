import flet as ft
import yt_dlp
import os
import threading

# --- CONFIGURATION ---
if os.name != 'nt': 
    DOWNLOAD_PATH = "/sdcard/Download"
else:
    DOWNLOAD_PATH = "downloads"

if not os.path.exists(DOWNLOAD_PATH):
    os.makedirs(DOWNLOAD_PATH)

class MusicLoaderApp:
    def __init__(self, page: ft.Page):
        self.page = page
        self.page.title = "Bobsicles Mp3s Pro"
        self.page.theme_mode = ft.ThemeMode.DARK
        self.page.padding = 20
        self.page.window_width = 400
        self.page.window_height = 800
        
        # State management
        self.is_downloading = False
        
        # UI Elements
        self.url_input = ft.TextField(
            label="YouTube Links",
            hint_text="Paste links here (one per line)",
            multiline=True,
            min_lines=3,
            max_lines=5,
            border_color=ft.Colors.BLUE_700
        )
        
        self.format_selector = ft.RadioGroup(
            content=ft.Row([
                ft.Radio(value="audio", label="Audio (M4A)"),
                ft.Radio(value="video", label="Video (MP4)")
            ], alignment=ft.MainAxisAlignment.CENTER)
        )
        self.format_selector.value = "audio" 
        
        self.progress_bar = ft.ProgressBar(width=400, color="blue", visible=False)
        self.log_column = ft.Column(scroll=ft.ScrollMode.ADAPTIVE, expand=True)
        self.dup_list = ft.Column(visible=False)

        # Buttons
        self.btn_download = ft.ElevatedButton(
            "Download", 
            icon=ft.Icons.DOWNLOAD, 
            on_click=self.start_download_thread,
            style=ft.ButtonStyle(color=ft.Colors.WHITE, bgcolor=ft.Colors.BLUE_800)
        )
        self.btn_clear_logs = ft.IconButton(
            icon=ft.Icons.DELETE_SWEEP, 
            tooltip="Clear Logs",
            icon_color="grey",
            on_click=self.clear_logs
        )

    def log(self, message, color=ft.Colors.WHITE):
        self.log_column.controls.append(ft.Text(message, color=color, size=14))
        self.page.update()

    def clear_logs(self, e):
        self.log_column.controls.clear()
        self.page.update()

    def progress_hook(self, d):
        if d['status'] == 'downloading':
            if not self.progress_bar.visible:
                self.progress_bar.visible = True
                self.page.update()
        elif d['status'] == 'finished':
            self.progress_bar.visible = False
            self.page.update()

    # --- DOWNLOAD LOGIC (Mobile Optimized) ---
    def run_downloads(self, urls, download_mode):
        if download_mode == "video":
            self.log("📹 Format Mode: Progressive MP4 Video", ft.Colors.BLUE_400)
            # Grabs a single pre-merged file so Android doesn't need ffmpeg to combine them
            format_rule = 'best[ext=mp4]/best'
        else:
            self.log("🎵 Format Mode: Audio Streams", ft.Colors.BLUE_400)
            # Falls back gracefully if 140/m4a is geo-blocked
            format_rule = 'bestaudio[ext=m4a]/bestaudio/best'

        ydl_opts = {
            'format': format_rule, 
            'outtmpl': os.path.join(DOWNLOAD_PATH, '%(title)s.%(ext)s'),
            'progress_hooks': [self.progress_hook],
            'quiet': True,
            'noplaylist': True,
            # Bypass for the 403 Forbidden error using client spoofing
            'extractor_args': {'youtube': {'player_client': ['android', 'web']}},
            'nocheckcertificate': True
        }

        for url in urls:
            if not url: continue
            try:
                self.log(f"🚀 Starting: {url[:30]}...", ft.Colors.BLUE_200)
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([url])
                self.log("✅ Saved to Downloads!", ft.Colors.GREEN_400)
            except Exception as e:
                self.log(f"❌ Failed: {str(e)}", ft.Colors.RED_400)
        
        # Reset UI post-download
        self.progress_bar.visible = False
        self.is_downloading = False
        self.btn_download.disabled = False
        self.page.update()

    def start_download_thread(self, e):
        # Extract and clean URLs
        raw_urls = self.url_input.value.splitlines() if self.url_input.value else []
        urls = [u.strip() for u in raw_urls if u.strip()]
        
        if not urls:
            self.page.snack_bar = ft.SnackBar(ft.Text("Please enter a valid link!"))
            self.page.snack_bar.open = True
            self.page.update()
            return
        
        # Lock button to prevent duplicate concurrent threads
        self.is_downloading = True
        self.btn_download.disabled = True
        self.page.update()
        
        mode = self.format_selector.value
        threading.Thread(target=self.run_downloads, args=(urls, mode), daemon=True).start()

    # --- DUPLICATE CHECKER ---
    def check_duplicates(self, e):
        self.log_column.controls.clear()
        self.dup_list.controls.clear()
        self.log("🔎 Scanning library...", ft.Colors.AMBER)
        
        files = [f for f in os.listdir(DOWNLOAD_PATH) if f.endswith(('.mp3', '.m4a', '.mp4'))]
        seen_files = {} 
        duplicates = []

        for f in files:
            path = os.path.join(DOWNLOAD_PATH, f)
            size = os.path.getsize(path)
            name_key = os.path.splitext(f)[0].strip().lower()
            file_id = (name_key, size)
            
            if file_id in seen_files:
                duplicates.append((path, seen_files[file_id]))
            else:
                seen_files[file_id] = path

        if not duplicates:
            self.log("✨ No duplicates found!", ft.Colors.GREEN)
        else:
            self.dup_list.visible = True
            for dup_path, original in duplicates:
                fname = os.path.basename(dup_path)
                self.dup_list.controls.append(
                    ft.Container(
                        content=ft.Row([
                            ft.Icon(ft.Icons.COPY, color="amber"),
                            ft.Text(f"{fname[:20]}...", expand=True),
                            ft.IconButton(
                                icon=ft.Icons.DELETE_FOREVER,
                                icon_color="red",
                                on_click=lambda _, p=dup_path: self.delete_file(p)
                            )
                        ]),
                        padding=10,
                        border=ft.border.all(1, ft.Colors.GREY_800),
                        border_radius=8
                    )
                )
        self.page.update()

    def delete_file(self, path):
        try:
            os.remove(path)
            self.log(f"🗑️ Deleted: {os.path.basename(path)}", ft.Colors.RED_200)
            self.check_duplicates(None) 
        except Exception as e:
            self.log(f"Error deleting: {e}")

    def build(self):
        header = ft.Column([
            ft.Text("Bobsicles Mp3s", size=32, weight="bold", color="blue"),
            ft.Text("Mobile Batch Downloader", size=14, color="grey"),
        ], spacing=0)

        buttons = ft.Row([
            self.btn_download,
            ft.OutlinedButton(
                "Check Dups", 
                icon=ft.Icons.REPLAY,
                on_click=self.check_duplicates
            ),
        ], alignment=ft.MainAxisAlignment.CENTER)

        log_header = ft.Row([
            ft.Text("Logs & Activity", size=16, weight="bold", expand=True),
            self.btn_clear_logs
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)

        self.page.add(
            header,
            ft.Divider(height=20, color="transparent"),
            self.url_input,
            ft.Text("Select Format Option:", size=14, weight="bold", color="blue_200"),
            self.format_selector,
            ft.Divider(height=10, color="transparent"),
            buttons,
            self.progress_bar,
            log_header,
            ft.Container(
                content=self.log_column,
                height=200,
                padding=10,
                bgcolor=ft.Colors.BLACK12,
                border_radius=10
            ),
            ft.Text("Duplicates Found", size=16, weight="bold"),
            self.dup_list
        )

def main(page: ft.Page):
    app = MusicLoaderApp(page)
    app.build()

ft.app(main)
