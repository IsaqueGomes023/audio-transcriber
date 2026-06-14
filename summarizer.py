"""
summarizer.py
-------------
Gera resumos estruturados a partir de transcrições usando LLMs gratuitos.

Hierarquia de providers (todos gratuitos):
  1. Groq API  → Llama 3.3 70B (60 req/min free tier, mais rápido)
  2. Gemini API → Gemini 1.5 Flash (1500 req/dia free tier)
  3. Fallback local → transformers (sem internet, mais lento)

Configure as chaves no arquivo .env:
  GROQ_API_KEY=gsk_...
  GEMINI_API_KEY=AIza...
"""

import os
import logging
from typing import Optional

from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

# ─── Prompt de sistema ───────────────────────────────────────────────────────

SYSTEM_PROMPT = """Você é um assistente especializado em análise e síntese de reuniões e conversas.
Sua tarefa é criar resumos estruturados, claros e acionáveis a partir de transcrições de áudio.
Sempre responda em Português do Brasil, independentemente do idioma da transcrição.
Seja objetivo e extraia apenas informações presentes na transcrição — nunca invente dados."""

SUMMARY_PROMPT_TEMPLATE = """Analise a transcrição abaixo e gere um resumo estruturado seguindo **exatamente** este formato:

---

## 📋 VISÃO GERAL
[2-3 frases descrevendo o contexto e objetivo principal da conversa/reunião]

## 🎯 TÓPICOS ABORDADOS
[Lista dos principais assuntos discutidos, em ordem cronológica]
- Tópico 1: breve descrição
- Tópico 2: breve descrição
- (continue conforme necessário)

## ✅ DECISÕES TOMADAS
[Liste apenas decisões concretas e acordos fechados]
- Decisão 1
- Decisão 2
- (se não houver decisões claras, escreva "Nenhuma decisão formal registrada")

## 📌 PRÓXIMOS PASSOS / AÇÕES
[Tarefas, responsabilidades e prazos mencionados]
- [ ] Ação 1 (Responsável: nome, se mencionado | Prazo: data, se mencionada)
- [ ] Ação 2
- (se não houver próximos passos, escreva "Nenhum próximo passo definido")

## 💡 PONTOS DE ATENÇÃO
[Problemas, riscos, dúvidas ou itens que merecem acompanhamento]
- Ponto 1
- (se não houver, escreva "Nenhum ponto crítico identificado")

## 📊 INFORMAÇÕES RELEVANTES
[Dados, números, nomes, datas ou referências importantes citados]
- Item 1
- (se não houver, omita esta seção)

---
**Idioma detectado na transcrição:** {language}
**Duração aproximada:** {duration}

TRANSCRIÇÃO:
{transcription}"""


def _build_prompt(transcription: str, language: str = "pt", duration: str = "desconhecida") -> str:
    """Monta o prompt completo para sumarização."""
    # Limita o tamanho da transcrição para evitar erros de contexto
    max_chars = 12_000
    if len(transcription) > max_chars:
        transcription = transcription[:max_chars] + "\n\n[... transcrição truncada para caber no contexto ...]"

    return SUMMARY_PROMPT_TEMPLATE.format(
        transcription=transcription,
        language=language,
        duration=duration,
    )


# ─── Provider: Groq ──────────────────────────────────────────────────────────

def _summarize_groq(prompt: str, model: str = "llama-3.3-70b-versatile") -> str:
    """
    Sumariza via Groq API (gratuito: 60 req/min, 6000 tokens/min).
    Modelos gratuitos disponíveis: llama-3.3-70b-versatile, llama-3.1-8b-instant, mixtral-8x7b-32768
    """
    try:
        from groq import Groq
    except ImportError:
        raise ImportError("Instale o Groq SDK: pip install groq")

    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY não encontrada no .env")

    client = Groq(api_key=api_key)

    logger.info(f"Sumarizando via Groq ({model})...")

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": prompt},
        ],
        temperature=0.3,
        max_tokens=2048,
    )

    return response.choices[0].message.content.strip()


# ─── Provider: Google Gemini ─────────────────────────────────────────────────

