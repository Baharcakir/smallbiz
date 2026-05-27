import json
import math
import re
import subprocess
import tempfile
import zipfile
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Dict, List
from xml.etree import ElementTree

try:
    import google.generativeai as genai
except Exception:
    genai = None


BASE_DIR = Path(__file__).resolve().parent.parent
SUPPORT_DIR = BASE_DIR / "data" / "customer_support"
DOCS_DIR = SUPPORT_DIR / "docs"
CONVERSATIONS_PATH = SUPPORT_DIR / "whatsapp_conversations.json"
SUPPORTED_DOCUMENT_TYPES = {".md", ".txt", ".pdf", ".doc", ".docx"}

DEFAULT_FAQ = """# SmallBiz SSS

## Kargo
Siparişler ödeme onayından sonra 1-3 iş günü içinde kargoya verilir. Teslimat genellikle 2-5 iş günü sürer.

## İade
Müşteriler teslimattan sonraki 14 gün içinde kullanılmamış ürünleri iade edebilir. İade talebi için sipariş numarası ve e-posta adresi gerekir.

## Değişim
Hasarlı veya yanlış ürünlerde değişim talebi destek ekibi tarafından öncelikli işlenir. Müşteriden ürün fotoğrafı ve sipariş numarası istenir.

## Çalışma Saatleri
Destek ekibi hafta içi 09:00-18:00 saatleri arasında yanıt verir. Mesai dışındaki mesajlar ilk iş gününde ele alınır.

## Ödeme
Kredi kartı ve banka transferi kabul edilir. Banka transferlerinde sipariş hazırlığı ödeme onayından sonra başlar.
"""

DEFAULT_CONVERSATIONS = [
    {
        "conversation_id": "WP-001",
        "customer_name": "Elif Yilmaz",
        "customer_phone": "+905551112233",
        "status": "bot_active",
        "channel": "whatsapp",
        "last_message_at": "2026-05-13 11:42:00",
        "messages": [
            {"sender": "customer", "message": "Merhaba, iade suresi kac gun?", "created_at": "2026-05-13 11:41:12"},
            {"sender": "agent", "message": "Teslimattan sonraki 14 gun icinde kullanilmamis urunleri iade edebilirsiniz.", "created_at": "2026-05-13 11:42:00"},
        ],
    },
    {
        "conversation_id": "WP-002",
        "customer_name": "Can Aydin",
        "customer_phone": "+905559998877",
        "status": "needs_human",
        "channel": "whatsapp",
        "last_message_at": "2026-05-13 10:16:00",
        "messages": [
            {"sender": "customer", "message": "Yanlis urun geldi, ne yapmaliyim?", "created_at": "2026-05-13 10:15:24"},
            {"sender": "agent", "message": "Degisim icin urun fotografi ve siparis numaranizi paylasmaniz gerekir.", "created_at": "2026-05-13 10:16:00"},
        ],
    },
]


