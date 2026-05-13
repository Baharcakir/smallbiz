import os
import json
from typing import Dict, Any, List, Optional
import pandas as pd
from datetime import datetime


def _read_csv(path: str) -> pd.DataFrame:
    df = pd.read_csv(path, parse_dates=["order_date"]) 
    # ensure types
    df["quantity"] = pd.to_numeric(df["quantity"], errors="coerce").fillna(0).astype(int)
    df["price"] = pd.to_numeric(df["price"], errors="coerce").fillna(0.0)
    df["line_total"] = df["quantity"] * df["price"]
    return df


def load_csv_tool(path: str) -> str:
    """Tool: load CSV and return schema and sample as JSON string."""
    if not os.path.exists(path):
        return json.dumps({"status": "error", "error": f"dosya bulunamadı: {path}"})
    df = _read_csv(path)
    summary = {
        "status": "ok",
        "nrows": int(df.shape[0]),
        "columns": {c: str(dtype) for c, dtype in df.dtypes.items()},
        "sample": df.head(3).to_dict(orient="records"),
    }
    return json.dumps(summary)


def generate_aggregates_tool(path: str) -> str:
    """Return aggregates useful for dashboards."""
    if not os.path.exists(path):
        return json.dumps({"status": "error", "error": f"dosya bulunamadı: {path}"})
    df = _read_csv(path)
    total_revenue = float(df["line_total"].sum())
    total_orders = int(df["order_id"].nunique())
    aov = float(total_revenue / total_orders) if total_orders else 0.0
    top_products = (
        df.groupby("product_name")["line_total"].sum().sort_values(ascending=False).head(5).to_dict()
    )
    aggregates = {
        "status": "ok",
        "total_revenue": total_revenue,
        "total_orders": total_orders,
        "average_order_value": aov,
        "top_products": top_products,
    }
    return json.dumps(aggregates)


def generate_time_series_tool(path: str, freq: str = "D") -> str:
    """Return timeseries revenue aggregated by date/freq."""
    if not os.path.exists(path):
        return json.dumps({"status": "error", "error": f"dosya bulunamadı: {path}"})
    df = _read_csv(path)
    ts = (
        df.set_index("order_date")["line_total"].resample(freq).sum().fillna(0)
    )
    series = {str(idx.date()): float(v) for idx, v in ts.items()}
    return json.dumps({"status": "ok", "series": series})


def nlp_summarize_tool(path: str, n_top: int = 5) -> str:
    """Produce a small set of human readable insights from the data."""
    if not os.path.exists(path):
        return json.dumps({"status": "error", "error": f"dosya bulunamadı: {path}"})
    df = _read_csv(path)
    insights: List[Dict[str, Any]] = []

    # top product by revenue
    top = df.groupby("product_name")["line_total"].sum().sort_values(ascending=False)
    if not top.empty:
        top_name = top.index[0]
        insights.append({
            "id": "top_product", 
            "title": "En Yüksek Gelirli Ürün", 
            "text": f'{top_name}, toplam ${top.iloc[0]:.2f} gelir sağladı.'
        })

    # region breakdown
    region = df.groupby("region")["line_total"].sum().sort_values(ascending=False)
    if not region.empty:
        reg_name = region.index[0]
        insights.append({
            "id": "top_region", 
            "title": "En Güçlü Bölge", 
            "text": f'{reg_name}, ${region.iloc[0]:.2f} gelir ile en güçlü bölge konumunda.'
        })

    # growth: compare last 30 days vs previous 30 days if possible
    try:
        max_date = df["order_date"].max()
        last = df[df["order_date"] >= (max_date - pd.Timedelta(days=30))]["line_total"].sum()
        prior = df[(df["order_date"] < (max_date - pd.Timedelta(days=30))) & (df["order_date"] >= (max_date - pd.Timedelta(days=60)))]["line_total"].sum()
        pct = ((last - prior) / prior * 100) if prior else 0.0
        insights.append({
            "id": "recent_growth", 
            "title": "Son Dönem Büyümesi", 
            "text": f'Son 30 günün geliri: ${last:.2f}. Önceki 30 güne kıyasla değişim: %{pct:.1f}.'
        })
    except Exception:
        pass

    # average order size
    try:
        avg_order = df.groupby("order_id")["line_total"].sum().mean()
        insights.append({
            "id": "avg_order", 
            "title": "Ortalama Sipariş Değeri", 
            "text": f'Ortalama sipariş değeri (sepet tutarı) ${avg_order:.2f} olarak gerçekleşti.'
        })
    except Exception:
        pass

    # payment method share
    pm = df.groupby("payment_method")["line_total"].sum().sort_values(ascending=False)
    if not pm.empty:
        top_pm = pm.index[0]
        insights.append({
            "id": "payment_share", 
            "title": "En Çok Tercih Edilen Ödeme Yöntemi", 
            "text": f'{top_pm}, toplam gelirin ${pm.iloc[0]:.2f}\'lık kısmını oluşturuyor.'
        })

    return json.dumps({"status": "ok", "insights": insights[:n_top]})


def chat_with_gemini(question: str, context: Optional[Dict[str, Any]] = None) -> str:
    """Wrap Gemini/chat if available; otherwise return a helpful message.

    `context` may include recent insights or other payload the UI wants to pass.
    """
    # Try to use google.generativeai if available and GEMINI_API_KEY is set.
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return json.dumps({"status": "error", "error": "GEMINI_API_KEY ayarlanmamış"})

    try:
        import google.generativeai as genai

        genai.configure(api_key=api_key)
        # simple chat call; keep payload small. Added Turkish instruction here!
        system = "Sen bir veri analitiği asistanısın. Cevaplarını kısa ve öz tut, gerektiğinde sana verilen bağlam (context) verilerini kullan. TÜM CEVAPLARINI TÜRKÇE VER."
        prompt = system + "\n\nBağlam (Context):\n" + (json.dumps(context) if context else "bağlam yok") + "\n\nKullanıcı:\n" + question
        # The library surface may differ by version; try chat.create first, then fallback.
        try:
            resp = genai.chat.create(model="gemini-lite", messages=[{"role": "user", "content": prompt}])
            text = resp.last or getattr(resp, "content", None)
            if isinstance(text, dict):
                text = text.get("content", "")
        except Exception:
            # fallback: text generation
            resp = genai.generate_text(model="gemini-lite", text=prompt)
            text = resp.text if hasattr(resp, "text") else str(resp)

        return json.dumps({"status": "ok", "response": str(text)})
    except Exception as e:
        msg = str(e)
        # Common protobuf/proto-plus compatibility error seen with some genai versions
        if "ProtoType" in msg and "DESCRIPTOR" in msg:
            hint = (
                "Bu, protobuf/proto-plus uyumluluk sorunu gibi görünüyor. "
                "Uyumlu bir protobuf sürümü yüklemeyi deneyin, örneğin:\n"
                "pip install 'protobuf<4.24.0' --upgrade\n"
                "veya 'protobuf==3.20.3' gibi bilinen iyi bir sürüme sabitleyin.\n"
                "Ardından bağımlılıkları yeniden yükleyin ve uygulamayı yeniden başlatın."
            )
            return json.dumps({"status": "error", "error": f"Gemini çağrısı başarısız oldu: {msg}. {hint}"})

        return json.dumps({"status": "error", "error": f"Gemini çağrısı başarısız oldu: {e}"})


if __name__ == "__main__":
    # quick local sanity
    path = os.path.join(os.path.dirname(__file__), "..", "data", "mock_sales.csv")
    path = os.path.abspath(path)
    print(load_csv_tool(path))