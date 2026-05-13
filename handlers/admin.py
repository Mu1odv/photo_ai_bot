from aiogram import Router, F, Bot
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.filters import Command
from database import db
from config import ADMIN_IDS
import logging
from datetime import date, timedelta

router = Router()
ADMIN_ID = ADMIN_IDS[0] if ADMIN_IDS else None  # Asosiy admin ID
logger = logging.getLogger(__name__)


def order_type_label(order_type: str) -> str:
    return {
        "enhance": "Rasmni yangilash",
        "video": "Rasmdan video",
        "print_frame": "Ramka bilan chop etish",
        "print_digital": "Ramkasiz chop etish",
        "video_file": "Video fayl",
    }.get(order_type, order_type.replace("_", " ").title())


def _today():
    return date.today().isoformat()


def _admin_notified_label(value) -> str:
    if value is None:
        return "Noma'lum"
    return "Ha" if value else "Yo'q"


def _order_date_label(order) -> str:
    return order["order_date"] or (str(order["created_at"])[:10] if order["created_at"] else "-")


def _render_order_text(order) -> str:
    display_number = order["daily_seq"] or order["id"]
    order_date = _order_date_label(order)
    username_text = f"@{order['username']}" if order['username'] else "Mavjud emas"
    admin_notified = _admin_notified_label(order["admin_notified"])
    return (
        f"📦 <b>Buyurtma #{display_number}</b>\n"
        f"🆔 ID: <code>{order['id']}</code>\n"
        f"👤 Foydalanuvchi: <a href='tg://user?id={order['user_id']}'>{order['full_name']}</a>\n"
        f"📧 Username: {username_text}\n"
        f"📝 Xizmat: {order_type_label(order['order_type'])}\n"
        f"💰 Narx: {order['price']} ball\n"
        f"⏳ Holat: {order['status']}\n"
        f"📬 Adminga yuborildi: {admin_notified}\n"
        f"📅 Sana: {order_date}"
    )


