import flet as ft
import yt_dlp
import os
import threading

# --- CONFIGURATION ---
DOWNLOAD_PATH = "downloads"
if not os.path.exists(DOWNLOAD_PATH):
    os.makedirs(DOWNLOAD_PATH)

class MusicLoaderApp:
    def __init__(self, page: ft.Page):
        self.page = page
        self.page.title = "Music Loader Pro"
        self.page.theme_mode = ft.ThemeMode.DARK
        self.page.padding = 20
        self.page.window_width = 400
        self.page.window_height = 800
        
        # UI Elements
        self.url_input = ft.TextField(
            label="YouTube Links",
            hint_text="Paste links here (one per line)",  # Changed from placeholder
            multiline=True,
            min_lines=3,
            max_lines=5,
            border_color=ft.Colors.BLUE_700  # Note the capital 'C'
        )
        
        self.progress_bar = ft.ProgressBar(width=400, color="blue", visible=False)
        self.log_column = ft.Column(scroll=ft.ScrollMode.ADAPTIVE, expand=True)
        self.dup_list = ft.Column(visible=False)

    def log(self, message, color=ft.Colors.WHITE):
        self.log_column.controls.append(ft.Text(message, color=color, size=14))
        self.page.update()

    def progress_hook(self, d):
        if d['status'] == 'downloading':
            self.progress_bar.visible = True
            self.page.update()
        if d['status'] == 'finished':
            self.progress_bar.visible = False
            self.page.update()

    def run_downloads(self, urls):
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': os.path.join(DOWNLOAD_PATH, '%(title)s.%(ext)s'),
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'progress_hooks': [self.progress_hook],
            'quiet': True,
            'noplaylist': True,
        }

        for url in urls:
            url = url.strip()
            if not url: continue
            try:
                self.log(f"🚀 Starting: {url[:30]}...", ft.Colors.BLUE_200)
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([url])
                self.log(f"✅ Downloaded successfully!", ft.Colors.GREEN_400)
            except Exception as e:
                self.log(f"❌ Failed: {str(e)}", ft.Colors.RED_400)
        
        self.progress_bar.visible = False
        self.page.update()

    def start_download_thread(self, e):
        urls = self.url_input.value.splitlines()
        if not urls:
            self.page.snack_bar = ft.SnackBar(ft.Text("Please enter at least one URL"))
            self.page.snack_bar.open = True
            self.page.update()
            return
        
        threading.Thread(target=self.run_downloads, args=(urls,), daemon=True).start()

    def check_duplicates(self, e):
        self.log_column.controls.clear()
        self.dup_list.controls.clear()
        self.log("🔎 Scanning library...", ft.Colors.AMBER)
        
        files = [f for f in os.listdir(DOWNLOAD_PATH) if f.endswith('.mp3')]
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
                            ft.Text(f"{fname[:25]}...", expand=True),
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
            ft.Text("Music Loader", size=32, weight="bold", color="blue"),
            ft.Text("Batch Downloader & Manager", size=14, color="grey"),
        ], spacing=0)

        buttons = ft.Row([
            ft.ElevatedButton(
                "Download", 
                icon=ft.Icons.DOWNLOAD, 
                on_click=self.start_download_thread,
                style=ft.ButtonStyle(color=ft.Colors.WHITE, bgcolor=ft.Colors.BLUE_800)
            ),
            ft.OutlinedButton(
                "Check Dups", 
                icon=ft.Icons.REPLAY,  # Changed from REPEATING_FFS
                on_click=self.check_duplicates
            ),
        ], alignment=ft.MainAxisAlignment.CENTER)

        self.page.add(
            header,
            ft.Divider(height=20, color="transparent"),
            self.url_input,
            buttons,
            self.progress_bar,
            ft.Text("Logs & Activity", size=16, weight="bold"),
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

# The modern way to run the app
ft.app(main)
