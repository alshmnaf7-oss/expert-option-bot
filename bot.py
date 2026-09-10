import sys
import asyncio
import logging
import os
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

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
from config import BOT_TOKEN, MARKETS, TIMEFRAMES, ADX_RANGING_THRESHOLD
from analysis import analyze_market

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

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

threading.Thread(target=start_health_server, daemon=True).start()

def get_markets_keyboard():
    """توليد لوحة أزرار الأسواق بشكل منظم وسهل التصفح"""
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
    """عرض رسالة الترحيب وقائمة الأسواق الموسعة"""
    reply_markup = get_markets_keyboard()
    welcome_text = (
        "🤖 *بوت توصيات تداول Expert Option (الإصدار الاحترافي V2.0)*\n\n"
        "👋 مرحباً بك! تم تحديث البوت بمحرك تحليل عالي الدقة يدمج:\n"
        "• مؤشر ADX المطور (عتبة 25 لإلغاء أي تذبذب)\n"
        "• فحص وتأكيد اتجاه الشموع الحية (Price Action)\n"
        "• مؤشرات الزخم المزدوجة (RSI + Stochastic)\n"
        "• تنبيهات انتهاء مدة الصفقة التلقائية ⏳\n\n"
        "📊 *اختر السوق أو الزوج الذي ترغب ببدء تحليله:*"
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
    else:
        await update.message.reply_text(
            welcome_text,
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )

async def notify_trade_finished(context: ContextTypes.DEFAULT_TYPE):
    """دالة التنبيه التلقائي بانتهاء مدة الصفقة بدقة بالثواني"""
    job_data = context.job.data
    chat_id = job_data["chat_id"]
    market_name = job_data["market_name"]
    tf_code = job_data["tf_code"]
    signal = job_data["signal"]

    action_buttons = [
        [InlineKeyboardButton("🔄 فحص نفس السوق لصفقة جديدة", callback_data=f"tf:{tf_code}")],
        [InlineKeyboardButton("📊 اختيار سوق آخر", callback_data="back_to_markets")]
    ]
    reply_markup = InlineKeyboardMarkup(action_buttons)

    finished_msg = (
        "⏰ *انتهت مدة الصفقة الآن!* 🏁\n\n"
        f"🔹 *الزوج:* `{market_name}`\n"
        f"⏱ *المدة المنتهية:* `{tf_code}`\n"
        f"📢 *الصفقة السابقة:* {signal}\n\n"
        "💡 *الخطوة التالية:*\n"
        "اضغط على زر *إعادة الفحص* بالأسفل لمعرفة وضع الشمعة الجديدة وما إذا كانت هناك فرصة دخول مؤكدة أخرى!"
    )

    try:
        await context.bot.send_message(
            chat_id=chat_id,
            text=finished_msg,
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
    except Exception as e:
        logger.error(f"Error sending finished notification: {e}")

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة جميع الأزرار التفاعلية بدقة وسرعة"""
    query = update.callback_query
    try:
        await query.answer()
    except Exception:
        pass

    data = query.data

    try:
        # 1. رجوع للأسواق
        if data == "back_to_markets":
            await start(update, context)
            return

        # 2. اختيار السوق
        if data.startswith("market:"):
            market_name = data.split("market:")[1]
            context.user_data["selected_market"] = market_name

            keyboard = []
            for tf_name, tf_code in TIMEFRAMES.items():
                keyboard.append([InlineKeyboardButton(tf_name, callback_data=f"tf:{tf_code}")])
            keyboard.append([InlineKeyboardButton("🔙 رجوع لقائمة الأسواق", callback_data="back_to_markets")])

            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(
                f"📊 *السوق المختار:* `{market_name}`\n\n"
                "⏱ حدد *مدة الصفقة* لبدء فحص الشموع الحية وتأكيد الإشارة:",
                reply_markup=reply_markup,
                parse_mode="Markdown"
            )
            return

        # 3. اختيار الفريم أو إعادة الفحص
        if data.startswith("tf:"):
            tf_code = data.split("tf:")[1]
            market_name = context.user_data.get("selected_market", "🇪🇺/🇺🇸 EUR/USD")
            symbol = MARKETS.get(market_name, "EURUSD=X")

            try:
                await query.edit_message_text(
                    f"⏳ *جاري سحب الشموع الحية وتحليل الزخم...*\n\n"
                    f"🔹 الزوج: `{market_name}`\n"
                    f"⏱ الفريم: `{tf_code}`\n\n"
                    "• فحص قوة الاتجاه ADX (معيار الأمان 25)\n"
                    "• فحص تأكيد شمعة الـ Price Action\n"
                    "• حساب توافق RSI و Stochastic..."
                )
            except BadRequest:
                pass

            try:
                result = await asyncio.wait_for(asyncio.to_thread(analyze_market, symbol, tf_code), timeout=12.0)
            except asyncio.TimeoutError:
                result = {
                    "status": "error",
                    "message": "استغرق جلب بيانات الشموع وقتاً أطول من المعتاد. اضغط على إعادة الفحص للمحاولة مجدداً."
                }
            except Exception as e:
                result = {
                    "status": "error",
                    "message": f"حدث خطأ أثناء فحص البيانات: {str(e)}"
                }

            action_buttons = [
                [InlineKeyboardButton("🔄 إعادة فحص نفس السوق", callback_data=f"tf:{tf_code}")],
                [InlineKeyboardButton("📊 اختيار سوق آخر", callback_data="back_to_markets")]
            ]
            reply_markup = InlineKeyboardMarkup(action_buttons)

            # حالة الخطأ
            if result.get("status") == "error":
                await query.edit_message_text(
                    f"❌ *تنبيه:*\n{result['message']}",
                    reply_markup=reply_markup,
                    parse_mode="Markdown"
                )
                return

            # حالة التذبذب
            if result.get("status") == "ranging":
                ranging_msg = (
                    "⚠️ *تنبيه: السوق في حالة تذبذب حالياً!* ⚠️\n\n"
                    f"🔹 *الزوج:* `{market_name}`\n"
                    f"⏱ *الفريم:* `{tf_code}`\n"
                    f"📉 *قوة الاتجاه (ADX):* `{result['adx']}` (أقل من {ADX_RANGING_THRESHOLD} ❌)\n"
                    f"📊 *مؤشر الزخم (RSI):* `{result['rsi']}`\n\n"
                    "🚫 *القرار والتحليل:*\n"
                    "السعر يتحرك بشكل عرضي تذبذبي عالي المخاطر.\n\n"
                    "👉 *تجنب الدخول في هذا التوقيت نهائياً لحماية رصيدك.*"
                )
                try:
                    await query.edit_message_text(ranging_msg, reply_markup=reply_markup, parse_mode="Markdown")
                except BadRequest as e:
                    if "Message is not modified" in str(e):
                        await query.answer("تم التحديث: السوق لا يزال متذبذباً.")

            # حالة وجود اتجاه
            else:
                signal_str = result['signal']
                signal_msg = (
                    "🎯 *توصية تداول عالية الدقة - Expert Option*\n\n"
                    f"🔹 *الزوج:* `{market_name}`\n"
                    f"⏱ *مدة الصفقة:* `{tf_code}`\n"
                    f"📢 *الإشارة:* *{signal_str}*\n"
                    f"💪 *قوة الفرصة:* `{result['strength']}`\n"
                    f"📉 *مؤشر ADX:* `{result['adx']}`\n"
                    f"📊 *مؤشر RSI:* `{result['rsi']}`\n\n"
                    f"💡 *التوجيه الاحترافي:* {result['tip']}\n\n"
                    "⏳ _تم تشغيل مؤقت الصفقة تلقائياً، وسيرسل لك البوت تنبيهاً فور انتهائها._"
                )
                try:
                    await query.edit_message_text(signal_msg, reply_markup=reply_markup, parse_mode="Markdown")
                except BadRequest as e:
                    if "Message is not modified" in str(e):
                        await query.answer("تم التحديث: الإشارة لا تزال مستمرة.")

                # تشغيل مؤقت التنبيه بانتهاء الصفقة إذا كانت التوصية صعود أو هبوط حقيقيين
                if "CALL" in signal_str or "PUT" in signal_str:
                    seconds_map = {"1m": 60, "2m": 120, "5m": 300}
                    wait_seconds = seconds_map.get(tf_code, 60)
                    chat_id = query.message.chat_id

                    # جدولة إشعار انتهاء الصفقة
                    context.job_queue.run_once(
                        notify_trade_finished,
                        when=wait_seconds,
                        data={
                            "chat_id": chat_id,
                            "market_name": market_name,
                            "tf_code": tf_code,
                            "signal": signal_str
                        }
                    )

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
    if not BOT_TOKEN:
        print("ERROR: BOT_TOKEN is missing in config.py")
        return

    app = Application.builder().token(BOT_TOKEN).concurrent_updates(True).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_callback))

    print("\nBot V2.0 is running successfully! Open Telegram and send /start")
    app.run_polling()

if __name__ == "__main__":
    main()
