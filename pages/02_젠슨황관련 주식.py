import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import time

# -------------------------------------------------------------
# 페이지 기본 설정
# -------------------------------------------------------------
st.set_page_config(
    page_title="AI 반도체 심층 분석 (젠슨 황 관련주 통합)",
    page_icon="⚡",
    layout="wide"
)

st.title("⚡ AI 반도체 심층 분석 대시보드")
st.markdown(
    "글로벌 AI 반도체 밸류체인과 **젠슨 황/엔비디아 관련주(지분 투자, AI서버/액체냉각 파트너)** 및 "
    "**고변동성 레버리지 ETF(2x/3x)**의 주가 추이와 펀더멘털을 심층 분석합니다."
)

# -------------------------------------------------------------
# AI 반도체 & 젠슨 황 관련주 티커 맵
# -------------------------------------------------------------
AI_SEMICONDUCTOR_MAP = {
    "🎯 젠슨 황 / 엔비디아 direct & 픽 (Jensen's Choice)": {
        "NVIDIA (NVDA) - 본주": "NVDA",
        "SoundHound AI (SOUN) - 음성 AI": "SOUN",
        "Arm Holdings (ARM) - 아키텍처 파트너": "ARM",
        "Recursion Pharma (RXRX) - AI 신약": "RXRX",
        "Serve Robotics (SERV) - 자율주행 로봇": "SERV",
        "Nano-X Imaging (NNOX) - AI 의료": "NNOX"
    },
    "❄️ AI 서버 & 액체냉각 / 인프라 (Server & Cooling)": {
        "Vertiv (VRT) - 액체 냉각 핵심": "VRT",
        "Super Micro Computer (SMCI) - AI 서버": "SMCI",
        "Dell Technologies (DELL) - AI 서버": "DELL",
        "Broadcom (AVGO) - 초고속 네트워크": "AVGO"
    },
    "🔥 레버리지 / 파생 ETF (Leveraged)": {
        "NVDL (엔비디아 2배 Bull)": "NVDL",
        "SOXL (필라델피아 반도체 3배 Bull)": "SOXL",
        "USD (반도체 2배 Bull)": "USD",
        "SOXS (필라델피아 반도체 3배 Bear)": "SOXS"
    },
    "AI 칩/GPU 설계 (Design)": {
        "NVIDIA (NVDA)": "NVDA",
        "AMD (AMD)": "AMD",
        "Broadcom (AVGO)": "AVGO",
        "ARM Holdings (ARM)": "ARM"
    },
    "파운드리/위탁생산 (Foundry)": {
        "TSMC (TSM) - 엔비디아 메인 파운드리": "TSM",
        "Intel (INTC)": "INTC"
    },
    "HBM 및 차세대 메모리 (Memory)": {
        "SK하이닉스 (000660.KS) - HBM 메인 공급": "000660.KS",
        "삼성전자 (005930.KS)": "005930.KS",
        "Micron Technology (MU)": "MU"
    }
}

# -------------------------------------------------------------
# 안전한 데이터 수집 및 정제 함수 (Rate Limit & MultiIndex 방어)
# -------------------------------------------------------------
@st.cache_data(ttl=3600, show_spinner=False)
def fetch_safe_stock_data(symbol, period="1y"):
    stock = yf.Ticker(symbol)
    raw_df = pd.DataFrame()
    info = {}

    # Backoff 기반 재시도 로직 (429 Rate Limit 대비)
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

    try:
        info = stock.info
        if not isinstance(info, dict):
            info = {}
    except Exception:
        info = {}

    if raw_df.empty:
        return pd.DataFrame(), info

    # MultiIndex 및 컬럼 중복 안전 제거
    clean_df = raw_df.copy()
    if isinstance(clean_df.columns, pd.MultiIndex):
        clean_df.columns = clean_df.columns.get_level_values(0)

    clean_df = clean_df.loc[:, ~clean_df.columns.duplicated()]

    # 순수 1차원 데이터 기반 재구성
    res_df = pd.DataFrame(index=clean_df.index)
    for col in ["Open", "High", "Low", "Close", "Volume"]:
        if col in clean_df.columns:
            val = clean_df[col]
            if isinstance(val, pd.DataFrame):
                val = val.iloc[:, 0]
            res_df[col] = pd.to_numeric(val, errors="coerce")

    res_df = res_df.dropna(subset=["Close"])
    return res_df, info