def _summarize_gemini(prompt: str, model: str = "gemini-1.5-flash") -> str:
    """
    Sumariza via Google Gemini API (gratuito: 1500 req/dia, 15 req/min).
    """
    try:
        import google.generativeai as genai
    except ImportError:
        raise ImportError("Instale: pip install google-generativeai")

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY não encontrada no .env")

    genai.configure(api_key=api_key)
    logger.info(f"Sumarizando via Gemini ({model})...")

    gemini_model = genai.GenerativeModel(
        model_name=model,
        system_instruction=SYSTEM_PROMPT,
    )

    response = gemini_model.generate_content(
        prompt,
        generation_config=genai.types.GenerationConfig(
            temperature=0.3,
            max_output_tokens=2048,
        ),
    )

    return response.text.strip()


# ─── Provider: Fallback Local ────────────────────────────────────────────────

def _summarize_local(transcription: str) -> str:
    """
    Fallback sem internet: usa transformers/pipeline local.
    Limitado a textos curtos e resumo básico (sem estrutura rica).
    """
    try:
        from transformers import pipeline
    except ImportError:
        raise ImportError("Instale: pip install transformers torch")

    logger.info("Sumarizando localmente (pipeline transformers)...")

    # Modelo leve de sumarização em PT/EN
    summarizer = pipeline(
        "summarization",
        model="facebook/bart-large-cnn",
        device=-1,  # CPU
    )

    # BART tem limite de ~1024 tokens
    text_chunk = transcription[:3000]
    result = summarizer(text_chunk, max_length=512, min_length=80, do_sample=False)
    raw_summary = result[0]["summary_text"]

    return f"""## 📋 RESUMO AUTOMÁTICO (Modo Local)

{raw_summary}

---
⚠️ *Resumo gerado localmente com capacidade limitada.*
*Para resumos estruturados completos, configure GROQ_API_KEY ou GEMINI_API_KEY no arquivo .env*"""


# ─── Função principal ─────────────────────────────────────────────────────────

def summarize(
    transcription: str,
    language: str = "pt",
    duration: str = "desconhecida",
    provider: str = "auto",
) -> dict:
    """
    Gera um resumo estruturado da transcrição.

    Args:
        transcription: Texto completo da transcrição.
        language:      Idioma detectado pelo Whisper.
        duration:      Duração formatada do áudio.
        provider:      'auto' | 'groq' | 'gemini' | 'local'
                       'auto' tenta Groq → Gemini → local

    Returns:
        Dicionário com:
          - summary:  Texto do resumo formatado em Markdown.
          - provider: Provider usado com sucesso.
          - error:    Mensagem de erro, se houver.
    """
    if not transcription or not transcription.strip():
        return {
            "summary":  "Transcrição vazia — nenhum conteúdo para resumir.",
            "provider": "none",
            "error":    "Transcrição vazia",
        }

    prompt = _build_prompt(transcription, language, duration)

    providers_to_try = []

    if provider == "auto":
        # Ordem de preferência automática baseada nas chaves disponíveis
        if os.getenv("GROQ_API_KEY"):
            providers_to_try.append("groq")
        if os.getenv("GEMINI_API_KEY"):
            providers_to_try.append("gemini")
        providers_to_try.append("local")
    else:
        providers_to_try = [provider]

    last_error = None

    for prov in providers_to_try:
        try:
            if prov == "groq":
                summary = _summarize_groq(prompt)
            elif prov == "gemini":
                summary = _summarize_gemini(prompt)
            elif prov == "local":
                summary = _summarize_local(transcription)
            else:
                raise ValueError(f"Provider desconhecido: '{prov}'")

            logger.info(f"Resumo gerado com sucesso via {prov.upper()}")
            return {"summary": summary, "provider": prov, "error": None}

        except Exception as e:
            last_error = str(e)
            logger.warning(f"Provider '{prov}' falhou: {e}")
            continue

    # Todos os providers falharam
    error_msg = (
        "Não foi possível gerar o resumo. Verifique:\n"
        "• GROQ_API_KEY ou GEMINI_API_KEY no arquivo .env\n"
        f"• Último erro: {last_error}"
    )
    return {"summary": error_msg, "provider": "none", "error": last_error}


def get_available_providers() -> list[str]:
    """Retorna lista de providers disponíveis com base nas chaves configuradas."""
    available = []
    if os.getenv("GROQ_API_KEY"):
        available.append("groq (Llama 3.3 70B)")
    if os.getenv("GEMINI_API_KEY"):
        available.append("gemini (Gemini 1.5 Flash)")
    available.append("local (BART — sem internet)")
    return available
