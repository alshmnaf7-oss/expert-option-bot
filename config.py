# إعدادات بوت توصيات Expert Option

# ضع توكن البوت الذي نسخته من BotFather هنا بين القوسين
BOT_TOKEN = "8770286973:AAEzq01P3Ytmf1SlmRZ9ODOyPGLqxSNMjHo"

# قائمة الأسواق والأزواج المتاحة ورموزها العالمية
MARKETS = {
    "🇪🇺/🇺🇸 EUR/USD": "EURUSD=X",
    "🇬🇧/🇺🇸 GBP/USD": "GBPUSD=X",
    "🇺🇸/🇯🇵 USD/JPY": "JPY=X",
    "🇦🇺/🇺🇸 AUD/USD": "AUDUSD=X",
    "🇺🇸/🇨🇦 USD/CAD": "CAD=X",
    "🥇 الذهب (XAU/USD)": "GC=F",
    "₿ البيتكوين (BTC/USD)": "BTC-USD",
    "💎 الإيثيريوم (ETH/USD)": "ETH-USD"
}

# مدد الصفقات المتاحة
TIMEFRAMES = {
    "⏱ 1 دقيقة": "1m",
    "⏱ 2 دقيقة": "2m",
    "⏱ 5 دقائق": "5m"
}

# معيار فحص التذبذب (إذا كان مؤشر ADX أقل من 22، فالسوق في تذبذب)
ADX_RANGING_THRESHOLD = 22
