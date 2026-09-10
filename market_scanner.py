import asyncio
from concurrent.futures import ThreadPoolExecutor
from analysis import analyze_market
from config import MARKETS

def scan_best_markets(interval: str = "1m") -> list:
    """
    فحص جميع الأسواق المفتوحة والنشطة حالياً بالتوازي
    واستخراج الأسواق التي بها فرص دخول صريحة وغير مغلقة
    """
    best_opportunities = []

    def check_one(name, symbol):
        res = analyze_market(symbol, interval)
        # نستبعد الأسواق المغلقة أو التي بها خطأ أو تذبذب
        if res.get("status") == "trend" and ("CALL" in res.get("signal", "") or "PUT" in res.get("signal", "")):
            return {
                "name": name,
                "symbol": symbol,
                "signal": res["signal"],
                "strength": res["strength"],
                "adx": res["adx"],
                "rsi": res["rsi"],
                "tip": res["tip"]
            }
        return None

    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = [executor.submit(check_one, name, sym) for name, sym in MARKETS.items()]
        for f in futures:
            try:
                res = f.result()
                if res:
                    best_opportunities.append(res)
            except Exception:
                pass

    best_opportunities.sort(key=lambda x: (1 if "فرصة ذهبية" in x["strength"] else 0, x["adx"]), reverse=True)
    return best_opportunities
