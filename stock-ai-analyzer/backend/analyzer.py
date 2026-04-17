import yfinance as yf
import pandas as pd
import numpy as np

def get_stock_data(ticker: str) -> dict:
    """ดึงราคาหุ้นและคำนวณ Technical Indicators"""
    
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period="6mo")
        
        if hist.empty:
            return {"error": f"ไม่พบข้อมูลหุ้น {ticker}"}
        
        current_price = hist["Close"].iloc[-1]
        prev_close = hist["Close"].iloc[-2]
        change = current_price - prev_close
        change_pct = (change / prev_close) * 100
        
        hist["MA20"] = hist["Close"].rolling(window=20).mean()
        hist["MA50"] = hist["Close"].rolling(window=50).mean()
        hist["MA200"] = hist["Close"].rolling(window=200).mean()
        
        ma20 = hist["MA20"].iloc[-1]
        ma50 = hist["MA50"].iloc[-1]
        ma200 = hist["MA200"].iloc[-1] if not np.isnan(hist["MA200"].iloc[-1]) else None
        
        avg_volume = hist["Volume"].rolling(window=20).mean().iloc[-1]
        current_volume = hist["Volume"].iloc[-1]
        volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1
        
        recent = hist.tail(60)
        highs = []
        lows = []
        
        for i in range(2, len(recent) - 2):
            if (recent["High"].iloc[i] > recent["High"].iloc[i-1] and
                recent["High"].iloc[i] > recent["High"].iloc[i-2] and
                recent["High"].iloc[i] > recent["High"].iloc[i+1] and
                recent["High"].iloc[i] > recent["High"].iloc[i+2]):
                highs.append(recent["High"].iloc[i])
            
            if (recent["Low"].iloc[i] < recent["Low"].iloc[i-1] and
                recent["Low"].iloc[i] < recent["Low"].iloc[i-2] and
                recent["Low"].iloc[i] < recent["Low"].iloc[i+1] and
                recent["Low"].iloc[i] < recent["Low"].iloc[i+2]):
                lows.append(recent["Low"].iloc[i])
        
        resistances = sorted([h for h in highs if h > current_price])[:3]
        supports = sorted([l for l in lows if l < current_price], reverse=True)[:3]
        
        delta = hist["Close"].diff()
        gain = delta.where(delta > 0, 0).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        current_rsi = rsi.iloc[-1]
        
        week52_high = hist["High"].max()
        week52_low = hist["Low"].min()
        
        return {
            "ticker": ticker,
            "current_price": round(current_price, 2),
            "change": round(change, 2),
            "change_pct": round(change_pct, 2),
            "ma20": round(ma20, 2) if not np.isnan(ma20) else None,
            "ma50": round(ma50, 2) if not np.isnan(ma50) else None,
            "ma200": round(ma200, 2) if ma200 and not np.isnan(ma200) else None,
            "volume_ratio": round(volume_ratio, 2),
            "current_volume": int(current_volume),
            "avg_volume": int(avg_volume),
            "supports": [round(s, 2) for s in supports],
            "resistances": [round(r, 2) for r in resistances],
            "rsi": round(current_rsi, 2) if not np.isnan(current_rsi) else None,
            "week52_high": round(week52_high, 2),
            "week52_low": round(week52_low, 2),
        }
    
    except Exception as e:
        return {"error": str(e)}