# -------------------------------------------------------------
# 사이드바 컨트롤러
# -------------------------------------------------------------
st.sidebar.header("🔍 분석 컨트롤러")

mode = st.sidebar.radio(
    "분석 모드 선택",
    ["개별 종목/ETF 심층 분석", "AI 반도체 종목 간 수익률 비교"]
)

category = st.sidebar.selectbox("섹터/카테고리 선택", list(AI_SEMICONDUCTOR_MAP.keys()))
available_stocks = AI_SEMICONDUCTOR_MAP[category]

period = st.sidebar.selectbox("조회 기간", ["1mo", "3mo", "6mo", "1y", "2y", "5y"], index=3)

if "레버리지" in category:
    st.warning(
        "⚠️ **레버리지 상품 주의사항:** 2배/3배 레버리지 상품은 일일 변동률을 추종하므로, "
        "횡보장이나 변동성 장세에서 **음의 이월 효과(Volatility Drag)**로 인해 장기 보유 시 원금 손실이 커질 수 있습니다."
    )

# -------------------------------------------------------------
# MODE 1: 개별 종목/ETF 심층 분석
# -------------------------------------------------------------
if mode == "개별 종목/ETF 심층 분석":
    selected_stock_name = st.sidebar.selectbox("분석할 종목 선택", list(available_stocks.keys()))
    ticker_symbol = available_stocks[selected_stock_name]

    with st.spinner("최신 데이터 수집 중..."):
        df, info = fetch_safe_stock_data(ticker_symbol, period)

    if df.empty or len(df) == 0:
        st.error("데이터를 불러올 수 없거나 Yahoo Finance 호출 제한에 도달했습니다. 잠시 후 다시 시도해 주세요.")
    else:
        try:
            latest_price = float(df["Close"].iloc[-1])
            prev_price = float(df["Close"].iloc[-2]) if len(df) > 1 else latest_price
            change = latest_price - prev_price
            pct_change = (change / prev_price) * 100 if prev_price != 0 else 0.0
            currency = info.get("currency", "USD") if info else "USD"

            st.subheader(f"📌 {selected_stock_name} 심층 리포트")
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("현재가", f"{latest_price:,.2f} {currency}")
            c2.metric("전일 대비", f"{change:+,.2f} {currency}", f"{pct_change:+.2f}%")
            c3.metric("기간 최고가", f"{float(df['High'].max()):,.2f} {currency}")
            c4.metric("기간 최저가", f"{float(df['Low'].min()):,.2f} {currency}")

            st.markdown("---")

            # 캔들스틱 차트 및 이동평균선
            fig = go.Figure()
            fig.add_trace(go.Candlestick(
                x=df.index,
                open=df["Open"],
                high=df["High"],
                low=df["Low"],
                close=df["Close"],
                name="주가 (OHLC)"
            ))

            ma20 = df["Close"].rolling(20).mean()
            ma60 = df["Close"].rolling(60).mean()
            fig.add_trace(go.Scatter(x=df.index, y=ma20, mode="lines", name="20일 이평선", line=dict(color="orange", width=1.5)))
            fig.add_trace(go.Scatter(x=df.index, y=ma60, mode="lines", name="60일 이평선", line=dict(color="green", width=1.5)))

            fig.update_layout(
                title=f"{selected_stock_name} 주가 차트 및 이동평균선",
                yaxis_title=f"가격 ({currency})",
                xaxis_rangeslider_visible=False,
                height=500,
                template="plotly_white"
            )
            st.plotly_chart(fig, use_container_width=True)

            # 거래량 차트
            fig_vol = go.Figure()
            fig_vol.add_trace(go.Bar(x=df.index, y=df["Volume"], name="거래량", marker_color="gray"))
            fig_vol.update_layout(
                title="거래량 추이",
                yaxis_title="거래량",
                height=220,
                template="plotly_white"
            )
            st.plotly_chart(fig_vol, use_container_width=True)

            # 재무 지표 및 개요
            st.markdown("### 🏢 기업 펀더멘털 및 Valuation 지표")
            
            col_a, col_b = st.columns(2)
            with col_a:
                st.markdown("**주요 재무 지표**")
                metrics_data = {
                    "지표명": ["Forward PER", "PBR", "ROE", "영업이익률 (Margin)"],
                    "값": [
                        str(info.get("forwardPE", "N/A")),
                        str(info.get("priceToBook", "N/A")),
                        f"{info.get('returnOnEquity', 0) * 100:.2f}%" if info.get('returnOnEquity') else "N/A",
                        f"{info.get('profitMargins', 0) * 100:.2f}%" if info.get('profitMargins') else "N/A"
                    ]
                }
                st.table(pd.DataFrame(metrics_data))

            with col_b:
                st.markdown("**52주 변동 범위 내 위치**")
                low52 = info.get("fiftyTwoWeekLow")
                high52 = info.get("fiftyTwoWeekHigh")
                if low52 and high52:
                    st.write(f"52주 최저: {low52:,.2f} {currency}")
                    st.write(f"52주 최고: {high52:,.2f} {currency}")
                    progress = min(max((latest_price - low52) / (high52 - low52), 0.0), 1.0)
                    st.progress(progress, text=f"52주 가격대 내 위치: {progress * 100:.1f}%")
                else:
                    st.write("52주 가격 범위 정보가 없습니다.")

            with st.expander("ℹ️ 종목/ETF 상세 개요 전문 보기"):
                st.write(info.get("longBusinessSummary", "상세 설명 정보가 없습니다."))

        except Exception as e:
            st.error(f"차트 처리 중 오류가 발생했습니다: {e}")

