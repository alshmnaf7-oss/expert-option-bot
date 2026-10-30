import websocket
import ssl
import json
import time
import logging
import threading
import pandas as pd
from config import EXPERT_TOKEN

logger = logging.getLogger(__name__)

SMARTY_CACHE = {"ts": 0, "df": None}
SMARTY_CACHE_TTL = 20  # كاش لمدة 20 ثانية لتسريع الاستجابة وتجنب ضغط الاتصال

ENDPOINTS = [
    "wss://fr24g1eu.expertoption.com/",
    "wss://fr24g1eu.expertoption.finance/ws/v40",
    "wss://fr24g1us.expertoption.com/"
]

def fetch_smarty_df(token=None):
    """
    سحب الشموع الحية الأصلية لمؤشر Smarty (Asset ID: 240) مباشرة من خوادم Expert Option.
    يدعم الاستمرار الذاتي (Self-Healing): إذا انتهت جلسة التوكن الخاصة بالمستخدم بعد ساعة،
    يتحول البوت تلقائياً إلى البث المباشر العام بدون توقف نهائياً.
    """
    global SMARTY_CACHE
    now = time.time()
    if SMARTY_CACHE["df"] is not None and (now - SMARTY_CACHE["ts"] < SMARTY_CACHE_TTL):
        return SMARTY_CACHE["df"]

    now_ts = int(now)

    # قائمة التوكنات للتجربة: أولاً توكن المستخدم، ثم توكن عام فارغ كبديل مضمون 100%
    preferred_token = token or EXPERT_TOKEN or ""
    tokens_to_try = [preferred_token]
    if preferred_token != "":
        tokens_to_try.append("")  # خط دفاع أخير يمنع توقف البوت بعد ساعة

    candles_rows = []

    def try_fetch(curr_token, url):
        nonlocal candles_rows
        history_request = {
            "action": "assetHistoryCandles",
            "message": {
                "assetid": 240,
                "periods": [[now_ts - 3600, now_ts]],
                "timeframes": [60]
            },
            "token": curr_token,
            "ns": 5
        }

        def on_message(ws, raw):
            try:
                msg = json.loads(raw.decode('utf-8') if isinstance(raw, bytes) else raw)
                action = msg.get("action")
                if action == "assetHistoryCandles":
                    candles_block = msg.get("message", {}).get("candles", [])
                    if candles_block:
                        tf = candles_block[0].get("tf", 60)
                        periods = candles_block[0].get("periods", [])
                        for p_start, c_list in periods:
                            for i, c in enumerate(c_list):
                                candle_ts = p_start + i * tf
                                candles_rows.append({
                                    "timestamp": pd.to_datetime(candle_ts, unit='s'),
                                    "Open": float(c[0]),
                                    "High": float(c[1]),
                                    "Low": float(c[2]),
                                    "Close": float(c[3]),
                                    "Volume": 100
                                })
                        try:
                            ws.close()
                        except Exception:
                            pass
            except Exception as e:
                logger.error(f"Error parsing candle message: {e}")

        def on_open(ws):
            try:
                ws.send(json.dumps(history_request))
            except Exception:
                pass

        try:
            ws = websocket.WebSocketApp(
                url,
                on_open=on_open,
                on_message=on_message,
                on_error=lambda ws, e: None,
                on_close=lambda ws, c, m: None
            )
            t = threading.Thread(target=ws.run_forever, kwargs={"sslopt": {"cert_reqs": ssl.CERT_NONE}})
            t.daemon = True
            t.start()
            t.join(timeout=4.5)
            try:
                ws.close()
            except Exception:
                pass
        except Exception as e:
            logger.warning(f"Connection to {url} failed: {e}")

    # محاولة جلب الشموع عبر التوكن الأساسي، ثم البديل المضمون
    for t_val in tokens_to_try:
        for endpoint in ENDPOINTS:
            try_fetch(t_val, endpoint)
            if candles_rows:
                break
        if candles_rows:
            break

    if not candles_rows:
        logger.error("Failed to fetch Smarty candles from all endpoints and tokens.")
        return None

    df = pd.DataFrame(candles_rows)
    df.set_index("timestamp", inplace=True)
    df.sort_index(inplace=True)
    df = df[~df.index.duplicated(keep='last')]

    if len(df) < 20:
        return None

    SMARTY_CACHE["ts"] = time.time()
    SMARTY_CACHE["df"] = df
    return df
