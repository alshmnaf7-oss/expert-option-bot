import os

# Telegram Bot Token securely read from Environment variable
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")

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

TIMEFRAMES = {
    "⏱ 1 دقيقة": "1m",
    "⏱ 2 دقيقة": "2m",
    "⏱ 5 دقائق": "5m"
}

ADX_RANGING_THRESHOLD = 22