# -------------------------------------------------------------
# MODE 2: AI 반도체 종목 간 수익률 비교
# -------------------------------------------------------------
else:
    st.subheader(f"📊 {category} 상대 수익률 (%) 비교 분석")
    st.markdown("선택한 기간 동안 동일한 기준점(0%)을 바탕으로 주가 변동률을 정규화하여 비교합니다.")

    selected_tickers = st.sidebar.multiselect(
        "비교할 종목 선택",
        options=list(available_stocks.keys()),
        default=list(available_stocks.keys())[:3]
    )

    if not selected_tickers:
        st.info("비교할 종목을 최소 하나 이상 선택해 주세요.")
    else:
        combined_df = pd.DataFrame()

        with st.spinner("종목별 상대 수익률 계산 중..."):
            for name in selected_tickers:
                symbol = available_stocks[name]
                df, _ = fetch_safe_stock_data(symbol, period)
                if not df.empty and "Close" in df.columns:
                    start_price = float(df["Close"].iloc[0])
                    if start_price != 0:
                        combined_df[name] = ((df["Close"] - start_price) / start_price) * 100

        if combined_df.empty:
            st.error("선택한 종목의 데이터를 불러오지 못했습니다.")
        else:
            fig_comp = px.line(
                combined_df,
                x=combined_df.index,
                y=combined_df.columns,
                title=f"기준일 대비 누적 수익률 추이 (%) - [{period}]",
                labels={"value": "수익률 (%)", "index": "날짜", "variable": "종목명"}
            )
            fig_comp.update_layout(height=550, template="plotly_white")
            st.plotly_chart(fig_comp, use_container_width=True)

            st.markdown("### 🏆 기간 내 최종 수익률 순위")
            final_returns = combined_df.iloc[-1].sort_values(ascending=False)
            ret_df = pd.DataFrame({"누적 수익률 (%)": final_returns.map("{:+.2f}%".format)})
            st.dataframe(ret_df, use_container_width=True)
