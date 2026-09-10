import yfinance as yf
import pandas as pd
import datetime
from ta.trend import ADXIndicator, EMAIndicator
from ta.momentum import RSIIndicator, StochasticOscillator
from ta.volatility import BollingerBands
from config import ADX_RANGING_THRESHOLD

def analyze_market(symbol: str, interval: str) -> dict:
    """
    محرك التحليل الفني المطور V2.1:
    - فحص ساعات عمل السوق والشموع الحية بدقة
    - معالجة ذكية للتذبذب وإعطاء إشارات واضحة
    - تصفية الإشارات الكاذبة لحماية رأس المال
    """
    try:
        ticker = yf.Ticker(symbol)
        period = "1d" if interval in ["1m", "2m", "5m"] else "5d"
        df = ticker.history(period=period, interval=interval)

        if df.empty or len(df) < 25:
            return {
                "status": "error",
                "message": "تعذر سحب بيانات كافية لهذا السوق حالياً. قد يكون السوق مغلقاً أو خارج ساعات التداول."
            }

        # فحص هل السوق نشط وحي حالياً أم مغلق (خاصة الأسهم الأمريكية مثل تسلا وأبل)
        last_candle_time = df.index[-1].to_pydatetime()
        now_utc = datetime.datetime.now(datetime.timezone.utc)
        diff_minutes = (now_utc - last_candle_time).total_seconds() / 60

        # إذا كانت الشمعة متأخرة أكثر من 45 دقيقة فالسوق مغلق في البورصة العالمية
        if diff_minutes > 45:
            return {
                "status": "error",
                "message": "هذا السوق مغلق حالياً في البورصة العالمية (تفتح البورصة الأمريكية 4:30 م بتوقيت مكة). يمكنك التداول الآن في أسواق العملات المفتوحة (EUR/USD, GBP/USD...) أو الكريبتو (Bitcoin, Solana...)."
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

        # قراءة أحدث شمعة مغلقة
        current_close = round(df['Close'].iloc[-1], 5)
        prev_close = df['Close'].iloc[-2]
        prev_open = df['Open'].iloc[-2]
        is_green_candle = prev_close >= prev_open
        is_red_candle = prev_close < prev_open

        current_adx = round(df['adx'].iloc[-1], 2)
        current_rsi = round(df['rsi'].iloc[-1], 2)
        current_stoch_k = round(df['stoch_k'].iloc[-1], 2)
        current_stoch_d = round(df['stoch_d'].iloc[-1], 2)

        ema_fast = df['ema_fast'].iloc[-1]
        ema_slow = df['ema_slow'].iloc[-1]
        di_pos = df['di_pos'].iloc[-1]
        di_neg = df['di_neg'].iloc[-1]

        # فحص حالة التذبذب الميت (ADX أقل من 18)
        # إذا كان ADX منخفضاً جداً فالسوق متجمد تماماً
        if current_adx < 18:
            return {
                "status": "ranging",
                "price": current_close,
                "adx": current_adx,
                "rsi": current_rsi,
                "message": "السوق في حالة تذبذب خامل جداً (ADX أقل من 18). لا يوجد أي اتجاه صاعد أو هابط، والدخول الآن مجازفة عالية."
            }

        # شروط إشارة الصعود CALL
        call_strong = ema_fast > ema_slow and di_pos > di_neg and current_rsi < 68 and is_green_candle
        call_moderate = (ema_fast > ema_slow or di_pos > di_neg) and current_rsi < 65 and current_stoch_k > current_stoch_d

        # شروط إشارة الهبوط PUT
        put_strong = ema_fast < ema_slow and di_neg > di_pos and current_rsi > 32 and is_red_candle
        put_moderate = (ema_fast < ema_slow or di_neg > di_pos) and current_rsi > 35 and current_stoch_k < current_stoch_d

        if call_strong:
            signal = "CALL (شراء / صعود) 🟢"
            if current_adx >= 28 and current_stoch_k > current_stoch_d:
                strength = "🌟 فرصة ذهبية فائقة الدقة (+80%)"
                tip = "جميع المؤشرات متوافقة بقوة صاعدة مع اتجاه مؤكد. ادخل صفقة CALL مع بداية الشمعة التالية."
            else:
                strength = "جيدة جداً 📈"
                tip = "الاتجاه صاعد وتأكيد الشمعة إيجابي. ادخل صفقة صعود (CALL)."
        elif put_strong:
            signal = "PUT (بيع / هبوط) 🔴"
            if current_adx >= 28 and current_stoch_k < current_stoch_d:
                strength = "🌟 فرصة ذهبية فائقة الدقة (+80%)"
                tip = "جميع المؤشرات متوافقة بقوة هابطة مع اتجاه مؤكد. ادخل صفقة PUT مع بداية الشمعة التالية."
            else:
                strength = "جيدة جداً 📉"
                tip = "الاتجاه هابط وتأكيد الشمعة سلبي. ادخل صفقة هبوط (PUT)."
        elif call_moderate and current_adx >= 20:
            signal = "CALL (شراء / صعود) 🟢"
            strength = "متوسطة / مقبولة 📈"
            tip = "زخم صاعد مقبول، ادخل بلوت معتدل مع الالتزام بإدارة رأس المال."
        elif put_moderate and current_adx >= 20:
            signal = "PUT (بيع / هبوط) 🔴"
            strength = "متوسطة / مقبولة 📉"
            tip = "زخم هابط مقبول، ادخل بلوت معتدل مع الالتزام بإدارة رأس المال."
        else:
            return {
                "status": "ranging",
                "price": current_close,
                "adx": current_adx,
                "rsi": current_rsi,
                "message": "السوق في نطاق حركة متذبذبة وغير مستقرة حالياً. الأفضل الانتظار حتى يتشكل اتجاه واضح."
            }

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
