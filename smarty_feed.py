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
SMARTY_CACHE_TTL = 15  # كاش لمدة 15 ثانية لتسريع الاستجابة وحماية الاتصال

ENDPOINTS = [
    "wss://fr24g1eu.expertoption.com/",
    "wss://fr24g1eu.expertoption.finance/ws/v40",
    "wss://fr24g1us.expertoption.com/"
]

def fetch_smarty_df(token=None):
    """
    سحب الشموع الحية الأصلية لمؤشر Smarty (Asset ID: 240) مباشرة من خوادم Expert Option
    عبر WebSocket.
    """
    global SMARTY_CACHE
    now = time.time()
    if SMARTY_CACHE["df"] is not None and (now - SMARTY_CACHE["ts"] < SMARTY_CACHE_TTL):
        return SMARTY_CACHE["df"]

    use_token = token or EXPERT_TOKEN
    if not use_token:
        logger.warning("No EXPERT_TOKEN configured.")
        return None

    now_ts = int(now)
    # طلب آخر 60 دقيقة من شموع 1 دقيقة
    history_request = {
        "action": "assetHistoryCandles",
        "message": {
            "assetid": 240,
            "periods": [[now_ts - 3600, now_ts]],
            "timeframes": [60]
        },
        "token": use_token,
        "ns": 5
    }

    candles_rows = []

    def run_connection(url):
        nonlocal candles_rows

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
                        ws.close()
            except Exception as e:
                logger.error(f"Error parsing candle message: {e}")

        def on_open(ws):
            ws.send(json.dumps(history_request))

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
            t.join(timeout=5)
            try:
                ws.close()
            except Exception:
                pass
        except Exception as e:
            logger.warning(f"Connection to {url} failed: {e}")

    # محاولة الاتصال بالخادم الأساسي ثم البديل إذا لزم
    for endpoint in ENDPOINTS:
        run_connection(endpoint)
        if candles_rows:
            break

    if not candles_rows:
        logger.error("Failed to fetch Smarty candles from all endpoints.")
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
