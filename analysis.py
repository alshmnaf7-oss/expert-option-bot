import yfinance as yf
import pandas as pd
from ta.trend import ADXIndicator, EMAIndicator
from ta.momentum import RSIIndicator
from config import ADX_RANGING_THRESHOLD

def analyze_market(symbol: str, interval: str) -> dict:
    """
    تحليل حركة الزوج عبر الشموع الحية واكتشاف التذبذب وقوة الاتجاه
    """
    try:
        # جلب بيانات الشموع الحية
        ticker = yf.Ticker(symbol)
        period = "1d" if interval in ["1m", "2m", "5m"] else "5d"
        df = ticker.history(period=period, interval=interval)

        if df.empty or len(df) < 30:
            return {
                "status": "error",
                "message": "تعذر سحب بيانات كافية لهذا السوق حالياً. قد يكون السوق مغلقاً أو البيانات غير متوفرة."
            }

        # 1. حساب مؤشر ADX لاكتشاف التذبذب وقوة الاتجاه
        adx_indicator = ADXIndicator(high=df['High'], low=df['Low'], close=df['Close'], window=14)
        df['adx'] = adx_indicator.adx()
        df['di_pos'] = adx_indicator.adx_pos()
        df['di_neg'] = adx_indicator.adx_neg()

        # 2. حساب مؤشر RSI لمعرفة مناطق التشبع والزخم
        rsi_indicator = RSIIndicator(close=df['Close'], window=14)
        df['rsi'] = rsi_indicator.rsi()

        # 3. حساب المتوسطات المتحركة السريعة والبطيئة (EMA 9 & EMA 21)
        df['ema_fast'] = EMAIndicator(close=df['Close'], window=9).ema_indicator()
        df['ema_slow'] = EMAIndicator(close=df['Close'], window=21).ema_indicator()

        # القيم الحالية عند أحدث شمعة مغلقة
        current_close = round(df['Close'].iloc[-1], 5)
        current_adx = round(df['adx'].iloc[-1], 2)
        current_rsi = round(df['rsi'].iloc[-1], 2)
        ema_fast = df['ema_fast'].iloc[-1]
        ema_slow = df['ema_slow'].iloc[-1]
        di_pos = df['di_pos'].iloc[-1]
        di_neg = df['di_neg'].iloc[-1]

        # فحص حالة التذبذب (إذا كانت قيمة ADX أقل من الحد المعياري 22)
        if current_adx < ADX_RANGING_THRESHOLD:
            return {
                "status": "ranging",
                "price": current_close,
                "adx": current_adx,
                "rsi": current_rsi,
                "message": "السوق في حالة تذبذب حالياً (لا يوجد اتجاه واضح، تجنب الدخول)."
            }

        # إذا كان هناك اتجاه واضح، نحدد التوصية (صعود / هبوط)
        # شروط الصعود: EMA السريع أعلى من البطيء، DI+ أعلى من DI-، و RSI ليس في تشبع شرائي مفرط
        if ema_fast > ema_slow and di_pos > di_neg and current_rsi < 68:
            signal = "CALL (شراء / صعود) 🟢"
            strength = "قوية جداً 🚀" if current_adx > 32 else "جيدة 📈"
            tip = "ادخل صفقة صعود (CALL) مع بداية الشمعة القادمة."
        # شروط الهبوط: EMA السريع أقل من البطيء، DI- أعلى من DI+، و RSI ليس في تشبع بيعي مفرط
        elif ema_fast < ema_slow and di_neg > di_pos and current_rsi > 32:
            signal = "PUT (بيع / هبوط) 🔴"
            strength = "قوية جداً 🚀" if current_adx > 32 else "جيدة 📉"
            tip = "ادخل صفقة هبوط (PUT) مع بداية الشمعة القادمة."
        else:
            signal = "محايد / انتظار ⏳"
            strength = "غير واضحة"
            tip = "الإشارات متضاربة، يفضل الانتظار حتى اكتمال شمعة تأكيد جديدة."

        return {
            "status": "trend",
            "signal": signal,
            "strength": strength,
            "price": current_close,
            "adx": current_adx,
            "rsi": current_rsi,
            "tip": tip
        }

    except Exception as e:
        return {"status": "error", "message": f"حدث خطأ أثناء التحليل: {str(e)}"}
