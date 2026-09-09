import sys
import asyncio
import logging

# ضبط ترميز الطرفية في ويندوز لدعم نصوص UTF-8
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.error import BadRequest
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from config import BOT_TOKEN, MARKETS, TIMEFRAMES
from analysis import analyze_market

# إعداد التسجيل والمراقبة للأخطاء
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

import os
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write("Bot is running 24/7!".encode("utf-8"))

    def log_message(self, format, *args):
        pass

def start_health_server():
    port = int(os.environ.get("PORT", 8080))
    try:
        server = HTTPServer(("0.0.0.0", port), HealthCheckHandler)
        server.serve_forever()
    except Exception as e:
        logger.warning(f"Health server info: {e}")

# تشغيل سيرفر فحص الصحة في الخلفية ليتوافق مع جميع السيرفرات السحابية
threading.Thread(target=start_health_server, daemon=True).start()

def get_markets_keyboard():
    """توليد لوحة أزرار الأسواق بشكل منظم"""
    keyboard = []
    row = []
    for name in MARKETS.keys():
        row.append(InlineKeyboardButton(name, callback_data=f"market:{name}"))
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    return InlineKeyboardMarkup(keyboard)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض رسالة الترحيب وقائمة الأسواق"""
    reply_markup = get_markets_keyboard()
    welcome_text = (
        "🤖 *بوت توصيات تداول Expert Option*\n\n"
        "👋 مرحباً بك! يحلل هذا البوت حركة الشموع الحية ويكتشف مناطق التذبذب وقوة الاتجاه لاقتراح أفضل توقيت للدخول.\n\n"
        "📊 *اختر السوق أو الزوج الذي ترغب بتحليله:*"
    )

    if update.callback_query:
        try:
            await update.callback_query.edit_message_text(
                welcome_text,
                reply_markup=reply_markup,
                parse_mode="Markdown"
            )
        except BadRequest as e:
            if "Message is not modified" not in str(e):
                await update.callback_query.message.reply_text(
                    welcome_text,
                    reply_markup=reply_markup,
                    parse_mode="Markdown"
                )
    elif update.message:
        await update.message.reply_text(
            welcome_text,
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة كافة نقرات الأزرار من المستخدم بسلاسة ودون تجميد"""
    query = update.callback_query
    try:
        await query.answer()
    except Exception:
        pass

    data = query.data

    try:
        # 1. المستخدم ضغط رجوع للأسواق
        if data == "back_to_markets":
            await start(update, context)
            return

        # 2. المستخدم اختار السوق
        if data.startswith("market:"):
            market_name = data.split("market:")[1]
            context.user_data["selected_market"] = market_name

            keyboard = []
            for tf_name, tf_code in TIMEFRAMES.items():
                keyboard.append([InlineKeyboardButton(tf_name, callback_data=f"tf:{tf_code}")])
            keyboard.append([InlineKeyboardButton("🔙 رجوع لاختيار سوق آخر", callback_data="back_to_markets")])

            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(
                f"📊 *السوق المختار:* `{market_name}`\n\n"
                "⏱ حدد *مدة الصفقة* لبدء فحص الشموع والمؤشرات:",
                reply_markup=reply_markup,
                parse_mode="Markdown"
            )
            return

        # 3. المستخدم اختار مدة الصفقة أو ضغط إعادة فحص
        if data.startswith("tf:"):
            tf_code = data.split("tf:")[1]
            market_name = context.user_data.get("selected_market", "🇪🇺/🇺🇸 EUR/USD")
            symbol = MARKETS.get(market_name, "EURUSD=X")

            # رسالة انتظار تفاعلية
            try:
                await query.edit_message_text(
                    f"⏳ *جاري تحليل السوق...*\n\n"
                    f"🔹 الزوج: `{market_name}`\n"
                    f"⏱ الفريم: `{tf_code}`\n\n"
                    "يرجى الانتظار ثوانٍ لسحب الشموع الحية وفحص التذبذب..."
                )
            except BadRequest:
                pass

            # تشغيل التحليل في Thread منفصل مع مهلة زمنية صارمة (10 ثوانٍ) لمنع أي تعليق نهائياً
            try:
                result = await asyncio.wait_for(asyncio.to_thread(analyze_market, symbol, tf_code), timeout=10.0)
            except asyncio.TimeoutError:
                result = {
                    "status": "error",
                    "message": "استغرق جلب بيانات السوق وقتاً أطول من المعتاد. اضغط على زر إعادة الفحص للمحاولة مجدداً."
                }
            except Exception as e:
                result = {
                    "status": "error",
                    "message": f"حدث خطأ أثناء فحص البيانات: {str(e)}"
                }

            # أزرار الإجراء بعد انتهاء التحليل
            action_buttons = [
                [InlineKeyboardButton("🔄 إعادة فحص نفس السوق", callback_data=f"tf:{tf_code}")],
                [InlineKeyboardButton("📊 اختيار سوق آخر", callback_data="back_to_markets")]
            ]
            reply_markup = InlineKeyboardMarkup(action_buttons)

            # حالة حدوث خطأ في سحب البيانات
            if result.get("status") == "error":
                await query.edit_message_text(
                    f"❌ *تنبيه:*\n{result['message']}",
                    reply_markup=reply_markup,
                    parse_mode="Markdown"
                )
                return

            # حالة السوق في تذبذب
            if result.get("status") == "ranging":
                ranging_msg = (
                    "⚠️ *تنبيه: السوق في حالة تذبذب حالياً!* ⚠️\n\n"
                    f"🔹 *الزوج:* `{market_name}`\n"
                    f"⏱ *الفريم:* `{tf_code}`\n"
                    f"📉 *قوة الاتجاه (ADX):* `{result['adx']}` (أقل من 22 ❌)\n"
                    f"📊 *مؤشر الزخم (RSI):* `{result['rsi']}`\n\n"
                    "🚫 *القرار والتحليل:*\n"
                    "حركة السعر تسير في نطاق عرضي عشوائي، لا يوجد اتجاه صاعد أو هابط واضح.\n\n"
                    "👉 *يُنصح بعدم دخول أي صفقة في هذا التوقيت لتجنب الخسارة.*"
                )
                try:
                    await query.edit_message_text(ranging_msg, reply_markup=reply_markup, parse_mode="Markdown")
                except BadRequest as e:
                    if "Message is not modified" in str(e):
                        await query.answer("تم تحديث البيانات: السوق لا يزال في حالة تذبذب.")

            # حالة وجود اتجاه وفرصة دخول
            else:
                signal_msg = (
                    "🎯 *توصية تداول - Expert Option*\n\n"
                    f"🔹 *الزوج:* `{market_name}`\n"
                    f"⏱ *مدة الصفقة:* `{tf_code}`\n"
                    f"📢 *الإشارة:* *{result['signal']}*\n"
                    f"💪 *قوة الفرصة:* `{result['strength']}`\n"
                    f"📉 *مؤشر ADX:* `{result['adx']}`\n"
                    f"📊 *مؤشر RSI:* `{result['rsi']}`\n\n"
                    f"💡 *التوجيه:* {result['tip']}\n\n"
                    "⚠️ _تذكير: التداول ينطوي على مخاطر، التزم دائماً بإدارة رأس المال._"
                )
                try:
                    await query.edit_message_text(signal_msg, reply_markup=reply_markup, parse_mode="Markdown")
                except BadRequest as e:
                    if "Message is not modified" in str(e):
                        await query.answer("تم تحديث البيانات: الإشارة الحالية لا تزال مستمرة.")

    except Exception as err:
        logger.error(f"خطأ أثناء معالجة الزر: {err}", exc_info=True)
        try:
            fallback_keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 العودة للرئيسية", callback_data="back_to_markets")]
            ])
            await query.edit_message_text("حدث خطأ بسيط أثناء معالجة الطلب، اضغط للعودة:", reply_markup=fallback_keyboard)
        except Exception:
            pass

def main():
    if not BOT_TOKEN or "ضع_التوكن" in BOT_TOKEN:
        print("ERROR: BOT_TOKEN is missing in config.py")
        return

    app = Application.builder().token(BOT_TOKEN).concurrent_updates(True).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_callback))

    print("\nBot is running successfully with concurrent updates enabled! Open Telegram and send /start")
    app.run_polling()

if __name__ == "__main__":
    main()
