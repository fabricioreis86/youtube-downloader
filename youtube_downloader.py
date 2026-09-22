"""
YouTube Downloader com Dublagem
Requer: pip install -r requirements.txt
Requer: ffmpeg instalado no sistema
"""

import os
import re
import json
import threading
import subprocess
import tkinter as tk
from tkinter import filedialog, messagebox
from datetime import datetime
from io import BytesIO
from pathlib import Path

import customtkinter as ctk
import requests
from PIL import Image

# ─── Configuração de aparência ────────────────────────────────────────────────
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

HISTORY_FILE = "downloads_history.json"
CONFIG_FILE  = "config.json"


def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def save_config(cfg):
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

# ─── Utilitários ──────────────────────────────────────────────────────────────

def format_duration(seconds):
    if not seconds:
        return "Desconhecida"
    seconds = int(seconds)
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    if h:
        return f"{h:02d}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"


def format_filesize(bytes_val):
    if not bytes_val:
        return ""
    for unit in ["B", "KB", "MB", "GB"]:
        if bytes_val < 1024:
            return f"{bytes_val:.1f} {unit}"
        bytes_val /= 1024
    return f"{bytes_val:.1f} TB"


def check_ffmpeg():
    try:
        subprocess.run(
            ["ffmpeg", "-version"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True,
        )
        return True
    except (FileNotFoundError, subprocess.CalledProcessError):
        return False


def load_history():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []


def save_history(entry):
    history = load_history()
    history.insert(0, entry)
    history = history[:100]  # manter apenas os 100 mais recentes
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)


# ─── Janela principal ─────────────────────────────────────────────────────────

def _make_context_menu(widget, readonly=False):
    """Cria e vincula menu de contexto (botão direito) a um widget de texto."""

    def show_menu(event):
        # Criar menu fresh a cada clique (evita erros de estado)
        menu = tk.Menu(widget.winfo_toplevel(), tearoff=0)
        if not readonly:
            menu.add_command(label="Recortar",    command=lambda: widget.event_generate("<<Cut>>"))
        menu.add_command(label="Copiar",          command=lambda: widget.event_generate("<<Copy>>"))
        if not readonly:
            menu.add_command(label="Colar",       command=lambda: widget.event_generate("<<Paste>>"))
        menu.add_separator()
        menu.add_command(label="Selecionar tudo", command=select_all)
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    def select_all():
        try:
            widget.select_range(0, "end")
            widget.icursor("end")
        except Exception:
            try:
                widget.tag_add("sel", "1.0", "end")
            except Exception:
                pass

    widget.bind("<Button-3>", show_menu)


