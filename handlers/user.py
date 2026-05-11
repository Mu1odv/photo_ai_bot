from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InputMediaPhoto, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import logging
import asyncio
import json
from datetime import date, timedelta

from config import ADMIN_IDS, PHOTO_COST, VIDEO_COST, TEST_MODE
from keyboards import (main_menu_keyboard, photo_options_keyboard, print_options_keyboard,
                       BTN_SEND_PHOTO, BTN_SEND_VIDEO, BTN_BALANCE, BTN_TOPUP, BTN_ADMIN)
from database import db
from handlers.ai_service import enhance_image_with_ai, build_telegram_file_url

logger = logging.getLogger(__name__)
router = Router()

ADMIN_ID = ADMIN_IDS[0] if ADMIN_IDS else 0


async def _send_media_group_with_caption(bot: Bot, chat_id: int, photos, caption: str):
    if not photos:
        return
    if len(photos) == 1:
        await bot.send_photo(chat_id=chat_id, photo=photos[0], caption=caption)
        return

    media_group = [InputMediaPhoto(media=pid) for pid in photos]
    media_group[0].caption = caption
    await bot.send_media_group(chat_id=chat_id, media=media_group)


# FSM States
class UserStates(StatesGroup):
    waiting_for_photo = State()
    waiting_for_video = State()
    waiting_for_print_option = State()
    waiting_for_delivery_date = State()
    waiting_for_delivery_phone = State()
    waiting_for_delivery_address = State()
    # accumulating_photos = State()  # reserved for future album logic


