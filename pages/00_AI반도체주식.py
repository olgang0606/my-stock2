import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import time

# 페이지 기본 설정
st.set_page_config(
    page_title="AI 반도체 & 레버리지 심층 분석",
    page_icon="⚡",
    layout="wide"
)

st.title("⚡ AI 반도체 & 레버리지 전문 대시보드")
st.markdown("글로벌 AI 반도체 핵심 기업 및 **고변동성 레버리지 ETF(2x/3x)**의 주가 추이와 수익률을 비교 분석합니다.")

# -------------------------------------------------------------
# AI 반도체 밸류체인 및 레버리지 티커 맵
# -------------------------------------------------------------
AI_SEMICONDUCTOR_MAP = {
    "🔥 레버리지 / 파생 ETF (Leveraged)": {
        "SOXL (필라델피아 반도체 3배 Bull)": "SOXL",
        "NVDL (엔비디아 2배 Bull)": "NVDL",
        "USD (반도체 2배 Bull)": "USD",
        "SOXS (필라델피아 반도체 3배 Bear/인버스)": "SOXS",
        "TSLR (테슬라 2배 Bull)": "TSLR"
    },
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
# 완벽히 안전한 데이터 처리 함수 (AttributeError 근본 차단)
# -------------------------------------------------------------
@st.cache_data(ttl=3600, show_spinner=False)
def fetch_safe_stock_data(symbol, period="1y"):
    stock = yf.Ticker(symbol)
    raw_df = pd.DataFrame()
    info = {}

    # 1. 주가 데이터 요청 (Retry 로직)
    for attempt in range(3):
        try:
            raw_df = stock.history(period=period)
            if not raw_df.empty:
                break
        except Exception as e:
            if "429" in str(e) or "Too Many Requests" in str(e):
                time.sleep(2 ** attempt)
                continue
            break

    # 2. 기업 정보 요청
    try:
        info = stock.info
        if not isinstance(info, dict):
            info = {}
    except Exception:
        info = {}

    if raw_df.empty:
        return pd.DataFrame(), info

    # 3. yfinance의 MultiIndex 및 불규칙 컬럼 완벽 평탄화 (Crucial Fix!)
    clean_df = raw_df.copy()
    if isinstance(clean_df.columns, pd.MultiIndex):
        clean_df.columns = clean_df.columns.get_level_values(0)

    # 중복 컬럼 제거 및 단일 1차원 데이터 처리
    clean_df = clean_df.loc[:, ~clean_df.columns.duplicated()]

    # 필요한 컬럼만 명확하게 1차원 Series로 추출하여 새로운 표준 DataFrame 구축
    res_df = pd.DataFrame(index=clean_df.index)
    for col in ["Open", "High", "Low", "Close", "Volume"]:
        if col in clean_df.columns:
            # iloc/values 기반 추출로 AttributeError 차단
            val = clean_df[col]
            if isinstance(val, pd.DataFrame):
                val = val.iloc[:, 0]
            res_df[col] = pd.to_numeric(val, errors="coerce")

    res_df = res_df.dropna(subset=["Close"])
    return res_df, info

# -------------------------------------------------------------
# 사이드바 설정
# -------------------------------------------------------------
st.sidebar.header("🔍 분석 컨트롤러")

mode = st.sidebar.radio(
    "분석 모드 선택",
    ["개별 종목/ETF 심층 분석", "종목 간 수익률 비교 (레버리지 vs 기초자산)"]
)

category = st.sidebar.selectbox("카테고리 선택", list(AI_SEMICONDUCTOR_MAP.keys()))
available_stocks = AI_SEMICONDUCTOR_MAP[category]

period = st.sidebar.selectbox("조회 기간", ["1mo", "3mo", "6mo", "1y", "2y", "5y"], index=3)

if "레버리지" in category:
    st.warning("⚠️ **레버리지 상품 주의사항:** 2배/3배 레버리지 상품은 일일 변동률을 추종하므로 횡보장이나 변동성 장세에서 **음의 이월 효과(Volatility Drag)**로 인해 장기 투자 시 손실이 커질 수 있습니다.")

# -------------------------------------------------------------
# MODE 1: 개별 종목 심층 분석
# -------------------------------------------------------------
if mode == "개별 종목/ETF 심층 분석":
    selected_stock_name = st.sidebar.selectbox("분석할 종목 선택", list(available_stocks.keys()))
    ticker_symbol = available_stocks[selected_stock_name]

    with st.spinner("데이터 요청 중..."):
        df, info = fetch_safe_stock_data(ticker_symbol, period)

    if df.empty or len(df) == 0:
        st.error("데이터를 불러올 수 없습니다. 잠시 후 다시 시도해주세요.")
    else:
        try:
            latest_price = float(df["Close"].iloc[-1])
            prev_price = float(df["Close"].iloc[-2]) if len(df) > 1 else latest_price
            change = latest_price - prev_price
            pct_change = (change / prev_price) * 100 if prev_price != 0 else 0.0
            currency = info.get("currency", "USD") if info else "USD"

            st.subheader(f"📌 {selected_stock_name}")
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("현재가", f"{latest_price:,.2f} {currency}")
            c2.metric("전일 대비", f"{change:+,.2f} {currency}", f"{pct_change:+.2f}%")
            c3.metric("기간 최고가", f"{float(df['High'].max()):,.2f} {currency}")
            c4.metric("기간 최저가", f"{float(df['Low'].min()):,.2f} {currency}")

            # 캔들스틱 차트
            fig = go.Figure()
            fig.add_trace(go.Candlestick(
                x=df.index,
                open=df["Open"],
                high=df["High"],
                low=df["Low"],
                close=df["Close"],
                name="OHLC"
            ))

            ma20 = df["Close"].rolling(20).mean()
            ma60 = df["Close"].rolling(60).mean()
            fig.add_trace(go.Scatter(x=df.index, y=ma20, mode="lines", name="20일 이평선", line=dict(color="orange")))
            fig.add_trace(go.Scatter(x=df.index, y=ma60, mode="lines", name="60일 이평선", line=dict(color="green")))

            fig.update_layout(
                title=f"{selected_stock_name} 차트",
                yaxis_title=f"가격 ({currency})",
                xaxis_rangeslider_visible=False,
                height=500,
                template="plotly_white"
            )
            st.plotly_chart(fig, use_container_width=True)

            with st.expander("ℹ️ 종목/ETF 상세설명 보기"):
                summary = info.get("longBusinessSummary", "개요 정보를 가져올 수 없습니다.") if info else "개요 정보가 없습니다."
                st.write(summary)
        except Exception as e:
            st.error(f"화면 구성 중 오류 발생: {e}")

# -------------------------------------------------------------
# MODE 2: 종목 간 수익률 비교
# -------------------------------------------------------------
else:
    st.subheader("📊 상대 수익률 (%) 비교 분석")
    st.markdown("기초 자산(예: NVDA)과 레버리지 상품(예: NVDL, SOXL)의 수익률 증폭 효과를 한눈에 비교해보세요.")

    selected_tickers = st.sidebar.multiselect(
        "비교 대상 선택",
        options=list(available_stocks.keys()),
        default=list(available_stocks.keys())[:3]
    )

    if not selected_tickers:
        st.info("비교할 종목을 선택해 주세요.")
    else:
        combined_df = pd.DataFrame()

        with st.spinner("수익률 계산 중..."):
            for name in selected_tickers:
                symbol = available_stocks[name]
                df, _ = fetch_safe_stock_data(symbol, period)
                if not df.empty and "Close" in df.columns:
                    start_price = float(df["Close"].iloc[0])
                    if start_price != 0:
                        # 1차원 데이터 백터 계산으로 AttributeError 예방
                        combined_df[name] = ((df["Close"] - start_price) / start_price) * 100

        if combined_df.empty:
            st.error("선택한 종목들의 데이터를 불러오지 못했습니다.")
        else:
            fig_comp = px.line(
                combined_df,
                x=combined_df.index,
                y=combined_df.columns,
                title=f"기준일 대비 수익률 추이 (%) - [{period}]",
                labels={"value": "수익률 (%)", "index": "날짜", "variable": "종목명"}
            )
            fig_comp.update_layout(height=550, template="plotly_white")
            st.plotly_chart(fig_comp, use_container_width=True)

            st.markdown("### 🏆 기간 내 최종 수익률 순위")
            final_returns = combined_df.iloc[-1].sort_values(ascending=False)
            ret_df = pd.DataFrame({"최종 누적 수익률 (%)": final_returns.map("{:+.2f}%".format)})
            st.dataframe(ret_df, use_container_width=True)