class YouTubeDownloader(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("YouTube Downloader com Dublagem")
        # Definir WMClass para o painel/taskbar reconhecer o programa
        self.tk.call("wm", "iconname", ".", "youtube-downloader")
        self.wm_iconname("youtube-downloader")
        self.tk.call("tk", "appname", "youtube-downloader")
        # Definir a classe WM (segundo valor do WM_CLASS)
        self.tk.call("wm", "title", ".", "YouTube Downloader com Dublagem")
        self.after(1, lambda: self.tk.call("wm", "iconphoto", ".", self.tk.call("image", "create", "photo")))
        # Forçar WM_CLASS completo via xdotool após janela aparecer
        self.after(500, self._set_wm_class)
        self.resizable(True, True)
        self.after(200, self._fit_to_screen)

        # Estado interno
        self._video_info = None
        self._audio_formats = []
        self._video_formats = []
        self._thumbnail_image = None
        self._downloading = False

        # Variáveis de controle
        self.url_var = ctk.StringVar()
        self.quality_var = ctk.StringVar(value="1080p")
        self.audio_var = ctk.StringVar(value="Melhor disponível")
        self.output_var = ctk.StringVar(value=str(Path.home() / "Downloads"))
        self.format_var = ctk.StringVar(value="MP4")
        self.search_var = ctk.StringVar()
        self.browser_var = ctk.StringVar(value="brave")

        self.sub_enabled_var = ctk.BooleanVar(value=False)
        self.sub_lang_var = ctk.StringVar(value="Nenhuma")
        self.sub_format_var = ctk.StringVar(value="srt")
        self.sub_embed_var = ctk.BooleanVar(value=False)
        self._subtitle_langs = {}   # label -> lang_code
        self._sub_lang_labels = []    # lista ordenada de labels para o picker
        self.convert_var = ctk.StringVar(value="nao")   # "nao" | "h264" | "h265"
        self.convert_delete_var = ctk.BooleanVar(value=True)  # apagar original após converter

        self._build_ui()
        self._bind_context_menus()
        self._load_config()
        # Adiar tarefas de rede/subprocess para após a janela aparecer
        self.after(300, self._startup_checks)

    def _bind_context_menus(self):
        """Vincula menu de contexto (botão direito) a todos os campos de texto."""
        # CTkEntry expõe o widget Tkinter interno via ._entry
        try:
            _make_context_menu(self.url_entry._entry)
        except Exception:
            _make_context_menu(self.url_entry)
        try:
            _make_context_menu(self.cookie_file_entry._entry)
        except Exception:
            _make_context_menu(self.cookie_file_entry)
        # Log — somente leitura (CTkTextbox expõe ._textbox)
        try:
            _make_context_menu(self.log_text._textbox, readonly=True)
        except Exception:
            _make_context_menu(self.log_text, readonly=True)
        # Ctrl+A no log
        self.log_text.bind("<Control-a>", lambda e: self.log_text.tag_add("sel", "1.0", "end"))

    def _set_wm_class(self):
        """Sobrescreve WM_CLASS usando python-xlib para corrigir o segundo valor."""
        try:
            from Xlib import display as xdisplay
            self.update_idletasks()
            d = xdisplay.Display()
            win = d.create_resource_object("window", self.winfo_id())
            win.set_wm_class("youtube-downloader", "youtube-downloader")
            d.sync()
            d.close()
        except ImportError:
            pass
        except Exception:
            pass

    def _fit_to_screen(self):
        """Posiciona a janela no monitor principal com largura ideal e altura maximizada."""
        self.update_idletasks()

        # Posição e largura do monitor principal via xrandr
        primary_x, primary_y, primary_w, primary_h = 0, 0, 0, 0
        try:
            out = subprocess.check_output(["xrandr", "--query"], text=True)
            import re as _re
            m = _re.search(r"connected primary (\d+)x(\d+)\+(\d+)\+(\d+)", out)
            if m:
                primary_w = int(m.group(1))
                primary_h = int(m.group(2))
                primary_x = int(m.group(3))
                primary_y = int(m.group(4))
        except Exception:
            pass

        if primary_w == 0:
            primary_w = self.winfo_screenwidth()
            primary_h = self.winfo_screenheight()

        # Largura ideal centralizada no monitor principal
        win_w = min(820, primary_w)
        pos_x = primary_x + (primary_w - win_w) // 2

        # Mover para o monitor principal primeiro
        self.geometry(f"{win_w}x600+{pos_x}+{primary_y}")
        self.update_idletasks()

        # Maximizar apenas verticalmente — deixa o WM calcular a altura certa
        self.wm_attributes("-zoomed", True)
        self.update_idletasks()

        # Capturar a altura que o WM atribuiu após maximizar
        zoomed_h = self.winfo_height()
        zoomed_y = self.winfo_y()

        # Restaurar tamanho normal mas com a altura correta que o WM usou
        self.wm_attributes("-zoomed", False)
        self.update_idletasks()

        self.geometry(f"{win_w}x{zoomed_h}+{pos_x}+{zoomed_y}")
        self.minsize(min(680, win_w), min(480, zoomed_h))
        # Garantir que o scroll começa no topo
        self.after(50, self._scroll_to_top)

    def _scroll_to_top(self):
        try:
            self._download_scroll._parent_canvas.yview_moveto(0)
        except Exception:
            pass

    # ── Construção da interface ───────────────────────────────────────────────

    def _load_config(self):
        """Carrega configuracoes salvas (pasta de destino, cookies, etc)."""
        cfg = load_config()
        if cfg.get("cookie_file"):
            self.cookie_file_var.set(cfg["cookie_file"])
            self.cookie_mode_var.set("arquivo")
        if cfg.get("output_dir") and os.path.isdir(cfg["output_dir"]):
            self.output_var.set(cfg["output_dir"])
        if cfg.get("cookie_mode"):
            self.cookie_mode_var.set(cfg["cookie_mode"])
        if cfg.get("browser"):
            self.browser_var.set(cfg["browser"])
        if cfg.get("quality"):
            self.quality_var.set(cfg["quality"])
        if cfg.get("format"):
            self.format_var.set(cfg["format"])

    def _save_config(self):
        """Salva configuracoes atuais para restaurar na proxima abertura."""
        save_config({
            "cookie_file":  self.cookie_file_var.get(),
            "cookie_mode":  self.cookie_mode_var.get(),
            "browser":      self.browser_var.get(),
            "output_dir":   self.output_var.get(),
            "quality":      self.quality_var.get(),
            "format":       self.format_var.get(),
        })

    def _build_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Notebook com abas
        self.tabview = ctk.CTkTabview(self, corner_radius=8)
        self.tabview.grid(row=0, column=0, sticky="nsew", padx=12, pady=12)

        self.tabview.add("⬇ Download")
        self.tabview.add("🕘 Histórico")

        self._build_download_tab(self.tabview.tab("⬇ Download"))
        self._build_history_tab(self.tabview.tab("🕘 Histórico"))

    def _build_download_tab(self, parent):
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_rowconfigure(0, weight=1)

        # Frame rolável que contém todo o conteúdo da aba
        self._download_scroll = ctk.CTkScrollableFrame(parent, fg_color="transparent")
        self._download_scroll.grid(row=0, column=0, sticky="nsew", padx=0, pady=0)
        self._download_scroll.grid_columnconfigure(0, weight=1)
        scroll = self._download_scroll
        parent = scroll  # redirecionar todos os widgets para o frame rolável


        # ── Seção URL ────────────────────────────────────────────────────────
        url_frame = ctk.CTkFrame(parent, corner_radius=8)
        url_frame.grid(row=0, column=0, sticky="ew", padx=4, pady=(4, 6))
        url_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(url_frame, text="URL do Vídeo:", font=("Segoe UI", 13, "bold")).grid(
            row=0, column=0, padx=(12, 8), pady=10, sticky="w"
        )
        self.url_entry = ctk.CTkEntry(
            url_frame, textvariable=self.url_var, placeholder_text="Cole o link do YouTube aqui..."
        )
        self.url_entry.grid(row=0, column=1, padx=(0, 8), pady=10, sticky="ew")
        self.btn_analyze = ctk.CTkButton(
            url_frame, text="Analisar", width=100, command=self._start_analyze
        )
        self.btn_analyze.grid(row=0, column=2, padx=(0, 12), pady=10)

        # ── Seção Info do vídeo ──────────────────────────────────────────────
        info_frame = ctk.CTkFrame(parent, corner_radius=8)
        info_frame.grid(row=1, column=0, sticky="ew", padx=4, pady=(0, 6))
        info_frame.grid_columnconfigure(1, weight=1)

        self.thumbnail_label = ctk.CTkLabel(
            info_frame,
            text="📺",
            font=("Segoe UI", 40),
            width=160,
            height=90,
            corner_radius=6,
            fg_color=("gray80", "gray20"),
        )
        self.thumbnail_label.grid(row=0, column=0, rowspan=3, padx=12, pady=10, sticky="w")

        self.title_label = ctk.CTkLabel(
            info_frame,
            text="Nenhum vídeo analisado",
            font=("Segoe UI", 13),
            wraplength=480,
            justify="left",
            anchor="w",
        )
        self.title_label.grid(row=0, column=1, padx=(8, 12), pady=(12, 2), sticky="w")

        self.duration_label = ctk.CTkLabel(
            info_frame, text="", font=("Segoe UI", 11), text_color="gray"
        )
        self.duration_label.grid(row=1, column=1, padx=(8, 12), pady=0, sticky="w")

        self.channel_label = ctk.CTkLabel(
            info_frame, text="", font=("Segoe UI", 11), text_color="gray"
        )
        self.channel_label.grid(row=2, column=1, padx=(8, 12), pady=(0, 10), sticky="w")

        # ── Seção Opções ─────────────────────────────────────────────────────
        opts_frame = ctk.CTkFrame(parent, corner_radius=8)
        opts_frame.grid(row=2, column=0, sticky="ew", padx=4, pady=(0, 6))
        opts_frame.grid_columnconfigure((1, 3), weight=1)

        ctk.CTkLabel(opts_frame, text="Qualidade:").grid(
            row=0, column=0, padx=(12, 6), pady=10, sticky="w"
        )
        self.quality_menu = ctk.CTkOptionMenu(
            opts_frame,
            variable=self.quality_var,
            values=["2160p (4K)", "1440p", "1080p", "720p", "480p", "360p", "Apenas Áudio"],
        )
        self.quality_menu.grid(row=0, column=1, padx=(0, 20), pady=10, sticky="ew")

        ctk.CTkLabel(opts_frame, text="Formato:").grid(
            row=0, column=2, padx=(0, 6), pady=10, sticky="w"
        )
        self.format_menu = ctk.CTkOptionMenu(
            opts_frame, variable=self.format_var, values=["MP4", "MKV", "WEBM", "MP3", "M4A"]
        )
        self.format_menu.grid(row=0, column=3, padx=(0, 12), pady=10, sticky="ew")

        ctk.CTkLabel(opts_frame, text="Faixa de Áudio:").grid(
            row=1, column=0, padx=(12, 6), pady=(0, 6), sticky="w"
        )
        self.audio_menu = ctk.CTkOptionMenu(
            opts_frame,
            variable=self.audio_var,
            values=["Melhor disponível"],
            state="disabled",
        )
        self.audio_menu.grid(row=1, column=1, columnspan=3, padx=(0, 12), pady=(0, 6), sticky="ew")

        # ── Linha de cookies ─────────────────────────────────────────────────
        ctk.CTkLabel(opts_frame, text="Cookies:").grid(
            row=2, column=0, padx=(12, 6), pady=(0, 10), sticky="w"
        )

        self.cookie_mode_var = ctk.StringVar(value="arquivo")
        cookie_mode_frame = ctk.CTkFrame(opts_frame, fg_color="transparent")
        cookie_mode_frame.grid(row=2, column=1, columnspan=3, padx=(0, 12), pady=(0, 10), sticky="ew")
        cookie_mode_frame.grid_columnconfigure(2, weight=1)

        ctk.CTkRadioButton(
            cookie_mode_frame, text="Navegador:", variable=self.cookie_mode_var,
            value="navegador", command=self._toggle_cookie_mode,
        ).grid(row=0, column=0, padx=(0, 6))

        self.browser_menu = ctk.CTkOptionMenu(
            cookie_mode_frame,
            variable=self.browser_var,
            values=["brave", "firefox", "chrome", "chromium", "edge", "opera", "vivaldi"],
            width=120,
        )
        self.browser_menu.grid(row=0, column=1, padx=(0, 16))

        ctk.CTkRadioButton(
            cookie_mode_frame, text="Arquivo cookies.txt:",
            variable=self.cookie_mode_var, value="arquivo",
            command=self._toggle_cookie_mode,
        ).grid(row=0, column=2, padx=(0, 6), sticky="e")

        self.cookie_file_var = ctk.StringVar(value="")
        self.cookie_file_entry = ctk.CTkEntry(
            cookie_mode_frame, textvariable=self.cookie_file_var,
            placeholder_text="caminho do cookies.txt", width=180,
        )
        self.cookie_file_entry.grid(row=0, column=3, padx=(0, 6))
        self.cookie_file_btn = ctk.CTkButton(
            cookie_mode_frame, text="…", width=30, command=self._choose_cookie_file,
        )
        self.cookie_file_btn.grid(row=0, column=4)

        # ── Seção pasta de destino ────────────────────────────────────────────
        dest_frame = ctk.CTkFrame(parent, corner_radius=8)
        dest_frame.grid(row=3, column=0, sticky="ew", padx=4, pady=(0, 6))
        dest_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(dest_frame, text="Salvar em:").grid(
            row=0, column=0, padx=(12, 8), pady=10, sticky="w"
        )
        ctk.CTkEntry(dest_frame, textvariable=self.output_var, state="readonly").grid(
            row=0, column=1, padx=(0, 8), pady=10, sticky="ew"
        )
        ctk.CTkButton(dest_frame, text="Escolher", width=90, command=self._choose_folder).grid(
            row=0, column=2, padx=(0, 12), pady=10
        )

        # ── Seção de legendas ───────────────────────────────────────
        sub_frame = ctk.CTkFrame(parent, corner_radius=8)
        sub_frame.grid(row=4, column=0, sticky="ew", padx=4, pady=(0, 6))
        sub_frame.grid_columnconfigure((1, 3), weight=1)

        ctk.CTkLabel(sub_frame, text="Legendas:", font=("Segoe UI", 12)).grid(
            row=0, column=0, padx=(12, 8), pady=10, sticky="w"
        )
        self.chk_sub_enabled = ctk.CTkCheckBox(
            sub_frame, text="Baixar legendas",
            variable=self.sub_enabled_var,
            command=self._toggle_sub_options,
        )
        self.chk_sub_enabled.grid(row=0, column=1, padx=(0, 16), pady=10, sticky="w")

        ctk.CTkLabel(sub_frame, text="Idioma:").grid(
            row=0, column=2, padx=(0, 6), pady=10, sticky="w"
        )
        # Frame que agrupa o campo + botão de seleção de legenda
        sub_pick_frame = ctk.CTkFrame(sub_frame, fg_color="transparent")
        sub_pick_frame.grid(row=0, column=3, padx=(0, 8), pady=10, sticky="ew")
        sub_pick_frame.grid_columnconfigure(0, weight=1)

        self.sub_lang_entry = ctk.CTkEntry(
            sub_pick_frame, textvariable=self.sub_lang_var,
            state="disabled", width=180,
        )
        self.sub_lang_entry.grid(row=0, column=0, sticky="ew", padx=(0, 4))

        self.sub_lang_btn = ctk.CTkButton(
            sub_pick_frame, text="▾", width=32,
            state="disabled", command=self._open_sub_lang_picker,
        )
        self.sub_lang_btn.grid(row=0, column=1)

        ctk.CTkLabel(sub_frame, text="Formato:").grid(
            row=0, column=4, padx=(0, 6), pady=10, sticky="w"
        )
        self.sub_format_menu = ctk.CTkOptionMenu(
            sub_frame, variable=self.sub_format_var,
            values=["srt", "vtt", "ass", "lrc"], state="disabled", width=80,
        )
        self.sub_format_menu.grid(row=0, column=5, padx=(0, 8), pady=10, sticky="w")

        self.chk_sub_embed = ctk.CTkCheckBox(
            sub_frame, text="Incorporar no vídeo",
            variable=self.sub_embed_var, state="disabled",
        )
        self.chk_sub_embed.grid(row=0, column=6, padx=(0, 12), pady=10, sticky="w")

        # ── Seção de conversão ───────────────────────────────────────────────
        conv_frame = ctk.CTkFrame(parent, corner_radius=8)
        conv_frame.grid(row=5, column=0, sticky="ew", padx=4, pady=(0, 6))
        conv_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(conv_frame, text="Converter codec:", font=("Segoe UI", 12)).grid(
            row=0, column=0, padx=(12, 10), pady=10, sticky="w"
        )

        radio_frame = ctk.CTkFrame(conv_frame, fg_color="transparent")
        radio_frame.grid(row=0, column=1, sticky="w", pady=10)

        ctk.CTkRadioButton(
            radio_frame, text="N\u00e3o converter",
            variable=self.convert_var, value="nao",
            command=self._toggle_convert_options,
        ).grid(row=0, column=0, padx=(0, 16))

        ctk.CTkRadioButton(
            radio_frame, text="H.264 (AVC)",
            variable=self.convert_var, value="h264",
            command=self._toggle_convert_options,
        ).grid(row=0, column=1, padx=(0, 16))

        ctk.CTkRadioButton(
            radio_frame, text="H.265 (HEVC)",
            variable=self.convert_var, value="h265",
            command=self._toggle_convert_options,
        ).grid(row=0, column=2, padx=(0, 16))

        self.chk_delete_original = ctk.CTkCheckBox(
            conv_frame,
            text="Apagar original ap\u00f3s converter",
            variable=self.convert_delete_var,
            state="disabled",
        )
        self.chk_delete_original.grid(row=0, column=2, padx=(0, 12), pady=10, sticky="e")

        # ── Progresso ────────────────────────────────────────────────────────
        prog_frame = ctk.CTkFrame(parent, corner_radius=8)
        prog_frame.grid(row=6, column=0, sticky="ew", padx=4, pady=(0, 6))
        prog_frame.grid_columnconfigure(0, weight=1)

        self.progress_bar = ctk.CTkProgressBar(prog_frame, height=14)
        self.progress_bar.grid(row=0, column=0, padx=12, pady=(10, 4), sticky="ew")
        self.progress_bar.set(0)

        self.progress_label = ctk.CTkLabel(prog_frame, text="0%", font=("Segoe UI", 11))
        self.progress_label.grid(row=1, column=0, pady=(0, 6))

        self.log_text = ctk.CTkTextbox(prog_frame, height=130, font=("Consolas", 11))
        self.log_text.grid(row=2, column=0, padx=12, pady=(0, 10), sticky="ew")
        self.log_text.configure(state="disabled")

        # ── Botão download ────────────────────────────────────────────────────
        self.btn_download = ctk.CTkButton(
            parent,
            text="⬇  Baixar",
            height=42,
            font=("Segoe UI", 15, "bold"),
            command=self._start_download,
        )
        self.btn_download.grid(row=7, column=0, padx=4, pady=(0, 4), sticky="ew")

    def _build_history_tab(self, parent):
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_rowconfigure(1, weight=1)

        top = ctk.CTkFrame(parent, fg_color="transparent")
        top.grid(row=0, column=0, sticky="ew", pady=(4, 8))
        top.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(top, text="Histórico de Downloads", font=("Segoe UI", 14, "bold")).grid(
            row=0, column=0, padx=4, sticky="w"
        )
        ctk.CTkButton(top, text="Limpar", width=80, command=self._clear_history).grid(
            row=0, column=1, padx=4
        )

        self.history_frame = ctk.CTkScrollableFrame(parent)
        self.history_frame.grid(row=1, column=0, sticky="nsew", padx=4)
        self.history_frame.grid_columnconfigure(0, weight=1)

        self._refresh_history()

    # ── Lógica de análise ─────────────────────────────────────────────────────

    def _start_analyze(self):
        url = self.url_var.get().strip()
        if not url:
            self._log("⚠  Cole uma URL antes de analisar.")
            return
        if not re.match(r"https?://(www\.)?(youtube\.com|youtu\.be)/(watch|shorts|playlist|@)", url) and "youtu.be/" not in url:
            self._log("❌  URL inválida. Use um link do YouTube.")
            return

        self.btn_analyze.configure(state="disabled", text="Analisando...")
        self._log("🔍  Analisando vídeo...")
        threading.Thread(target=self._analyze_thread, daemon=True).start()

    def _analyze_thread(self):
        url = self.url_var.get().strip()
        browser = self.browser_var.get()
        cookie_args = self.after(0, self._get_cookie_args) or ["--cookies-from-browser", browser]
        # _get_cookie_args precisa rodar na thread principal; lemos as vars diretamente
        mode = self.cookie_mode_var.get()
        if mode == "arquivo":
            cpath = self.cookie_file_var.get().strip()
            cookie_args = ["--cookies", cpath] if cpath and os.path.isfile(cpath) else []
        else:
            cookie_args = ["--cookies-from-browser", browser]
        try:
            result = subprocess.run(
                ["yt-dlp", "--dump-json", "--no-playlist", *cookie_args, url],
                capture_output=True,
                text=True,
                timeout=300,
            )

            # Tentar parsear mesmo se returncode != 0 (warnings não fatais)
            stdout = result.stdout.strip()
            if not stdout:
                err = result.stderr.strip().splitlines()
                msg = next((l for l in reversed(err) if "ERROR" in l), None) or result.stderr.strip()
                raise RuntimeError(msg or "Sem resposta do yt-dlp.")

            info = json.loads(stdout)
            self._video_info = info
            self._parse_formats(info)
            self.after(0, self._update_ui_after_analyze, info)

        except FileNotFoundError:
            self.after(0, self._log, "❌  yt-dlp não encontrado. Instale com: pip install yt-dlp")
        except json.JSONDecodeError:
            self.after(0, self._log, "❌  Resposta inválida do yt-dlp.")
        except Exception as e:
            self.after(0, self._log, f"❌  Erro: {e}")
        finally:
            self.after(0, self._reset_buttons)

    def _parse_formats(self, info):
        formats = info.get("formats", [])

        # ── Formatos de vídeo ─────────────────────────────────────────────────
        video_fmts = {}
        for f in formats:
            vcodec = f.get("vcodec") or "none"
            if vcodec == "none":
                continue
            if (f.get("ext") or "") == "mhtml":
                continue
            h = f.get("height")
            if not h:
                continue
            if h not in video_fmts:
                codec = vcodec.split(".")[0].upper()
                video_fmts[h] = f"{h}p ({codec})"

        sorted_heights = sorted(video_fmts.keys(), reverse=True)
        self._video_formats = [video_fmts[h] for h in sorted_heights]
        if not self._video_formats:
            self._video_formats = ["Melhor disponível"]

        # ── Formatos de áudio ─────────────────────────────────────────────────
        LANG_MAP = {
            "pt": "Portugues", "pt-BR": "Portugues (BR)", "pt-PT": "Portugues (PT)",
            "en": "Ingles", "en-US": "Ingles (EUA)", "en-GB": "Ingles (UK)",
            "es": "Espanhol", "es-US": "Espanhol (EUA)",
            "fr": "Frances", "fr-FR": "Frances (FR)",
            "de": "Alemao", "it": "Italiano", "ja": "Japones",
            "ko": "Coreano", "zh": "Chines", "zh-CN": "Chines (CN)",
            "nl": "Holandes", "nl-NL": "Holandes (NL)",
            "pl": "Polones", "uk": "Ucraniano", "id": "Indonesio",
            "ta": "Tamil", "ml": "Malaiala", "bn": "Bengali",
            "iw": "Hebraico", "he": "Hebraico",
        }

        audio_seen = {}
        lang_seen = set()

        for f in formats:
            vcodec = f.get("vcodec") or "none"
            if vcodec != "none":
                continue
            if (f.get("ext") or "") == "mhtml":
                continue
            lang = (f.get("language") or "").strip()
            if not lang:
                continue
            fmt_note = (f.get("format_note") or "").lower()
            lang_pref = f.get("language_preference") or 0

            if "original" in fmt_note or lang_pref >= 10:
                tipo = "Original"
            elif "dubbed" in fmt_note or "dub" in fmt_note:
                tipo = "Dublagem (auto)"
            else:
                tipo = "Dublagem"

            nome_idioma = LANG_MAP.get(lang, lang.upper())
            label = f"{nome_idioma} - {tipo}"

            key = f"{lang}|{tipo}"
            if key not in lang_seen:
                lang_seen.add(key)
                audio_seen[label] = lang

        self._audio_formats = audio_seen

        # ── Legendas disponíveis ──────────────────────────────────────────────
        LANG_NAMES = {
            "pt": "Português", "pt-BR": "Português (BR)", "pt-PT": "Português (PT)",
            "en": "Inglês", "en-US": "Inglês (EUA)", "en-GB": "Inglês (UK)",
            "es": "Espanhol", "es-419": "Espanhol (Lat)",
            "fr": "Francês", "de": "Alemão", "it": "Italiano",
            "ja": "Japonês", "ko": "Coreano", "zh": "Chinês",
            "zh-Hans": "Chinês Simpl.", "zh-Hant": "Chinês Trad.",
            "ar": "Árabe", "ru": "Russo", "nl": "Holandês",
            "pl": "Polonês", "tr": "Turco", "sv": "Sueco",
            "id": "Indonésio", "hi": "Hindi",
        }

        sub_langs = {}

        # Legendas manuais (subtitles)
        for lang, tracks in (info.get("subtitles") or {}).items():
            if lang == "live_chat":
                continue
            nome = LANG_NAMES.get(lang, lang.upper())
            label = f"{nome} — Manual"
            sub_langs[label] = lang

        # Legendas automáticas (automatic_captions)
        for lang, tracks in (info.get("automatic_captions") or {}).items():
            if lang == "live_chat":
                continue
            nome = LANG_NAMES.get(lang, lang.upper())
            label = f"{nome} — Automática"
            if label not in sub_langs:
                sub_langs[label] = lang

        self._subtitle_langs = sub_langs

    def _update_ui_after_analyze(self, info):
        title = info.get("title", "Título desconhecido")
        duration = format_duration(info.get("duration"))
        channel = info.get("uploader") or info.get("channel") or ""

        self.title_label.configure(text=title)
        self.duration_label.configure(text=f"⏱  {duration}")
        self.channel_label.configure(text=f"📺  {channel}" if channel else "")

        # Atualizar menus de qualidade
        qualities = self._video_formats + ["Apenas Áudio"]
        self.quality_menu.configure(values=qualities)
        if self._video_formats:
            self.quality_var.set(self._video_formats[0])

        # Atualizar menu de áudio
        if self._audio_formats:
            audio_labels = ["Melhor disponível"] + list(self._audio_formats.keys())
            self.audio_menu.configure(values=audio_labels, state="normal")
            self.audio_var.set(audio_labels[0])
            self._log(f"✅  {len(self._audio_formats)} faixa(s) de áudio encontrada(s).")
        else:
            self.audio_menu.configure(values=["Melhor disponível"], state="disabled")
            self._log("ℹ️  Faixa única de áudio detectada.")

        # Thumbnail — monta lista de candidatos do mais específico ao mais simples
        thumb_candidates = []
        thumbnails = info.get("thumbnails") or []
        # Ordena por resolução decrescente e pega as melhores candidatas
        for t in sorted(thumbnails, key=lambda x: (x.get("width") or 0), reverse=True):
            u = t.get("url", "")
            if u and u not in thumb_candidates:
                thumb_candidates.append(u)
        # Garante que o campo "thumbnail" também está na lista
        main = info.get("thumbnail")
        if main and main not in thumb_candidates:
            thumb_candidates.insert(0, main)

        if thumb_candidates:
            threading.Thread(
                target=self._load_thumbnail, args=(thumb_candidates,), daemon=True
            ).start()

        # Atualizar menu de legendas
        if self._subtitle_langs:
            lang_labels = list(self._subtitle_langs.keys())
            self._sub_lang_labels = lang_labels
            # Selecionar português por padrão se disponível
            default = next(
                (l for l in lang_labels if "Português" in l and "Manual" in l),
                next((l for l in lang_labels if "Português" in l), lang_labels[0])
            )
            self.sub_lang_var.set(default)
            self._log(f"✅  {len(lang_labels)} faixa(s) de legenda encontrada(s).")
        else:
            self._sub_lang_labels = ["Nenhuma"]
            self.sub_lang_var.set("Nenhuma")
            self._log("ℹ️  Nenhuma legenda disponível para este vídeo.")

        self._log(f"✅  Análise concluída: {title}")

    def _load_thumbnail(self, candidates):
        """Tenta baixar a thumbnail em thread secundária e renderiza na thread principal."""
        if isinstance(candidates, str):
            candidates = [candidates]

        headers = {
            "User-Agent": (
                "Mozilla/5.0 (X11; Linux x86_64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/125.0.0.0 Safari/537.36"
            ),
            "Referer": "https://www.youtube.com/",
            "Accept": "image/webp,image/apng,image/*,*/*;q=0.8",
        }

        for url in candidates[:3]:
            try:
                r = requests.get(url, timeout=10, headers=headers)
                r.raise_for_status()
                img = Image.open(BytesIO(r.content)).convert("RGB")
                img = img.resize((160, 90), Image.LANCZOS)
                # Passa a imagem PIL para a thread principal criar o CTkImage lá
                self.after(0, self._apply_thumbnail, img)
                return
            except Exception:
                continue

        self.after(0, self._log, "⚠  Não foi possível carregar a thumbnail.")

    def _apply_thumbnail(self, pil_img):
        """Cria o CTkImage e aplica na label — deve rodar na thread principal do Tkinter."""
        try:
            ctk_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(160, 90))
            self._thumbnail_image = ctk_img
            self.thumbnail_label.configure(image=ctk_img, text="")
        except Exception as e:
            self._log(f"⚠  Erro ao exibir thumbnail: {e}")

    # ── Lógica de download ────────────────────────────────────────────────────

    def _start_download(self):
        if self._downloading:
            return
        if not self._video_info:
            self._log("⚠  Analise um vídeo primeiro.")
            return

        out_dir = self.output_var.get()
        if not os.path.isdir(out_dir):
            self._log("❌  Pasta de destino inválida.")
            return
        if not os.access(out_dir, os.W_OK):
            self._log("❌  Sem permissão de escrita na pasta selecionada.")
            return

        self._downloading = True
        self.btn_download.configure(state="disabled", text="Baixando...")
        self.progress_bar.set(0)
        self.progress_label.configure(text="0%")
        threading.Thread(target=self._download_thread, daemon=True).start()

    def _download_thread(self):
        success = False
        try:
            cmd = self._build_command()
            self.after(0, self._log, f"▶  Comando: {' '.join(cmd)}")

            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
            )

            downloaded_file = None

            for line in process.stdout:
                line = line.strip()
                if not line:
                    continue
                self.after(0, self._log, line)
                pct = self._parse_progress(line)
                if pct is not None:
                    self.after(0, self._update_progress, pct)
                if "[Merger]" in line or "has already been downloaded" in line:
                    success = True
                if "Deleting original file" in line:
                    success = True
                if "[info]" in line and ".srt" in line or ".vtt" in line or ".ass" in line:
                    success = True
                if "[Subtitles]" in line or "Writing video subtitles" in line:
                    success = True
                # Capturar caminho do arquivo final
                m = re.search(r'\[Merger\] Merging formats into "(.+?)"', line)
                if m:
                    downloaded_file = m.group(1)
                m2 = re.search(r'\[download\] (.+?) has already been downloaded', line)
                if m2:
                    downloaded_file = m2.group(1)
                # Arquivo único sem merge (ex: apenas áudio)
                m3 = re.search(r'\[download\] Destination: (.+)', line)
                if m3 and not downloaded_file:
                    downloaded_file = m3.group(1)

            process.wait()
            if process.returncode == 0 or success:
                self.after(0, self._on_success, downloaded_file)
            else:
                self.after(0, self._log, "❌  O download terminou com erros.")
        except FileNotFoundError:
            self.after(0, self._log, "❌  yt-dlp não encontrado.")
        except Exception as e:
            self.after(0, self._log, f"❌  Erro inesperado: {e}")
        finally:
            self._downloading = False
            self.after(0, self._reset_buttons)

    def _build_command(self):
        url = self.url_var.get().strip()
        out_dir = self.output_var.get()
        quality = self.quality_var.get()
        audio_choice = self.audio_var.get()
        fmt_out = self.format_var.get().lower()

        # cookies
        mode = self.cookie_mode_var.get()
        if mode == "arquivo":
            cpath = self.cookie_file_var.get().strip()
            cookie_args = ["--cookies", cpath] if cpath and os.path.isfile(cpath) else []
        else:
            cookie_args = ["--cookies-from-browser", self.browser_var.get()]

        output_template = os.path.join(out_dir, "%(title)s.%(ext)s")

        # Apenas áudio
        if quality == "Apenas Áudio" or fmt_out in ("mp3", "m4a"):
            ext = "mp3" if fmt_out == "mp3" else "m4a"
            sub_args = self._build_subtitle_args()
            return [
                "yt-dlp",
                *cookie_args,
                "-f", "bestaudio",
                "--extract-audio",
                "--audio-format", ext,
                "-o", output_template,
                *sub_args,
                url,
            ]

        # Extrair altura desejada
        match = re.search(r"(\d+)p", quality)
        height = match.group(1) if match else "1080"

        # Seleção de áudio por idioma
        if audio_choice != "Melhor disponível" and audio_choice in self._audio_formats:
            lang_code = self._audio_formats[audio_choice]
            # Tenta selecionar pelo idioma; cai em bestaudio se não encontrar
            format_sel = (
                f"bestvideo[height<={height}]+"
                f"bestaudio[language={lang_code}]/"
                f"bestvideo[height<={height}]+bestaudio"
            )
        else:
            format_sel = f"bestvideo[height<={height}]+bestaudio"

        merge_fmt = fmt_out if fmt_out in ("mp4", "mkv", "webm") else "mp4"

        # Argumentos de legenda
        sub_args = self._build_subtitle_args()

        return [
            "yt-dlp",
            *cookie_args,
            "-f", format_sel,
            "--merge-output-format", merge_fmt,
            "-o", output_template,
            "--no-playlist",
            *sub_args,
            url,
        ]

    def _build_subtitle_args(self):
        """Retorna os argumentos yt-dlp para download de legendas."""
        if not self.sub_enabled_var.get():
            return []

        sub_label = self.sub_lang_var.get()
        sub_fmt   = self.sub_format_var.get()
        embed     = self.sub_embed_var.get()

        # Resolver código do idioma a partir do label selecionado
        lang_code = self._subtitle_langs.get(sub_label, "")

        # Determinar se é legenda automática ou manual
        is_auto = "Automática" in sub_label

        # O yt-dlp aceita padrões com wildcard — "pt.*" pega pt, pt-BR, pt-PT etc.
        # Para códigos compostos (pt-BR) usar o código exato; para simples (pt) usar pt.*
        if lang_code and "-" not in lang_code:
            lang_pattern = f"{lang_code}.*"
        elif lang_code:
            lang_pattern = lang_code
        else:
            lang_pattern = ""

        args = []

        if lang_pattern:
            if is_auto:
                # --write-sub tenta manual primeiro; --write-auto-sub pega automática
                args += ["--write-auto-sub", "--write-sub", "--sub-langs", lang_pattern]
            else:
                args += ["--write-sub", "--sub-langs", lang_pattern]
        else:
            # Sem vídeo analisado — tentar ambos
            args += ["--write-sub", "--write-auto-sub"]

        args += ["--sub-format", sub_fmt]

        if embed:
            args += ["--embed-subs"]

        return args

    def _parse_progress(self, line):
        # yt-dlp imprime linhas como: [download]  45.3% of 123.45MiB
        m = re.search(r"\[download\]\s+([\d.]+)%", line)
        if m:
            try:
                return float(m.group(1)) / 100.0
            except ValueError:
                pass
        return None

    def _update_progress(self, pct):
        self.progress_bar.set(pct)
        self.progress_label.configure(text=f"{pct * 100:.1f}%")

    def _on_success(self, downloaded_file=None):
        self._update_progress(1.0)
        title = self._video_info.get("title", "Vídeo")
        out_dir = self.output_var.get()

        codec = self.convert_var.get()
        if codec != "nao" and downloaded_file and os.path.isfile(downloaded_file):
            # Disparar conversão em thread separada
            threading.Thread(
                target=self._convert_thread,
                args=(downloaded_file, codec, title),
                daemon=True,
            ).start()
        else:
            self._log(f"✅  Concluído! Arquivo salvo em: {out_dir}")
            save_history({
                "title": title,
                "url": self.url_var.get().strip(),
                "folder": out_dir,
                "quality": self.quality_var.get(),
                "audio": self.audio_var.get(),
                "date": datetime.now().strftime("%d/%m/%Y %H:%M"),
            })
            self._refresh_history()

    def _convert_thread(self, src_path, codec, title):
        """Converte o arquivo baixado para h264 ou h265 usando ffmpeg."""
        codec_map = {
            "h264": ("libx264", "h264"),
            "h265": ("libx265", "h265"),
        }
        ffmpeg_codec, suffix = codec_map.get(codec, ("libx264", "h264"))

        base, ext = os.path.splitext(src_path)
        dst_path = f"{base}_{suffix}.mp4"

        self.after(0, self._log, f"🔄  Convertendo para {codec.upper()}...")
        self.after(0, self._log, f"   Origem:  {os.path.basename(src_path)}")
        self.after(0, self._log, f"   Destino: {os.path.basename(dst_path)}")

        cmd = [
            "ffmpeg", "-y",
            "-i", src_path,
            "-c:v", ffmpeg_codec,
            "-preset", "medium",
            "-crf", "23",
            "-c:a", "aac",
            "-b:a", "192k",
            "-movflags", "+faststart",
            dst_path,
        ]

        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
            )

            duration_total = None
            time_done = 0.0

            for line in process.stdout:
                line = line.strip()
                if not line:
                    continue

                # Extrair duração total
                m = re.search(r"Duration:\s*(\d+):(\d+):(\d+\.\d+)", line)
                if m and duration_total is None:
                    h, mi, s = int(m.group(1)), int(m.group(2)), float(m.group(3))
                    duration_total = h * 3600 + mi * 60 + s

                # Extrair tempo processado
                m = re.search(r"time=(\d+):(\d+):(\d+\.\d+)", line)
                if m and duration_total:
                    h, mi, s = int(m.group(1)), int(m.group(2)), float(m.group(3))
                    time_done = h * 3600 + mi * 60 + s
                    pct = min(time_done / duration_total, 1.0)
                    self.after(0, self._update_progress, pct)
                    self.after(0, self._log, f"   Convertendo: {pct*100:.1f}%")

            process.wait()

            if process.returncode == 0:
                self.after(0, self._update_progress, 1.0)
                self.after(0, self._log, f"✅  Conversão concluída: {os.path.basename(dst_path)}")
                if self.convert_delete_var.get():
                    try:
                        os.remove(src_path)
                        self.after(0, self._log, f"🗑️  Original removido: {os.path.basename(src_path)}")
                    except Exception as e:
                        self.after(0, self._log, f"⚠️  Não foi possível remover o original: {e}")
                save_history({
                    "title": title,
                    "url": self.url_var.get().strip(),
                    "folder": self.output_var.get(),
                    "quality": self.quality_var.get() + f" + {codec.upper()}",
                    "audio": self.audio_var.get(),
                    "date": datetime.now().strftime("%d/%m/%Y %H:%M"),
                })
                self.after(0, self._refresh_history)
            else:
                self.after(0, self._log, "❌  Erro na conversão. O arquivo original foi mantido.")

        except FileNotFoundError:
            self.after(0, self._log, "❌  ffmpeg não encontrado.")
        except Exception as e:
            self.after(0, self._log, f"❌  Erro na conversão: {e}")
        finally:
            self.after(0, self._reset_buttons)

    # ── Histórico ─────────────────────────────────────────────────────────────

    def _refresh_history(self):
        for widget in self.history_frame.winfo_children():
            widget.destroy()

        history = load_history()
        if not history:
            ctk.CTkLabel(
                self.history_frame, text="Nenhum download registrado.", text_color="gray"
            ).grid(row=0, column=0, pady=20)
            return

        for i, entry in enumerate(history):
            row_frame = ctk.CTkFrame(self.history_frame, corner_radius=6)
            row_frame.grid(row=i, column=0, sticky="ew", pady=3, padx=2)
            row_frame.grid_columnconfigure(0, weight=1)

            ctk.CTkLabel(
                row_frame,
                text=entry.get("title", "Sem título"),
                font=("Segoe UI", 12, "bold"),
                anchor="w",
            ).grid(row=0, column=0, padx=10, pady=(6, 0), sticky="w")

            info_text = (
                f"{entry.get('date', '')}  •  "
                f"{entry.get('quality', '')}  •  "
                f"{entry.get('audio', '')}  •  "
                f"{entry.get('folder', '')}"
            )
            ctk.CTkLabel(
                row_frame, text=info_text, font=("Segoe UI", 10), text_color="gray", anchor="w"
            ).grid(row=1, column=0, padx=10, pady=(0, 6), sticky="w")

            def make_cb(url=entry.get("url", "")):
                return lambda: self._load_from_history(url)

            ctk.CTkButton(
                row_frame, text="↻", width=32, height=28, command=make_cb()
            ).grid(row=0, column=1, rowspan=2, padx=8)

    def _load_from_history(self, url):
        self.url_var.set(url)
        self.tabview.set("⬇ Download")
        self._start_analyze()

    def _clear_history(self):
        if messagebox.askyesno("Confirmar", "Apagar todo o histórico?"):
            if os.path.exists(HISTORY_FILE):
                os.remove(HISTORY_FILE)
            self._refresh_history()

    # ── Auxiliares ────────────────────────────────────────────────────────────

    def _toggle_sub_options(self):
        """Habilita/desabilita opções de legenda conforme o checkbox."""
        enabled = self.sub_enabled_var.get()
        state = "normal" if enabled else "disabled"
        self.sub_lang_btn.configure(state=state)
        self.sub_format_menu.configure(state=state)
        self.chk_sub_embed.configure(state=state)

    def _open_sub_lang_picker(self):
        """Abre janela com Listbox rolável para selecionar idioma da legenda."""
        labels = getattr(self, "_sub_lang_labels", ["Nenhuma"])

        popup = tk.Toplevel(self)
        popup.title("Selecionar legenda")
        popup.resizable(False, False)
        popup.transient(self)
        popup.grab_set()

        # Posicionar próximo ao botão
        self.update_idletasks()
        x = self.sub_lang_btn.winfo_rootx()
        y = self.sub_lang_btn.winfo_rooty() + self.sub_lang_btn.winfo_height()
        popup.geometry(f"320x300+{x}+{y}")

        # Frame com Listbox + Scrollbar
        frame = tk.Frame(popup, bg="#2b2b2b")
        frame.pack(fill="both", expand=True, padx=6, pady=6)

        scrollbar = tk.Scrollbar(frame, orient="vertical")
        listbox = tk.Listbox(
            frame,
            yscrollcommand=scrollbar.set,
            selectmode="single",
            bg="#2b2b2b", fg="white",
            selectbackground="#1f6aa5",
            selectforeground="white",
            font=("Segoe UI", 11),
            relief="flat",
            highlightthickness=0,
            activestyle="dotbox",
        )
        scrollbar.config(command=listbox.yview)
        scrollbar.pack(side="right", fill="y")
        listbox.pack(side="left", fill="both", expand=True)

        # Popular lista e pré-selecionar valor atual
        current = self.sub_lang_var.get()
        for i, label in enumerate(labels):
            listbox.insert("end", label)
            if label == current:
                listbox.selection_set(i)
                listbox.see(i)

        # Campo de filtro
        filter_var = tk.StringVar()
        def on_filter(*_):
            term = filter_var.get().lower()
            listbox.delete(0, "end")
            for label in labels:
                if term in label.lower():
                    listbox.insert("end", label)

        filter_entry = tk.Entry(
            popup, textvariable=filter_var,
            bg="#3b3b3b", fg="white", insertbackground="white",
            font=("Segoe UI", 11), relief="flat",
        )
        filter_entry.pack(fill="x", padx=6, pady=(0, 6))
        filter_var.trace_add("write", on_filter)
        filter_entry.focus_set()
        filter_entry.insert(0, "🔍 Filtrar...")
        filter_entry.bind("<FocusIn>", lambda e: filter_entry.delete(0, "end") if filter_entry.get().startswith("🔍") else None)

        def on_select(event=None):
            sel = listbox.curselection()
            if sel:
                self.sub_lang_var.set(listbox.get(sel[0]))
            popup.destroy()

        listbox.bind("<Double-Button-1>", on_select)
        listbox.bind("<Return>", on_select)

        tk.Button(
            popup, text="OK", command=on_select,
            bg="#1f6aa5", fg="white", relief="flat",
            font=("Segoe UI", 11), padx=12,
        ).pack(pady=(0, 6))

    def _toggle_convert_options(self):
        """Habilita/desabilita o checkbox de apagar original conforme o modo de conversão."""
        if self.convert_var.get() == "nao":
            self.chk_delete_original.configure(state="disabled")
        else:
            self.chk_delete_original.configure(state="normal")

    def _reset_buttons(self):
        """Reabilita os botões Analisar e Baixar — deve rodar na thread principal."""
        self.btn_download.configure(state="normal", text="⬇  Baixar")
        self.btn_analyze.configure(state="normal", text="Analisar")

    def _choose_folder(self):
        folder = filedialog.askdirectory(initialdir=self.output_var.get())
        if folder:
            self.output_var.set(folder)
            self._save_config()

    def _choose_cookie_file(self):
        path = filedialog.askopenfilename(
            title="Selecionar arquivo cookies.txt",
            filetypes=[("Texto", "*.txt"), ("Todos", "*.*")],
        )
        if path:
            self.cookie_file_var.set(path)
            self.cookie_mode_var.set("arquivo")
            self._save_config()

    def _toggle_cookie_mode(self):
        # sem efeito visual necessário; o modo é lido em tempo de execução
        pass

    def _get_cookie_args(self):
        """Retorna os argumentos de cookies para o yt-dlp conforme o modo escolhido."""
        mode = self.cookie_mode_var.get()
        if mode == "arquivo":
            path = self.cookie_file_var.get().strip()
            if path and os.path.isfile(path):
                return ["--cookies", path]
            self._log("⚠  Arquivo de cookies não encontrado; tentando sem cookies.")
            return []
        else:
            return ["--cookies-from-browser", self.browser_var.get()]

    def _log(self, msg):
        self.log_text.configure(state="normal")
        self.log_text.insert("end", msg + "\n")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def _startup_checks(self):
        """Roda verificações de inicialização em thread para não travar a UI."""
        threading.Thread(target=self._startup_checks_thread, daemon=True).start()

    def _startup_checks_thread(self):
        # 1. Verificar ffmpeg
        if not check_ffmpeg():
            self.after(0, self._log,
                "⚠  ffmpeg não encontrado! Execute: sudo apt install ffmpeg"
            )
        else:
            self.after(0, self._log, "✅  ffmpeg detectado.")

        # 2. Verificar versão do yt-dlp (sem atualizar — apenas informa)
        try:
            result = subprocess.run(
                ["yt-dlp", "--version"],
                capture_output=True, text=True, timeout=5,
            )
            version = result.stdout.strip()
            if version:
                self.after(0, self._log, f"yt-dlp: {version}")
        except Exception:
            pass

    def _check_ffmpeg_on_start(self):
        pass  # substituído por _startup_checks

    def _auto_update_ytdlp(self):
        pass  # substituído por _startup_checks


# ─── Entry point ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    app = YouTubeDownloader()
    app.protocol("WM_DELETE_WINDOW", lambda: (app._save_config(), app.destroy()))
    app.mainloop()