def _build_delivery_calendar(min_date: date, days: int = 14) -> InlineKeyboardMarkup:
    buttons = []
    current = min_date
    for _ in range(days):
        label = current.strftime("%d %b")
        buttons.append(
            InlineKeyboardButton(
                text=label,
                callback_data=f"delivery_date:{current.isoformat()}"
            )
        )
        current += timedelta(days=1)

    rows = [buttons[i:i + 7] for i in range(0, len(buttons), 7)]
    rows.append([InlineKeyboardButton(text="Bekor qilish", callback_data="delivery_cancel")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


# ==================== START ====================
@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext, bot: Bot):
    """Start command handler"""
    await state.clear()
    
    user_id = message.from_user.id
    username = message.from_user.username
    full_name = message.from_user.full_name or "Foydalanuvchi"
    
    # Database'ga foydalanuvchini qo'shish yoki yangilash
    db.add_user(user_id, username, full_name)
    
    welcome_text = f"""<b>{full_name}</b>, xush kelibsiz! 🎉

Sizda eski, xira rasmlar bormi? Yoki ulardan ajoyib video xohlaysizmi?

🪄 <b>Men bularning barchasini hal qilaman:</b>

<b>Qanday ishlatish:</b>
1️⃣ Rasm yuboring (eski yoki yangi)
2️⃣ Men uni ishlab beraman
3️⃣ Natijadan bahramand bo'ling!

🎯 <b>Tez start:</b> /yangilash
📚 <b>Batafsil:</b> /help

Keling, birga go'zal rasmlar yarataylik! 💫"""
    
    await message.answer(welcome_text, reply_markup=main_menu_keyboard(), parse_mode="HTML")


# ==================== 📸 RASM YUBORISH ====================
@router.message(F.text == BTN_SEND_PHOTO)
async def ask_for_photo(message: Message, state: FSMContext):
    """User clicked 'Send Photo' button"""
    await state.set_state(UserStates.waiting_for_photo)
    await message.answer(
        f"📸 Marhamat, rasmingizni yuboring! (Narxi: {PHOTO_COST} ball)",
        reply_markup=None
    )


@router.message(Command("help"))
async def cmd_help(message: Message):
    """Help command handler"""
    await message.answer(
        "📚 Yordam menyusi\n\n"
        "/start - Asosiy menyuga qaytish\n"
        "/yangilash - Botni yangilash / qayta ishga tushirish\n"
        "📸 Rasm yuboring - rasmni ishlash uchun yuboring\n"
        "🎬 Video yuboring - video ishlash uchun yuboring\n"
        "💰 Balansim - balansni ko'rish\n"
        "💳 To'ldirish - balans to'ldirish bo'yicha ma'lumot\n"
        "👨‍💻 Admin - admin bilan bog'lanish\n\n"
        "Agar tugmalar ishlamasa, /start ni bosing va qayta urinib ko'ring."
    )


@router.message(Command("yangilash"))
async def cmd_refresh(message: Message, state: FSMContext):
    """Refresh command alias"""
    await state.clear()
    await message.answer("✅ Bot qayta ishga tushirildi. Asosiy menyuga qaytish uchun /start ni bosing.")


# A dictionary to store user's photos and their process tasks for album effect
ALBUM_ACCUMULATOR = {}

@router.message(UserStates.waiting_for_photo, F.photo)
async def handle_photo(message: Message, state: FSMContext, bot: Bot):
    """Handle photo from user with accumulator logic"""
    if not message.photo:
        await message.answer("❌ Iltimos, rasm yuboring!")
        return
    
    user_id = message.from_user.id
    photo_file_id = message.photo[-1].file_id
    
    if user_id not in ALBUM_ACCUMULATOR:
        ALBUM_ACCUMULATOR[user_id] = {
            "photos": [],
            "task": None
        }
    
    ALBUM_ACCUMULATOR[user_id]["photos"].append(photo_file_id)
    
    # Bir nechta rasm kelganda avvalgi kutishni to'xtatamiz
    if ALBUM_ACCUMULATOR[user_id]["task"]:
        ALBUM_ACCUMULATOR[user_id]["task"].cancel()
        
    task = asyncio.create_task(process_photos_after_delay(message, state, bot, user_id))
    ALBUM_ACCUMULATOR[user_id]["task"] = task

async def process_photos_after_delay(message: Message, state: FSMContext, bot: Bot, user_id: int):
    """Process accumulated photos after delay"""
    try:
        await asyncio.sleep(1)  # 1 soniya kutish

        cache = ALBUM_ACCUMULATOR.pop(user_id, None)
        if not cache or not cache["photos"]:
            return

        photos = cache["photos"]

        # Rasmlarni holatda saqlaymiz
        await state.update_data(photos=photos, user_id=user_id)

        # Foydalanuvchiga javob beramiz
        await bot.send_message(
            chat_id=message.chat.id,
            text=f"📸 {len(photos)} ta rasm qabul qilindi. Nima qilamiz?",
            reply_markup=photo_options_keyboard()
        )
    except asyncio.CancelledError:
        # Agar yangi rasm kelib qolsa, bu task bekor qilinadi
        return


# ==================== 🎬 RASM -> VIDEO ====================
@router.callback_query(F.data == "photo_to_video")
async def photo_to_video(callback: CallbackQuery, state: FSMContext, bot: Bot):
    """Convert photo to video"""
    data = await state.get_data()
    photos = data.get("photos", [])
    user_id = callback.from_user.id
    username = callback.from_user.username or "noma'lum"
    full_name = callback.from_user.full_name or "Foydalanuvchi"

    admin_username = (await bot.get_me()).username

    # Ballarni tekshirish (rasm uchun konfiguratsiyadan olinadi)
    current_balance = db.get_balance(user_id)
    
    if current_balance < VIDEO_COST:
        await callback.message.answer(
            f"❌ Balans yetarli emas!\n\n"
            f"💰 Sizning balansingiz: {current_balance}\n"
            f"🎬 Video uchun kerak: {VIDEO_COST} bal\n\n"
            f"Admin bilan bog'laning: @{admin_username}"
        )
        await callback.answer("❌ Balans yetarli emas")
        return
    
    # Ballarni kamaytirish
    new_balance = db.add_balance(user_id, -VIDEO_COST, username=username, full_name=full_name)
    
    # Buyurtmani bazaga saqlaymiz
    order_id = db.add_order(
        user_id=user_id,
        username=username,
        full_name=full_name,
        order_type="video",
        details=json.dumps({"photos": photos}),
        price=VIDEO_COST,
    )
    
    # Respond to user
    await callback.message.answer(
        f"✅ Sizning rasmlaringiz qabul qilindi, tez orada video tayyor bo'ladi!\n"
        f"💰 Balans: {new_balance} (-{VIDEO_COST})"
    )
    
    # Notify admin with media group (album)
    if ADMIN_ID:
        username_text = f"@{username}" if username != "noma'lum" else "Mavjud emas"
        admin_message = (
            f"🎬 Video qilish uchun buyurtma #{order_id}\n\n"
            f"👤 Foydalanuvchi: <a href='tg://user?id={user_id}'>{full_name}</a>\n"
            f"📧 Username: {username_text}\n"
            f"🆔 User ID: <code>{user_id}</code>\n"
            f"📋 Xizmat: Video yaratish\n"
            f"📸 Rasmlar soni: {len(photos)}\n"
            f"💰 Balans kamaydi: {current_balance} → {new_balance} (-{VIDEO_COST})"
        )
        
        if photos:
            for i in range(0, len(photos), 10):
                chunk = photos[i:i + 10]
                media_group = [InputMediaPhoto(media=pid) for pid in chunk]
                if i == 0:
                    media_group[0].caption = admin_message
                await bot.send_media_group(chat_id=ADMIN_ID, media=media_group)
        else:
            await bot.send_message(chat_id=ADMIN_ID, text=admin_message)
    
    await callback.answer("✅ Buyurtma qabul qilindi!")
    await state.clear()


# ==================== ✨ RASMNI YANGILASH ====================
@router.callback_query(F.data == "photo_enhance")
async def photo_enhance(callback: CallbackQuery, state: FSMContext, bot: Bot):
    """Enhance photo"""
    data = await state.get_data()
    photos = data.get("photos", [])
    user_id = callback.from_user.id
    username = callback.from_user.username or "noma'lum"
    full_name = callback.from_user.full_name or "Foydalanuvchi"

    if not photos:
        await callback.message.answer("❌ Rasm topilmadi. Iltimos, qayta yuboring.")
        await callback.answer("❌ Rasm topilmadi")
        return

    current_balance = db.get_balance(user_id)
    admin_username = (await bot.get_me()).username
    if current_balance < PHOTO_COST:
        await callback.message.answer(
            f"❌ Balans yetarli emas!\n\n"
            f"💰 Sizning balansingiz: {current_balance}\n"
            f"✨ Yangilash uchun kerak: {PHOTO_COST} bal\n\n"
            f"Admin bilan bog'laning: @{admin_username}"
        )
        await callback.answer("❌ Balans yetarli emas")
        return

    new_balance = db.add_balance(user_id, -PHOTO_COST, username=username, full_name=full_name)

    order_id = db.add_order(
        user_id=user_id,
        username=username,
        full_name=full_name,
        order_type="enhance",
        details=json.dumps({"photos": photos}),
        price=PHOTO_COST,
    )

    caption = "Test natija" if TEST_MODE else "Natija"
    processed_outputs = []
    for photo_id in photos:
        try:
            if TEST_MODE:
                processed_outputs.append(photo_id)
                continue

            file_url = await build_telegram_file_url(bot, photo_id)
            output_url = await enhance_image_with_ai(
                file_url,
                prompt="restore old photo, improve clarity and colors",
                test_mode=TEST_MODE,
            )
            processed_outputs.append(output_url or photo_id)
        except Exception as e:
            logger.error(f"Enhance failed for user {user_id}: {e}")
            processed_outputs.append(photo_id)

    await _send_media_group_with_caption(bot, callback.message.chat.id, processed_outputs, caption)
    await callback.message.answer(f"💰 Balans: {new_balance} (-{PHOTO_COST})")

    if ADMIN_ID:
        username_text = f"@{username}" if username != "noma'lum" else "Mavjud emas"
        admin_message = (
            f"✨ Rasmni yangilash buyurtma #{order_id}\n\n"
            f"👤 Foydalanuvchi: <a href='tg://user?id={user_id}'>{full_name}</a>\n"
            f"📧 Username: {username_text}\n"
            f"🆔 User ID: <code>{user_id}</code>\n"
            f"📋 Xizmat: Rasmni yangilash\n"
            f"📸 Rasmlar soni: {len(photos)}\n"
            f"💰 Balans kamaydi: {current_balance} → {new_balance} (-{PHOTO_COST})"
        )
        if photos:
            for i in range(0, len(photos), 10):
                chunk = photos[i:i + 10]
                media_group = [InputMediaPhoto(media=pid) for pid in chunk]
                if i == 0:
                    media_group[0].caption = admin_message
                await bot.send_media_group(chat_id=ADMIN_ID, media=media_group)
        else:
            await bot.send_message(chat_id=ADMIN_ID, text=admin_message)

    await callback.answer("✅ Yangilash qabul qilindi!")
    await state.clear()


# ==================== 🖼 RASM -> CHIQARTIRISH ====================
@router.callback_query(F.data == "photo_to_print")
async def photo_to_print(callback: CallbackQuery, state: FSMContext):
    """Print photo - show options"""
    await state.set_state(UserStates.waiting_for_print_option)
    await callback.message.answer(
        "Chiqartirish opsiyasini tanlang:",
        reply_markup=print_options_keyboard()
    )
    await callback.answer()


# ==================== 🖼 RAMKA BILAN ====================
@router.callback_query(F.data == "print_with_frame")
async def print_with_frame(callback: CallbackQuery, state: FSMContext, bot: Bot):
    """Print with frame"""
    data = await state.get_data()
    photos = data.get("photos", [])
    user_id = callback.from_user.id
    username = callback.from_user.username or "noma'lum"
    full_name = callback.from_user.full_name or "Foydalanuvchi"

    # Ballarni tekshirish (rasm uchun konfiguratsiyadan olinadi)
    current_balance = db.get_balance(user_id)
    
    admin_username = (await bot.get_me()).username
    if current_balance < PHOTO_COST:
        await callback.message.answer(
            f"❌ Balans yetarli emas!\n\n"
            f"💰 Sizning balansingiz: {current_balance}\n"
            f"🖼 Chiqartirish uchun kerak: {PHOTO_COST} bal\n\n"
            f"Admin bilan bog'laning: @{admin_username}"
        )
        await callback.answer("❌ Balans yetarli emas")
        return
    
    # Ballarni kamaytirish
    new_balance = db.add_balance(user_id, -PHOTO_COST, username=username, full_name=full_name)
    
    order_id = db.add_order(
        user_id=user_id,
        username=username,
        full_name=full_name,
        order_type="print_frame",
        details=json.dumps({"photos": photos}),
        price=PHOTO_COST,
    )
    
    admin_username = (await bot.get_me()).username
    
    # Respond to user
    await callback.message.answer(
        f"✅ Buyurtmangiz qabul qilindi. Batafsil ma'lumot uchun admin bilan bog'laning: @{admin_username}\n"
        f"💰 Balans: {new_balance} (-{PHOTO_COST})"
    )

    digital_caption = "Test natija (elektron variant)" if TEST_MODE else "Elektron variant"
    await _send_media_group_with_caption(bot, callback.message.chat.id, photos, digital_caption)

    min_delivery_date = date.today() + timedelta(days=3)
    await state.update_data(
        delivery_order_id=order_id,
        delivery_user_id=user_id,
        delivery_username=username,
        delivery_full_name=full_name,
        delivery_order_type="print_frame",
    )
    await state.set_state(UserStates.waiting_for_delivery_date)
    await callback.message.answer(
        "🚚 Yetkazib berish sanasini tanlang (kamida 3 kun oldin):",
        reply_markup=_build_delivery_calendar(min_delivery_date)
    )
    
    # Notify admin with media group (album)
    if ADMIN_ID:
        username_text = f"@{username}" if username != "noma'lum" else "Mavjud emas"
        admin_message = (
            f"📦 Buyurtma: #{order_id}\n\n"
            f"🖼 Ramka bilan chiqartirish buyurtmasi\n\n"
            f"👤 Foydalanuvchi: <a href='tg://user?id={user_id}'>{full_name}</a>\n"
            f"📧 Username: {username_text}\n"
            f"🆔 User ID: <code>{user_id}</code>\n"
            f"📋 Xizmat: Ramka bilan print\n"
            f"📸 Rasmlar soni: {len(photos)}\n"
            f"💰 Balans kamaydi: {current_balance} → {new_balance} (-{PHOTO_COST})"
        )
        
        if photos:
            for i in range(0, len(photos), 10):
                chunk = photos[i:i + 10]
                media_group = [InputMediaPhoto(media=pid) for pid in chunk]
                if i == 0:
                    media_group[0].caption = admin_message
                await bot.send_media_group(chat_id=ADMIN_ID, media=media_group)
        else:
            await bot.send_message(chat_id=ADMIN_ID, text=admin_message)
    
    await callback.answer("✅ Buyurtma qabul qilindi!")


# ==================== 📧 ELEKTRON VARIANT ====================
@router.callback_query(F.data == "print_digital")
async def print_digital(callback: CallbackQuery, state: FSMContext, bot: Bot):
    """Print digital version"""
    data = await state.get_data()
    photos = data.get("photos", [])
    user_id = callback.from_user.id
    username = callback.from_user.username or "noma'lum"
    full_name = callback.from_user.full_name or "Foydalanuvchi"

    # Ballarni tekshirish (rasm uchun konfiguratsiyadan olinadi)
    current_balance = db.get_balance(user_id)
    
    admin_username = (await bot.get_me()).username
    if current_balance < PHOTO_COST:
        await callback.message.answer(
            f"❌ Balans yetarli emas!\n\n"
            f"💰 Sizning balansingiz: {current_balance}\n"
            f"📧 Elektron variant uchun kerak: {PHOTO_COST} bal\n\n"
            f"Admin bilan bog'laning: @{admin_username}"
        )
        await callback.answer("❌ Balans yetarli emas")
        return
    
    # Ballarni kamaytirish
    new_balance = db.add_balance(user_id, -PHOTO_COST, username=username, full_name=full_name)
    
    order_id = db.add_order(
        user_id=user_id,
        username=username,
        full_name=full_name,
        order_type="print_digital",
        details=json.dumps({"photos": photos}),
        price=PHOTO_COST,
    )
    
    admin_username = (await bot.get_me()).username
    
    # Respond to user
    await callback.message.answer(
        f"✅ Buyurtmangiz qabul qilindi. Batafsil ma'lumot uchun admin bilan bog'laning: @{admin_username}\n"
        f"💰 Balans: {new_balance} (-{PHOTO_COST})"
    )

    digital_caption = "Test natija (elektron variant)" if TEST_MODE else "Elektron variant"
    await _send_media_group_with_caption(bot, callback.message.chat.id, photos, digital_caption)
    
    # Notify admin with media group (album)
    if ADMIN_ID:
        username_text = f"@{username}" if username != "noma'lum" else "Mavjud emas"
        admin_message = (
            f"📦 Buyurtma: #{order_id}\n\n"
            f"📧 Elektron variant buyurtmasi\n\n"
            f"👤 Foydalanuvchi: <a href='tg://user?id={user_id}'>{full_name}</a>\n"
            f"📧 Username: {username_text}\n"
            f"🆔 User ID: <code>{user_id}</code>\n"
            f"📋 Xizmat: Elektron variantni yuboring\n"
            f"📸 Rasmlar soni: {len(photos)}\n"
            f"💰 Balans kamaydi: {current_balance} → {new_balance} (-{PHOTO_COST})"
        )
        
        if photos:
            for i in range(0, len(photos), 10):
                chunk = photos[i:i + 10]
                media_group = [InputMediaPhoto(media=pid) for pid in chunk]
                if i == 0:
                    media_group[0].caption = admin_message
                await bot.send_media_group(chat_id=ADMIN_ID, media=media_group)
        else:
            await bot.send_message(chat_id=ADMIN_ID, text=admin_message)
    
    await callback.answer("✅ Buyurtma qabul qilindi!")
    await state.clear()


@router.callback_query(F.data == "delivery_cancel")
async def delivery_cancel(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.answer("❌ Yetkazib berish bekor qilindi.")
    await callback.answer("Bekor qilindi")


@router.callback_query(F.data.startswith("delivery_date:"))
async def delivery_date_selected(callback: CallbackQuery, state: FSMContext, bot: Bot):
    selected = callback.data.split(":", 1)[-1]
    data = await state.get_data()
    order_id = data.get("delivery_order_id")
    user_id = data.get("delivery_user_id")
    username = data.get("delivery_username")
    full_name = data.get("delivery_full_name")
    order_type = data.get("delivery_order_type")

    if not order_id or not user_id:
        await callback.message.answer("❌ Buyurtma topilmadi. Iltimos, qayta urining.")
        await callback.answer("❌ Buyurtma topilmadi")
        await state.clear()
        return

    min_delivery_date = date.today() + timedelta(days=3)
    try:
        chosen_date = date.fromisoformat(selected)
    except ValueError:
        await callback.answer("❌ Sana noto'g'ri", show_alert=True)
        return

    if chosen_date < min_delivery_date:
        await callback.answer("❌ Sana 3 kundan keyin bo'lishi kerak", show_alert=True)
        return

    await state.update_data(delivery_date=selected)
    contact_keyboard = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📲 Telefonni ulashish", request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )
    await callback.message.answer(
        "📞 Telefon raqamingizni yuboring yoki tugma orqali ulashing (masalan: +998901234567)",
        reply_markup=contact_keyboard,
    )
    await callback.answer("✅ Sana tanlandi")
    await state.set_state(UserStates.waiting_for_delivery_phone)


@router.message(UserStates.waiting_for_delivery_phone, F.contact)
async def delivery_phone_received_contact(message: Message, state: FSMContext):
    phone = message.contact.phone_number if message.contact else ""
    phone = phone.strip()
    if len(phone) < 7:
        await message.answer("❌ Telefon raqami noto'g'ri. Qayta yuboring.", reply_markup=None)
        return

    await state.update_data(delivery_phone=phone)
    await state.set_state(UserStates.waiting_for_delivery_address)
    await message.answer("🏠 Yetkazib berish manzilini yuboring", reply_markup=None)


@router.message(UserStates.waiting_for_delivery_phone)
async def delivery_phone_received(message: Message, state: FSMContext):
    phone = (message.text or "").strip()
    if len(phone) < 7:
        await message.answer("❌ Telefon raqami noto'g'ri. Qayta yuboring.", reply_markup=None)
        return

    await state.update_data(delivery_phone=phone)
    await state.set_state(UserStates.waiting_for_delivery_address)
    await message.answer("🏠 Yetkazib berish manzilini yuboring", reply_markup=None)


@router.message(UserStates.waiting_for_delivery_address)
async def delivery_address_received(message: Message, state: FSMContext, bot: Bot):
    address = (message.text or "").strip()
    if len(address) < 5:
        await message.answer("❌ Manzil juda qisqa. Qayta yuboring.")
        return

    data = await state.get_data()
    order_id = data.get("delivery_order_id")
    user_id = data.get("delivery_user_id")
    username = data.get("delivery_username")
    full_name = data.get("delivery_full_name")
    order_type = data.get("delivery_order_type")
    delivery_date = data.get("delivery_date")
    delivery_phone = data.get("delivery_phone")

    if not order_id or not user_id:
        await message.answer("❌ Buyurtma topilmadi. Iltimos, qayta urining.")
        await state.clear()
        return

    order = db.get_order(order_id)
    details = {}
    if order and order["details"]:
        try:
            details = json.loads(order["details"])
        except Exception:
            details = {}

    details["delivery"] = {
        "date": delivery_date,
        "phone": delivery_phone,
        "address": address,
    }
    db.update_order_details(order_id, json.dumps(details))

    await message.answer("✅ Dastavka ma'lumotlari qabul qilindi")

    if ADMIN_ID:
        username_text = f"@{username}" if username and username != "noma'lum" else "Mavjud emas"
        admin_message = (
            f"🚚 Dastavka ma'lumotlari\n\n"
            f"📦 Buyurtma: #{order_id}\n"
            f"📋 Xizmat: {order_type}\n"
            f"📅 Sana: {delivery_date}\n"
            f"📞 Telefon: {delivery_phone}\n"
            f"🏠 Manzil: {address}\n\n"
            f"👤 Foydalanuvchi: <a href='tg://user?id={user_id}'>{full_name}</a>\n"
            f"📧 Username: {username_text}\n"
            f"🆔 User ID: <code>{user_id}</code>"
        )
        await bot.send_message(chat_id=ADMIN_ID, text=admin_message)

    await state.clear()


# ==================== 💰 BALANSIM ====================
@router.message(F.text == BTN_BALANCE)
async def show_balance(message: Message):
    """Show user balance"""
    user_id = message.from_user.id
    balance = db.get_balance(user_id)
    
    await message.answer(
        f"💰 Sizning balansingiz\n\n"
        f"<b>Hozirgi balans: {balance}</b>\n\n"
        f"Balans orqali xizmatlar to'lanadi.",
        parse_mode="HTML"
    )


# ==================== 💳 TO'LDIRISH ====================
@router.message(F.text == BTN_TOPUP)
async def topup(message: Message):
    """Top-up info"""
    await message.answer(
        "💳 To'ldirish\n\n"
        "Bugungi kuni bepul! Admin bilan bog'laning."
    )


# ==================== 👨‍💻 ADMIN ====================
@router.message(F.text == BTN_ADMIN)
async def contact_admin(message: Message, bot: Bot):
    """Show admin contact"""
    if ADMIN_ID:
        try:
            admin_chat = await bot.get_chat(ADMIN_ID)
            admin_username = f"@{admin_chat.username}" if admin_chat.username else f"ID: <code>{ADMIN_ID}</code>"
        except Exception:
            admin_username = f"ID: <code>{ADMIN_ID}</code>"

        await message.answer(
            f"👨‍💻 Admin bilan bog'lanish\n\n"
            f"Admin: {admin_username}",
            parse_mode="HTML"
        )
    else:
        await message.answer("👨‍💻 Admin hozircha belgilanmagan.")


# ==================== 🎬 VIDEO YUBORISH ====================
@router.message(F.text == BTN_SEND_VIDEO)
async def ask_for_video(message: Message, state: FSMContext, bot: Bot):
    """Video qabul qilish bosqichi"""
    user_id = message.from_user.id
    username = message.from_user.username or "noma'lum"
    full_name = message.from_user.full_name or "Foydalanuvchi"

    # Video uchun alohida state ishlatamiz.
    await state.set_state(UserStates.waiting_for_video)
    await message.answer(
        "🎬 Video fayl yuboring!\n\n"
        "Maksimal hajm: 1 GB"
    )

    # Adminga oldindan xabar yuboramiz.
    if ADMIN_ID:
        username_text = f"@{username}" if username != "noma'lum" else "Mavjud emas"
        admin_message = (
            f"📹 Video qilish uchun buyurtma\n\n"
            f"👤 Foydalanuvchi: <a href='tg://user?id={user_id}'>{full_name}</a>\n"
            f"📧 Username: {username_text}\n"
            f"🆔 User ID: <code>{user_id}</code>\n"
            f"📋 Xizmat: Video file"
        )
        await bot.send_message(chat_id=ADMIN_ID, text=admin_message)


@router.message(UserStates.waiting_for_video, F.video)
async def handle_video(message: Message, state: FSMContext, bot: Bot):
    """Handle video from user"""
    if not message.video:
        return  # Bu rasm uchun handler emas
    
    user_id = message.from_user.id
    username = message.from_user.username or "noma'lum"
    full_name = message.from_user.full_name or "Foydalanuvchi"
    video_file_id = message.video.file_id
    
    # Ballarni tekshirish (video uchun konfiguratsiyadan olinadi)
    current_balance = db.get_balance(user_id)
    
    admin_username = (await bot.get_me()).username
    if current_balance < VIDEO_COST:
        await message.answer(
            f"❌ Balans yetarli emas!\n\n"
            f"💰 Sizning balansingiz: {current_balance}\n"
            f"🎬 Video ishlash uchun kerak: {VIDEO_COST} bal\n\n"
            f"Admin bilan bog'laning: @{admin_username}"
        )
        return
    
    # Ballarni kamaytirish
    new_balance = db.add_balance(user_id, -VIDEO_COST, username=username, full_name=full_name)
    
    order_id = db.add_order(
        user_id=user_id,
        username=username,
        full_name=full_name,
        order_type="video_file",
        details=json.dumps({"video_file_id": video_file_id}),
        price=VIDEO_COST,
    )
    
    # Foydalanuvchiga javob
    await message.answer(
        f"✅ Video qabul qilindi! Tez orada ishlab beraman.\n"
        f"💰 Balans: {new_balance} (-{VIDEO_COST})"
    )
    
    # Admin'ga video yuborish
    if ADMIN_ID:
        username_text = f"@{username}" if username != "noma'lum" else "Mavjud emas"
        admin_caption = (
            f"📹 Video qabul qilindi (# {order_id})\n\n"
            f"👤 Foydalanuvchi: <a href='tg://user?id={user_id}'>{full_name}</a>\n"
            f"📧 Username: {username_text}\n"
            f"🆔 User ID: <code>{user_id}</code>\n"
            f"📋 Xizmat: Video ishlash\n"
            f"💰 Balans kamaydi: {current_balance} → {new_balance} (-{VIDEO_COST})"
        )
        
        try:
            await bot.send_video(
                chat_id=ADMIN_ID,
                video=video_file_id,
                caption=admin_caption,
                parse_mode="HTML"
            )
        except Exception as e:
            logger.error(f"Failed to send video to admin: {e}")
            # Fallback to text message
            await bot.send_message(chat_id=ADMIN_ID, text=admin_caption, parse_mode="HTML")
    
    await state.clear()


# ==================== UNCAUGHT HANDLER ====================
@router.message()
async def echo(message: Message):
    """Catch all unhandled messages"""
    await message.answer(
        "❌ Siz yuborgan xabar noma'lum!\n\nBotdan foydalanish uchun menyudagi tugmalardan foydalaning.",
        reply_markup=main_menu_keyboard()
    )
