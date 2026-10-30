import os

# إعدادات بوت توصيات Expert Option

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
EXPERT_TOKEN = os.environ.get("EXPERT_OPTION_TOKEN", "b7ae455450cdfe7832df64f0b820d3f0")

# قائمة الأسواق المختارة (مؤشر سمارتي + البيتكوين 24/7)
MARKETS = {
    # مؤشر سمارتي الحقيقي عبر اتصال الويب سوكيت المباشر مع Expert Option
    "🤖 مؤشر سمارتي (Smarty)": "EXPERT_SMARTY",

    # عملة البيتكوين الرقمية المفتوحة 24/7
    "₿ Bitcoin": "BTC-USD"
}

# مدد الصفقات المتاحة
TIMEFRAMES = {
    "⏱ 1 دقيقة": "1m",
    "⏱ 2 دقيقة": "2m",
    "⏱ 5 دقائق": "5m"
}

# معيار فحص التذبذب المحدث (25)
ADX_RANGING_THRESHOLD = 25
