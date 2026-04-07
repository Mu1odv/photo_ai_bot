from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton


# Button labels
BTN_SEND_PHOTO = "📸 Rasm yuboring"
BTN_SEND_VIDEO = "🎬 Video yuboring"
BTN_BALANCE = "💰 Balansim"
BTN_TOPUP = "💳 To'ldirish"
BTN_ADMIN = "👨‍💻 Admin"


def main_menu_keyboard() -> ReplyKeyboardMarkup:
    """Asosiy menyu"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=BTN_SEND_PHOTO), KeyboardButton(text=BTN_SEND_VIDEO)],
            [KeyboardButton(text=BTN_BALANCE)],
            [KeyboardButton(text=BTN_TOPUP), KeyboardButton(text=BTN_ADMIN)],
        ],
        resize_keyboard=True,
    )


def photo_options_keyboard() -> InlineKeyboardMarkup:
    """Rasm qabul qilingandan keyin tugmalar"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🎬 Video qilish", callback_data="photo_to_video")],
            [InlineKeyboardButton(text="🖼 Chiqartirish", callback_data="photo_to_print")],
        ]
    )


def print_options_keyboard() -> InlineKeyboardMarkup:
    """Chiqartirish opsiyalari"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🖼 Ramka bilan", callback_data="print_with_frame")],
            [InlineKeyboardButton(text="📧 Elektron variant", callback_data="print_digital")],
        ]
    )