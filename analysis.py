import yfinance as yf
import pandas as pd
import datetime
import time
from ta.trend import ADXIndicator, EMAIndicator, MACD
from ta.momentum import RSIIndicator, StochasticOscillator
from ta.volatility import BollingerBands
from config import ADX_RANGING_THRESHOLD

CACHE = {}
CACHE_TTL = 20

def get_candle_timing() -> dict:
    now = datetime.datetime.now(datetime.timezone.utc)
    sec = now.second
    sec_left = 60 - sec

    if sec <= 10:
        advice = f'🟢 **توقيت ممتاز للدخول الآن!** (بدأت الشمعة قبل {sec} ثانية)'
        urgency = 'enter_now'
    elif sec >= 50:
        advice = f'⚡ **استعد!** الشمعة الجديدة ستبدأ بعد {sec_left} ثانية (ادخل فور بدايتها عند 00:00)'
        urgency = 'prepare'
    else:
        advice = f'⏳ **تنبيه توقيت:** مضى {sec} ثانية من الشمعة الحالية. انتظر الشمعة القادمة بعد {sec_left} ثانية'
        urgency = 'wait'

    return {
        'seconds_passed': sec,
        'seconds_left': sec_left,
        'advice': advice,
        'urgency': urgency
    }

def analyze_market(symbol: str, interval: str) -> dict:
    cache_key = f'{symbol}_{interval}'
    now_ts = time.time()

    if cache_key in CACHE:
        cached_time, cached_data = CACHE[cache_key]
        if now_ts - cached_time < CACHE_TTL:
            cached_data['timing'] = get_candle_timing()
            return cached_data

    try:
        ticker = yf.Ticker(symbol)
        period = '1d' if interval in ['1m', '2m', '5m'] else '5d'
        df = ticker.history(period=period, interval=interval)

        if df.empty or len(df) < 30:
            return {
                'status': 'error',
                'message': 'تعذر سحب بيانات كافية لهذا السوق حالياً. قد يكون السوق مغلقاً أو خارج ساعات التداول.'
            }

        last_candle_time = df.index[-1].to_pydatetime()
        now_utc = datetime.datetime.now(datetime.timezone.utc)
        diff_minutes = (now_utc - last_candle_time).total_seconds() / 60

        if diff_minutes > 45:
            return {
                'status': 'error',
                'message': 'هذا السوق مغلق حالياً في البورصة العالمية (تفتح البورصات صباح الإثنين). الأسواق المفتوحة والنشطة حالياً 24/7 طوال عطلة نهاية الأسبوع هي العملات الرقمية فقط: Bitcoin و Ethereum و Solana.'
            }

        close = df['Close']
        high = df['High']
        low = df['Low']
        open_p = df['Open']

        bb = BollingerBands(close=close, window=20, window_dev=2)
        df['bb_upper'] = bb.bollinger_hband()
        df['bb_middle'] = bb.bollinger_mavg()
        df['bb_lower'] = bb.bollinger_lband()

        adx_ind = ADXIndicator(high=high, low=low, close=close, window=14)
        df['adx'] = adx_ind.adx()
        df['di_pos'] = adx_ind.adx_pos()
        df['di_neg'] = adx_ind.adx_neg()

        df['rsi'] = RSIIndicator(close=close, window=14).rsi()
        df['ema_fast'] = EMAIndicator(close=close, window=9).ema_indicator()
        df['ema_slow'] = EMAIndicator(close=close, window=21).ema_indicator()

        macd_ind = MACD(close=close, window_fast=12, window_slow=26, window_sign=9)
        df['macd_diff'] = macd_ind.macd_diff()

        stoch = StochasticOscillator(high=high, low=low, close=close, window=14, smooth_window=3)
        df['stoch_k'] = stoch.stoch()
        df['stoch_d'] = stoch.stoch_signal()

        c_candle = df.iloc[-2]
        c_open = c_candle['Open']
        c_close = c_candle['Close']
        c_high = c_candle['High']
        c_low = c_candle['Low']

        current_price = round(df['Close'].iloc[-1], 5)
        current_adx = round(c_candle['adx'], 1)
        current_rsi = round(c_candle['rsi'], 1)
        current_stoch_k = round(c_candle['stoch_k'], 1)
        current_stoch_d = round(c_candle['stoch_d'], 1)

        bb_up = c_candle['bb_upper']
        bb_low = c_candle['bb_lower']
        bb_mid = c_candle['bb_middle']

        ema_f = c_candle['ema_fast']
        ema_s = c_candle['ema_slow']
        macd_d = c_candle['macd_diff']
        prev_macd_d = df['macd_diff'].iloc[-3]

        candle_body = abs(c_close - c_open)
        upper_wick = c_high - max(c_open, c_close)
        lower_wick = min(c_open, c_close) - c_low

        is_bullish = c_close >= c_open
        is_bearish = c_close < c_open

        top_rejection = upper_wick > (candle_body * 1.3) and upper_wick > lower_wick
        bottom_rejection = lower_wick > (candle_body * 1.3) and lower_wick > upper_wick

        timing = get_candle_timing()

        # ----------------------------------------------------
        # محرك التقييم الذكي V5.0 (Multi-Factor Scoring Engine)
        # لحل مشكلة التذبذب المستمر ورفع دقة الصفقات في الخيارات الثنائية
        # ----------------------------------------------------
        call_score = 0
        put_score = 0

        # 1. قوة واتجاه المتوسطات المتحركة EMA 9 و EMA 21 (25 نقطة)
        if ema_f > ema_s:
            call_score += 15
            if c_close > ema_f:
                call_score += 10
        elif ema_f < ema_s:
            put_score += 15
            if c_close < ema_f:
                put_score += 10

        # 2. مؤشر القوة النسبية RSI والارتداد (25 نقطة)
        if current_rsi <= 32:
            call_score += 25  # ارتداد قاع حاد
        elif 42 <= current_rsi <= 65:
            call_score += 15  # اتجاه صاعد صحي
        
        if current_rsi >= 68:
            put_score += 25   # ارتداد قمة حاد
        elif 35 <= current_rsi <= 58:
            put_score += 15   # اتجاه هابط صحي

        # 3. مؤشر ستوكاستيك Stochastic (20 نقطة)
        if current_stoch_k > current_stoch_d:
            if current_stoch_k <= 35:
                call_score += 20  # تقاطع صاعد من القاع
            elif current_stoch_k < 85:
                call_score += 15  # استمرار الزخم
        elif current_stoch_k < current_stoch_d:
            if current_stoch_k >= 65:
                put_score += 20   # تقاطع هابط من القمة
            elif current_stoch_k > 15:
                put_score += 15   # استمرار الزخم

        # 4. مؤشر الماكد MACD والتسارع (15 نقطة)
        if macd_d > prev_macd_d:
            call_score += 15
        elif macd_d < prev_macd_d:
            put_score += 15

        # 5. البولينجر باند والبرايس أكشن (15 نقطة)
        if c_low <= bb_low or c_close <= bb_low * 1.001:
            call_score += 15
        elif c_high >= bb_up or c_close >= bb_up * 0.999:
            put_score += 15

        # تأثير ذيول الشموع (Price Action Rejection)
        if bottom_rejection and not is_bearish:
            call_score += 10
        if top_rejection and not is_bullish:
            put_score += 10

        # عقوبة الدخول ضد ذيل الرفض الحاد
        if top_rejection:
            call_score -= 25
        if bottom_rejection:
            put_score -= 25

        # فحص التذبذب الميت فقط (إذا كانت حركة السوق خاملة جداً)
        if current_adx < 16 and (40 <= current_rsi <= 60):
            res = {
                'status': 'ranging',
                'price': current_price,
                'adx': current_adx,
                'rsi': current_rsi,
                'timing': timing,
                'message': f'السوق في حالة خمول عرضي تام (ADX = {current_adx}). تم حجب الصفقة لعدم وجود سيولة كافية.'
            }
            CACHE[cache_key] = (now_ts, res)
            return res

        # القرار النهائي للدخول
        if call_score >= 70 and call_score > put_score + 20:
            strength = "🌟 صفقة قناص مؤكدة (+88%)" if call_score >= 85 else "🚀 صفقة صعود قوية (+82%)"
            tip = "ارتداد قوي من القاع مدعوم بزخم إيجابي وتوافق مؤشرات الشراء." if current_rsi <= 35 else "اتجاه صاعد مدعوم بالقوة النسبية والمتوسطات بدون ذيول معاكسة."
            res = {
                'status': 'trend',
                'signal': 'CALL (شراء / صعود) 🟢',
                'strength': strength,
                'price': current_price,
                'adx': current_adx,
                'rsi': current_rsi,
                'timing': timing,
                'tip': tip
            }
        elif put_score >= 70 and put_score > call_score + 20:
            strength = "🌟 صفقة قناص مؤكدة (+88%)" if put_score >= 85 else "🚀 صفقة هبوط قوية (+82%)"
            tip = "ارتداد قوي من القمة مدعوم بزخم سلبي وتوافق مؤشرات البيع." if current_rsi >= 65 else "اتجاه هابط مدعوم بالقوة النسبية والمتوسطات بدون ذيول معاكسة."
            res = {
                'status': 'trend',
                'signal': 'PUT (بيع / هبوط) 🔴',
                'strength': strength,
                'price': current_price,
                'adx': current_adx,
                'rsi': current_rsi,
                'timing': timing,
                'tip': tip
            }
        else:
            res = {
                'status': 'ranging',
                'price': current_price,
                'adx': current_adx,
                'rsi': current_rsi,
                'timing': timing,
                'message': 'المؤشرات متوازنة حالياً وتنتظر تشكل شمعة اختراق صريحة. اضغط على (أفضل الأسواق) لاقتراح زوج أسرع.'
            }

        CACHE[cache_key] = (now_ts, res)
        return res

    except Exception as e:
        return {'status': 'error', 'message': f'حدث خطأ أثناء التحليل: {str(e)}'}
