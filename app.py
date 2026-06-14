"""
app.py
------
AudioTranscriber — Interface Streamlit completa.

Fluxo:
  1. Upload do arquivo de áudio (drag & drop)
  2. Validação do formato e tamanho
  3. Transcrição via Groq Whisper API (nuvem, gratuito)
  4. Sumarização via Groq Llama 3.3 (mesma API key)
  5. Download do resultado em TXT ou DOCX

Rodar localmente:   streamlit run app.py
Rodar no Windows:   clique duplo em rodar.bat
"""

import os
import re
import logging

import streamlit as st
from dotenv import load_dotenv

from audio_processor import validate_audio_file, SUPPORTED_DISPLAY, MAX_FILE_SIZE_MB
from transcriber import transcribe, transcribe_with_segments_text, GROQ_AUDIO_MODELS
from summarizer import summarize
from exporter import to_txt, to_docx, get_download_filename

# ─── Setup ───────────────────────────────────────────────────────────────────

load_dotenv()
logging.basicConfig(level=logging.WARNING)

st.set_page_config(
    page_title="AudioTranscriber",
    page_icon="🎙️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── CSS ─────────────────────────────────────────────────────────────────────

st.markdown("""
<style>
    .block-container { padding-top: 1.5rem; padding-bottom: 2rem; }

    /* Card de resultado */
    .result-card {
        background: #f8faff;
        color: #1f2937;
        border-radius: 10px;
        padding: 1.2rem 1.5rem;
        border-left: 4px solid #1a56db;
        margin-bottom: 1rem;
        font-size: 0.95rem;
        line-height: 1.7;
    }

    /* Botões de download */
    .stDownloadButton > button {
        width: 100%;
        border-radius: 8px;
        font-weight: 600;
        padding: 0.5rem;
    }

    /* Área de upload destacada */
    [data-testid="stFileUploader"] > div {
        border: 2px dashed #1a56db;
        border-radius: 10px;
        background: #f0f4ff;
        padding: 0.5rem;
    }

    /* Avisos e status */
    .status-box {
        padding: 0.8rem 1rem;
        border-radius: 8px;
        margin: 0.5rem 0;
        font-size: 0.9rem;
    }
    .status-ok     { background: #d1fae5; border-left: 3px solid #10b981; color: #065f46; }
    .status-warn   { background: #fef3c7; border-left: 3px solid #f59e0b; color: #92400e; }
    .status-error  { background: #fee2e2; border-left: 3px solid #ef4444; color: #991b1b; }

    /* Footer */
    .footer {
        text-align: center;
        color: #9ca3af;
        font-size: 0.78rem;
        margin-top: 3rem;
        padding-top: 1rem;
        border-top: 1px solid #e5e7eb;
    }
</style>
""", unsafe_allow_html=True)

# ─── Session state ────────────────────────────────────────────────────────────

for key, default in {
    "t_result":           None,
    "s_result":           None,
    "last_filename":      None,
    "session_duration_s": 0.0,   # segundos de áudio transcritos na sessão
    "session_mb":         0.0,   # MB enviados na sessão
    "session_requests":   0,     # sumarizações realizadas na sessão
}.items():
    if key not in st.session_state:
        st.session_state[key] = default

# Limites diários do free tier Groq
LIMIT_DURATION_SEC  = 20 * 3600   # 20 horas
LIMIT_REQUESTS      = 14_400      # req/dia (sumarização)

# ─── Sidebar ─────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("## ⚙️ Configurações")

    # API Key
    st.markdown("### 🔑 Groq API Key")
    env_key  = os.getenv("GROQ_API_KEY", "")
    api_key_input = st.text_input(
        "Cole sua chave aqui",
        value=env_key,
        type="password",
        placeholder="gsk_...",
        help="Gratuito em console.groq.com — não precisa de cartão de crédito",
    )

    # Usa a chave digitada ou a do .env
    active_key = api_key_input.strip() or env_key.strip()

    if active_key:
        st.markdown('<div class="status-box status-ok">✅ API Key configurada</div>', unsafe_allow_html=True)
    else:
        st.markdown(
            '<div class="status-box status-warn">⚠️ API Key não configurada.<br>'
            'Obtenha grátis em <a href="https://console.groq.com/keys" target="_blank">console.groq.com</a></div>',
            unsafe_allow_html=True,
        )

    st.markdown("---")

    # Modelo de transcrição
    st.markdown("### 🎤 Modelo de Transcrição")
    model_choice = st.selectbox(
        "Modelo Whisper",
        options=list(GROQ_AUDIO_MODELS.keys()),
        index=0,
        format_func=lambda x: GROQ_AUDIO_MODELS[x],
        label_visibility="collapsed",
    )

    # Idioma
    st.markdown("### 🌐 Idioma do Áudio")
    lang_map = {
        "auto": "🔍 Detecção automática",
        "pt":   "🇧🇷 Português",
        "en":   "🇺🇸 English",
        "es":   "🇪🇸 Español",
        "fr":   "🇫🇷 Français",
        "de":   "🇩🇪 Deutsch",
        "it":   "🇮🇹 Italiano",
        "ja":   "🇯🇵 日本語",
        "zh":   "🇨🇳 中文",
    }
    lang_choice = st.selectbox(
        "Idioma",
        options=list(lang_map.keys()),
        format_func=lambda x: lang_map[x],
        label_visibility="collapsed",
    )

    st.markdown("---")

    # Limites do free tier com barras de uso
    with st.expander("📊 Limites Gratuitos Groq", expanded=False):

        # ── Tempo de áudio transcrito ──
        dur_s     = st.session_state.session_duration_s
        dur_used  = f"{int(dur_s//3600):02d}:{int((dur_s%3600)//60):02d}:{int(dur_s%60):02d}"
        dur_pct   = min(dur_s / LIMIT_DURATION_SEC, 1.0)
        dur_left  = max(LIMIT_DURATION_SEC - dur_s, 0)
        dur_left_h = f"{int(dur_left//3600)}h {int((dur_left%3600)//60)}min"
        st.markdown("**🎙️ Tempo de áudio (sessão)**")
        st.progress(dur_pct)
        st.caption(f"Utilizado: **{dur_used}** · Disponível: **{dur_left_h}** de 20h/dia")

        st.markdown("")

        # ── MB processados ──
        mb_used  = st.session_state.session_mb
        mb_limit = 1024.0
        mb_pct   = min(mb_used / mb_limit, 1.0)
        mb_left  = max(mb_limit - mb_used, 0)
        st.markdown("**💾 Dados enviados (sessão)**")
        st.progress(mb_pct)
        st.caption(f"Utilizado: **{mb_used:.1f} MB** · Disponível: **{mb_left:.0f} MB** de 200 MB/arquivo")

        st.markdown("")

        # ── Sumarizações ──
        req_used = st.session_state.session_requests
        req_pct  = min(req_used / LIMIT_REQUESTS, 1.0)
        req_left = max(LIMIT_REQUESTS - req_used, 0)
        st.markdown("**✨ Sumarizações (sessão)**")
        st.progress(req_pct)
        st.caption(f"Utilizadas: **{req_used}** · Disponíveis: **{req_left:,}** de 14.400/dia")

        st.markdown("")
        st.caption("ℹ️ Contadores da sessão atual. Os limites da Groq renovam a cada 24h.")

    with st.expander("❓ Como obter a API Key"):
        st.markdown("""
1. Acesse [console.groq.com](https://console.groq.com/keys)
2. Clique em **"Create free account"**
3. Vá em **API Keys → Create API Key**
4. Copie e cole no campo acima

Não precisa de cartão de crédito.
        """)

# ─── Cabeçalho ───────────────────────────────────────────────────────────────

col_h1, col_h2 = st.columns([3, 1])
with col_h1:
    st.markdown("# 🎙️ AudioTranscriber")
    st.markdown("**Transcrição automática + resumo inteligente — 100% gratuito**")
with col_h2:
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown(f"<small>Formatos: `{SUPPORTED_DISPLAY}`<br>Tamanho máx: `{MAX_FILE_SIZE_MB} MB`</small>", unsafe_allow_html=True)

st.markdown("---")

# ─── Upload ───────────────────────────────────────────────────────────────────

st.markdown("### 📤 Upload do Áudio")
uploaded = st.file_uploader(
    "Arraste o arquivo aqui ou clique para selecionar",
    type=["mp3", "m4a", "mp4", "ogg", "wav", "flac", "webm"],
    label_visibility="collapsed",
)

# ─── Processamento ───────────────────────────────────────────────────────────

if uploaded is not None:
    audio_bytes = uploaded.read()
    filename    = uploaded.name
    size_mb     = len(audio_bytes) / (1024 * 1024)

    # Métricas do arquivo
    c1, c2, c3 = st.columns(3)
    c1.metric("📁 Arquivo",  filename)
    c2.metric("💾 Tamanho",  f"{size_mb:.1f} MB")
    c3.metric("🎵 Formato",  filename.rsplit(".", 1)[-1].upper() if "." in filename else "?")

    st.markdown("")

    # Aviso de tamanho
    if size_mb > MAX_FILE_SIZE_MB:
        st.error(
            f"❌ Arquivo de {size_mb:.1f} MB excede o limite de {MAX_FILE_SIZE_MB} MB.\n\n"
            "Compacte o áudio ou corte em partes menores antes de enviar."
        )
        st.stop()

    if not active_key:
        st.warning("⚠️ Configure a Groq API Key na barra lateral para continuar.")
        st.stop()

    # Define a key ativa nas variáveis de ambiente para os módulos
    os.environ["GROQ_API_KEY"] = active_key

    # Botão de processar
    already_done = (st.session_state.last_filename == filename and
                    st.session_state.t_result is not None)

    if already_done:
        st.success("✅ Arquivo já processado — veja os resultados abaixo.")

    run = st.button(
        "🚀 Transcrever e Resumir",
        type="primary",
        use_container_width=True,
        disabled=False,
    )

    if run:
        st.session_state.t_result   = None
        st.session_state.s_result   = None
        st.session_state.last_filename = filename

        try:
            # Etapa 1: Validar arquivo
            with st.status("🔍 Validando arquivo...", expanded=True) as s:
                validate_audio_file(filename, audio_bytes)
                st.write("✅ Formato e tamanho válidos.")
                s.update(state="complete", label="✅ Arquivo validado")

            # Etapa 2: Transcrever
            with st.status("🎤 Transcrevendo com Groq Whisper...", expanded=True) as s:
                st.write(f"Modelo: **{GROQ_AUDIO_MODELS[model_choice]}**")
                st.write("⏳ Enviando áudio para a API Groq...")

                lang_param = None if lang_choice == "auto" else lang_choice
                t_result = transcribe(
                    audio_bytes=audio_bytes,
                    filename=filename,
                    model=model_choice,
                    language=lang_param,
                )
                st.session_state.t_result = t_result

                # Atualiza contadores de uso
                dur = t_result["duration"]
                st.session_state.session_duration_s += dur
                st.session_state.session_mb         += size_mb
                dur_str = f"{int(dur//60)}:{int(dur%60):02d}"
                words   = len(t_result["text"].split())
                st.write(f"✅ **{words:,} palavras** transcritas · Idioma: **{t_result['language'].upper()}** · Duração: **{dur_str}**")
                s.update(state="complete", label="✅ Transcrição concluída")

            # Etapa 3: Sumarizar
            with st.status("✨ Gerando resumo com Llama 3.3 70B...", expanded=True) as s:
                st.write("Analisando a transcrição...")
                dur_display = f"{int(dur//60)}m {int(dur%60)}s"
                s_result = summarize(
                    transcription=t_result["text"],
                    language=t_result["language"],
                    duration=dur_display,
                    provider="groq",
                )
                st.session_state.s_result = s_result
                st.session_state.session_requests += 1

                if s_result["error"]:
                    st.write(f"⚠️ {s_result['error']}")
                    s.update(state="error", label="⚠️ Resumo com aviso")
                else:
                    st.write("✅ Resumo estruturado gerado com sucesso.")
                    s.update(state="complete", label="✅ Resumo concluído")

            st.balloons()
            st.success("🎉 Processamento concluído!")

        except Exception as e:
            st.error(f"❌ Erro: {str(e)}")

    # ─── Resultados ──────────────────────────────────────────────────────────

    t_result = st.session_state.t_result
    s_result = st.session_state.s_result

    if t_result and s_result:
        st.markdown("---")
        st.markdown("## 📊 Resultados")

        # Métricas
        dur      = t_result["duration"]
        dur_str  = f"{int(dur//60)}:{int(dur%60):02d}"
        words    = len(t_result["text"].split())
        segs     = len(t_result.get("segments", []))

        m1, m2, m3 = st.columns(3)
        m1.metric("⏱ Duração",  dur_str)
        m2.metric("📝 Palavras", f"{words:,}")
        m3.metric("🔢 Segmentos", segs)

        # Abas de conteúdo
        tab1, tab2, tab3 = st.tabs([
            "✨ Resumo Inteligente",
            "📝 Transcrição Completa",
            "🕒 Transcrição com Timestamps",
        ])

        with tab1:
            if s_result.get("error"):
                st.warning(s_result["summary"])
            else:
                st.markdown(
                    f'<div class="result-card">{s_result["summary"]}</div>',
                    unsafe_allow_html=True,
                )

        with tab2:
            # Quebra de parágrafo após fim de frase (. ! ?) seguido de letra maiúscula
            transcricao_formatada = re.sub(
                r'([.!?])\s+([A-ZÁÉÍÓÚÂÊÎÔÛÃÕÇ])',
                r'\1\n\n\2',
                t_result["text"]
            )
            st.text_area(
                "transcrição",
                value=transcricao_formatada,
                height=380,
                label_visibility="collapsed",
            )
            st.caption(f"🌐 Idioma: **{t_result['language'].upper()}** | 🤖 Modelo: **{t_result['model']}**")

        with tab3:
            segs_text = transcribe_with_segments_text(t_result)
            st.text_area(
                "timestamps",
                value=segs_text,
                height=380,
                label_visibility="collapsed",
            )

        # ── Downloads ────────────────────────────────────────────────────────
        st.markdown("---")
        st.markdown("### 💾 Download")

        dur_label  = f"{int(dur//60)}m {int(dur%60)}s"
        segs_text  = transcribe_with_segments_text(t_result)
        audio_base = filename

        d1, d2, d3, d4 = st.columns(4)

        # TXT completo
        with d1:
            st.download_button(
                label="📄 TXT Completo",
                data=to_txt(
                    transcription=t_result["text"],
                    summary=s_result["summary"],
                    audio_filename=audio_base,
                    language=t_result["language"],
                    duration=dur_label,
                    include_segments=segs_text,
                ),
                file_name=get_download_filename(audio_base, "txt"),
                mime="text/plain;charset=utf-8",
                use_container_width=True,
                help="Resumo + Transcrição completa + Timestamps",
            )

        # DOCX completo
        with d2:
            try:
                st.download_button(
                    label="📘 DOCX Completo",
                    data=to_docx(
                        transcription=t_result["text"],
                        summary=s_result["summary"],
                        audio_filename=audio_base,
                        language=t_result["language"],
                        duration=dur_label,
                        include_segments=segs_text,
                    ),
                    file_name=get_download_filename(audio_base, "docx"),
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    use_container_width=True,
                    help="Documento Word formatado profissionalmente",
                )
            except ImportError:
                st.warning("python-docx não instalado.")

        # TXT só resumo
        with d3:
            st.download_button(
                label="📋 TXT Resumo",
                data=to_txt(
                    transcription="",
                    summary=s_result["summary"],
                    audio_filename=audio_base,
                    language=t_result["language"],
                    duration=dur_label,
                ),
                file_name=get_download_filename(audio_base + "_resumo", "txt"),
                mime="text/plain;charset=utf-8",
                use_container_width=True,
                help="Apenas o resumo estruturado",
            )

        # TXT só transcrição
        with d4:
            st.download_button(
                label="📝 TXT Transcrição",
                data=to_txt(
                    transcription=t_result["text"],
                    summary="",
                    audio_filename=audio_base,
                    language=t_result["language"],
                    duration=dur_label,
                    include_segments=segs_text,
                ),
                file_name=get_download_filename(audio_base + "_transcricao", "txt"),
                mime="text/plain;charset=utf-8",
                use_container_width=True,
                help="Transcrição completa com timestamps",
            )

# ─── Estado vazio ─────────────────────────────────────────────────────────────

else:
    st.markdown("""
    <div style="text-align:center; padding:3rem 1rem; color:#6b7280;">
        <div style="font-size:4rem; margin-bottom:1rem;">🎙️</div>
        <h3 style="color:#374151;">Faça o upload de um arquivo de áudio para começar</h3>
        <p style="margin:0.3rem 0;">Suporte a <strong>MP3, M4A, OGG, WAV, FLAC</strong> · Até 200 MB (chunking automático)</p>
        <p style="margin:0.3rem 0;">Transcrição via <strong>Groq Whisper</strong> · Resumo via <strong>Llama 3.3 70B</strong></p>
        <p style="margin:0.3rem 0; font-size:0.85rem;">🔒 Seu áudio é processado na Groq e não é armazenado</p>
    </div>
    """, unsafe_allow_html=True)

    with st.expander("📖 Como funciona?"):
        st.markdown("""
**Fluxo completo (tudo na nuvem, tudo grátis):**

1. **Upload** — Arraste ou selecione seu arquivo de áudio
2. **Transcrição** — Enviado para a API Groq (Whisper Large v3 Turbo) · resultados em segundos
3. **Sumarização** — A transcrição é analisada pelo Llama 3.3 70B para gerar o resumo estruturado
4. **Download** — Baixe o resultado em **TXT** ou **DOCX formatado**

**Por que é gratuito?**
- Groq oferece **20 horas/dia** de transcrição grátis
- Groq oferece **14.400 req/dia** de sumarização grátis
- Streamlit Cloud hospeda o site de graça
- Uma única API Key da Groq cobre tudo

**Privacidade:** os arquivos de áudio são enviados à Groq somente para transcrição e não são armazenados.
        """)

# ─── Footer ───────────────────────────────────────────────────────────────────

st.markdown("""
<div class="footer">
    🎙️ AudioTranscriber &nbsp;·&nbsp;
    Powered by <a href="https://groq.com" target="_blank">Groq</a> (Whisper + Llama 3) &nbsp;·&nbsp;
    <a href="https://streamlit.io" target="_blank">Streamlit</a> &nbsp;·&nbsp;
    100% Gratuito
</div>
""", unsafe_allow_html=True)
