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
from market_scanner import scan_best_markets

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
    """توليد لوحة أزرار الأسواق مع زر المسح لأفضل الأسواق"""
    keyboard = [
        [InlineKeyboardButton("🔥 أفضل الأسواق للتداول الآن (فرص مؤكدة) 🔥", callback_data="scan_best")]
    ]
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
        "🤖 *بوت توصيات تداول Expert Option (الإصدار الاحترافي V4.0)*\n\n"
        "⚡ *تحليل فوري فائق السرعة + توقيت الدخول الدقيق بالشواني*\n\n"
        "👋 مرحباً بك! لاختيار أفضل صفقة جاهزة الآن اضغط على:\n"
        "👉 *[🔥 أفضل الأسواق للتداول الآن]*\n\n"
        "أو اختر السوق مباشرة من القائمة بالأسفل:"
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

async def delayed_trade_finish(bot, chat_id: int, market_name: str, tf_code: str, signal: str, wait_seconds: int):
    """مؤقت غير متزامن مستقل وآمن 100% لإرسال تنبيه انتهاء الصفقة بدون الحاجة لـ JobQueue"""
    await asyncio.sleep(wait_seconds)

    action_buttons = [
        [InlineKeyboardButton("🔄 فحص نفس السوق لصفقة جديدة", callback_data=f"tf:{tf_code}:{market_name}")],
        [InlineKeyboardButton("🔥 أفضل الأسواق للتداول الآن", callback_data="scan_best")],
        [InlineKeyboardButton("📊 اختيار سوق آخر", callback_data="back_to_markets")]
    ]
    reply_markup = InlineKeyboardMarkup(action_buttons)

    finished_msg = (
        "⏰ *انتهت مدة الصفقة الآن!* 🏁\n\n"
        f"🔹 *الزوج:* `{market_name}`\n"
        f"⏱ *المدة المنتهية:* `{tf_code}`\n"
        f"📢 *الصفقة السابقة:* {signal}\n\n"
        "💡 *الخطوة التالية:*\n"
        "اضغط على زر *إعادة الفحص* أو *أفضل الأسواق* لمعرفة الفرصة القادمة مباشرة!"
    )

    try:
        await bot.send_message(
            chat_id=chat_id,
            text=finished_msg,
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
    except Exception as e:
        logger.error(f"Error sending finished notification: {e}")

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة جميع الأزرار التفاعلية بدقة وموثوقية تامة وبدون أي أخطاء"""
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

        # 2. ميزة فحص أفضل الأسواق الآن (Smart Scanner)
        if data == "scan_best":
            try:
                await query.edit_message_text(
                    "🔍 *جاري مسح جميع الأسواق الحية المفتوحة بالتوازي...*\n\n"
                    "• استبعاد الأسواق المغلقة والمتذبذبة 🚫\n"
                    "• استخراج الفرص المؤكدة ذات الاتجاه الصاعد أو الهابط الصريح 🌟\n\n"
                    "_يرجى الانتظار ثوانٍ معدودة..._"
                )
            except BadRequest:
                pass

            try:
                opportunities = await asyncio.wait_for(
                    asyncio.to_thread(scan_best_markets, "1m"),
                    timeout=15.0
                )
            except Exception as e:
                logger.error(f"Scanner error: {e}")
                opportunities = []

            if not opportunities:
                no_msg = (
                    "⚠️ *تنبيه المسح الذكي:*\n\n"
                    "جميع الأسواق المفتوحة حالياً تتحرك في نطاق تذبذب عرضي خامل (ADX منخفض).\n\n"
                    "💡 *نصيحة أمان لحماية رصيدك:* تجنب الدخول الآن، واضغط على إعادة المسح بعد دقيقة أو اختر سوقاً يدوياً."
                )
                buttons = [
                    [InlineKeyboardButton("🔄 إعادة مسح الأسواق الآن", callback_data="scan_best")],
                    [InlineKeyboardButton("📊 اختيار سوق يدوياً", callback_data="back_to_markets")]
                ]
                await query.edit_message_text(no_msg, reply_markup=InlineKeyboardMarkup(buttons), parse_mode="Markdown")
                return

            # عرض أفضل الأسواق مع أزرار مباشرة تحمل اسم السوق
            msg_lines = [
                "🔥 *أفضل الأسواق المهيأة للتداول الآن (فرص مؤكدة):*\n",
                "الأزواج التالية حققت شروط الاتجاه والزخم الإيجابي بالكامل:\n"
            ]
            scanner_buttons = []
            for item in opportunities[:5]:
                msg_lines.append(
                    f"🔹 *{item['name']}*\n"
                    f"   ├ الإشارة: *{item['signal']}*\n"
                    f"   ├ القوة: `{item['strength']}`\n"
                    f"   └ قوة الاتجاه (ADX): `{item['adx']}`\n"
                )
                scanner_buttons.append([InlineKeyboardButton(f"🚀 تداول في {item['name']}", callback_data=f"market:{item['name']}")])

            scanner_buttons.append([InlineKeyboardButton("🔄 تحديث قائمة أفضل الأسواق", callback_data="scan_best")])
            scanner_buttons.append([InlineKeyboardButton("🔙 رجوع للقائمة الكاملة", callback_data="back_to_markets")])

            msg_text = "\n".join(msg_lines)
            await query.edit_message_text(msg_text, reply_markup=InlineKeyboardMarkup(scanner_buttons), parse_mode="Markdown")
            return

        # 3. اختيار السوق
        if data.startswith("market:"):
            market_name = data.split("market:", 1)[1]
            context.user_data["selected_market"] = market_name

            keyboard = []
            for tf_name, tf_code in TIMEFRAMES.items():
                keyboard.append([InlineKeyboardButton(tf_name, callback_data=f"tf:{tf_code}:{market_name}")])
            keyboard.append([InlineKeyboardButton("🔙 رجوع لقائمة الأسواق", callback_data="back_to_markets")])

            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(
                f"📊 *السوق المختار:* `{market_name}`\n\n"
                "⏱ حدد *مدة الصفقة* لبدء فحص الشموع الحية وتأكيد الإشارة:",
                reply_markup=reply_markup,
                parse_mode="Markdown"
            )
            return

        # 4. اختيار الفريم أو إعادة الفحص
        if data.startswith("tf:"):
            parts = data.split(":")
            tf_code = parts[1]
            if len(parts) >= 3:
                market_name = parts[2]
                context.user_data["selected_market"] = market_name
            else:
                market_name = context.user_data.get("selected_market", "🤖 Smarty")

            symbol = MARKETS.get(market_name, "AIQ")

            try:
                await query.edit_message_text(
                    f"⏳ *جاري سحب الشموع الحية وتحليل الزخم...*\n\n"
                    f"🔹 الزوج: `{market_name}`\n"
                    f"⏱ الفريم: `{tf_code}`\n\n"
                    "• فحص نشاط وساعات عمل السوق\n"
                    "• حساب قوة الاتجاه ومؤشرات RSI و Stochastic..."
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
                [InlineKeyboardButton("🔄 إعادة فحص نفس السوق", callback_data=f"tf:{tf_code}:{market_name}")],
                [InlineKeyboardButton("🔥 أفضل الأسواق للتداول الآن", callback_data="scan_best")],
                [InlineKeyboardButton("📊 اختيار سوق آخر", callback_data="back_to_markets")]
            ]
            reply_markup = InlineKeyboardMarkup(action_buttons)

            # حالة الخطأ أو السوق مغلق
            if result.get("status") == "error":
                await query.edit_message_text(
                    f"❌ *تنبيه:*\n{result['message']}",
                    reply_markup=reply_markup,
                    parse_mode="Markdown"
                )
                return

            # حالة التذبذب
            timing_info = result.get("timing", {})
            timing_str = timing_info.get("advice", "")

            if result.get("status") == "ranging":
                ranging_msg = (
                    "⚠️ *تنبيه: السوق في حالة تذبذب حالياً!* ⚠️\n\n"
                    f"🔹 *الزوج:* `{market_name}`\n"
                    f"⏱ *الفريم:* `{tf_code}`\n"
                    f"📉 *قوة الاتجاه (ADX):* `{result['adx']}` (خامل / ضعيف ❌)\n"
                    f"📊 *مؤشر الزخم (RSI):* `{result['rsi']}`\n\n"
                    f"⏱ *توقيت الشمعة:* {timing_str}\n\n"
                    "🚫 *القرار والتحليل:*\n"
                    f"{result['message']}\n\n"
                    "👉 *اضغط على زر (أفضل الأسواق) بالأسفل لاقتراح زوج نشط وفيه اتجاه صريح.*"
                )
                try:
                    await query.edit_message_text(ranging_msg, reply_markup=reply_markup, parse_mode="Markdown")
                except BadRequest as e:
                    if "Message is not modified" in str(e):
                        await query.answer("تم التحديث: السوق لا يزال متذبذباً.")

            # حالة وجود اتجاه وفرصة
            else:
                signal_str = result['signal']
                signal_msg = (
                    "🎯 *توصية تداول عالية الدقة - Expert Option V4.0*\n\n"
                    f"🔹 *الزوج:* `{market_name}`\n"
                    f"⏱ *مدة الصفقة:* `{tf_code}`\n"
                    f"📢 *الإشارة:* *{signal_str}*\n"
                    f"💪 *قوة الفرصة:* `{result['strength']}`\n"
                    f"📉 *مؤشر ADX:* `{result['adx']}` | 📊 *مؤشر RSI:* `{result['rsi']}`\n\n"
                    f"⏱ *توقيت الدخول الحاسم (Expert Option):*\n{timing_str}\n\n"
                    f"💡 *التوجيه الاحترافي:* {result['tip']}\n\n"
                    "⏳ _تم تشغيل مؤقت الصفقة تلقائياً، وسيرسل لك البوت تنبيهاً فور انتهائها._"
                )
                try:
                    await query.edit_message_text(signal_msg, reply_markup=reply_markup, parse_mode="Markdown")
                except BadRequest as e:
                    if "Message is not modified" in str(e):
                        await query.answer("تم التحديث: الإشارة لا تزال مستمرة.")

                # تشغيل مؤقت التنبيه بانتهاء الصفقة بشكل آمن وموثوق عبر asyncio.create_task
                if "CALL" in signal_str or "PUT" in signal_str:
                    seconds_map = {"1m": 60, "2m": 120, "5m": 300}
                    wait_seconds = seconds_map.get(tf_code, 60)
                    chat_id = query.message.chat_id

                    asyncio.create_task(
                        delayed_trade_finish(
                            bot=context.bot,
                            chat_id=chat_id,
                            market_name=market_name,
                            tf_code=tf_code,
                            signal=signal_str,
                            wait_seconds=wait_seconds
                        )
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

async def background_cache_updater():
    """تحديث دوري سريع في الخلفية لأهم الأسواق لتكون الاستجابة فورية بأقل من ثانية"""
    popular = ["EURUSD=X", "GBPUSD=X", "BTC-USD", "AIQ", "JPY=X"]
    while True:
        try:
            for sym in popular:
                await asyncio.to_thread(analyze_market, sym, "1m")
                await asyncio.sleep(1)
        except Exception:
            pass
        await asyncio.sleep(15)

async def auto_clean_shutdown():
    """إنهاء البوت بشكل نظيف بعد 330 دقيقة قبل انتهاء مهلة الـ 350 دقيقة لتجنب رسائل الخطأ من جيت هب"""
    await asyncio.sleep(330 * 60)
    logger.info("Restart cycle reached (330 mins). Clean exit code 0.")
    os._exit(0)

async def on_startup(application: Application):
    asyncio.create_task(background_cache_updater())
    asyncio.create_task(auto_clean_shutdown())

def main():
    if not BOT_TOKEN:
        print("ERROR: BOT_TOKEN is missing in config.py")
        return

    app = Application.builder().token(BOT_TOKEN).post_init(on_startup).concurrent_updates(True).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_callback))

    print("\nBot V4.0 is running successfully! Open Telegram and send /start")
    app.run_polling()

if __name__ == "__main__":
    main()
