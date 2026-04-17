from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from groq import Groq
from dotenv import load_dotenv
import os

from analyzer import get_stock_data, get_fundamental_data
from news import get_stock_news

load_dotenv()

groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

DEFAULT_STOCKS = {
    "NVDA": "NVIDIA",
    "TSM": "TSMC",
    "LLY": "Eli Lilly",
    "MU": "Micron Technology",
    "WM": "Waste Management",
    "JNJ": "Johnson & Johnson",
}

@app.get("/api/stocks")
def get_stocks():
    return {"stocks": [{"ticker": k, "name": v} for k, v in DEFAULT_STOCKS.items()]}

@app.get("/api/analyze/{ticker}")
def analyze_stock(ticker: str):
    ticker = ticker.upper()
    # รองรับทั้ง default stocks และ ticker ที่ค้นหาเอง
    company_name = DEFAULT_STOCKS.get(ticker, "")

    # ถ้าไม่ใช่ default ให้ดึงชื่อบริษัทจาก yfinance
    if not company_name:
        try:
            import yfinance as yf
            info = yf.Ticker(ticker).info
            company_name = info.get("shortName") or info.get("longName") or ticker
        except:
            company_name = ticker

    # ดึงข้อมูลทั้งหมด
    tech_data = get_stock_data(ticker)
    if "error" in tech_data:
        return {"error": tech_data["error"]}

    fund_data = get_fundamental_data(ticker)
    news = get_stock_news(ticker, company_name)

    # --- สร้าง prompt ---
    news_text = "\n".join([f"- {n['title']} | {n['source']} ({n['published']})" for n in news]) or "ไม่พบข่าว"
    supports_text = ", ".join([f"${s}" for s in tech_data["supports"]]) or "ไม่พบ"
    resistances_text = ", ".join([f"${r}" for r in tech_data["resistances"]]) or "ไม่พบ"

    ma_trend = "ไม่มีข้อมูล"
    if tech_data["ma20"] and tech_data["ma50"]:
        if tech_data["ma20"] > tech_data["ma50"]:
            ma_trend = "MA20 อยู่เหนือ MA50 (แนวโน้มขาขึ้น)"
        else:
            ma_trend = "MA20 อยู่ใต้ MA50 (แนวโน้มขาลง)"

    rsi_status = "ไม่มีข้อมูล"
    if tech_data["rsi"]:
        if tech_data["rsi"] > 70:
            rsi_status = f"RSI {tech_data['rsi']} (Overbought)"
        elif tech_data["rsi"] < 30:
            rsi_status = f"RSI {tech_data['rsi']} (Oversold)"
        else:
            rsi_status = f"RSI {tech_data['rsi']} (ปกติ)"

    # Fundamental summary
    inc = fund_data.get("income", {})
    bal = fund_data.get("balance_sheet", {})
    val = fund_data.get("valuation", {})
    pro = fund_data.get("profitability", {})
    per = fund_data.get("per_share", {})
    ana = fund_data.get("analyst", {})

    fund_text = f"""
=== ข้อมูลพื้นฐานบริษัท (Fundamental) ===
--- รายได้และกำไร ---
รายได้รวม: ${inc.get('revenue_b', 'N/A')}B | กำไรขั้นต้น: ${inc.get('gross_profit_b', 'N/A')}B
กำไรสุทธิ: ${inc.get('net_income_b', 'N/A')}B | EBITDA: ${inc.get('ebitda_b', 'N/A')}B
การเติบโตรายได้: {inc.get('revenue_growth_pct', 'N/A')}% | การเติบโตกำไร: {inc.get('earnings_growth_pct', 'N/A')}%

--- งบดุล ---
เงินสด: ${bal.get('total_cash_b', 'N/A')}B | หนี้สินรวม: ${bal.get('total_debt_b', 'N/A')}B
Current Ratio: {bal.get('current_ratio', 'N/A')} | D/E Ratio: {bal.get('debt_to_equity', 'N/A')}

--- Valuation ---
Market Cap: ${val.get('market_cap_b', 'N/A')}B | P/E: {val.get('pe_ratio', 'N/A')} | Forward P/E: {val.get('forward_pe', 'N/A')}
PEG: {val.get('peg_ratio', 'N/A')} | P/S: {val.get('ps_ratio', 'N/A')} | P/B: {val.get('pb_ratio', 'N/A')}
EV/EBITDA: {val.get('ev_ebitda', 'N/A')}

--- ความสามารถทำกำไร ---
Gross Margin: {pro.get('gross_margin_pct', 'N/A')}% | Operating Margin: {pro.get('operating_margin_pct', 'N/A')}%
Net Margin: {pro.get('net_margin_pct', 'N/A')}% | ROE: {pro.get('roe_pct', 'N/A')}% | ROA: {pro.get('roa_pct', 'N/A')}%

--- Per Share ---
EPS (Trailing): ${per.get('eps_trailing', 'N/A')} | EPS (Forward): ${per.get('eps_forward', 'N/A')}
Dividend Yield: {per.get('dividend_yield_pct', 'N/A')}%

--- นักวิเคราะห์ ---
เป้าหมายราคา: ${ana.get('target_low', 'N/A')} - ${ana.get('target_high', 'N/A')} (เฉลี่ย ${ana.get('target_mean', 'N/A')})
Consensus: {ana.get('recommendation', 'N/A')} (จาก {ana.get('analyst_count', 'N/A')} นักวิเคราะห์)
"""

    prompt = f"""
คุณเป็นผู้ช่วยวิเคราะห์หุ้นภาษาไทย วิเคราะห์หุ้น {ticker} ({company_name}) จากข้อมูลต่อไปนี้:

=== ข้อมูลราคา ===
ราคาปัจจุบัน: ${tech_data['current_price']}
เปลี่ยนแปลงวันนี้: {tech_data['change_pct']}% (${tech_data['change']})
52-Week High: ${tech_data['week52_high']} | 52-Week Low: ${tech_data['week52_low']}

=== Technical Indicators ===
MA20: ${tech_data['ma20']} | MA50: ${tech_data['ma50']} | MA200: ${tech_data['ma200']}
แนวโน้ม: {ma_trend}
{rsi_status}
Volume: {tech_data['volume_ratio']}x ค่าเฉลี่ย
แนวรับ: {supports_text}
แนวต้าน: {resistances_text}

{fund_text}

=== ข่าวล่าสุด ===
{news_text}

กรุณาวิเคราะห์เป็นภาษาไทย แบ่งเป็น 5 หัวข้อ:

1. **สรุปภาพรวม** (สุขภาพบริษัทและแนวโน้มตลาด 2-3 ประโยค)
2. **วิเคราะห์ Fundamental** (รายได้ กำไร หนี้สิน valuation เทียบกับ sector)
3. **วิเคราะห์ Technical** (แนวรับ/แนวต้านสำคัญ พร้อมเหตุผล)
4. **วิเคราะห์ข่าว** (sentiment และผลกระทบต่อราคา)
5. **จุดน่าสนใจ** (โซนที่ควรพิจารณาเข้าซื้อหรือขาย พร้อมเงื่อนไข)

⚠️ เป็นข้อมูลประกอบการตัดสินใจเท่านั้น ไม่ใช่คำแนะนำการลงทุน
"""

    try:
        response = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1500,
        )
        ai_analysis = response.choices[0].message.content
    except Exception as e:
        ai_analysis = f"ไม่สามารถวิเคราะห์ได้: {str(e)}"

    return {
        "ticker": ticker,
        "company": company_name,
        "technical": tech_data,
        "fundamental": fund_data,
        "news": news,
        "ai_analysis": ai_analysis,
    }

# Serve frontend
import os as _os
BASE_DIR = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
FRONTEND_DIR = _os.path.join(BASE_DIR, "frontend")
app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")