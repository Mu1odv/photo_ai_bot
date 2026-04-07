from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import logging

from config import ADMIN_IDS
from keyboards import main_menu_keyboard, photo_options_keyboard, print_options_keyboard

logger = logging.getLogger(__name__)
router = Router()

ADMIN_ID = ADMIN_IDS[0] if ADMIN_IDS else 0


# FSM States
class UserStates(StatesGroup):
    waiting_for_photo = State()
    waiting_for_print_option = State()


# ==================== START ====================
@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    """Start command handler"""
    await state.clear()
    
    user_name = message.from_user.first_name or "Foydalanuvchi"
    welcome_text = f"""*{user_name}, xush kelibsiz!* 🎉

Sizda eski, xira rasmlar bormi? Yoki ulardan ajoyib video xohlaysizmi? 

🪄 *Men bularning barchasini hal qilaman:*

📸 Rasmlarni yangilash va yaxshilash
🎬 Rasmlardan video yaratish
🖼 Rasmlarni chiqarish opsiyalari

Boshlash uchun pastdagi tugmalardan birini tanlang! 👋
"""
    
    await message.answer(welcome_text, parse_mode="Markdown", reply_markup=main_menu_keyboard())


# ==================== 📸 RASM YUBORISH ====================
@router.message(F.text == "📸 Rasm yuboring")
async def ask_for_photo(message: Message, state: FSMContext):
    """User clicked 'Send Photo' button"""
    await state.set_state(UserStates.waiting_for_photo)
    await message.answer(
        "📸 Marhamat, rasmingizni yuboring! (Narxi: 10 ball)",
        reply_markup=None
    )


@router.message(UserStates.waiting_for_photo)
async def handle_photo(message: Message, state: FSMContext, bot: Bot):
    """Handle photo from user"""
    if not message.photo:
        await message.answer("❌ Iltimos, rasm yuboring!")
        return
    
    # Get the highest resolution photo
    photo_file_id = message.photo[-1].file_id
    user_id = message.from_user.id
    
    # Save photo info in state
    await state.update_data(photo_file_id=photo_file_id, user_id=user_id)
    
    # Send photo back with options
    await message.answer_photo(
        photo=photo_file_id,
        caption="Rasm qabul qilindi! Endi qanday qilmoqchisiz?",
        reply_markup=photo_options_keyboard()
    )


# ==================== 🎬 RASM -> VIDEO ====================
@router.callback_query(F.data == "photo_to_video")
async def photo_to_video(callback: CallbackQuery, state: FSMContext, bot: Bot):
    """Convert photo to video"""
    data = await state.get_data()
    photo_file_id = data.get("photo_file_id")
    user_id = callback.from_user.id
    
    # Respond to user
    await callback.message.answer(
        "✅ Sizning rasmingiz qabul qilindi, tez orada video tayyor bo'ladi!"
    )
    
    # Return photo to user
    if photo_file_id:
        await callback.message.answer_photo(photo=photo_file_id)
    
    # Notify admin
    if ADMIN_ID:
        admin_message = f"""📹 *Video qilish uchun buyurtma*

👤 Foydalanuvchi: {callback.from_user.full_name}
🆔 User ID: `{user_id}`
📸 Rasm qabul qilindi"""
        
        if photo_file_id:
            await bot.send_photo(
                chat_id=ADMIN_ID,
                photo=photo_file_id,
                caption=admin_message,
                parse_mode="Markdown"
            )
        else:
            await bot.send_message(chat_id=ADMIN_ID, text=admin_message, parse_mode="Markdown")
    
    await callback.answer("✅ Buyurtma qabul qilindi!")
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
    photo_file_id = data.get("photo_file_id")
    user_id = callback.from_user.id
    
    admin_username = (await bot.get_me()).username
    
    # Respond to user
    await callback.message.answer(
        f"✅ Buyurtmangiz qabul qilindi. Batafsil ma'lumot uchun admin bilan bog'laning: @{admin_username}"
    )
    
    # Return photo to user
    if photo_file_id:
        await callback.message.answer_photo(photo=photo_file_id)
    
    # Notify admin
    if ADMIN_ID:
        admin_message = f"""🖼 *Ramka bilan chiqartirish buyurtmasi*

👤 Foydalanuvchi: {callback.from_user.full_name}
🆔 User ID: `{user_id}`
📋 Opsiya: Ramka bilan chiqartirish"""
        
        if photo_file_id:
            await bot.send_photo(
                chat_id=ADMIN_ID,
                photo=photo_file_id,
                caption=admin_message,
                parse_mode="Markdown"
            )
        else:
            await bot.send_message(chat_id=ADMIN_ID, text=admin_message, parse_mode="Markdown")
    
    await callback.answer("✅ Buyurtma qabul qilindi!")
    await state.clear()


