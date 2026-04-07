#!/usr/bin/env python3
"""Test all bot components"""

from handlers import user, admin
from keyboards import main_menu_keyboard, photo_options_keyboard
from database import db

print("=" * 50)
print("BOT COMPONENT TEST")
print("=" * 50)

# Test 1: Keyboards
print("\n1️⃣ KEYBOARDS TEST:")
kb = main_menu_keyboard()
print(f"   ✅ Main menu: {len(kb.keyboard)} qators")
for i, row in enumerate(kb.keyboard):
    texts = [btn.text for btn in row]
    print(f"      Row {i}: {texts}")

photo_kb = photo_options_keyboard()
print(f"   ✅ Photo options: {len(photo_kb.inline_keyboard)} tugma")
for row in photo_kb.inline_keyboard:
    texts = [btn.text for btn in row]
    print(f"      {texts}")

# Test 2: Database
print("\n2️⃣ DATABASE TEST:")
db.add_user(987654, 'testuser', 'Test Foydalanuvchi')
print(f"   ✅ User added")

balance = db.get_balance(987654)
print(f"   ✅ Balance (before): {balance}")

new_balance = db.add_balance(987654, 250)
print(f"   ✅ Balance (after add 250): {new_balance}")

new_balance = db.add_balance(987654, -100)
print(f"   ✅ Balance (after subtract 100): {new_balance}")

# Test 3: Config
print("\n3️⃣ CONFIG TEST:")
from config import ADMIN_IDS, DATABASE_PATH, BOT_TOKEN
print(f"   ✅ ADMIN_IDS: {ADMIN_IDS}")
print(f"   ✅ DATABASE_PATH: {DATABASE_PATH}")
print(f"   ✅ BOT_TOKEN: {'***' if BOT_TOKEN else 'Not set'}")

print("\n" + "=" * 50)
print("✅ BARCHA TESTLER MUVAFFAQIYATLI!")
print("=" * 50)
