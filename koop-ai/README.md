# 🌿 Koop-AI — Hatay Kadınlar Kooperatifi Yönetim Sistemi

> **Google AI Academy Hackathon** · Python 3.11 · FastAPI · LangChain · ChromaDB · Gemini 1.5 Flash · Streamlit

---

## 🎯 Proje Hakkında

**Koop-AI**, deprem bölgesi Hatay'daki kadın kooperatiflerinin manuel iş yükünü sıfırlamak için tasarlanmış çok-ajanlı bir yapay zeka sistemidir.

**Problem:** Kooperatif üyeleri zamanlarının büyük bölümünü WhatsApp mesajlarına el ile yanıt vererek, siparişleri deftere yazarak ve satış verilerinden hiçbir içgörü üretemeden harcıyor.

**Çözüm:** Her biri kendi alanına sahip 5 uzmanlaşmış AI agent, ortak bir SQLite veritabanı ve FastAPI backend üzerinden iletişim kuruyor.

---

## 🚀 Hızlı Başlangıç

```bash
# 1. Kurulum
pip install -r requirements.txt

# 2. Ortam değişkenleri
cp .env.example .env
# .env dosyasını açıp GOOGLE_API_KEY değerini girin

# 3. Veritabanı + demo veri
python database/seed.py

# 4. ChromaDB'ye doküman yükle (RAG için)
python agents/customer_support/ingest.py

# 5. FastAPI backend (Terminal 1)
uvicorn main:app --reload --port 8000

# 6. Streamlit dashboard (Terminal 2)
streamlit run dashboard/app.py
```

**Dashboard:** http://localhost:8501  
**API Docs:** http://localhost:8000/docs

---

## 🤖 Agent Mimarisi

```
Streamlit Dashboard (localhost:8501)
         │
         ▼
   FastAPI (main.py — localhost:8000)
   ┌──────────────────────────────────────────────┐
   │ /api/support/*  ──► Agent 1: Müşteri Destek  │
   │                         └─► ChromaDB (RAG)   │
   │ /api/orders/*   ──► Agent 2: Sipariş & Stok  │
   │                         └─► SQLite + E-posta  │
   │ /api/analytics/* ─► Agent 3: Satış Analizi   │
   │                         └─► pandas + Gemini   │
   │ /api/cargo/*    ──► Agent 4: Kargo Takip      │
   │                         └─► SQLite            │
   │ /api/workflow/* ──► Agent 5: İş Akışı         │
   │                         └─► SQLite            │
   └──────────────────────────────────────────────┘
```

---

## 📁 Proje Yapısı

```
koop-ai/
├── main.py                    ← FastAPI uygulama giriş noktası
├── requirements.txt
├── .env.example
├── database/
│   ├── db.py                  ← SQLite bağlantı & session
│   ├── models.py              ← SQLAlchemy modelleri
│   └── seed.py                ← Hatay kooperatifi demo verisi
├── agents/
│   ├── customer_support/
│   │   ├── agent.py           ← RAG zinciri (LangChain + ChromaDB)
│   │   ├── ingest.py          ← Doküman vektörizasyonu
│   │   └── docs/              ← faq.txt, products.txt, about.txt
│   ├── order_inventory/
│   │   ├── agent.py           ← Sipariş CRUD, stok yönetimi
│   │   └── mailer.py          ← smtplib e-posta gönderici
│   ├── analytics/
│   │   ├── agent.py           ← pandas + Gemini özetleme
│   │   └── sample_sales.csv   ← Demo satış verisi
│   ├── cargo/
│   │   └── agent.py           ← Kargo takip & durum yönetimi
│   └── workflow/
│       └── agent.py           ← Çalışan görev takibi
├── dashboard/
│   └── app.py                 ← 5 sekmeli Streamlit dashboard
└── tests/
    └── test_agents.py         ← pytest test paketi
```

---

## ⚙️ Ortam Değişkenleri

`.env` dosyası oluşturun (git'e commit etmeyin!):

```env
GOOGLE_API_KEY=your_gemini_api_key_here
SMTP_EMAIL=your_email@gmail.com
SMTP_PASSWORD=your_gmail_app_password
DATABASE_URL=sqlite:///./koop_ai.db
CHROMA_PERSIST_DIR=./chroma_db
```

**Gemini API anahtarı almak için:** https://aistudio.google.com/app/apikey

---

## 🧪 Testler

```bash
pytest tests/ -v
```

---

## 🎬 Demo Akışı (5 dakika)

| # | Sekme | Eylem | Ne Gösterir |
|---|-------|-------|-------------|
| 1 | 💬 Destek | "Biber salçanızda koruyucu var mı?" yaz | RAG → Gemini yanıtı + kaynak doküman |
| 2 | 📦 Siparişler | Antep Fıstıklı Sucuk için sipariş oluştur | Stok düşer, düşük stok uyarısı çıkar |
| 3 | 🚚 Kargo | Oluşturulan takip numarasını sorgula | 5 adımlı kargo zaman çizelgesi |
| 4 | 📊 Analiz | Analiz sekmesine geç | Grafik + Gemini Türkçe özeti |
| 5 | 👥 Çalışanlar | Çalışanlar sekmesine geç | Gecikmiş görevler kırmızı, yük dağılımı |

---

## 🏆 Hackathon Değerlendirme Kriterleri

- **Teknik Derinlik:** Çok-ajanlı mimari + RAG + LLM özetleme
- **Gerçek Problem:** Hatay deprem bölgesi kadın kooperatifleri
- **Çalışan Demo:** 5 dakikada uçtan uca akış
- **Kod Kalitesi:** Her agent izole, test edilebilir ve bağımsız
- **Etki:** Her özellik gerçek bir ağrı noktasına karşılık geliyor

---

*Google AI Academy Hackathon · Koop-AI Team*
