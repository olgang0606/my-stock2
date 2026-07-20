import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
import time

# 페이지 기본 설정
st.set_page_config(
    page_title="글로벌 주식 대시보드",
    page_icon="📈",
    layout="wide"
)

st.title("📈 글로벌 주요 주식 대시보드")
st.markdown("yfinance와 Plotly를 활용한 실시간 글로벌 주가지수 및 기업 주가 조회 서비스입니다.")

# 사이드바 - 주요 주식 선택
st.sidebar.header("📌 종목 및 기간 선택")

TICKERS = {
    "미국 - S&P 500": "^GSPC",
    "미국 - 나스닥 종합": "^IXIC",
    "미국 - 애플 (AAPL)": "AAPL",
    "미국 - 엔비디아 (NVDA)": "NVDA",
    "미국 - 테슬라 (TSLA)": "TSLA",
    "한국 - 코스피 (KOSPI)": "^KS11",
    "한국 - 삼성전자": "005930.KS",
    "일본 - 닛케이 225": "^N225",
    "독일 - DAX": "^GDAXI"
}

selected_name = st.sidebar.selectbox("종목 선택", list(TICKERS.keys()))
ticker_symbol = TICKERS[selected_name]

custom_ticker = st.sidebar.text_input("또는 직접 티커 입력 (예: MSFT, 000660.KS)", "")
if custom_ticker.strip():
    ticker_symbol = custom_ticker.strip().upper()
    selected_name = ticker_symbol

period = st.sidebar.selectbox(
    "조회 기간",
    options=["1mo", "3mo", "6mo", "1y", "2y", "5y", "max"],
    index=3
)

show_ma20 = st.sidebar.checkbox("20일 이동평균선 표시", value=True)
show_ma60 = st.sidebar.checkbox("60일 이동평균선 표시", value=True)

# -------------------------------------------------------------
# Rate Limit 대응 데이터 로딩 함수 (재시도 로직 + 캐싱 적용)
# -------------------------------------------------------------
@st.cache_data(ttl=3600, show_spinner=False)  # 1시간 동안 요청 결과 캐싱
def fetch_stock_data_with_retry(symbol, period_val, retries=3, backoff_factor=2):
    stock = yf.Ticker(symbol)
    
    for attempt in range(retries):
        try:
            df = stock.history(period=period_val)
            info = stock.info
            if not df.empty:
                return df, info
        except Exception as e:
            if "Too Many Requests" in str(e) or "429" in str(e):
                if attempt < retries - 1:
                    sleep_time = backoff_factor ** attempt
                    time.sleep(sleep_time)  # 대기 후 재시도
                    continue
            raise e
            
    return df, info

try:
    with st.spinner("주식 데이터를 안전하게 불러오는 중..."):
        df, info = fetch_stock_data_with_retry(ticker_symbol, period)

    if df.empty:
        st.warning(f"'{ticker_symbol}' 데이터가 비어 있거나 호출 제한에 도달했습니다. 잠시 후 다시 시도해 주세요.")
    else:
        # 상단 요약 정보
        latest_price = df["Close"].iloc[-1]
        prev_price = df["Close"].iloc[-2] if len(df) > 1 else latest_price
        change = latest_price - prev_price
        pct_change = (change / prev_price) * 100
        currency = info.get("currency", "USD") if isinstance(info, dict) else "USD"

        col1, col2, col3 = st.columns(3)
        col1.metric("종목명 / 티커", selected_name, ticker_symbol)
        col2.metric("최근 종가", f"{latest_price:,.2f} {currency}")
        col3.metric("전일 대비 변동", f"{change:+,.2f} {currency}", f"{pct_change:+.2f}%")

        st.markdown("---")

        # 캔들스틱 차트
        fig = go.Figure()
        fig.add_trace(go.Candlestick(
            x=df.index,
            open=df["Open"],
            high=df["High"],
            low=df["Low"],
            close=df["Close"],
            name="주가 (OHLC)"
        ))

        if show_ma20:
            df["MA20"] = df["Close"].rolling(window=20).mean()
            fig.add_trace(go.Scatter(
                x=df.index, y=df["MA20"],
                mode="lines", name="20일 이평선",
                line=dict(color="orange", width=1.5)
            ))

        if show_ma60:
            df["MA60"] = df["Close"].rolling(window=60).mean()
            fig.add_trace(go.Scatter(
                x=df.index, y=df["MA60"],
                mode="lines", name="60일 이평선",
                line=dict(color="green", width=1.5)
            ))

        fig.update_layout(
            title=f"{selected_name} 주가 추이",
            yaxis_title=f"가격 ({currency})",
            xaxis_title="날짜",
            xaxis_rangeslider_visible=False,
            height=550,
            template="plotly_white"
        )

        st.plotly_chart(fig, use_container_width=True)

        # 거래량 차트
        fig_vol = go.Figure()
        fig_vol.add_trace(go.Bar(
            x=df.index,
            y=df["Volume"],
            name="거래량",
            marker_color="gray"
        ))
        fig_vol.update_layout(
            title="거래량 추이",
            yaxis_title="거래량",
            height=250,
            template="plotly_white"
        )

        st.plotly_chart(fig_vol, use_container_width=True)

        # Data Table
        with st.expander("📊 최근 주가 데이터 보기 (Data Table)"):
            st.dataframe(df.sort_index(ascending=False))

except Exception as e:
    st.error("야후 파이낸스 서버 요청 제한(Rate Limit)에 걸렸습니다.")
    st.info("💡 **해결 팁:** 1~2분 정도 기다린 후 종목을 변경하거나 새로고침을 해주세요.")