def ensure_support_workspace() -> None:
    SUPPORT_DIR.mkdir(parents=True, exist_ok=True)
    DOCS_DIR.mkdir(parents=True, exist_ok=True)

    faq_path = DOCS_DIR / "faq.md"
    if not faq_path.exists():
        faq_path.write_text(DEFAULT_FAQ, encoding="utf-8")

    if not CONVERSATIONS_PATH.exists():
        CONVERSATIONS_PATH.write_text(
            json.dumps(DEFAULT_CONVERSATIONS, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )


def create_customer_support_agent(api_key: str = "") -> Dict:
    ensure_support_workspace()
    clean_key = api_key.strip() if isinstance(api_key, str) else ""
    if clean_key and genai is not None:
        genai.configure(api_key=clean_key)
    return {
        "api_key": clean_key,
        "model": "gemini-1.5-flash",
        "temperature": 0.25,
        "name": "WhatsApp Customer Support Agent",
    }


def list_support_documents() -> List[Dict]:
    ensure_support_workspace()
    documents = []
    for path in sorted(DOCS_DIR.iterdir()):
        if not path.is_file() or path.name.startswith("."):
            continue
        if path.suffix.lower() not in {".md", ".txt"}:
            continue
        content = path.read_text(encoding="utf-8", errors="ignore")
        documents.append(
            {
                "filename": path.name,
                "path": str(path),
                "characters": len(content),
                "chunks": len(_chunk_text(content)),
                "updated_at": datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
            }
        )
    return documents


def save_support_document(filename: str, content: str) -> Path:
    ensure_support_workspace()
    safe_name = re.sub(r"[^A-Za-z0-9_.-]+", "_", filename.strip()) or "support_doc.txt"
    if not safe_name.lower().endswith((".md", ".txt")):
        safe_name += ".txt"
    path = DOCS_DIR / safe_name
    path.write_text(content, encoding="utf-8")
    return path


def save_uploaded_support_document(filename: str, file_bytes: bytes) -> Dict:
    ensure_support_workspace()
    source_ext = Path(filename).suffix.lower()
    if source_ext not in SUPPORTED_DOCUMENT_TYPES:
        return {"ok": False, "error": "Desteklenen dosya tipleri: md, txt, pdf, doc, docx.", "path": ""}

    extracted_text = extract_document_text(filename, file_bytes)
    if not extracted_text.strip():
        return {"ok": False, "error": "Dosyadan metin çıkarılamadı. Taranmış PDF veya eski DOC formatı olabilir.", "path": ""}

    safe_name = re.sub(r"[^A-Za-z0-9_.-]+", "_", filename.strip()) or "support_doc"
    target_name = safe_name if source_ext in {".md", ".txt"} else f"{safe_name}.txt"
    path = DOCS_DIR / target_name
    path.write_text(f"# Kaynak: {filename}\n\n{extracted_text.strip()}\n", encoding="utf-8")
    return {"ok": True, "error": "", "path": str(path), "filename": path.name}


def extract_document_text(filename: str, file_bytes: bytes) -> str:
    suffix = Path(filename).suffix.lower()
    if suffix in {".md", ".txt"}:
        return file_bytes.decode("utf-8", errors="ignore")
    if suffix == ".pdf":
        return _extract_pdf_text(file_bytes)
    if suffix == ".docx":
        return _extract_docx_text(file_bytes)
    if suffix == ".doc":
        return _extract_doc_text(filename, file_bytes)
    return ""


def delete_support_document(filename: str) -> bool:
    ensure_support_workspace()
    path = DOCS_DIR / filename
    if not path.exists() or not path.is_file():
        return False
    path.unlink()
    return True


def get_support_snapshot() -> Dict:
    documents = list_support_documents()
    conversations = load_whatsapp_conversations()
    open_threads = [item for item in conversations if item.get("status") != "closed"]
    needs_human = [item for item in conversations if item.get("status") == "needs_human"]
    return {
        "documents": len(documents),
        "chunks": sum(item["chunks"] for item in documents),
        "conversations": len(conversations),
        "open_threads": len(open_threads),
        "needs_human": len(needs_human),
    }


def load_whatsapp_conversations() -> List[Dict]:
    ensure_support_workspace()
    try:
        data = json.loads(CONVERSATIONS_PATH.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except Exception:
        return []


def save_whatsapp_conversations(conversations: List[Dict]) -> None:
    ensure_support_workspace()
    CONVERSATIONS_PATH.write_text(json.dumps(conversations, ensure_ascii=False, indent=2), encoding="utf-8")


def add_whatsapp_message(
    conversation_id: str,
    customer_name: str,
    customer_phone: str,
    sender: str,
    message: str,
    status: str = "bot_active",
) -> Dict:
    conversations = load_whatsapp_conversations()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conversation = next((item for item in conversations if item["conversation_id"] == conversation_id), None)
    if conversation is None:
        conversation = {
            "conversation_id": conversation_id,
            "customer_name": customer_name,
            "customer_phone": customer_phone,
            "status": status,
            "channel": "whatsapp",
            "last_message_at": now,
            "messages": [],
        }
        conversations.insert(0, conversation)

    conversation["customer_name"] = customer_name or conversation.get("customer_name", "")
    conversation["customer_phone"] = customer_phone or conversation.get("customer_phone", "")
    conversation["status"] = status
    conversation["last_message_at"] = now
    conversation.setdefault("messages", []).append({"sender": sender, "message": message, "created_at": now})
    save_whatsapp_conversations(conversations)
    return conversation


def run_customer_support_agent(agent: Dict, user_input: str) -> Dict:
    context_chunks = retrieve_support_context(user_input, limit=4)
    if not context_chunks:
        answer = "Bu bilgi sirket dosyalarinda bulunamadi. Destek ekibinden kontrol etmem gerekiyor."
        return {"answer": answer, "sources": [], "confidence": "low"}

    answer = _answer_with_gemini(agent, user_input, context_chunks) or _answer_from_context(context_chunks)
    return {
        "answer": answer,
        "sources": [
            {"filename": chunk["filename"], "section": chunk["section"], "score": round(chunk["score"], 3)}
            for chunk in context_chunks
        ],
        "confidence": _confidence_label(context_chunks[0]["score"]),
    }


def retrieve_support_context(query: str, limit: int = 4) -> List[Dict]:
    query_tokens = _tokenize(query)
    if not query_tokens:
        return []

    chunks = []
    for document in _load_document_chunks():
        chunk_tokens = _tokenize(document["text"])
        if not chunk_tokens:
            continue
        overlap = query_tokens.intersection(chunk_tokens)
        if not overlap:
            continue
        document["score"] = len(overlap) / math.sqrt(len(chunk_tokens))
        chunks.append(document)

    return sorted(chunks, key=lambda item: item["score"], reverse=True)[:limit]


def _load_document_chunks() -> List[Dict]:
    chunks = []
    for document in list_support_documents():
        path = Path(document["path"])
        content = path.read_text(encoding="utf-8", errors="ignore")
        for index, chunk in enumerate(_chunk_text(content), start=1):
            chunks.append(
                {
                    "filename": path.name,
                    "section": _section_title(chunk) or f"Parca {index}",
                    "text": chunk,
                    "score": 0.0,
                }
            )
    return chunks


def _chunk_text(content: str, max_chars: int = 900) -> List[str]:
    sections = re.split(r"(?=^##?\s+)", content.strip(), flags=re.MULTILINE)
    chunks = []
    for section in sections:
        cleaned = section.strip()
        if not cleaned:
            continue
        if len(cleaned) <= max_chars:
            chunks.append(cleaned)
            continue
        paragraphs = [item.strip() for item in cleaned.split("\n\n") if item.strip()]
        current = ""
        for paragraph in paragraphs:
            if len(current) + len(paragraph) > max_chars and current:
                chunks.append(current.strip())
                current = paragraph
            else:
                current = f"{current}\n\n{paragraph}".strip()
        if current:
            chunks.append(current.strip())
    return chunks


def _section_title(text: str) -> str:
    first_line = text.strip().splitlines()[0] if text.strip() else ""
    return first_line.lstrip("#").strip()


def _tokenize(text: str) -> set[str]:
    normalized = text.lower()
    normalized = normalized.replace("ı", "i").replace("ğ", "g").replace("ü", "u")
    normalized = normalized.replace("ş", "s").replace("ö", "o").replace("ç", "c")
    words = re.findall(r"[a-z0-9]{3,}", normalized)
    stopwords = {"bir", "ile", "icin", "gibi", "olan", "var", "yok", "the", "and", "for", "what", "how", "kac", "gun", "sure", "merhaba"}
    return {word for word in words if word not in stopwords}


def _answer_with_gemini(agent: Dict, user_input: str, chunks: List[Dict]) -> str:
    if not agent.get("api_key") or genai is None:
        return ""

    context = "\n\n---\n\n".join(
        f"Kaynak: {chunk['filename']} / {chunk['section']}\n{chunk['text']}"
        for chunk in chunks
    )
    prompt = f"""Sen SmallBiz WhatsApp musteri destek asistanisin.
Sadece verilen sirket dosyalarindaki baglama dayanarak cevap ver.
Baglamda olmayan bir bilgiyi uydurma.
Cevabin kisa, net ve musteri dostu Turkce olsun.

Sirket dosyalari:
{context}

Musteri sorusu:
{user_input}
"""
    try:
        model = genai.GenerativeModel(agent.get("model", "gemini-1.5-flash"))
        response = model.generate_content(prompt)
        return getattr(response, "text", "") or ""
    except Exception:
        return ""


def _answer_from_context(chunks: List[Dict]) -> str:
    best = chunks[0]
    lines = [
        line.strip("# ").strip()
        for line in best["text"].splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]
    if not lines:
        return "Bu konuda sirket dosyalarinda bilgi var, ancak cevap uretmek icin icerik yeterince acik degil."

    answer = " ".join(lines[:2])
    if len(answer) > 420:
        answer = answer[:420].rsplit(" ", 1)[0] + "..."
    return answer


def _confidence_label(score: float) -> str:
    if score >= 0.55:
        return "high"
    if score >= 0.25:
        return "medium"
    return "low"


def _extract_pdf_text(file_bytes: bytes) -> str:
    try:
        from pypdf import PdfReader
    except Exception:
        return ""

    try:
        reader = PdfReader(BytesIO(file_bytes))
        pages = [page.extract_text() or "" for page in reader.pages]
        return "\n\n".join(page.strip() for page in pages if page.strip())
    except Exception:
        return ""


def _extract_docx_text(file_bytes: bytes) -> str:
    try:
        with zipfile.ZipFile(BytesIO(file_bytes)) as archive:
            xml_content = archive.read("word/document.xml")
        root = ElementTree.fromstring(xml_content)
    except Exception:
        return ""

    namespace = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    paragraphs = []
    for paragraph in root.findall(".//w:p", namespace):
        parts = []
        for node in paragraph.iter():
            if node.tag == f"{{{namespace['w']}}}t" and node.text:
                parts.append(node.text)
            elif node.tag == f"{{{namespace['w']}}}tab":
                parts.append("\t")
            elif node.tag == f"{{{namespace['w']}}}br":
                parts.append("\n")
        text = "".join(parts).strip()
        if text:
            paragraphs.append(text)
    return "\n\n".join(paragraphs)


def _extract_doc_text(filename: str, file_bytes: bytes) -> str:
    suffix = Path(filename).suffix.lower() or ".doc"
    with tempfile.NamedTemporaryFile(suffix=suffix) as temp_file:
        temp_file.write(file_bytes)
        temp_file.flush()
        try:
            result = subprocess.run(
                ["textutil", "-convert", "txt", "-stdout", temp_file.name],
                capture_output=True,
                check=False,
                timeout=10,
            )
        except Exception:
            return ""

    if result.returncode != 0:
        return ""
    return result.stdout.decode("utf-8", errors="ignore").strip()