def _build_admin_date_picker(days: int = 14) -> InlineKeyboardMarkup:
    buttons = []
    current = date.today()
    for _ in range(days):
        label = current.strftime("%d %b")
        buttons.append(
            InlineKeyboardButton(
                text=label,
                callback_data=f"admin_orders_date:{current.isoformat()}"
            )
        )
        current -= timedelta(days=1)

    rows = [buttons[i:i + 7] for i in range(0, len(buttons), 7)]
    rows.append([InlineKeyboardButton(text="Bekor qilish", callback_data="admin_orders_cancel")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def admin_menu():
    kb = [
        [KeyboardButton(text="📊 Statistika")],
        [KeyboardButton(text="📦 Buyurtmalar")],
        [KeyboardButton(text="📋 Barcha buyurtmalar")],
        [KeyboardButton(text="🔙 Asosiy menyu")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)


@router.message(Command("give"))
async def give_balance_cmd(message: Message, bot: Bot):
    """Admin tomonidan foydalanuvchiga balance berish"""
    if message.from_user.id not in ADMIN_IDS:
        logger.warning(f"Unauthorized access to /give by user {message.from_user.id}")
        await message.answer("❌ Sizga bu buyruqdan foydalanish ruxsati yo'q")
        return

    args = message.text.split()
    if len(args) != 3:
        await message.answer("Format: /give [user_id] [miqdor]\nMisol: /give 123456789 500")
        return

    try:
        user_id = int(args[1])
        amount = int(args[2])
        
        # Manfiy qiymat ham qabul qilinadi (balansni kamaytirish uchun)
        new_balance = db.add_balance(user_id, amount)
        
        if amount > 0:
            action_text = "qo'shildi"
            user_message = f"🎉 <b>Sizning balansingiz {amount} ga to'ldirildi!</b>\n💰 Hozirgi balans: <b>{new_balance}</b>"
        else:
            action_text = "kamaytirildi"
            user_message = f"💸 <b>Sizning balansingiz {abs(amount)} ga kamaytirildi!</b>\n💰 Hozirgi balans: <b>{new_balance}</b>"
        
        await message.answer(f"✅ ID {user_id} ga {abs(amount)} balance {action_text}. Yangi balans: {new_balance}")

        try:
            await bot.send_message(
                user_id, 
                user_message,
                parse_mode="HTML"
            )
        except Exception as e:
            logger.warning(f"Could not notify user {user_id}: {e}")
        
        logger.info(f"Admin {message.from_user.id} {'added' if amount > 0 else 'subtracted'} {abs(amount)} balance to user {user_id}")
    except ValueError:
        await message.answer("❌ Xato format. ID va miqdor raqam bo'lishi kerak")
    except Exception as e:
        logger.error(f"Error in give_balance_cmd: {e}")
        await message.answer(f"❌ Xato yuz berdi: {e}")


@router.message(Command("solo"))
async def check_balance_cmd(message: Message, bot: Bot):
    """Admin uchun foydalanuvchi balansini ko'rish"""
    if message.from_user.id not in ADMIN_IDS:
        logger.warning(f"Unauthorized access to /solo by user {message.from_user.id}")
        await message.answer("❌ Sizga bu buyruqdan foydalanish ruxsati yo'q")
        return

    args = message.text.split()
    if len(args) != 2:
        await message.answer("Format: /solo [user_id]\nMisol: /solo 123456789")
        return

    try:
        user_id = int(args[1])
        
        # Foydalanuvchi ma'lumotlarini olish
        user = db.get_user(user_id)
        if not user:
            await message.answer(f"❌ ID {user_id} foydalanuvchi topilmadi")
            return
        
        balance = user['balance']
        username = user['username'] or "Mavjud emas"
        full_name = user['full_name'] or "Noma'lum"
        
        response = (
            f"👤 <b>Foydalanuvchi ma'lumotlari:</b>\n\n"
            f"🆔 <b>User ID:</b> <code>{user_id}</code>\n"
            f"👤 <b>Ism:</b> {full_name}\n"
            f"📧 <b>Username:</b> @{username}\n"
            f"💰 <b>Balans:</b> {balance}\n\n"
            f"💡 <b>To'ldirish uchun:</b> /give {user_id} [miqdor]"
        )
        
        await message.answer(response, parse_mode="HTML")
        logger.info(f"Admin {message.from_user.id} checked balance for user {user_id}")
        
    except ValueError:
        await message.answer("❌ Xato format. ID raqam bo'lishi kerak")
    except Exception as e:
        logger.error(f"Error in check_balance_cmd: {e}")
        await message.answer(f"❌ Xato yuz berdi: {e}")


@router.message(Command("admin"))
async def cmd_admin(message: Message):
    if message.from_user.id in ADMIN_IDS:
        await message.answer("🔧 Admin panel", reply_markup=admin_menu())


@router.message(F.text == "📊 Statistika")
async def show_stats(message: Message):
    if message.from_user.id in ADMIN_IDS:
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as count FROM users")
        result = cursor.fetchone()
        cursor.execute("SELECT SUM(balance) as total_balance FROM users")
        balance_result = cursor.fetchone()
        conn.close()
        count = result[0] if result else 0
        total_balance = balance_result[0] if balance_result and balance_result[0] is not None else 0
        total_orders = db.get_orders_count()
        today_orders = db.get_orders_count(order_date=_today())
        pending_orders = db.get_orders_count(status="pending")
        await message.answer(
            f"👥 Jami foydalanuvchilar: {count}\n"
            f"💰 Jami balans: {total_balance} ball\n"
            f"📦 Jami buyurtmalar: {total_orders}\n"
            f"📅 Bugungi buyurtmalar: {today_orders}\n"
            f"⏳ Kutilayotgan buyurtmalar: {pending_orders}"
        )


@router.message(F.text == "📦 Buyurtmalar")
async def show_orders(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        return

    today = _today()
    orders = db.get_orders(order_date=today)
    if not orders:
        await message.answer("📦 Bugungi buyurtmalar yo'q")
        return

    total_today = db.get_orders_count(order_date=today)
    pending_today = db.get_orders_count(status="pending", order_date=today)
    await message.answer(
        f"📅 Bugungi buyurtmalar: {total_today}\n"
        f"⏳ Pending: {pending_today}"
    )

    for order in orders:
        text = _render_order_text(order)

        if order["status"] == "pending":
            buttons = [
                [InlineKeyboardButton(text="✅ Tasdiqlash", callback_data=f"order_approve_{order['id']}"),
                 InlineKeyboardButton(text="❌ Rad etish", callback_data=f"order_reject_{order['id']}")]
            ]

            await message.answer(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
        else:
            await message.answer(text, parse_mode="HTML")


@router.message(F.text == "📋 Barcha buyurtmalar")
async def show_all_orders(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        return

    await message.answer(
        "📋 Qaysi kunning buyurtmalarini ko'rmoqchisiz?",
        reply_markup=_build_admin_date_picker()
    )


@router.callback_query(F.data == "admin_orders_cancel")
async def admin_orders_cancel(callback: CallbackQuery):
    await callback.answer("Bekor qilindi")
    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass


@router.callback_query(F.data.startswith("admin_orders_date:"))
async def admin_orders_by_date(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        return

    selected = callback.data.split(":", 1)[-1]
    orders = db.get_orders(order_date=selected)

    if not orders:
        await callback.message.answer("📦 Bu kunda buyurtmalar yo'q")
        await callback.answer("Buyurtmalar yo'q")
        return

    total_orders = db.get_orders_count(order_date=selected)
    pending_orders = db.get_orders_count(status="pending", order_date=selected)
    approved_orders = db.get_orders_count(status="approved", order_date=selected)
    rejected_orders = db.get_orders_count(status="rejected", order_date=selected)

    await callback.message.answer(
        f"📅 Sana: {selected}\n"
        f"📦 Jami buyurtmalar: {total_orders}\n"
        f"⏳ Pending: {pending_orders}\n"
        f"✅ Tasdiqlangan: {approved_orders}\n"
        f"❌ Rad etilgan: {rejected_orders}"
    )

    for order in orders:
        text = _render_order_text(order)
        if order["status"] == "pending":
            buttons = [
                [InlineKeyboardButton(text="✅ Tasdiqlash", callback_data=f"order_approve_{order['id']}"),
                 InlineKeyboardButton(text="❌ Rad etish", callback_data=f"order_reject_{order['id']}")]
            ]
            await callback.message.answer(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
        else:
            await callback.message.answer(text, parse_mode="HTML")

    await callback.answer("Tayyor")


@router.callback_query(F.data.startswith("order_approve_"))
async def approve_order(callback: CallbackQuery, bot: Bot):
    if callback.from_user.id not in ADMIN_IDS:
        return

    order_id = int(callback.data.split("_")[-1])
    order = db.get_order(order_id)
    if not order:
        await callback.answer("Buyurtma topilmadi", show_alert=True)
        return

    if order["status"] != "pending":
        await callback.answer("Bu buyurtma allaqachon qayta ishlangan", show_alert=True)
        return

    db.update_order_status(order_id, "approved")
    await callback.answer("✅ Buyurtma tasdiqlandi")

    try:
        await bot.send_message(
            order["user_id"],
            f"✅ Sizning buyurtmangiz #{order_id} tasdiqlandi. Admin tez orada siz bilan bog'lanadi."
        )
    except Exception as e:
        logger.warning(f"User notification failed for approved order {order_id}: {e}")

    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass

    await callback.message.answer(f"✅ Buyurtma #{order_id} tasdiqlandi.")


@router.callback_query(F.data.startswith("order_reject_"))
async def reject_order(callback: CallbackQuery, bot: Bot):
    if callback.from_user.id not in ADMIN_IDS:
        return

    order_id = int(callback.data.split("_")[-1])
    order = db.get_order(order_id)
    if not order:
        await callback.answer("Buyurtma topilmadi", show_alert=True)
        return

    if order["status"] != "pending":
        await callback.answer("Bu buyurtma allaqachon qayta ishlangan", show_alert=True)
        return

    db.update_order_status(order_id, "rejected")
    db.add_balance(order["user_id"], order["price"], username=order["username"], full_name=order["full_name"])
    await callback.answer("❌ Buyurtma rad etildi va balans qaytarildi")

    try:
        await bot.send_message(
            order["user_id"],
            f"❌ Sizning buyurtmangiz #{order_id} rad etildi. {order['price']} ball balansingizga qaytarildi."
        )
    except Exception as e:
        logger.warning(f"User notification failed for rejected order {order_id}: {e}")

    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass

    await callback.message.answer(f"❌ Buyurtma #{order_id} rad etildi.")


@router.message(F.text == "🔙 Asosiy menyu")
async def back_home(message: Message):
    from keyboards import main_menu_keyboard
    await message.answer("Asosiy menyu", reply_markup=main_menu_keyboard())


# Pul yechish so'rovlari bo'limi hozircha o'chirilgan.
# Agar keyinchalik bu funksiyani yoqmoqchi bo'lsangiz, alohida jadval va metodlar qo'shishingiz kerak.


# Pul so'rovlari tugmalari hozircha mavjud emas.
# Agar keyinchalik bu bo'limni tiklasangiz, alohida muomala qo'shing.