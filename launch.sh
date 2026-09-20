#!/bin/bash
# Launcher do YouTube Downloader
# Garante que yt-dlp e deno estão no PATH e corrige o WM_CLASS

export PATH="$HOME/.local/bin:$HOME/.deno/bin:$PATH"

PROGRAM_DIR="/home/fabricio/Downloads/Softwares/Youtube Downloader"

# Iniciar o programa em background
"$PROGRAM_DIR/dist/youtube-downloader" &
APP_PID=$!

# Aguardar a janela aparecer e corrigir WM_CLASS (até 10 segundos)
for i in $(seq 1 20); do
    sleep 0.5
    WID=$(xdotool search --pid "$APP_PID" --onlyvisible 2>/dev/null | head -1)
    if [ -n "$WID" ]; then
        xdotool set_window --classname "youtube-downloader" \
                           --class "youtube-downloader" "$WID" 2>/dev/null
        break
    fi
done

wait "$APP_PID"
