import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import time

# 페이지 설정
st.set_page_config(
    page_title="AI 반도체 밸류체인 심층 분석",
    page_icon="🤖",
    layout="wide"
)

st.title("🤖 AI 반도체 심층 분석 대시보드")
st.markdown("글로벌 AI 반도체 생태계(설계, 파운드리, 장비, HBM/메모리)의 주가 추이 및 재무 펀더멘털을 전문적으로 비교 분석합니다.")

# -------------------------------------------------------------
# AI 반도체 카테고리별 티커 정의
# -------------------------------------------------------------
AI_SEMICONDUCTOR_MAP = {
    "AI 칩/GPU 설계 (Design)": {
        "NVIDIA (NVDA)": "NVDA",
        "AMD (AMD)": "AMD",
        "Broadcom (AVGO)": "AVGO",
        "ARM Holdings (ARM)": "ARM"
    },
    "파운드리/위탁생산 (Foundry)": {
        "TSMC (TSM)": "TSM",
        "Intel (INTC)": "INTC"
    },
    "반도체 장비 (EUV/Etch/CVD)": {
        "ASML (ASML)": "ASML",
        "Applied Materials (AMAT)": "AMAT",
        "Lam Research (LRCX)": "LRCX"
    },
    "HBM 및 차세대 메모리 (Memory)": {
        "SK하이닉스 (000660.KS)": "000660.KS",
        "삼성전자 (005930.KS)": "005930.KS",
        "Micron Technology (MU)": "MU"
    }
}

# -------------------------------------------------------------
# 데이터 로딩 및 Rate Limit 방지 함수
# -------------------------------------------------------------
@st.cache_data(ttl=3600, show_spinner=False)
def get_stock_data(symbol, period="1y"):
    stock = yf.Ticker(symbol)
    for attempt in range(3):
        try:
            df = stock.history(period=period)
            info = stock.info
            if not df.empty:
                return df, info
        except Exception as e:
            if "429" in str(e) or "Too Many Requests" in str(e):
                time.sleep(2 ** attempt)
                continue
            break
    return pd.DataFrame(), {}

# -------------------------------------------------------------
# 사이드바 컨트롤러
# -------------------------------------------------------------
st.sidebar.header("🔍 분석 설정")

# 1. 분석 모드 선택
mode = st.sidebar.radio(
    "분석 모드 선택",
    ["개별 종목 심층 분석", "AI 반도체 종목 간 수익률 비교"]
)

# 2. 섹터 및 종목 선택
category = st.sidebar.selectbox("분석 섹터 선택", list(AI_SEMICONDUCTOR_MAP.keys()))
available_stocks = AI_SEMICONDUCTOR_MAP[category]

period = st.sidebar.selectbox("조회 기간", ["1mo", "3mo", "6mo", "1y", "2y", "5y"], index=3)

