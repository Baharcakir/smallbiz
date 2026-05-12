import os
import streamlit as st
import pandas as pd
from pathlib import Path
import json

from agents import analytics_agent


st.set_page_config(page_title="Analytics Agent", layout="wide")


def get_default_csv_path() -> str:
    base = Path(__file__).resolve().parents[1]
    return str(base / "data" / "mock_sales.csv")


def load_df(path: str) -> pd.DataFrame:
    df = pd.read_csv(path, parse_dates=["order_date"]) 
    # normalize types and compute line_total for charts
    df["quantity"] = pd.to_numeric(df.get("quantity", 0), errors="coerce").fillna(0).astype(int)
    df["price"] = pd.to_numeric(df.get("price", 0.0), errors="coerce").fillna(0.0)
    df["line_total"] = df["quantity"] * df["price"]
    return df


def main():
    st.title("Analytics Agent")

    sidebar = st.sidebar
    sidebar.header("Controls")
    csv_default = get_default_csv_path()
    csv_path = sidebar.text_input("CSV path", value=csv_default)
    run = sidebar.button("Run analysis")

    if "df" not in st.session_state:
        try:
            st.session_state.df = load_df(csv_path)
        except Exception:
            st.session_state.df = None

    if run or st.session_state.df is None:
        try:
            info = analytics_agent.load_csv_tool(csv_path)
            st.session_state.load_info = json.loads(info)
            st.session_state.df = load_df(csv_path)
            st.success("Loaded CSV")
        except Exception as e:
            st.error(f"Failed to load CSV: {e}")

    if st.session_state.df is None:
        st.info("Provide a valid CSV path in the sidebar.")
        return

    # Top metrics
    col1, col2, col3, col4 = st.columns(4)
    agg = json.loads(analytics_agent.generate_aggregates_tool(csv_path))
    if agg.get("status") == "ok":
        col1.metric("Total revenue", f"${agg['total_revenue']:.2f}")
        col2.metric("Total orders", agg["total_orders"]) 
        col3.metric("Average order value", f"${agg['average_order_value']:.2f}")
        top_prod = next(iter(agg.get("top_products", {}).keys()), "—")
        col4.metric("Top product", top_prod)

    # Charts
    st.subheader("Sales over time")
    ts = json.loads(analytics_agent.generate_time_series_tool(csv_path))
    if ts.get("status") == "ok":
        series = pd.Series(ts["series"])
        series.index = pd.to_datetime(series.index)
        st.line_chart(series)

    st.subheader("Product revenue")
    df = st.session_state.df
    prod = df.groupby("product_name")["line_total"].sum().sort_values(ascending=False)
    st.bar_chart(prod)

    st.subheader("Insights")
    insights = json.loads(analytics_agent.nlp_summarize_tool(csv_path))
    if insights.get("status") == "ok":
        for ins in insights.get("insights", []):
            with st.expander(ins["title"]):
                st.write(ins["text"])

    st.subheader("Chat with the Analytics Agent (Gemini)")
    prompt = st.text_area("Ask a question about the dataset")
    if st.button("Send") and prompt.strip():
        context = {"top_insights": insights.get("insights", [])}
        resp = analytics_agent.chat_with_gemini(prompt, context=context)
        try:
            parsed = json.loads(resp)
            if parsed.get("status") == "ok":
                st.markdown(parsed.get("response"))
            else:
                st.error(parsed.get("error"))
        except Exception:
            st.write(resp)


if __name__ == "__main__":
    main()
