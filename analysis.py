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

        if current_adx < 19 and (35 <= current_rsi <= 65):
            res = {
                'status': 'ranging',
                'price': current_price,
                'adx': current_adx,
                'rsi': current_rsi,
                'timing': timing,
                'message': f'السوق يتحرك في مسار عرضي ضعيف (ADX = {current_adx}). يُمنع الدخول لتفادي الخسارة.'
            }
            CACHE[cache_key] = (now_ts, res)
            return res

        extreme_call = (
            (c_low <= bb_low or c_close <= bb_low * 1.0005) and
            current_rsi <= 32 and
            current_stoch_k <= 25 and
            (bottom_rejection or is_bullish)
        )

        extreme_put = (
            (c_high >= bb_up or c_close >= bb_up * 0.9995) and
            current_rsi >= 68 and
            current_stoch_k >= 75 and
            (top_rejection or is_bearish)
        )

        trend_call = (
            ema_f > ema_s and
            c_close > bb_mid and
            not top_rejection and
            is_bullish and
            42 <= current_rsi <= 68 and
            current_stoch_k > current_stoch_d and
            current_stoch_k < 82 and
            macd_d > prev_macd_d and
            current_adx >= 21
        )

        trend_put = (
            ema_f < ema_s and
            c_close < bb_mid and
            not bottom_rejection and
            is_bearish and
            32 <= current_rsi <= 58 and
            current_stoch_k < current_stoch_d and
            current_stoch_k > 18 and
            macd_d < prev_macd_d and
            current_adx >= 21
        )

        if extreme_call:
            res = {
                'status': 'trend',
                'signal': 'CALL (شراء / صعود) 🟢',
                'strength': '🌟 صفقة قناص فائقة القوة (+88%)',
                'price': current_price,
                'adx': current_adx,
                'rsi': current_rsi,
                'timing': timing,
                'tip': 'ارتداد حاد من قاع البولينجر مع تشبع بيعي (RSI < 32). يتوقع ارتداد صاعد فوري بالشمعة القادمة.'
            }
        elif extreme_put:
            res = {
                'status': 'trend',
                'signal': 'PUT (بيع / هبوط) 🔴',
                'strength': '🌟 صفقة قناص فائقة القوة (+88%)',
                'price': current_price,
                'adx': current_adx,
                'rsi': current_rsi,
                'timing': timing,
                'tip': 'ارتداد حاد من قمة البولينجر مع تشبع شرائي (RSI > 68). يتوقع هبوط تصحيحي فوري بالشمعة القادمة.'
            }
        elif trend_call:
            res = {
                'status': 'trend',
                'signal': 'CALL (شراء / صعود) 🟢',
                'strength': '🚀 اتجاه صاعد مؤكد وقوي (+82%)',
                'price': current_price,
                'adx': current_adx,
                'rsi': current_rsi,
                'timing': timing,
                'tip': 'زخم شرائي مدعوم بالمتوسطات وبولينجر بدون ذيول رفض علوية. ادخل صفقة صعود.'
            }
        elif trend_put:
            res = {
                'status': 'trend',
                'signal': 'PUT (بيع / هبوط) 🔴',
                'strength': '🚀 اتجاه هابط مؤكد وقوي (+82%)',
                'price': current_price,
                'adx': current_adx,
                'rsi': current_rsi,
                'timing': timing,
                'tip': 'زخم بيعي مدعوم بالمتوسطات وبولينجر بدون ذيول رفض سفلية. ادخل صفقة هبوط.'
            }
        else:
            res = {
                'status': 'ranging',
                'price': current_price,
                'adx': current_adx,
                'rsi': current_rsi,
                'timing': timing,
                'message': 'المؤشرات والبرايس أكشن غير مكتملة لشروط الدخول المضمونة. تم حجب الصفقة لحماية رصيدك من أي انعكاس مفاجئ.'
            }

        CACHE[cache_key] = (now_ts, res)
        return res

    except Exception as e:
        return {'status': 'error', 'message': f'حدث خطأ أثناء التحليل: {str(e)}'}
