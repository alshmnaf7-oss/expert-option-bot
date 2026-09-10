import yfinance as yf
import pandas as pd
from ta.trend import ADXIndicator, EMAIndicator
from ta.momentum import RSIIndicator, StochasticOscillator
from ta.volatility import BollingerBands
from config import ADX_RANGING_THRESHOLD

def analyze_market(symbol: str, interval: str) -> dict:
    """
    محرك التحليل الفني المطور V2.0:
    - فحص قوة الاتجاه عبر ADX مع رفع حد الأمان إلى 25 لمنع الدخول في التذبذب
    - تأكيد اتجاه الشموع الحية (Price Action Candle Confirmation)
    - فحص المتوسطات المتحركة EMA 9 و EMA 21
    - فحص مؤشر RSI لمنع الشراء عند القمم أو البيع عند القيعان
    - فحص مؤشر Stochastic Oscillator لزيادة دقة الدخول وتأكيد الزخم
    - تصنيف التوصيات بدقة عالية (فرصة ذهبية عالية الدقة / جيدة / تجنب الدخول)
    """
    try:
        ticker = yf.Ticker(symbol)
        period = "1d" if interval in ["1m", "2m", "5m"] else "5d"
        df = ticker.history(period=period, interval=interval)

        if df.empty or len(df) < 30:
            return {
                "status": "error",
                "message": "تعذر سحب بيانات كافية لهذا السوق حالياً. قد يكون السوق مغلقاً أو خارج ساعات التداول."
            }

        # 1. حساب مؤشر ADX
        adx_indicator = ADXIndicator(high=df['High'], low=df['Low'], close=df['Close'], window=14)
        df['adx'] = adx_indicator.adx()
        df['di_pos'] = adx_indicator.adx_pos()
        df['di_neg'] = adx_indicator.adx_neg()

        # 2. حساب مؤشر RSI
        rsi_indicator = RSIIndicator(close=df['Close'], window=14)
        df['rsi'] = rsi_indicator.rsi()

        # 3. حساب المتوسطات المتحركة EMA 9 و EMA 21
        df['ema_fast'] = EMAIndicator(close=df['Close'], window=9).ema_indicator()
        df['ema_slow'] = EMAIndicator(close=df['Close'], window=21).ema_indicator()

        # 4. حساب مؤشر Stochastic Oscillator
        stoch = StochasticOscillator(high=df['High'], low=df['Low'], close=df['Close'], window=14, smooth_window=3)
        df['stoch_k'] = stoch.stoch()
        df['stoch_d'] = stoch.stoch_signal()

        # 5. حساب مؤشر Bollinger Bands
        bb = BollingerBands(close=df['Close'], window=20, window_dev=2)
        df['bb_high'] = bb.bollinger_hband()
        df['bb_low'] = bb.bollinger_lband()

        # قراءة أحدث شمعة مغلقة
        current_close = round(df['Close'].iloc[-1], 5)
        prev_close = df['Close'].iloc[-2]
        prev_open = df['Open'].iloc[-2]
        is_green_candle = prev_close >= prev_open  # شمعة التأكيد صاعدة
        is_red_candle = prev_close < prev_open    # شمعة التأكيد هابطة

        current_adx = round(df['adx'].iloc[-1], 2)
        current_rsi = round(df['rsi'].iloc[-1], 2)
        current_stoch_k = round(df['stoch_k'].iloc[-1], 2)
        current_stoch_d = round(df['stoch_d'].iloc[-1], 2)

        ema_fast = df['ema_fast'].iloc[-1]
        ema_slow = df['ema_slow'].iloc[-1]
        di_pos = df['di_pos'].iloc[-1]
        di_neg = df['di_neg'].iloc[-1]

        # فحص حالة التذبذب (إذا كان ADX أقل من 25)
        if current_adx < ADX_RANGING_THRESHOLD:
            return {
                "status": "ranging",
                "price": current_close,
                "adx": current_adx,
                "rsi": current_rsi,
                "message": "السوق في نطاق تذبذب عرضي ضعيف. لا يوجد اتجاه قوي حالياً، يُنصح بالانتظار لحماية رأس المال."
            }

        # شروط إشارة الصعود CALL:
        # 1. متوسط EMA السريع أعلى من البطيء
        # 2. DI+ أعلى من DI-
        # 3. RSI ليس في تشبع شرائي مفرط (أقل من 68)
        # 4. تأكيد الشمعة: الشمعة السابقة خضراء (صعودية)
        call_condition = (
            ema_fast > ema_slow and
            di_pos > di_neg and
            current_rsi < 68 and
            is_green_candle and
            current_stoch_k < 80
        )

        # شروط إشارة الهبوط PUT:
        # 1. متوسط EMA السريع أقل من البطيء
        # 2. DI- أعلى من DI+
        # 3. RSI ليس في تشبع بيعي مفرط (أعلى من 32)
        # 4. تأكيد الشمعة: الشمعة السابقة حمراء (هبوطية)
        put_condition = (
            ema_fast < ema_slow and
            di_neg > di_pos and
            current_rsi > 32 and
            is_red_candle and
            current_stoch_k > 20
        )

        if call_condition:
            signal = "CALL (شراء / صعود) 🟢"
            # فرصة ذهبية إذا كان ADX قوي والستوكاستيك يؤكد الصعود
            if current_adx >= 32 and current_stoch_k > current_stoch_d:
                strength = "🌟 فرصة ذهبية فائقة الدقة (+80%)"
                tip = "جميع المؤشرات متوافقة بقوة صاعدة. ادخل صفقة CALL مع بداية الشمعة التالية."
            else:
                strength = "جيدة جداً 📈"
                tip = "الاتجاه صاعد مع تأكيد الشمعة. ادخل صفقة صعود (CALL)."
        elif put_condition:
            signal = "PUT (بيع / هبوط) 🔴"
            # فرصة ذهبية إذا كان ADX قوي والستوكاستيك يؤكد الهبوط
            if current_adx >= 32 and current_stoch_k < current_stoch_d:
                strength = "🌟 فرصة ذهبية فائقة الدقة (+80%)"
                tip = "جميع المؤشرات متوافقة بقوة هابطة. ادخل صفقة PUT مع بداية الشمعة التالية."
            else:
                strength = "جيدة جداً 📉"
                tip = "الاتجاه هابط مع تأكيد الشمعة. ادخل صفقة هبوط (PUT)."
        else:
            signal = "محايد / انتظار ⏳"
            strength = "إشارات غير مكتملة"
            tip = "شروط الدخول لم تكتمل بنسبة 100% (تضارب في مؤشرات الزخم أو لون الشمعة). الأفضل الانتظار."

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
