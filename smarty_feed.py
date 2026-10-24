import websocket
import ssl
import json
import time
import logging
import pandas as pd
from config import EXPERT_TOKEN

logger = logging.getLogger(__name__)

SMARTY_CACHE = {"ts": 0, "df": None}
SMARTY_CACHE_TTL = 15  # كاش لمدة 15 ثانية لتسريع الاستجابة وعدم الضغط على سيرفر المنصة

def fetch_smarty_df(token=None, candle_count=45):
    """
    سحب الشموع الحية الأصلية لمؤشر Smarty (Asset ID: 240) مباشرة من سيرفر Expert Option عبر WebSocket
    """
    global SMARTY_CACHE
    now = time.time()
    if SMARTY_CACHE["df"] is not None and (now - SMARTY_CACHE["ts"] < SMARTY_CACHE_TTL):
        return SMARTY_CACHE["df"]

    use_token = token or EXPERT_TOKEN
    if not use_token:
        logger.warning("No EXPERT_TOKEN provided.")
        return None

    url = "wss://fr24g1eu.expertoption.com/"
    candles_received = []

    def on_message(ws, raw):
        try:
            msg = json.loads(raw.decode('utf-8') if isinstance(raw, bytes) else raw)
            action = msg.get("action")
            
            if action == "multipleAction":
                for a in msg.get("message", {}).get("actions", []):
                    if a.get("action") == "assetHistoryCandles":
                        data_240 = a.get("message", {}).get("240", [])
                        if data_240:
                            candles_received.extend(data_240)
                            ws.close()
            elif action == "assetHistoryCandles":
                data_240 = msg.get("message", {}).get("240", [])
                if data_240:
                    candles_received.extend(data_240)
                    ws.close()
        except Exception:
            pass

    def on_open(ws):
        now_ts = int(time.time())
        periods = []
        for i in range(candle_count):
            start_p = now_ts - (i + 1) * 60
            end_p = now_ts - i * 60
            periods.append([start_p, end_p])
            
        payload = {
            "action": "multipleAction",
            "token": use_token,
            "v": 18,
            "message": {
                "token": use_token,
                "actions": [
                    {
                        "action": "assetHistoryCandles",
                        "message": {
                            "assetid": 240,
                            "periods": periods,
                            "timeframes": [60]
                        },
                        "token": use_token,
                        "v": 18,
                        "ns": 101
                    }
                ]
            }
        }
        ws.send(json.dumps(payload))

    try:
        ws = websocket.WebSocketApp(
            url,
            on_open=on_open,
            on_message=on_message,
            on_error=lambda ws, e: None,
            on_close=lambda ws, c, m: None
        )

        import threading
        t = threading.Thread(target=ws.run_forever, kwargs={"sslopt": {"cert_reqs": ssl.CERT_NONE}})
        t.daemon = True
        t.start()
        t.join(timeout=5)
        try:
            ws.close()
        except Exception:
            pass
    except Exception as e:
        logger.error(f"Error connecting to ExpertOption WebSocket: {e}")
        return None

    if not candles_received:
        return None

    candles_received.sort(key=lambda x: x["t"])
    rows = []
    for c in candles_received:
        rows.append({
            "timestamp": pd.to_datetime(c["t"], unit='s'),
            "Open": float(c["o"]),
            "High": float(c["h"]),
            "Low": float(c["l"]),
            "Close": float(c["c"]),
            "Volume": 100
        })

    df = pd.DataFrame(rows)
    df.set_index("timestamp", inplace=True)
    
    SMARTY_CACHE["ts"] = time.time()
    SMARTY_CACHE["df"] = df
    return df
