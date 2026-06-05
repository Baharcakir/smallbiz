"""
Agent 3 — Satış Analizi & İçgörüler
pandas + Gemini 1.5 Flash Türkçe özet
"""
import os
import json
import pandas as pd
from io import StringIO
from dotenv import load_dotenv

load_dotenv()

from google import genai
from google.genai import types as genai_types

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")

SAMPLE_CSV = os.path.join(os.path.dirname(__file__), "sample_sales.csv")

SUMMARY_PROMPT = """
Sen bir kooperatif danışmanısın. Aşağıdaki satış metriklerini analiz et ve
kooperatif sahibinin anlayabileceği sade Türkçe ile 4-5 madde halinde özetle.
Önemli trendleri, uyarıları ve önerileri belirt.

Metrikler:
{metrics_json}

Çıktı formatı (her madde yeni satırda):
✅ [pozitif trend]
⚠️ [dikkat edilmesi gereken nokta]
💡 [öneri]
"""


def load_dataframe(csv_content: str = None) -> pd.DataFrame:
    """CSV içeriği veya örnek dosyadan DataFrame yükle."""
    if csv_content:
        df = pd.read_csv(StringIO(csv_content))
    else:
        df = pd.read_csv(SAMPLE_CSV)

    df["date"] = pd.to_datetime(df["date"])
    return df


def compute_metrics(df: pd.DataFrame) -> dict:
    """Temel satış metriklerini hesapla."""
    weekly = df.resample("W", on="date")["total"].sum()
    best_week = weekly.idxmax()

    top_products = (
        df.groupby("product_name")["quantity"].sum().nlargest(3).to_dict()
    )

    revenue_by_product = (
        df.groupby("product_name")["total"].sum().sort_values(ascending=False).to_dict()
    )

    region_revenue = (
        df.groupby("customer_region")["total"].sum().sort_values(ascending=False).to_dict()
    )

    monthly_revenue = (
        df.resample("ME", on="date")["total"].sum()
        .rename(lambda x: x.strftime("%Y-%m"))
        .to_dict()
    )

    return {
        "total_revenue": round(df["total"].sum(), 2),
        "total_orders": int(len(df)),
        "avg_order_value": round(df["total"].mean(), 2),
        "top_products_by_quantity": top_products,
        "revenue_by_product": revenue_by_product,
        "monthly_revenue": monthly_revenue,
        "best_week": best_week.strftime("%Y-%m-%d") if pd.notna(best_week) else None,
        "best_week_revenue": round(weekly.max(), 2),
        "region_revenue": region_revenue,
        "weekly_revenue": {
            k.strftime("%Y-%m-%d"): round(v, 2)
            for k, v in weekly.items()
        },
    }


def generate_gemini_summary(metrics: dict) -> str:
    """Gemini Flash ile Türkçe iş özeti oluştur."""
    if not GOOGLE_API_KEY:
        return "⚠️ GOOGLE_API_KEY bulunamadı. .env dosyasına Gemini API anahtarınızı ekleyin."

    try:
        client = genai.Client(api_key=GOOGLE_API_KEY)
        prompt = SUMMARY_PROMPT.format(
            metrics_json=json.dumps(metrics, ensure_ascii=False, indent=2, default=str)
        )
        response = client.models.generate_content(
            model="gemini-1.5-flash",
            contents=prompt,
        )
        return response.text
    except Exception as e:
        return f"⚠️ Özet üretilemedi: {str(e)}"


def get_full_analysis(csv_content: str = None) -> dict:
    """
    Tam analiz: metrikler + Gemini özeti + grafik verisi.
    Returns: {"metrics": dict, "summary": str, "charts": dict}
    """
    df = load_dataframe(csv_content)
    metrics = compute_metrics(df)
    summary = generate_gemini_summary(metrics)

    # Grafik verisi (Streamlit/Plotly için)
    charts = {
        "weekly_revenue": [
            {"week": k, "revenue": v}
            for k, v in metrics["weekly_revenue"].items()
        ],
        "product_revenue": [
            {"product": k, "revenue": v}
            for k, v in metrics["revenue_by_product"].items()
        ],
        "region_revenue": [
            {"region": k, "revenue": v}
            for k, v in metrics["region_revenue"].items()
        ],
        "monthly_revenue": [
            {"month": k, "revenue": v}
            for k, v in metrics["monthly_revenue"].items()
        ],
    }

    return {
        "metrics": metrics,
        "summary": summary,
        "charts": charts,
    }
