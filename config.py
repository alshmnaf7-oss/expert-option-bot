import os

# إعدادات بوت توصيات Expert Option

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "8770286973:AAHswe11b03wjkyGcym_DYnW6urLN8url5k")

# قائمة الأسواق والأزواج المتاحة مطابقة لمنصة Expert Option
MARKETS = {
    # سوق Smarty المباشر
    "🤖 Smarty": "AIQ",

    # العملات الرئيسية (Forex)
    "🇪🇺/🇺🇸 EUR/USD": "EURUSD=X",
    "🇬🇧/🇺🇸 GBP/USD": "GBPUSD=X",
    "🇺🇸/🇯🇵 USD/JPY": "JPY=X",
    "🇦🇺/🇺🇸 AUD/USD": "AUDUSD=X",
    "🇺🇸/🇨🇦 USD/CAD": "CAD=X",
    "🇺🇸/🇨🇭 USD/CHF": "USDCHF=X",
    "🇪🇺/🇯🇵 EUR/JPY": "EURJPY=X",
    "🇬🇧/🇯🇵 GBP/JPY": "GBPJPY=X",
    "🇪🇺/🇬🇧 EUR/GBP": "EURGBP=X",
    
    # العملات الرقمية (Crypto)
    "₿ Bitcoin": "BTC-USD",
    "💎 Ethereum": "ETH-USD",
    "☀️ Solana": "SOL-USD",

    # الأسهم الأكثر تداولاً
    "🍏 Apple": "AAPL",
    "🚗 Tesla": "TSLA",
    "📦 Amazon": "AMZN",
    "💻 NVIDIA": "NVDA"
}

# مدد الصفقات المتاحة
TIMEFRAMES = {
    "⏱ 1 دقيقة": "1m",
    "⏱ 2 دقيقة": "2m",
    "⏱ 5 دقائق": "5m"
}

# معيار فحص التذبذب المحدث (25)
ADX_RANGING_THRESHOLD = 25
