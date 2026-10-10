import os

# إعدادات بوت توصيات Expert Option

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")

# قائمة الأسواق والأزواج المتاحة والمطابقة 100% لمنصة Expert Option (تقبل دقيقة واحدة دائماً)
MARKETS = {
    # العملات الرقمية الأساسية المفتوحة والنشطة 24/7 في Expert Option
    "₿ Bitcoin": "BTC-USD",
    "💎 Ethereum": "ETH-USD",
    "⚡ Ripple": "XRP-USD",

    # الذهب واليورو/دولار (مفتوحة من الإثنين إلى الجمعة)
    "🥇 الذهب (Gold)": "GC=F",
    "🇪🇺/🇺🇸 EUR/USD": "EURUSD=X"
}

# مدد الصفقات المتاحة
TIMEFRAMES = {
    "⏱ 1 دقيقة": "1m",
    "⏱ 2 دقيقة": "2m",
    "⏱ 5 دقائق": "5m"
}

# معيار فحص التذبذب المحدث (25)
ADX_RANGING_THRESHOLD = 25
