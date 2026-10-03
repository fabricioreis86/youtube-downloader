# YouTube Downloader com Dublagem 🎬

Interface gráfica para baixar vídeos do YouTube com suporte a múltiplas faixas de áudio (dublagem), legendas, playlists, conversão de codec e histórico de downloads.

---

## Índice

1. [Requisitos do sistema](#1-requisitos-do-sistema)
2. [Instalação das dependências](#2-instalação-das-dependências)
3. [Configuração dos cookies do YouTube](#3-configuração-dos-cookies-do-youtube)
4. [Como usar o programa](#4-como-usar-o-programa)
5. [Funcionalidades](#5-funcionalidades)
6. [Criar atalho na área de trabalho](#6-criar-atalho-na-área-de-trabalho)
7. [Instalar no Windows](#7-instalar-no-windows)
8. [Solução de problemas](#8-solução-de-problemas)

---

## 1. Requisitos do sistema

- **Sistema operacional:** Linux (testado no Xubuntu 24.04 LTS) ou Windows 10/11
- **Python:** 3.9 ou superior
- **Navegador:** Brave, Chrome, Firefox ou outro baseado em Chromium

---

## 2. Instalação das dependências

Execute os comandos abaixo **na ordem** apresentada.

### 2.1 Dependências do sistema (apt)

```bash
# Tkinter e suporte a imagens na interface gráfica
sudo apt install python3-tk python3-pil.imagetk

# FFmpeg — necessário para mesclar vídeo+áudio e converter codecs
sudo apt install ffmpeg

# xprop e xdotool — detecta área útil da tela e corrige ícone no painel
sudo apt install x11-utils xdotool
```

### 2.2 Deno — runtime JavaScript para o yt-dlp

O yt-dlp precisa do Deno para resolver o JavaScript challenge do YouTube. Sem ele, alguns vídeos retornam erro 400 ou ficam travados na análise.

```bash
# Instalar o Deno
curl -fsSL https://deno.land/install.sh | sh

# Adicionar ao PATH
echo 'export PATH="$HOME/.deno/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc

# Confirmar instalação
deno --version
```

### 2.3 Dependências Python (pip3)

```bash
pip3 install -r requirements.txt --break-system-packages
```

> **Recomendado:** usar a versão nightly do yt-dlp para melhor compatibilidade:
> ```bash
> pip3 install --pre "yt-dlp[default]" --break-system-packages
> ```

---

## 3. Configuração dos cookies do YouTube

O YouTube exige autenticação para liberar os formatos de vídeo completos. Sem os cookies, o yt-dlp recebe erro 400 ou 429.

### 3.1 Instalar a extensão de exportação

No Brave (ou Chrome), instale a extensão **"Get cookies.txt LOCALLY"**:
`https://chrome.google.com/webstore/detail/get-cookiestxt-locally/cclelndahbckbenkjhflpdbgdldlbecc`

### 3.2 Exportar os cookies corretamente

> ⚠️ Siga os passos **exatamente** nesta ordem para evitar que os cookies sejam rotacionados pelo YouTube.

1. Abra uma **janela anônima** no Brave (`Ctrl+Shift+N`)
2. Acesse `https://www.youtube.com` e faça login
3. **Na mesma aba**, acesse `https://www.youtube.com/robots.txt`
4. Clique na extensão e exporte para o domínio `.youtube.com`
5. Salve como `cookies.txt` na pasta do programa
6. **Feche a janela anônima imediatamente**

### 3.3 Configurar no programa

1. Na seção **Cookies**, selecione **"Arquivo cookies.txt"**
2. Clique em **"…"** e selecione o arquivo exportado
3. O caminho é salvo em `config.json` — não precisa selecionar novamente

> **Validade:** Os cookies expiram periodicamente. Se receber erros 400 ou 429, repita a exportação.

---

## 4. Como usar o programa

### Executar

```bash
bash "/home/fabricio/Downloads/Softwares/Youtube Downloader/launch.sh"
```

Ou pelo atalho na área de trabalho (seção 6).

### Download de vídeo

1. Cole a URL no campo "URL do Vídeo"
2. Clique em **"Analisar"**
3. Configure as opções e clique em **"⬇ Baixar"**
4. Use **"✕ Cancelar"** para interromper a qualquer momento

### Download de playlist

1. Cole a URL da playlist (ex: `https://www.youtube.com/playlist?list=...`)
2. Clique em **"Analisar"** — o programa detecta automaticamente que é uma playlist e lista os vídeos
3. Configure qualidade, áudio e legendas (aplicados a todos os vídeos)
4. Clique em **"⬇ Baixar"** — os vídeos são baixados em sequência com progresso `[1/N]`, `[2/N]` etc.

### Opções disponíveis

| Opção | Descrição |
|---|---|
| Qualidade | 144p até 2160p (4K) |
| Formato | MP4, MKV, WEBM, MP3, M4A |
| Faixa de Áudio | Idioma da dublagem |
| Legendas | Idioma, formato (SRT/VTT/ASS/LRC), incorporar no vídeo |
| Converter codec | H.264 (AVC) ou H.265 (HEVC) após o download |
| Cancelar | Interrompe download ou conversão a qualquer momento |

---

## 5. Funcionalidades

| Funcionalidade | Descrição |
|---|---|
| Vídeos e Shorts | Download de vídeos normais e Shorts |
| Playlists | Download completo de playlists com progresso por vídeo |
| Múltiplas qualidades | 144p até 2160p (4K), detecção automática |
| Dublagem | Seleção de faixa de áudio por idioma |
| Apenas áudio | Download em MP3 ou M4A |
| Legendas | Manual ou automática, múltiplos idiomas e formatos |
| Incorporar legenda | Embute no vídeo e apaga o arquivo externo automaticamente |
| Conversão de codec | H.264 (AVC) ou H.265 (HEVC) com ffmpeg |
| Cancelar | Botão para cancelar download ou conversão a qualquer momento |
| Thumbnail | Exibida após análise |
| Histórico | Últimos 100 downloads em `downloads_history.json` |
| Configurações salvas | Pasta, cookies e preferências em `config.json` |
| Menu de contexto | Copiar/Colar com botão direito do mouse |
| Multi-monitor | Abre no monitor principal automaticamente |

---

## 6. Criar atalho na área de trabalho

### 6.1 Instalar o ícone no sistema

```bash
mkdir -p ~/.local/share/icons/hicolor/512x512/apps
cp "/home/fabricio/Downloads/Softwares/Youtube Downloader/icon.png" \
   ~/.local/share/icons/hicolor/512x512/apps/youtube-downloader.png
gtk-update-icon-cache ~/.local/share/icons/hicolor/ 2>/dev/null || true
```

### 6.2 Criar o atalho

```bash
cat > "/home/fabricio/Área de trabalho/youtube-downloader.desktop" << 'DESKTOP'
[Desktop Entry]
Version=1.0
Type=Application
Name=YouTube Downloader
Comment=Baixar vídeos do YouTube com dublagem
Exec=/home/fabricio/Downloads/Softwares/Youtube\ Downloader/launch.sh
Icon=youtube-downloader
Terminal=false
Categories=AudioVideo;Network;
StartupWMClass=youtube-downloader
StartupNotify=true
DESKTOP

chmod +x "/home/fabricio/Área de trabalho/youtube-downloader.desktop"
cp "/home/fabricio/Área de trabalho/youtube-downloader.desktop" \
   ~/.local/share/applications/youtube-downloader.desktop
update-desktop-database ~/.local/share/applications/
```

### 6.3 Estrutura de arquivos

```
Youtube Downloader/
├── youtube_downloader.py     # Código-fonte principal
├── launch.sh                 # Script de inicialização (use este para abrir)
├── requirements.txt          # Dependências Python
├── README.md                 # Este arquivo
├── icon.png                  # Ícone do programa (PNG)
├── icon.svg                  # Ícone vetorial
├── icon.ico                  # Ícone para Windows
├── build_windows.bat         # Script de build para Windows
├── installer.iss             # Script do instalador Windows (Inno Setup)
├── INSTALAR_WINDOWS.md       # Instruções para gerar o instalador Windows
├── cookies.txt               # Cookies do YouTube (gerado por você)
├── config.json               # Configurações salvas (gerado automaticamente)
└── downloads_history.json    # Histórico de downloads (gerado automaticamente)
```

---

## 7. Instalar no Windows

Consulte o arquivo `INSTALAR_WINDOWS.md` para o passo a passo completo de como gerar o instalador `YouTube_Downloader_Setup.exe` para Windows 10/11.

Resumo:
1. Instale Python 3.11+, FFmpeg, Deno e Inno Setup 6
2. Execute `build_windows.bat` para gerar o `.exe` via PyInstaller
3. Abra `installer.iss` no Inno Setup e pressione F9 para gerar o instalador

---

## 8. Solução de problemas

### Erro 400, 429 ou "The page needs to be reloaded"
- Exporte um novo `cookies.txt` seguindo o passo a passo da seção 3
- Verifique se o Deno está no PATH: `deno --version`
- Abra sempre pelo `launch.sh` ou pelo atalho

### "No supported JavaScript runtime"
```bash
deno --version
echo $PATH | grep deno
# Se não aparecer:
echo 'export PATH="$HOME/.deno/bin:$PATH"' >> ~/.bashrc && source ~/.bashrc
```

### Thumbnail não aparece
- Verifique a conexão com a internet e tente analisar novamente

### ffmpeg não encontrado
```bash
sudo apt install ffmpeg && ffmpeg -version
```

### ModuleNotFoundError: No module named 'tkinter'
```bash
sudo apt install python3-tk
```

### ModuleNotFoundError: No module named 'customtkinter'
```bash
pip3 install -r requirements.txt --break-system-packages
```

### Janela cortada pelo painel
```bash
sudo apt install x11-utils
xprop -root _NET_WORKAREA
```
