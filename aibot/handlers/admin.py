from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from datetime import datetime, timedelta

from config import ADMIN_IDS
from database import *

router = Router()

class AdminStates(StatesGroup):
    waiting_broadcast = State()
    waiting_user_id = State()
    waiting_card = State()
    waiting_card_owner = State()
    waiting_channel = State()
    waiting_promo_code = State()
    waiting_promo_type = State()
    waiting_promo_days = State()
    waiting_promo_max = State()
    waiting_promo_discount = State()
    waiting_promo_expire = State()
    waiting_stars_price = State()
    waiting_premium_price = State()
    waiting_daily_limit = State()
    waiting_broadcast_text = State()

def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS

def admin_main_kb():
    kb = [
        [InlineKeyboardButton(text="📊 Statistika", callback_data="adm_stats"),
         InlineKeyboardButton(text="👥 Foydalanuvchilar", callback_data="adm_users")],
        [InlineKeyboardButton(text="💳 To'lovlar", callback_data="adm_payments"),
         InlineKeyboardButton(text="📢 Xabar yuborish", callback_data="adm_broadcast")],
        [InlineKeyboardButton(text="⚙️ Funksiyalar", callback_data="adm_features"),
         InlineKeyboardButton(text="💰 Narxlar", callback_data="adm_prices")],
        [InlineKeyboardButton(text="📣 Kanallar", callback_data="adm_channels"),
         InlineKeyboardButton(text="🎁 Promokodlar", callback_data="adm_promos")],
        [InlineKeyboardButton(text="🔧 Karta sozlash", callback_data="adm_card")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)

@router.message(Command("admin"))
async def admin_handler(message: Message):
    if not is_admin(message.from_user.id):
        return
    await message.answer("🔧 Admin panel:", reply_markup=admin_main_kb())

# ==================== STATISTICS ====================
@router.callback_query(F.data == "adm_stats")
async def admin_stats(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    stats = await get_stats()
    weekly = await get_weekly_stats()

    weekly_text = ""
    for row in weekly:
        weekly_text += f"📅 {row['date']}: {row['new_users']} yangi, {row['total_requests']} so'rov\n"

    text = f"""📊 Statistika

👥 Jami foydalanuvchilar: {stats['total']}
💎 Premium: {stats['premium']}
🚫 Bloklangan: {stats['blocked']}

📈 Bugun:
• Yangi foydalanuvchilar: {stats['today_new']}
• Faol foydalanuvchilar: {stats['active_today']}
• Jami so'rovlar: {stats['today_requests']}
• To'lovlar: {stats['today_payments']}
• Kutayotgan to'lovlar: {stats['pending_payments']}

📆 Haftalik:
{weekly_text}"""

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Ortga", callback_data="adm_main")]
    ])
    await callback.message.edit_text(text, reply_markup=kb)

# ==================== FEATURES ====================
@router.callback_query(F.data == "adm_features")
async def admin_features(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return

    features = {
        "feature_chat": "💬 AI Suhbat",
        "feature_image": "🎨 Rasm yaratish",
        "feature_search": "🔍 Internet qidirish",
        "feature_premium": "💎 Premium tizim",
        "feature_registration": "👤 Ro'yxatdan o'tish",
        "bot_active": "🤖 Bot holati",
    }

    buttons = []
    for key, name in features.items():
        val = await get_setting(key)
        status = "✅" if val == "1" else "❌"
        buttons.append([InlineKeyboardButton(
            text=f"{status} {name}",
            callback_data=f"toggle_{key}"
        )])
    buttons.append([InlineKeyboardButton(text="🔙 Ortga", callback_data="adm_main")])

    await callback.message.edit_text(
        "⚙️ Funksiyalarni boshqarish:\n(Bosib yoqing/o'chiring)",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
    )

@router.callback_query(F.data.startswith("toggle_"))
async def toggle_feature(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    key = callback.data[7:]
    current = await get_setting(key)
    new_val = "0" if current == "1" else "1"
    await set_setting(key, new_val)
    await admin_features(callback)

# ==================== PRICES ====================
@router.callback_query(F.data == "adm_prices")
async def admin_prices(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    price = await get_setting("premium_price")
    stars = await get_setting("stars_price")
    limit = await get_setting("daily_limit")
    days = await get_setting("premium_days")

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"💰 Narx: {price} so'm", callback_data="adm_set_price")],
        [InlineKeyboardButton(text=f"⭐ Stars: {stars}", callback_data="adm_set_stars")],
        [InlineKeyboardButton(text=f"📊 Kunlik limit: {limit}", callback_data="adm_set_limit")],
        [InlineKeyboardButton(text="🔙 Ortga", callback_data="adm_main")]
    ])
    await callback.message.edit_text("💰 Narxlar va limitlar:", reply_markup=kb)

