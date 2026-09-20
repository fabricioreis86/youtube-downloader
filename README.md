# YouTube Downloader com Dublagem 🎬

Interface gráfica para baixar vídeos do YouTube com suporte a múltiplas faixas de áudio (dublagem), legendas, conversão de codec e histórico de downloads.

---

## Índice

1. [Requisitos do sistema](#1-requisitos-do-sistema)
2. [Instalação das dependências](#2-instalação-das-dependências)
3. [Configuração dos cookies do YouTube](#3-configuração-dos-cookies-do-youtube)
4. [Como usar o programa](#4-como-usar-o-programa)
5. [Funcionalidades](#5-funcionalidades)
6. [Criar atalho na área de trabalho](#6-criar-atalho-na-área-de-trabalho)
7. [Solução de problemas](#7-solução-de-problemas)

---

## 1. Requisitos do sistema

- **Sistema operacional:** Linux (testado no Xubuntu 24.04 LTS)
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

# xprop — detecta a área útil da tela (desconta painel/taskbar)
# xdotool — corrige o ícone do programa no painel
sudo apt install x11-utils xdotool
```

### 2.2 Deno — runtime JavaScript para o yt-dlp

O yt-dlp precisa do Deno para resolver o JavaScript challenge do YouTube. Sem ele, alguns vídeos retornam erro 400 ou ficam travados na análise.

```bash
# Instalar o Deno
curl -fsSL https://deno.land/install.sh | sh

# Adicionar ao PATH (necessário para o programa encontrar o Deno)
echo 'export PATH="$HOME/.deno/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc

# Confirmar instalação
deno --version
```

### 2.3 Dependências Python (pip3)

```bash
pip3 install -r requirements.txt --break-system-packages
```

---

## 3. Configuração dos cookies do YouTube

O YouTube exige autenticação para liberar os formatos de vídeo completos. Sem os cookies, o yt-dlp recebe erro 400 ou 429.

### 3.1 Instalar a extensão de exportação

No Brave (ou Chrome), acesse a Chrome Web Store e instale a extensão:

**"Get cookies.txt LOCALLY"**
`https://chrome.google.com/webstore/detail/get-cookiestxt-locally/cclelndahbckbenkjhflpdbgdldlbecc`

### 3.2 Exportar os cookies corretamente

> ⚠️ Siga os passos **exatamente** nesta ordem para evitar que os cookies sejam rotacionados pelo YouTube.

1. Abra uma **janela anônima** no Brave (`Ctrl+Shift+N`)
2. Acesse `https://www.youtube.com` e faça login com sua conta Google
3. **Na mesma aba**, acesse `https://www.youtube.com/robots.txt`
   - Esse passo "congela" a sessão e evita a rotação dos cookies
4. Com a aba em `robots.txt`, clique na extensão **"Get cookies.txt LOCALLY"**
5. Selecione o domínio `.youtube.com` e clique em exportar
6. Salve o arquivo como `cookies.txt` na pasta do programa:
   ```
   /home/fabricio/Downloads/Softwares/Youtube Downloader/cookies.txt
   ```
7. **Feche a janela anônima imediatamente** — não abra mais nenhuma aba do YouTube nessa sessão

### 3.3 Configurar no programa

Ao abrir o programa pela primeira vez:
1. Na seção **Cookies**, selecione a opção **"Arquivo cookies.txt"**
2. Clique no botão **"…"** e selecione o arquivo `cookies.txt` exportado
3. O caminho é salvo automaticamente em `config.json` — não precisa selecionar novamente nas próximas aberturas

> **Validade dos cookies:** Os cookies do YouTube expiram periodicamente. Se começar a receber erros 400 ou 429 novamente, repita o processo de exportação e selecione o novo arquivo no programa.

---

## 4. Como usar o programa

### Executar o programa

Use o script `launch.sh` que garante que o PATH está correto e o ícone aparece no painel:

```bash
bash "/home/fabricio/Downloads/Softwares/Youtube Downloader/launch.sh"
```

Ou pelo atalho na área de trabalho (após criá-lo na seção 6).

### Fluxo básico de download

1. **Cole a URL** do vídeo no campo "URL do Vídeo"
   - Suporta vídeos normais, Shorts e playlists
2. **Clique em "Analisar"** — o programa carrega título, thumbnail, qualidades disponíveis, faixas de áudio e legendas
3. **Configure as opções:**
   - **Qualidade:** resolução do vídeo (144p até 2160p/4K)
   - **Formato:** MP4, MKV, WEBM, MP3 ou M4A
   - **Faixa de Áudio:** idioma da dublagem (ex: Português BR)
   - **Cookies:** selecione o arquivo `cookies.txt` (salvo automaticamente após a primeira vez)
   - **Salvar em:** pasta de destino (salva automaticamente)
   - **Legendas:** ative e escolha idioma, formato e se deseja incorporar no vídeo
   - **Converter codec:** converta para H.264 ou H.265 após o download
4. **Clique em "⬇ Baixar"**

---

## 5. Funcionalidades

| Funcionalidade | Descrição |
|---|---|
| Múltiplas qualidades | 144p até 2160p (4K), detecção automática |
| Dublagem | Seleção de faixa de áudio por idioma |
| Apenas áudio | Download em MP3 ou M4A |
| Legendas | Manual ou automática, vários idiomas e formatos (SRT, VTT, ASS, LRC) |
| Incorporar legenda | Embute a legenda no arquivo de vídeo |
| Conversão de codec | H.264 (AVC) ou H.265 (HEVC) com ffmpeg |
| Thumbnail | Exibida após análise do vídeo |
| Histórico | Registra os últimos 100 downloads em `downloads_history.json` |
| Configurações salvas | Pasta de destino, cookies e preferências salvas em `config.json` |
| Menu de contexto | Copiar/Colar/Recortar com botão direito do mouse nos campos de texto |
| Multi-monitor | Abre automaticamente no monitor principal |

---

## 6. Criar atalho na área de trabalho

O programa é iniciado pelo `launch.sh`, que garante o PATH correto (Deno, yt-dlp) e o ícone correto no painel do Xfce.

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

# Instalar também no menu de aplicações
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
├── icon.png                  # Ícone do programa
├── icon.svg                  # Ícone vetorial
├── cookies.txt               # Cookies do YouTube (gerado por você)
├── config.json               # Configurações salvas (gerado automaticamente)
└── downloads_history.json    # Histórico de downloads (gerado automaticamente)
```

---

## 7. Solução de problemas

### Erro 400, 429 ou "The page needs to be reloaded"
- Exporte um novo `cookies.txt` seguindo o passo a passo da seção 3
- Certifique-se de que o Deno está instalado e no PATH: `deno --version`
- Sempre abra o programa pelo `launch.sh` ou pelo atalho da área de trabalho

### "No supported JavaScript runtime"
O yt-dlp não encontrou o Deno. Verifique:
```bash
deno --version
echo $PATH | grep deno
```
Se o Deno não aparecer no PATH, adicione novamente:
```bash
echo 'export PATH="$HOME/.deno/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

### Thumbnail não aparece
- Verifique sua conexão com a internet
- O problema pode ser temporário — tente analisar o vídeo novamente

### ffmpeg não encontrado
```bash
sudo apt install ffmpeg
ffmpeg -version
```

### ModuleNotFoundError: No module named 'tkinter'
```bash
sudo apt install python3-tk
```

### ModuleNotFoundError: No module named 'customtkinter'
```bash
pip3 install -r requirements.txt --break-system-packages
```

### Janela cortada pelo painel da barra de tarefas
O programa detecta automaticamente a área útil da tela. Se ainda ocorrer, verifique se o `xprop` está instalado:
```bash
sudo apt install x11-utils
xprop -root _NET_WORKAREA
```
