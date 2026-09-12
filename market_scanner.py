import datetime
from concurrent.futures import ThreadPoolExecutor
from analysis import analyze_market
from config import MARKETS

def scan_best_markets(interval: str = "1m") -> list:
    """
    فحص الأسواق المفتوحة والنشطة حالياً بالتوازي:
    في الويكند (السبت والأحد): فحص العملات الرقمية الحية المفتوحة 24/7 فقط
    في أيام الأسبوع (الإثنين - الجمعة): فحص جميع الأسواق والذهب والفوركس
    """
    best_opportunities = []

    # فحص عطلة نهاية الأسبوع (5: السبت، 6: الأحد)
    is_weekend = datetime.datetime.now(datetime.timezone.utc).weekday() in [5, 6]

    if is_weekend:
        target_markets = {k: v for k, v in MARKETS.items() if "-USD" in v}
    else:
        target_markets = MARKETS

    def check_one(name, symbol):
        try:
            res = analyze_market(symbol, interval)
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
        except Exception:
            pass
        return None

    with ThreadPoolExecutor(max_workers=len(target_markets)) as executor:
        futures = [executor.submit(check_one, name, sym) for name, sym in target_markets.items()]
        for f in futures:
            try:
                res = f.result(timeout=6.0)
                if res:
                    best_opportunities.append(res)
            except Exception:
                pass

    best_opportunities.sort(key=lambda x: (1 if "فرصة ذهبية" in x["strength"] else 0, x["adx"]), reverse=True)
    return best_opportunities