# ==================== 📧 ELEKTRON VARIANT ====================
@router.callback_query(F.data == "print_digital")
async def print_digital(callback: CallbackQuery, state: FSMContext, bot: Bot):
    """Print digital version"""
    data = await state.get_data()
    photo_file_id = data.get("photo_file_id")
    user_id = callback.from_user.id
    
    admin_username = (await bot.get_me()).username
    
    # Respond to user
    await callback.message.answer(
        f"✅ Buyurtmangiz qabul qilindi. Batafsil ma'lumot uchun admin bilan bog'laning: @{admin_username}"
    )
    
    # Return photo to user
    if photo_file_id:
        await callback.message.answer_photo(photo=photo_file_id)
    
    # Notify admin
    if ADMIN_ID:
        admin_message = f"""📧 *Elektron variant buyurtmasi*

👤 Foydalanuvchi: {callback.from_user.full_name}
🆔 User ID: `{user_id}`
📋 Opsiya: Elektron variantni yuboring"""
        
        if photo_file_id:
            await bot.send_photo(
                chat_id=ADMIN_ID,
                photo=photo_file_id,
                caption=admin_message,
                parse_mode="Markdown"
            )
        else:
            await bot.send_message(chat_id=ADMIN_ID, text=admin_message, parse_mode="Markdown")
    
    await callback.answer("✅ Buyurtma qabul qilindi!")
    await state.clear()


# ==================== 💰 BALANSIM ====================
@router.message(F.text == "💰 Balansim")
async def show_balance(message: Message):
    """Show user balance"""
    await message.answer(
        "💰 *Sizning hisobingiz*\n\n"
        "_Balans tizimi hozircha sozlanmoqda..._",
        parse_mode="Markdown"
    )


# ==================== 💳 TO'LDIRISH ====================
@router.message(F.text == "💳 To'ldirish")
async def topup(message: Message):
    """Top-up info"""
    await message.answer(
        "💳 *To'ldirish*\n\n"
        "_Bugungi kuni bepul! Admin bilan bog'laning._",
        parse_mode="Markdown"
    )


# ==================== 👨‍💻 ADMIN ====================
@router.message(F.text == "👨‍💻 Admin")
async def contact_admin(message: Message, bot: Bot):
    """Show admin contact"""
    admin_username = (await bot.get_me()).username
    await message.answer(
        f"👨‍💻 *Admin bilan bog'lanish*\n\n"
        f"Admin: @{admin_username}",
        parse_mode="Markdown"
    )


# ==================== 🎬 VIDEO YUBORISH ====================
@router.message(F.text == "🎬 Video yuboring")
async def ask_for_video(message: Message, state: FSMContext):
    """Video sending - coming soon"""
    await message.answer(
        "🎬 *Video yuborish*\n\n"
        "_Ushbu xizmat hozircha tayyorlanmoqda. Iloji borida admin bilan bog'laning._",
        parse_mode="Markdown"
    )


# ==================== UNCAUGHT HANDLER ====================
@router.message()
async def echo(message: Message):
    """Catch all unhandled messages"""
    await message.answer(
        "❌ Siz yuborgan xabar noma'lum!\n\nBotdan foydalanish uchun menyudagi tugmalardan foydalaning.",
        reply_markup=main_menu_keyboard()
    )
