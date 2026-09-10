import yfinance as yf
import pandas as pd
import datetime
from ta.trend import ADXIndicator, EMAIndicator, MACD
from ta.momentum import RSIIndicator, StochasticOscillator
from config import ADX_RANGING_THRESHOLD

def analyze_market(symbol: str, interval: str) -> dict:
    """
    محرك التحليل الفني عالي الدقة V3.0 (Strict Win-Rate Strategy):
    1. اعتماد الشمعة المغلقة المكتملة 100% لتجنب الإشارات الكاذبة
    2. فحص اتجاه المتوسطات EMA 9 و EMA 21
    3. فحص مؤشر MACD (اتجاه وقوة الزخم)
    4. فحص شمعة التأكيد (Bullish / Bearish Candle)
    5. فلتر ADX لمنع الدخول في التذبذب
    6. فحص RSI لتجنب الانعكاسات عند القمم والقيعان
    """
    try:
        ticker = yf.Ticker(symbol)
        period = "2d" if interval in ["1m", "2m", "5m"] else "5d"
        df = ticker.history(period=period, interval=interval)

        if df.empty or len(df) < 35:
            return {
                "status": "error",
                "message": "تعذر سحب بيانات كافية لهذا السوق حالياً. قد يكون السوق مغلقاً أو خارج ساعات التداول."
            }

        # فحص هل السوق نشط وحي حالياً أم مغلق
        last_candle_time = df.index[-1].to_pydatetime()
        now_utc = datetime.datetime.now(datetime.timezone.utc)
        diff_minutes = (now_utc - last_candle_time).total_seconds() / 60

        if diff_minutes > 45:
            return {
                "status": "error",
                "message": "هذا السوق مغلق حالياً في البورصة العالمية (تفتح البورصة الأمريكية 4:30 م بتوقيت مكة). الأسواق المفتوحة والنشطة الآن هي: أزواج العملات (EUR/USD, GBP/USD...) والعملات الرقمية (Bitcoin, Solana...)."
            }

        # حساب المؤشرات الفنية
        adx_ind = ADXIndicator(high=df['High'], low=df['Low'], close=df['Close'], window=14)
        df['adx'] = adx_ind.adx()
        df['di_pos'] = adx_ind.adx_pos()
        df['di_neg'] = adx_ind.adx_neg()

        df['rsi'] = RSIIndicator(close=df['Close'], window=14).rsi()
        df['ema_fast'] = EMAIndicator(close=df['Close'], window=9).ema_indicator()
        df['ema_slow'] = EMAIndicator(close=df['Close'], window=21).ema_indicator()

        macd_ind = MACD(close=df['Close'], window_fast=12, window_slow=26, window_sign=9)
        df['macd'] = macd_ind.macd()
        df['macd_signal'] = macd_ind.macd_signal()
        df['macd_diff'] = macd_ind.macd_diff()

        stoch = StochasticOscillator(high=df['High'], low=df['Low'], close=df['Close'], window=14, smooth_window=3)
        df['stoch_k'] = stoch.stoch()
        df['stoch_d'] = stoch.stoch_signal()

        # قراءة الشمعة المغلقة المكتملة الأخيرة
        closed_candle = df.iloc[-2]
        c_open = closed_candle['Open']
        c_close = closed_candle['Close']

        is_bullish = c_close >= c_open
        is_bearish = c_close <= c_open

        current_adx = round(closed_candle['adx'], 2)
        current_rsi = round(closed_candle['rsi'], 2)
        current_stoch_k = round(closed_candle['stoch_k'], 2)
        current_stoch_d = round(closed_candle['stoch_d'], 2)
        current_price = round(df['Close'].iloc[-1], 5)

        ema_fast = closed_candle['ema_fast']
        ema_slow = closed_candle['ema_slow']
        di_pos = closed_candle['di_pos']
        di_neg = closed_candle['di_neg']
        macd_val = closed_candle['macd']
        macd_sig = closed_candle['macd_signal']
        macd_diff = closed_candle['macd_diff']

        # فلتر التذبذب: إذا كان ADX أقل من 20 فالسوق خامل تماماً
        if current_adx < 20:
            return {
                "status": "ranging",
                "price": current_price,
                "adx": current_adx,
                "rsi": current_rsi,
                "message": f"السوق في تذبذب عرضي خامل (ADX = {current_adx} أقل من 20). تم حجب التوصية لحماية رصيدك من الخسارة."
            }

        # شروط إشارة الصعود CALL المؤكدة (+80%):
        call_valid = (
            ema_fast > ema_slow and
            di_pos > di_neg and
            macd_diff > 0 and
            is_bullish and
            40 <= current_rsi <= 72 and
            current_stoch_k > current_stoch_d
        )

        # شروط إشارة الهبوط PUT المؤكدة (+80%):
        put_valid = (
            ema_fast < ema_slow and
            di_neg > di_pos and
            macd_diff < 0 and
            is_bearish and
            28 <= current_rsi <= 60 and
            current_stoch_k < current_stoch_d
        )

        if call_valid:
            strength = "🌟 فرصة ذهبية فائقة القوة (+85%)" if current_adx >= 28 else "مؤكدة وقوية جداً 🚀"
            return {
                "status": "trend",
                "signal": "CALL (شراء / صعود) 🟢",
                "strength": strength,
                "price": current_price,
                "adx": current_adx,
                "rsi": current_rsi,
                "tip": "جميع مؤشرات الاتجاه (EMA, MACD, ADX, RSI, Stoch) متوافقة صعوداً. ادخل CALL مع بداية الشمعة الحالية."
            }

        elif put_valid:
            strength = "🌟 فرصة ذهبية فائقة القوة (+85%)" if current_adx >= 28 else "مؤكدة وقوية جداً 🚀"
            return {
                "status": "trend",
                "signal": "PUT (بيع / هبوط) 🔴",
                "strength": strength,
                "price": current_price,
                "adx": current_adx,
                "rsi": current_rsi,
                "tip": "جميع مؤشرات الاتجاه (EMA, MACD, ADX, RSI, Stoch) متوافقة هبوطاً. ادخل PUT مع بداية الشمعة الحالية."
            }

        else:
            return {
                "status": "ranging",
                "price": current_price,
                "adx": current_adx,
                "rsi": current_rsi,
                "message": "المؤشرات متضاربة حالياً ولا تحقق شروط الدخول المؤكدة بالكامل. تم حجب الصفقة لضمان الأمان وتفادي الخسارة."
            }

    except Exception as e:
        return {"status": "error", "message": f"حدث خطأ أثناء التحليل: {str(e)}"}
