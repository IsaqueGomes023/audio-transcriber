# 🎙️ AudioTranscriber

Transcrição automática + resumo inteligente de áudio.
**100% gratuito** · Funciona no Windows, Mac, Linux e na nuvem.

---

## ✨ O que ele faz

- Aceita **MP3, M4A, OGG, WAV, FLAC** (até 200 MB — chunking automático)
- **Transcreve** o áudio automaticamente em segundos
- **Resume** em formato estruturado: Tópicos, Decisões, Próximos Passos
- **Baixe** o resultado em `.TXT` ou `.DOCX` formatado
- **Interface drag & drop** no navegador

---

## ⚙️ Pré-requisito único: Groq API Key (grátis)

Uma única chave cobre transcrição E sumarização.

**Como obter (2 minutos):**
1. Acesse **https://console.groq.com/keys**
2. Clique em **"Create free account"** (sem cartão de crédito)
3. Clique em **"API Keys" → "Create API Key"**
4. Copie a chave (começa com `gsk_...`)

**Limites gratuitos:**
- Transcrição: **20 horas de áudio por dia**
- Sumarização: **14.400 requisições por dia**

---

## 🖥️ Instalação no Windows (passo a passo)

### Passo 1 — Instale o Python

1. Acesse **https://www.python.org/downloads/**
2. Clique no botão amarelo **"Download Python 3.x.x"**
3. Abra o instalador baixado
4. ✅ **IMPORTANTE:** Marque **"Add Python to PATH"** antes de clicar em Install
5. Clique em **"Install Now"** e aguarde

> Para verificar se funcionou: abra o **Prompt de Comando** (tecla Windows + R, digite `cmd`, Enter) e digite `python --version`. Deve mostrar a versão instalada.

---

### Passo 2 — Baixe e extraia o projeto

Baixe os arquivos do AudioTranscriber e salve em uma pasta, por exemplo:
```
C:\AudioTranscriber\
```

A pasta deve conter estes arquivos:
```
AudioTranscriber\
├── app.py
├── audio_processor.py
├── transcriber.py
├── summarizer.py
├── exporter.py
├── requirements.txt
├── .env.example
├── instalar.bat       ← Script de instalação
└── rodar.bat          ← Script para rodar
```

---

### Passo 3 — Execute a instalação

1. Abra a pasta `AudioTranscriber` no **Explorador de Arquivos**
2. Clique duas vezes no arquivo **`instalar.bat`**
3. Uma janela preta vai abrir e instalar tudo automaticamente
4. Ao final, você verá: **"Instalacao concluida com sucesso!"**

> Se o Windows bloquear o arquivo, clique com botão direito → **"Executar como administrador"**

---

### Passo 4 — Configure a API Key

1. Na pasta `AudioTranscriber`, você verá um arquivo chamado **`.env`**
   > Se não aparecer, renomeie `.env.example` para `.env`
2. Abra o `.env` com o **Bloco de Notas**
3. Substitua `cole_sua_chave_aqui` pela sua chave Groq:
   ```
   GROQ_API_KEY=gsk_SuaChaveAqui...
   ```
4. **Salve** o arquivo (Ctrl+S)

---

### Passo 5 — Rode o aplicativo

1. Clique duas vezes no arquivo **`rodar.bat`**
2. Uma janela preta abrirá e o **navegador abrirá automaticamente** em `http://localhost:8501`
3. Pronto! Faça o upload do seu áudio e clique em **"Transcrever e Resumir"**

> Para encerrar: feche a janela preta ou pressione `Ctrl+C` nela.

---

## 🌐 Hospedar online (acesso de qualquer lugar)

Para acessar o app de qualquer lugar sem instalar nada, hospede no **Streamlit Cloud** (gratuito).

### Deploy no Streamlit Cloud

**Passo 1 — Crie um repositório no GitHub**
1. Acesse **https://github.com** e crie uma conta gratuita
2. Clique em **"New repository"**
3. Nome: `audio-transcriber` · Visibilidade: **Public** ou **Private**
4. Clique em **"Create repository"**

**Passo 2 — Suba os arquivos**

Na página do seu repositório, clique em **"uploading an existing file"** e envie todos os arquivos do projeto **exceto** o `.env` (nunca suba sua API Key!).

**Passo 3 — Configure o Streamlit Cloud**
1. Acesse **https://share.streamlit.io**
2. Clique em **"Sign in with GitHub"**
3. Clique em **"New app"**
4. Selecione seu repositório `audio-transcriber`
5. **Main file path:** `app.py`
6. Clique em **"Advanced settings"** → aba **"Secrets"**
7. Cole o seguinte (com sua chave real):
   ```toml
   GROQ_API_KEY = "gsk_SuaChaveAqui..."
   ```
8. Clique em **"Deploy!"**

Em poucos minutos você terá uma URL pública como:
`https://seu-usuario-audio-transcriber.streamlit.app`

> Você pode acessar de qualquer computador, celular ou tablet, sem instalar nada.

---

## 📁 Estrutura do Projeto

```
app.py               → Interface web (Streamlit)
audio_processor.py   → Validação do arquivo de áudio
transcriber.py       → Transcrição via Groq Whisper API
summarizer.py        → Resumo via Groq Llama 3.3 70B
exporter.py          → Geração de TXT e DOCX
requirements.txt     → Dependências Python
packages.txt         → Pacotes de sistema para Streamlit Cloud (ffmpeg)
.env.example         → Modelo de configuração
instalar.bat         → Instalação com 1 clique (Windows)
rodar.bat            → Execução com 1 clique (Windows)
```

---

## ❓ Perguntas Frequentes

**O Python não foi reconhecido após a instalação?**
Feche e abra novamente o Prompt de Comando. Se ainda não funcionar, reinstale o Python marcando "Add Python to PATH".

**O arquivo .env não aparece no Explorador de Arquivos?**
Clique em **"Exibir" → marque "Itens ocultos"** no Explorador. Ou abra o Bloco de Notas e use **Arquivo → Abrir → mude o filtro para "Todos os arquivos"** e navegue até a pasta.

**Arquivos M4A ou acima de 25 MB?**
O app converte M4A para MP3 automaticamente e divide arquivos grandes em chunks. Para isso, o **FFmpeg** precisa estar instalado. No Windows: abra o Prompt de Comando e execute `winget install ffmpeg`.

**O Windows bloqueou o instalar.bat?**
Clique com botão direito no arquivo → **"Propriedades"** → marque **"Desbloquear"** → OK.

---

*AudioTranscriber · Powered by Groq (Whisper + Llama 3) · Streamlit*