@router.callback_query(F.data == "adm_set_price")
async def set_price_handler(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return
    await callback.message.edit_text("💰 Yangi premium narxni kiriting (so'mda):")
    await state.set_state(AdminStates.waiting_premium_price)

@router.message(AdminStates.waiting_premium_price)
async def save_price(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    try:
        int(message.text)
        await set_setting("premium_price", message.text)
        await message.answer(f"✅ Narx {message.text} so'mga o'zgartirildi!", reply_markup=admin_main_kb())
    except:
        await message.answer("❌ Faqat raqam kiriting!")
    await state.clear()

@router.callback_query(F.data == "adm_set_stars")
async def set_stars_handler(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return
    await callback.message.edit_text("⭐ Yangi Stars narxini kiriting:")
    await state.set_state(AdminStates.waiting_stars_price)

@router.message(AdminStates.waiting_stars_price)
async def save_stars(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    try:
        int(message.text)
        await set_setting("stars_price", message.text)
        await message.answer(f"✅ Stars narxi {message.text} ga o'zgartirildi!", reply_markup=admin_main_kb())
    except:
        await message.answer("❌ Faqat raqam kiriting!")
    await state.clear()

@router.callback_query(F.data == "adm_set_limit")
async def set_limit_handler(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return
    await callback.message.edit_text("📊 Yangi kunlik limitni kiriting:")
    await state.set_state(AdminStates.waiting_daily_limit)

@router.message(AdminStates.waiting_daily_limit)
async def save_limit(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    try:
        int(message.text)
        await set_setting("daily_limit", message.text)
        await message.answer(f"✅ Kunlik limit {message.text} ga o'zgartirildi!", reply_markup=admin_main_kb())
    except:
        await message.answer("❌ Faqat raqam kiriting!")
    await state.clear()

# ==================== CARD ====================
@router.callback_query(F.data == "adm_card")
async def admin_card(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    card = await get_setting("payment_card")
    owner = await get_setting("payment_card_owner")
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 Kartani o'zgartirish", callback_data="adm_set_card")],
        [InlineKeyboardButton(text="👤 Egasini o'zgartirish", callback_data="adm_set_owner")],
        [InlineKeyboardButton(text="🔙 Ortga", callback_data="adm_main")]
    ])
    await callback.message.edit_text(
        f"💳 Karta sozlamalari:\n\nKarta: {card or 'Kiritilmagan'}\nEgasi: {owner or 'Kiritilmagan'}",
        reply_markup=kb
    )

@router.callback_query(F.data == "adm_set_card")
async def set_card_handler(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return
    await callback.message.edit_text("💳 Karta raqamini kiriting:")
    await state.set_state(AdminStates.waiting_card)

@router.message(AdminStates.waiting_card)
async def save_card(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await set_setting("payment_card", message.text)
    await message.answer("✅ Karta saqlandi!", reply_markup=admin_main_kb())
    await state.clear()

@router.callback_query(F.data == "adm_set_owner")
async def set_owner_handler(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return
    await callback.message.edit_text("👤 Karta egasining ismini kiriting:")
    await state.set_state(AdminStates.waiting_card_owner)

@router.message(AdminStates.waiting_card_owner)
async def save_owner(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await set_setting("payment_card_owner", message.text)
    await message.answer("✅ Egasi saqlandi!", reply_markup=admin_main_kb())
    await state.clear()

# ==================== PAYMENTS ====================
@router.callback_query(F.data == "adm_payments")
async def admin_payments(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    payments = await get_pending_payments()
    if not payments:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Ortga", callback_data="adm_main")]
        ])
        await callback.message.edit_text("✅ Kutayotgan to'lovlar yo'q.", reply_markup=kb)
        return

    for p in payments:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Tasdiqlash", callback_data=f"confirm_pay_{p['id']}_{p['user_id']}"),
                InlineKeyboardButton(text="❌ Rad etish", callback_data=f"reject_pay_{p['id']}_{p['user_id']}")
            ]
        ])
        text = f"💳 To'lov #{p['id']}\n👤 {p['full_name']}\n🆔 {p['user_id']}\n💰 {p['amount']} so'm\n📅 {p['created_at'][:16]}"
        if p["proof_file_id"]:
            await callback.message.answer_photo(p["proof_file_id"], caption=text, reply_markup=kb)
        else:
            await callback.message.answer(text, reply_markup=kb)

    await callback.message.answer("🔙", reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Ortga", callback_data="adm_main")]
    ]))

@router.callback_query(F.data.startswith("confirm_pay_"))
async def confirm_pay(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    parts = callback.data.split("_")
    payment_id = int(parts[2])
    user_id = int(parts[3])
    days = int(await get_setting("premium_days"))
    await confirm_payment(payment_id)
    await set_premium(user_id, days)

    try:
        user = await get_user(user_id)
        lang = user["language"] if user else "uz"
        from locales.texts import t
        await callback.bot.send_message(user_id, t(lang, "payment_confirmed", days=days))
    except:
        pass

    await callback.answer("✅ Tasdiqlandi!")
    await callback.message.edit_caption("✅ To'lov tasdiqlandi!")

@router.callback_query(F.data.startswith("reject_pay_"))
async def reject_pay(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    parts = callback.data.split("_")
    payment_id = int(parts[2])
    user_id = int(parts[3])
    await reject_payment(payment_id)

    try:
        user = await get_user(user_id)
        lang = user["language"] if user else "uz"
        from locales.texts import t
        await callback.bot.send_message(user_id, t(lang, "payment_rejected"))
    except:
        pass

    await callback.answer("❌ Rad etildi!")
    await callback.message.edit_caption("❌ To'lov rad etildi!")

# ==================== USERS ====================
@router.callback_query(F.data == "adm_users")
async def admin_users(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔍 ID bo'yicha qidirish", callback_data="adm_find_user")],
        [InlineKeyboardButton(text="💎 Premium berish", callback_data="adm_give_premium")],
        [InlineKeyboardButton(text="🚫 Bloklash", callback_data="adm_block_user")],
        [InlineKeyboardButton(text="✅ Blokdan chiqarish", callback_data="adm_unblock_user")],
        [InlineKeyboardButton(text="🔙 Ortga", callback_data="adm_main")]
    ])
    stats = await get_stats()
    await callback.message.edit_text(
        f"👥 Foydalanuvchilar\n\nJami: {stats['total']}\nPremium: {stats['premium']}\nBloklangan: {stats['blocked']}",
        reply_markup=kb
    )

@router.callback_query(F.data == "adm_give_premium")
async def give_premium_handler(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return
    await callback.message.edit_text("💎 Premium berish uchun user ID kiriting:")
    await state.set_state(AdminStates.waiting_user_id)
    await state.update_data(action="give_premium")

@router.callback_query(F.data == "adm_block_user")
async def block_user_handler(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return
    await callback.message.edit_text("🚫 Bloklash uchun user ID kiriting:")
    await state.set_state(AdminStates.waiting_user_id)
    await state.update_data(action="block")

@router.callback_query(F.data == "adm_unblock_user")
async def unblock_user_handler(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return
    await callback.message.edit_text("✅ Blokdan chiqarish uchun user ID kiriting:")
    await state.set_state(AdminStates.waiting_user_id)
    await state.update_data(action="unblock")

@router.callback_query(F.data == "adm_find_user")
async def find_user_handler(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return
    await callback.message.edit_text("🔍 User ID kiriting:")
    await state.set_state(AdminStates.waiting_user_id)
    await state.update_data(action="find")

@router.message(AdminStates.waiting_user_id)
async def process_user_id(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    data = await state.get_data()
    action = data.get("action")
    try:
        uid = int(message.text)
        user = await get_user(uid)
        if not user:
            await message.answer("❌ Foydalanuvchi topilmadi!", reply_markup=admin_main_kb())
            await state.clear()
            return

        if action == "give_premium":
            days = int(await get_setting("premium_days"))
            await set_premium(uid, days)
            await message.answer(f"✅ {uid} ga {days} kunlik Premium berildi!", reply_markup=admin_main_kb())
        elif action == "block":
            await block_user(uid)
            await message.answer(f"🚫 {uid} bloklandi!", reply_markup=admin_main_kb())
        elif action == "unblock":
            await unblock_user(uid)
            await message.answer(f"✅ {uid} blokdan chiqarildi!", reply_markup=admin_main_kb())
        elif action == "find":
            premium_until = user["premium_until"][:10] if user["premium_until"] else "-"
            text = f"""👤 Foydalanuvchi ma'lumotlari:

🆔 ID: {user['user_id']}
👤 Ism: {user['full_name']}
📱 Username: @{user['username'] or '-'}
🌍 Til: {user['language']}
💎 Premium: {'✅' if user['is_premium'] else '❌'}
⏰ Premium tugaydi: {premium_until}
🚫 Bloklangan: {'✅' if user['is_blocked'] else '❌'}
📅 Ro'yxatdan: {user['join_date'][:10] if user['join_date'] else '-'}"""
            await message.answer(text, reply_markup=admin_main_kb())
    except ValueError:
        await message.answer("❌ Faqat raqam kiriting!", reply_markup=admin_main_kb())

    await state.clear()

# ==================== BROADCAST ====================
@router.callback_query(F.data == "adm_broadcast")
async def admin_broadcast(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📢 Hammaga", callback_data="broadcast_all")],
        [InlineKeyboardButton(text="💎 Faqat Premiumlarga", callback_data="broadcast_premium")],
        [InlineKeyboardButton(text="👤 Faqat oddiy foydalanuvchilarga", callback_data="broadcast_free")],
        [InlineKeyboardButton(text="🔙 Ortga", callback_data="adm_main")]
    ])
    await callback.message.edit_text("📢 Kimga xabar yuborish?", reply_markup=kb)

@router.callback_query(F.data.startswith("broadcast_"))
async def broadcast_target(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return
    target = callback.data.split("_")[1]
    await state.update_data(broadcast_target=target)
    await callback.message.edit_text("📝 Xabar matnini yozing:")
    await state.set_state(AdminStates.waiting_broadcast_text)

@router.message(AdminStates.waiting_broadcast_text)
async def send_broadcast(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    data = await state.get_data()
    target = data.get("broadcast_target", "all")

    if target == "all":
        users = await get_all_users()
    elif target == "premium":
        users = await get_premium_users()
    else:
        all_users = await get_all_users()
        users = [u for u in all_users if not u["is_premium"]]

    sent = 0
    failed = 0
    for user in users:
        try:
            await message.bot.send_message(user["user_id"], message.text)
            sent += 1
        except:
            failed += 1

    await message.answer(
        f"✅ Xabar yuborildi!\n📤 Yuborildi: {sent}\n❌ Xato: {failed}",
        reply_markup=admin_main_kb()
    )
    await state.clear()

# ==================== CHANNELS ====================
@router.callback_query(F.data == "adm_channels")
async def admin_channels(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    channels = await get_channels()
    require = await get_setting("require_channel")

    text = f"📣 Kanallar\n\n{'✅ Majburiy obuna YOQIQ' if require == '1' else '❌ Majburiy obuna O\'CHIQ'}\n\n"
    if channels:
        for ch in channels:
            text += f"• {ch['channel_name']} (@{ch['channel_username']}) [ID: {ch['id']}]\n"
    else:
        text += "Kanallar yo'q.\n"

    buttons = [
        [InlineKeyboardButton(text="➕ Kanal qo'shish", callback_data="adm_add_channel")],
        [InlineKeyboardButton(
            text="🔴 Majburiy obunani o'chir" if require == "1" else "🟢 Majburiy obunani yoq",
            callback_data="toggle_require_channel"
        )],
    ]
    if channels:
        buttons.append([InlineKeyboardButton(text="🗑 Kanal o'chirish", callback_data="adm_del_channel")])
    buttons.append([InlineKeyboardButton(text="🔙 Ortga", callback_data="adm_main")])

    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))

@router.callback_query(F.data == "toggle_require_channel")
async def toggle_require(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    current = await get_setting("require_channel")
    await set_setting("require_channel", "0" if current == "1" else "1")
    await admin_channels(callback)

@router.callback_query(F.data == "adm_add_channel")
async def add_channel_handler(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return
    await callback.message.edit_text(
        "📣 Kanal ma'lumotlarini kiriting:\n\nFormat: @username|Kanal nomi\nMisol: @mynewschannel|Mening Kanalim"
    )
    await state.set_state(AdminStates.waiting_channel)

@router.message(AdminStates.waiting_channel)
async def save_channel(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    try:
        parts = message.text.split("|")
        username = parts[0].strip()
        name = parts[1].strip() if len(parts) > 1 else username

        chat = await message.bot.get_chat(username)
        await add_channel(str(chat.id), username.lstrip("@"), name)
        await message.answer(f"✅ '{name}' kanali qo'shildi!", reply_markup=admin_main_kb())
    except Exception as e:
        await message.answer(f"❌ Xatolik: {str(e)}\n\nFormat: @username|Kanal nomi", reply_markup=admin_main_kb())
    await state.clear()

@router.callback_query(F.data == "adm_del_channel")
async def del_channel_handler(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return
    channels = await get_channels()
    buttons = []
    for ch in channels:
        buttons.append([InlineKeyboardButton(
            text=f"🗑 {ch['channel_name']}",
            callback_data=f"delch_{ch['id']}"
        )])
    buttons.append([InlineKeyboardButton(text="🔙 Ortga", callback_data="adm_channels")])
    await callback.message.edit_text("Qaysi kanalni o'chirish?", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))

@router.callback_query(F.data.startswith("delch_"))
async def delete_channel(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    ch_id = int(callback.data.split("_")[1])
    await remove_channel(ch_id)
    await callback.answer("✅ Kanal o'chirildi!")
    await admin_channels(callback)

# ==================== PROMOCODES ====================
@router.callback_query(F.data == "adm_promos")
async def admin_promos(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    promos = await get_promos()
    text = "🎁 Promokodlar:\n\n"
    if promos:
        for p in promos:
            status = "✅" if p["is_active"] else "❌"
            if p["type"] == "free":
                info = f"{p['days']} kun bepul"
            else:
                info = f"{p['discount']}% chegirma"
            text += f"{status} {p['code']} — {info} ({p['used_count']}/{p['max_uses']})\n"
    else:
        text += "Promokodlar yo'q."

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Bepul promokod", callback_data="adm_promo_free")],
        [InlineKeyboardButton(text="➕ Chegirma promokod", callback_data="adm_promo_discount")],
        [InlineKeyboardButton(text="🛑 Promokodni o'chirish", callback_data="adm_promo_deactivate")],
        [InlineKeyboardButton(text="🔙 Ortga", callback_data="adm_main")]
    ])
    await callback.message.edit_text(text, reply_markup=kb)

@router.callback_query(F.data.in_({"adm_promo_free", "adm_promo_discount"}))
async def create_promo_start(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return
    promo_type = "free" if callback.data == "adm_promo_free" else "discount"
    await state.update_data(promo_type=promo_type)
    await callback.message.edit_text("🎁 Promokod nomini kiriting (masalan: SALE50):")
    await state.set_state(AdminStates.waiting_promo_code)

@router.message(AdminStates.waiting_promo_code)
async def promo_code_name(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await state.update_data(promo_code=message.text.upper())
    data = await state.get_data()
    if data["promo_type"] == "free":
        await message.answer("📅 Necha kunlik Premium bersin? (masalan: 30):")
        await state.set_state(AdminStates.waiting_promo_days)
    else:
        await message.answer("💰 Chegirma foizini kiriting (masalan: 50):")
        await state.set_state(AdminStates.waiting_promo_discount)

@router.message(AdminStates.waiting_promo_days)
async def promo_days(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    try:
        int(message.text)
        await state.update_data(promo_days=int(message.text), promo_discount=0)
        await message.answer("👥 Nechta foydalanuvchi ishlatishi mumkin? (masalan: 100):")
        await state.set_state(AdminStates.waiting_promo_max)
    except:
        await message.answer("❌ Raqam kiriting!")

@router.message(AdminStates.waiting_promo_discount)
async def promo_discount(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    try:
        int(message.text)
        await state.update_data(promo_discount=int(message.text), promo_days=0)
        await message.answer("👥 Nechta foydalanuvchi ishlatishi mumkin?")
        await state.set_state(AdminStates.waiting_promo_max)
    except:
        await message.answer("❌ Raqam kiriting!")

@router.message(AdminStates.waiting_promo_max)
async def promo_max(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    try:
        int(message.text)
        await state.update_data(promo_max=int(message.text))
        await message.answer("⏰ Muddat kiriting (YYYY-MM-DD) yoki '0' (cheksiz):")
        await state.set_state(AdminStates.waiting_promo_expire)
    except:
        await message.answer("❌ Raqam kiriting!")

@router.message(AdminStates.waiting_promo_expire)
async def promo_expire(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    data = await state.get_data()
    expires = None if message.text == "0" else message.text

    await create_promo(
        code=data["promo_code"],
        promo_type=data["promo_type"],
        discount=data.get("promo_discount", 0),
        days=data.get("promo_days", 30),
        max_uses=data["promo_max"],
        expires_at=expires
    )
    await message.answer(
        f"✅ Promokod yaratildi!\n\n"
        f"📋 Kod: {data['promo_code']}\n"
        f"🔖 Turi: {data['promo_type']}\n"
        f"👥 Limit: {data['promo_max']}",
        reply_markup=admin_main_kb()
    )
    await state.clear()

@router.callback_query(F.data == "adm_promo_deactivate")
async def deactivate_promo_handler(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    promos = await get_promos()
    active = [p for p in promos if p["is_active"]]
    if not active:
        await callback.answer("Faol promokodlar yo'q!", show_alert=True)
        return
    buttons = []
    for p in active:
        buttons.append([InlineKeyboardButton(text=f"🛑 {p['code']}", callback_data=f"deact_{p['id']}")])
    buttons.append([InlineKeyboardButton(text="🔙 Ortga", callback_data="adm_promos")])
    await callback.message.edit_text("Qaysi promokodni o'chirish?", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))

@router.callback_query(F.data.startswith("deact_"))
async def deactivate_promo(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    promo_id = int(callback.data.split("_")[1])
    await deactivate_promo(promo_id)
    await callback.answer("✅ Promokod o'chirildi!")
    await admin_promos(callback)

@router.callback_query(F.data == "adm_main")
async def adm_main_handler(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    await callback.message.edit_text("🔧 Admin panel:", reply_markup=admin_main_kb())