# -------------------------------------------------------------
# MODE 1: 개별 종목 심층 분석
# -------------------------------------------------------------
if mode == "개별 종목 심층 분석":
    selected_stock_name = st.sidebar.selectbox("분석할 종목 선택", list(available_stocks.keys()))
    ticker_symbol = available_stocks[selected_stock_name]

    with st.spinner("데이터 수집 중..."):
        df, info = get_stock_data(ticker_symbol, period)

    if df.empty:
        st.warning("데이터를 불러오지 못했습니다. 잠시 후 다시 시도해 주세요.")
    else:
        # 상단 핵심 지표 카드
        latest_price = df["Close"].iloc[-1]
        prev_price = df["Close"].iloc[-2] if len(df) > 1 else latest_price
        change = latest_price - prev_price
        pct_change = (change / prev_price) * 100
        currency = info.get("currency", "USD")

        st.subheader(f"📌 {selected_stock_name}")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("현재가", f"{latest_price:,.2f} {currency}")
        c2.metric("전일 대비", f"{change:+,.2f} {currency}", f"{pct_change:+.2f}%")
        c3.metric("PER (시가총액 대비 수익률)", f"{info.get('trailingPE', 'N/A')}")
        c4.metric("시가총액", f"{info.get('marketCap', 0) / 1e9:,.1f} B {currency}")

        # 메인 차트 (차트 + 이동평균선 + RSI)
        fig = go.Figure()
        fig.add_trace(go.Candlestick(
            x=df.index, open=df["Open"], high=df["High"],
            low=df["Low"], close=df["Close"], name="OHLC"
        ))
        
        # 20일 / 60일 이평선
        df["MA20"] = df["Close"].rolling(20).mean()
        df["MA60"] = df["Close"].rolling(60).mean()
        fig.add_trace(go.Scatter(x=df.index, y=df["MA20"], mode="lines", name="MA20", line=dict(color="orange")))
        fig.add_trace(go.Scatter(x=df.index, y=df["MA60"], mode="lines", name="MA60", line=dict(color="green")))

        fig.update_layout(
            title=f"{selected_stock_name} 주가 추이 (캔들스틱)",
            yaxis_title=f"가격 ({currency})",
            xaxis_rangeslider_visible=False,
            height=500,
            template="plotly_white"
        )
        st.plotly_chart(fig, use_container_width=True)

        # 재무 / 기업 개요
        st.markdown("### 🏢 기업 개요 및 펀더멘털")
        st.write(info.get("longBusinessSummary", "기업 설명 정보가 없습니다."))

        col_a, col_b = st.columns(2)
        with col_a:
            st.markdown("**주요 재무 비율**")
            metrics_df = pd.DataFrame({
                "지표명": ["Forward PER", "PBR (주가순자산비율)", "ROE (자기자본이익률)", "영업이익률 (Profit Margin)"],
                "값": [
                    info.get("forwardPE", "N/A"),
                    info.get("priceToBook", "N/A"),
                    f"{info.get('returnOnEquity', 0) * 100:.2f}%" if info.get('returnOnEquity') else "N/A",
                    f"{info.get('profitMargins', 0) * 100:.2f}%" if info.get('profitMargins') else "N/A"
                ]
            })
            st.table(metrics_df)

        with col_b:
            st.markdown("**52주 가격 범위**")
            low52 = info.get("fiftyTwoWeekLow", 0)
            high52 = info.get("fiftyTwoWeekHigh", 0)
            st.write(f"52주 최저: {low52:,.2f} {currency}")
            st.write(f"52주 최고: {high52:,.2f} {currency}")
            if high52 > low52:
                progress = min(max((latest_price - low52) / (high52 - low52), 0.0), 1.0)
                st.progress(progress, text=f"현재 위치: 52주 범위 중 {progress*100:.1f}% 지점")

# -------------------------------------------------------------
# MODE 2: AI 반도체 종목 간 수익률 비교
# -------------------------------------------------------------
else:
    st.subheader(f"📊 {category} 주요 종목 수익률 비교")
    st.write("선택된 섹터 내 종목들의 기준일 대비 누적 수익률(%) 변화를 비교합니다.")

    selected_tickers = st.sidebar.multiselect(
        "비교 대상 선택",
        options=list(available_stocks.keys()),
        default=list(available_stocks.keys())
    )

    if not selected_tickers:
        st.info("비교할 종목을 하나 이상 선택해 주세요.")
    else:
        combined_df = pd.DataFrame()

        with st.spinner("각 종목의 수익률 데이터를 가져오는 중..."):
            for name in selected_tickers:
                symbol = available_stocks[name]
                df, _ = get_stock_data(symbol, period)
                if not df.empty:
                    # 수익률 정규화 (시작일 기준 % 변동)
                    start_price = df["Close"].iloc[0]
                    normalized_return = ((df["Close"] - start_price) / start_price) * 100
                    combined_df[name] = normalized_return

        if combined_df.empty:
            st.error("데이터를 불러오지 못했습니다.")
        else:
            fig_comp = px.line(
                combined_df,
                x=combined_df.index,
                y=combined_df.columns,
                title=f"기준일 대비 누적 수익률 (%) - [{period}]",
                labels={"value": "수익률 (%)", "index": "날짜", "variable": "종목명"}
            )
            fig_comp.update_layout(height=550, template="plotly_white")
            st.plotly_chart(fig_comp, use_container_width=True)

            st.markdown("### 📈 기간 내 누적 수익률 요약")
            final_returns = combined_df.iloc[-1].sort_values(ascending=False)
            ret_df = pd.DataFrame({"누적 수익률 (%)": final_returns.map("{:+.2f}%".format)})
            st.dataframe(ret_df, use_container_width=True)
