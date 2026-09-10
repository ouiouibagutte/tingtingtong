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
        
        # Color Theme derived from Logo (Vibrant Blue & Accent Orange)
        self.COLOR_PRIMARY = ft.Colors.BLUE_600
        self.COLOR_ACCENT = ft.Colors.ORANGE_600
        
        # State management
        self.is_downloading = False
        
        # UI Elements
        self.url_input = ft.TextField(
            label="YouTube Links",
            hint_text="Paste links here (one per line)",
            multiline=True,
            min_lines=3,
            max_lines=5,
            border_color=self.COLOR_PRIMARY,
            focused_border_color=self.COLOR_ACCENT
        )
        
        self.format_selector = ft.RadioGroup(
            content=ft.Row([
                ft.Radio(value="audio", label="Audio Only (M4A/WebM)", active_color=self.COLOR_ACCENT),
                ft.Radio(value="video", label="Video (MP4)", active_color=self.COLOR_ACCENT)
            ], alignment=ft.MainAxisAlignment.CENTER)
        )
        self.format_selector.value = "audio" 
        
        self.progress_bar = ft.ProgressBar(width=400, color=self.COLOR_ACCENT, visible=False)
        self.log_column = ft.Column(scroll=ft.ScrollMode.ADAPTIVE, expand=True)
        self.dup_list = ft.Column(visible=False)

        # Buttons
        self.btn_download = ft.ElevatedButton(
            "Download", 
            icon=ft.Icons.DOWNLOAD, 
            on_click=self.start_download_thread,
            style=ft.ButtonStyle(
                color=ft.Colors.WHITE, 
                bgcolor=self.COLOR_PRIMARY
            )
        )
        self.btn_clear_logs = ft.IconButton(
            icon=ft.Icons.DELETE_SWEEP, 
            tooltip="Clear Logs",
            icon_color=ft.Colors.GREY_400,
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

    # --- DOWNLOAD LOGIC ---
    def run_downloads(self, urls, download_mode):
        if download_mode == "video":
            self.log("📹 Format Mode: MP4 Video", self.COLOR_PRIMARY)
            format_rule = 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best'
        else:
            self.log("🎵 Format Mode: Audio Only", self.COLOR_PRIMARY)
            # Strictly matches audio streams; never falls back to video
            format_rule = 'bestaudio[ext=m4a]/bestaudio'

        ydl_opts = {
            'format': format_rule, 
            'outtmpl': os.path.join(DOWNLOAD_PATH, '%(title)s.%(ext)s'),
            'progress_hooks': [self.progress_hook],
            'quiet': True,
            'noplaylist': True,
            'nocheckcertificate': True
        }

        for url in urls:
            if not url: 
                continue
            try:
                # Fetch metadata first to log human-readable title
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=False)
                    title = info.get('title', 'Unknown Title')
                    self.log(f"🚀 Starting: {title}", self.COLOR_ACCENT)
                    ydl.process_info(info)
                self.log(f"✅ Saved: {title}", ft.Colors.GREEN_400)
            except Exception as e:
                self.log(f"❌ Failed: {str(e)}", ft.Colors.RED_400)
        
        # Reset UI post-download
        self.progress_bar.visible = False
        self.is_downloading = False
        self.btn_download.disabled = False
        self.page.update()

    def start_download_thread(self, e):
        raw_urls = self.url_input.value.splitlines() if self.url_input.value else []
        urls = [u.strip() for u in raw_urls if u.strip()]
        
        if not urls:
            self.page.snack_bar = ft.SnackBar(ft.Text("Please enter a valid link!"))
            self.page.snack_bar.open = True
            self.page.update()
            return
        
        self.is_downloading = True
        self.btn_download.disabled = True
        self.page.update()
        
        mode = self.format_selector.value
        threading.Thread(target=self.run_downloads, args=(urls, mode), daemon=True).start()

    # --- DUPLICATE CHECKER ---
    def check_duplicates(self, e):
        self.log_column.controls.clear()
        self.dup_list.controls.clear()
        self.log("🔎 Scanning library...", self.COLOR_ACCENT)
        
        files = [f for f in os.listdir(DOWNLOAD_PATH) if f.endswith(('.mp3', '.m4a', '.mp4', '.webm'))]
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
                            ft.Icon(ft.Icons.COPY, color=self.COLOR_ACCENT),
                            ft.Text(f"{fname[:20]}...", expand=True),
                            ft.IconButton(
                                icon=ft.Icons.DELETE_FOREVER,
                                icon_color=ft.Colors.RED_400,
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
            ft.Text("Bobsicles Mp3s", size=32, weight="bold", color=self.COLOR_PRIMARY),
            ft.Text("Mobile Batch Downloader", size=14, color=ft.Colors.GREY_400),
        ], spacing=0)

        buttons = ft.Row([
            self.btn_download,
            ft.OutlinedButton(
                "Check Dups", 
                icon=ft.Icons.REPLAY,
                on_click=self.check_duplicates,
                style=ft.ButtonStyle(color=self.COLOR_ACCENT)
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
            ft.Text("Select Format Option:", size=14, weight="bold", color=self.COLOR_PRIMARY),
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