def get_fundamental_data(ticker: str) -> dict:
    """ดึงข้อมูล Fundamental ของบริษัท"""
    
    try:
        stock = yf.Ticker(ticker)
        info = stock.info

        def safe(key, default=None):
            val = info.get(key, default)
            if val is None or (isinstance(val, float) and np.isnan(val)):
                return default
            return val

        def fmt_billion(val):
            if val is None:
                return None
            return round(val / 1e9, 2)

        # --- Income Statement ---
        revenue = safe("totalRevenue")
        gross_profit = safe("grossProfits")
        net_income = safe("netIncomeToCommon")
        ebitda = safe("ebitda")
        revenue_growth = safe("revenueGrowth")
        earnings_growth = safe("earningsGrowth")

        # --- Balance Sheet ---
        total_cash = safe("totalCash")
        total_debt = safe("totalDebt")
        current_ratio = safe("currentRatio")
        debt_to_equity = safe("debtToEquity")
        book_value = safe("bookValue")

        # --- Valuation ---
        pe_ratio = safe("trailingPE")
        forward_pe = safe("forwardPE")
        peg_ratio = safe("pegRatio")
        ps_ratio = safe("priceToSalesTrailingTwelveMonths")
        pb_ratio = safe("priceToBook")
        market_cap = safe("marketCap")
        enterprise_value = safe("enterpriseValue")
        ev_ebitda = safe("enterpriseToEbitda")

        # --- Profitability ---
        gross_margin = safe("grossMargins")
        operating_margin = safe("operatingMargins")
        net_margin = safe("profitMargins")
        roe = safe("returnOnEquity")
        roa = safe("returnOnAssets")

        # --- Per Share ---
        eps_trailing = safe("trailingEps")
        eps_forward = safe("forwardEps")
        dividend_yield = safe("dividendYield")

        # --- Analyst ---
        target_high = safe("targetHighPrice")
        target_low = safe("targetLowPrice")
        target_mean = safe("targetMeanPrice")
        recommendation = safe("recommendationKey")
        analyst_count = safe("numberOfAnalystOpinions")

        return {
            "income": {
                "revenue_b": fmt_billion(revenue),
                "gross_profit_b": fmt_billion(gross_profit),
                "net_income_b": fmt_billion(net_income),
                "ebitda_b": fmt_billion(ebitda),
                "revenue_growth_pct": round(revenue_growth * 100, 2) if revenue_growth else None,
                "earnings_growth_pct": round(earnings_growth * 100, 2) if earnings_growth else None,
            },
            "balance_sheet": {
                "total_cash_b": fmt_billion(total_cash),
                "total_debt_b": fmt_billion(total_debt),
                "current_ratio": round(current_ratio, 2) if current_ratio else None,
                "debt_to_equity": round(debt_to_equity, 2) if debt_to_equity else None,
                "book_value": round(book_value, 2) if book_value else None,
            },
            "valuation": {
                "market_cap_b": fmt_billion(market_cap),
                "enterprise_value_b": fmt_billion(enterprise_value),
                "pe_ratio": round(pe_ratio, 2) if pe_ratio else None,
                "forward_pe": round(forward_pe, 2) if forward_pe else None,
                "peg_ratio": round(peg_ratio, 2) if peg_ratio else None,
                "ps_ratio": round(ps_ratio, 2) if ps_ratio else None,
                "pb_ratio": round(pb_ratio, 2) if pb_ratio else None,
                "ev_ebitda": round(ev_ebitda, 2) if ev_ebitda else None,
            },
            "profitability": {
                "gross_margin_pct": round(gross_margin * 100, 2) if gross_margin else None,
                "operating_margin_pct": round(operating_margin * 100, 2) if operating_margin else None,
                "net_margin_pct": round(net_margin * 100, 2) if net_margin else None,
                "roe_pct": round(roe * 100, 2) if roe else None,
                "roa_pct": round(roa * 100, 2) if roa else None,
            },
            "per_share": {
                "eps_trailing": round(eps_trailing, 2) if eps_trailing else None,
                "eps_forward": round(eps_forward, 2) if eps_forward else None,
                "dividend_yield_pct": round(dividend_yield * 100, 2) if dividend_yield else None,
            },
            "analyst": {
                "target_high": target_high,
                "target_low": target_low,
                "target_mean": target_mean,
                "recommendation": recommendation,
                "analyst_count": analyst_count,
            }
        }

    except Exception as e:
        return {"error": str(e)}