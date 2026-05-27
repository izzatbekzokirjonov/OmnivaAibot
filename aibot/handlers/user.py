from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, LabeledPrice, PreCheckoutQuery
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import anthropic
import openai
from datetime import datetime, timedelta

from config import ANTHROPIC_API_KEY, OPENAI_API_KEY, CLAUDE_MODEL
from database import *
from locales.texts import t

router = Router()

# Start cooldown
start_cooldown = {}

class UserStates(StatesGroup):
    waiting_promo = State()
    waiting_image = State()
    waiting_card_proof = State()

def main_keyboard(lang: str, is_premium: bool = False):
    kb = [
        [InlineKeyboardButton(text=t(lang, "btn_chat"), callback_data="chat_mode"),
         InlineKeyboardButton(text=t(lang, "btn_image"), callback_data="image_mode")],
        [InlineKeyboardButton(text=t(lang, "btn_profile"), callback_data="profile"),
         InlineKeyboardButton(text=t(lang, "btn_premium"), callback_data="premium")],
        [InlineKeyboardButton(text=t(lang, "btn_promo"), callback_data="promo"),
         InlineKeyboardButton(text=t(lang, "btn_settings"), callback_data="settings")],
        [InlineKeyboardButton(text=t(lang, "btn_help"), callback_data="help")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)

def lang_keyboard():
    kb = [
        [InlineKeyboardButton(text="🇺🇿 O'zbek", callback_data="lang_uz")],
        [InlineKeyboardButton(text="🇷🇺 Русский", callback_data="lang_ru")],
        [InlineKeyboardButton(text="🇬🇧 English", callback_data="lang_en")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)

async def check_subscription(bot, user_id: int) -> bool:
    require = await get_setting("require_channel")
    if require != "1":
        return True
    channels = await get_channels()
    if not channels:
        return True
    for ch in channels:
        try:
            member = await bot.get_chat_member(ch["channel_id"], user_id)
            if member.status in ["left", "kicked", "banned"]:
                return False
        except:
            pass
    return True

async def subscription_keyboard(lang: str, channels, bot):
    buttons = []
    for ch in channels:
        try:
            invite = await bot.export_chat_invite_link(ch["channel_id"])
            buttons.append([InlineKeyboardButton(
                text=t(lang, "subscribe_btn", name=ch["channel_name"]),
                url=invite
            )])
        except:
            buttons.append([InlineKeyboardButton(
                text=t(lang, "subscribe_btn", name=ch["channel_name"]),
                url=f"https://t.me/{ch['channel_username'].lstrip('@')}"
            )])
    buttons.append([InlineKeyboardButton(text=t(lang, "check_subscribe"), callback_data="check_sub")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

@router.message(CommandStart())
async def start_handler(message: Message, state: FSMContext):
    await state.clear()

    # Cooldown tekshirish
    user_id = message.from_user.id
    now = datetime.now()
    if user_id in start_cooldown:
        diff = (now - start_cooldown[user_id]).total_seconds()
        if diff < 5:
            return
    start_cooldown[user_id] = now

    bot_active = await get_setting("bot_active")
    if bot_active != "1":
        await message.answer("🔴 Bot hozircha ishlamayapti.")
        return

    user = await get_user(user_id)
    if not user:
        reg_enabled = await get_setting("feature_registration")
        if reg_enabled != "1":
            await message.answer("❌ Yangi ro'yxatdan o'tish hozircha yopilgan.")
            return
        await message.answer(t("uz", "choose_lang"), reply_markup=lang_keyboard())
        return

    lang = user["language"]
    if user["is_blocked"]:
        await message.answer(t(lang, "blocked"))
        return

    subscribed = await check_subscription(message.bot, user_id)
    if not subscribed:
        channels = await get_channels()
        kb = await subscription_keyboard(lang, channels, message.bot)
        ch_text = "\n".join([f"• {ch['channel_name']}" for ch in channels])
        await message.answer(t(lang, "subscribe_required", channels=ch_text), reply_markup=kb)
        return

    await message.answer(
        t(lang, "welcome", name=message.from_user.first_name),
        reply_markup=main_keyboard(lang, bool(user["is_premium"]))
    )

@router.callback_query(F.data.startswith("lang_"))
async def lang_selected(callback: CallbackQuery):
    lang = callback.data.split("_")[1]
    user = await get_user(callback.from_user.id)
    if not user:
        await create_user(
            callback.from_user.id,
            callback.from_user.username or "",
            callback.from_user.full_name,
            lang
        )
    else:
        await update_user_language(callback.from_user.id, lang)

    await callback.message.edit_text(
        t(lang, "welcome", name=callback.from_user.first_name),
        reply_markup=main_keyboard(lang)
    )

@router.callback_query(F.data == "check_sub")
async def check_sub_handler(callback: CallbackQuery):
    user = await get_user(callback.from_user.id)
    lang = user["language"] if user else "uz"
    subscribed = await check_subscription(callback.bot, callback.from_user.id)
    if subscribed:
        await callback.message.edit_text(
            t(lang, "welcome", name=callback.from_user.first_name),
            reply_markup=main_keyboard(lang)
        )
    else:
        await callback.answer(t(lang, "not_subscribed"), show_alert=True)

@router.callback_query(F.data == "profile")
async def profile_handler(callback: CallbackQuery):
    user = await get_user(callback.from_user.id)
    lang = user["language"]
    daily_limit = await get_setting("daily_limit")
    daily_count = await get_daily_count(callback.from_user.id)

    premium_status = t(lang, "premium_status_premium") if user["is_premium"] else t(lang, "premium_status_free")
    premium_until = ""
    if user["is_premium"] and user["premium_until"]:
        dt = user["premium_until"][:10]
        premium_until = t(lang, "premium_until", date=dt)

    lang_names = {"uz": "O'zbek 🇺🇿", "ru": "Русский 🇷🇺", "en": "English 🇬🇧"}
    join = user["join_date"][:10] if user["join_date"] else "-"

    text = t(lang, "profile_text",
             user_id=callback.from_user.id,
             name=callback.from_user.full_name,
             language=lang_names.get(lang, lang),
             premium_status=premium_status,
             premium_until=premium_until,
             daily_count=daily_count,
             daily_limit=daily_limit,
             join_date=join)

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t(lang, "back"), callback_data="main_menu")]
    ])
    await callback.message.edit_text(text, reply_markup=kb)

@router.callback_query(F.data == "main_menu")
async def main_menu_handler(callback: CallbackQuery):
    user = await get_user(callback.from_user.id)
    lang = user["language"] if user else "uz"
    await callback.message.edit_text(
        t(lang, "main_menu"),
        reply_markup=main_keyboard(lang, bool(user["is_premium"]) if user else False)
    )

@router.callback_query(F.data == "help")
async def help_handler(callback: CallbackQuery):
    user = await get_user(callback.from_user.id)
    lang = user["language"] if user else "uz"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t(lang, "back"), callback_data="main_menu")]
    ])
    await callback.message.edit_text(t(lang, "help_text"), reply_markup=kb)

@router.callback_query(F.data == "settings")
async def settings_handler(callback: CallbackQuery):
    user = await get_user(callback.from_user.id)
    lang = user["language"] if user else "uz"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t(lang, "btn_change_lang"), callback_data="change_lang")],
        [InlineKeyboardButton(text=t(lang, "back"), callback_data="main_menu")]
    ])
    await callback.message.edit_text(t(lang, "settings_text"), reply_markup=kb)

@router.callback_query(F.data == "change_lang")
async def change_lang_handler(callback: CallbackQuery):
    await callback.message.edit_text(t("uz", "choose_lang"), reply_markup=lang_keyboard())

@router.callback_query(F.data == "premium")
async def premium_handler(callback: CallbackQuery):
    user = await get_user(callback.from_user.id)
    lang = user["language"] if user else "uz"
    feature_premium = await get_setting("feature_premium")
    if feature_premium != "1":
        await callback.answer(t(lang, "feature_disabled"), show_alert=True)
        return

    price = await get_setting("premium_price")
    stars = await get_setting("stars_price")
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t(lang, "btn_pay_card"), callback_data="pay_card")],
        [InlineKeyboardButton(text=t(lang, "btn_pay_stars"), callback_data="pay_stars")],
        [InlineKeyboardButton(text=t(lang, "btn_promo"), callback_data="promo")],
        [InlineKeyboardButton(text=t(lang, "back"), callback_data="main_menu")]
    ])
    await callback.message.edit_text(
        t(lang, "premium_info", price=price, stars=stars),
        reply_markup=kb
    )

@router.callback_query(F.data == "pay_card")
async def pay_card_handler(callback: CallbackQuery, state: FSMContext):
    user = await get_user(callback.from_user.id)
    lang = user["language"] if user else "uz"
    price = await get_setting("premium_price")
    card = await get_setting("payment_card")
    owner = await get_setting("payment_card_owner")

    if not card:
        await callback.answer("❌ Karta raqami sozlanmagan. Admin bilan bog'laning.", show_alert=True)
        return

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t(lang, "cancel"), callback_data="premium")]
    ])
    await callback.message.edit_text(
        t(lang, "card_payment", price=price, card=card, owner=owner),
        reply_markup=kb
    )
    await state.set_state(UserStates.waiting_card_proof)

@router.message(UserStates.waiting_card_proof, F.photo)
async def card_proof_handler(message: Message, state: FSMContext):
    user = await get_user(message.from_user.id)
    lang = user["language"] if user else "uz"
    price = await get_setting("premium_price")

    file_id = message.photo[-1].file_id
    payment_id = await add_payment(message.from_user.id, price, "card", file_id)

    from config import ADMIN_IDS
    for admin_id in ADMIN_IDS:
        try:
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(text="✅ Tasdiqlash", callback_data=f"confirm_pay_{payment_id}_{message.from_user.id}"),
                    InlineKeyboardButton(text="❌ Rad etish", callback_data=f"reject_pay_{payment_id}_{message.from_user.id}")
                ]
            ])
            await message.bot.send_photo(
                admin_id,
                file_id,
                caption=f"💳 Yangi to'lov!\n\n"
                        f"👤 {message.from_user.full_name}\n"
                        f"🆔 {message.from_user.id}\n"
                        f"💰 {price} so'm\n"
                        f"📋 To'lov ID: {payment_id}",
                reply_markup=kb
            )
        except:
            pass

    await message.answer(t(lang, "payment_sent"))
    await state.clear()

@router.callback_query(F.data == "pay_stars")
async def pay_stars_handler(callback: CallbackQuery):
    user = await get_user(callback.from_user.id)
    lang = user["language"] if user else "uz"
    stars = int(await get_setting("stars_price"))
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text=t(lang, "btn_pay_stars_confirm", stars=stars),
            callback_data=f"stars_invoice_{stars}"
        )],
        [InlineKeyboardButton(text=t(lang, "back"), callback_data="premium")]
    ])
    await callback.message.edit_text(
        t(lang, "stars_payment", stars=stars),
        reply_markup=kb
    )

@router.callback_query(F.data.startswith("stars_invoice_"))
async def stars_invoice_handler(callback: CallbackQuery):
    stars = int(callback.data.split("_")[2])
    await callback.message.answer_invoice(
        title="💎 Premium obuna",
        description=f"{stars} Telegram Stars evaziga 1 oylik Premium",
        payload=f"premium_{callback.from_user.id}",
        currency="XTR",
        prices=[LabeledPrice(label="Premium", amount=stars)]
    )

@router.pre_checkout_query()
async def pre_checkout(pre_checkout_query: PreCheckoutQuery):
    await pre_checkout_query.answer(ok=True)

@router.message(F.successful_payment)
async def successful_payment_handler(message: Message):
    user = await get_user(message.from_user.id)
    lang = user["language"] if user else "uz"
    days = int(await get_setting("premium_days"))
    await set_premium(message.from_user.id, days)
    stars = message.successful_payment.total_amount
    await add_payment(message.from_user.id, str(stars), "stars")

    from config import ADMIN_IDS
    for admin_id in ADMIN_IDS:
        try:
            await message.bot.send_message(
                admin_id,
                f"⭐ Stars to'lov!\n👤 {message.from_user.full_name}\n🆔 {message.from_user.id}\n⭐ {stars} Stars"
            )
        except:
            pass

    await message.answer(t(lang, "payment_confirmed", days=days))

@router.callback_query(F.data == "promo")
async def promo_handler(callback: CallbackQuery, state: FSMContext):
    user = await get_user(callback.from_user.id)
    lang = user["language"] if user else "uz"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t(lang, "cancel"), callback_data="main_menu")]
    ])
    await callback.message.edit_text(t(lang, "promo_enter"), reply_markup=kb)
    await state.set_state(UserStates.waiting_promo)

@router.message(UserStates.waiting_promo)
async def promo_code_handler(message: Message, state: FSMContext):
    user = await get_user(message.from_user.id)
    lang = user["language"] if user else "uz"
    promo, status = await use_promo(message.from_user.id, message.text.strip())

    if status == "not_found":
        await message.answer(t(lang, "promo_not_found"))
    elif status == "expired":
        await message.answer(t(lang, "promo_expired"))
    elif status == "limit":
        await message.answer(t(lang, "promo_limit"))
    elif status == "already_used":
        await message.answer(t(lang, "promo_already_used"))
    elif status == "ok":
        if promo["type"] == "free":
            await set_premium(message.from_user.id, promo["days"])
            await message.answer(t(lang, "promo_free_success", days=promo["days"]))
        else:
            await message.answer(t(lang, "promo_discount_success", discount=promo["discount"]))

    await state.clear()
    await message.answer(t(lang, "main_menu"), reply_markup=main_keyboard(lang))

@router.callback_query(F.data == "chat_mode")
async def chat_mode_handler(callback: CallbackQuery):
    user = await get_user(callback.from_user.id)
    lang = user["language"] if user else "uz"
    feature_chat = await get_setting("feature_chat")
    if feature_chat != "1":
        await callback.answer(t(lang, "feature_disabled"), show_alert=True)
        return
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t(lang, "back"), callback_data="main_menu")]
    ])
    hints = {
        "uz": "💬 Savolingizni yozing:",
        "ru": "💬 Напишите ваш вопрос:",
        "en": "💬 Write your question:"
    }
    await callback.message.edit_text(hints.get(lang, hints["uz"]), reply_markup=kb)

@router.callback_query(F.data == "image_mode")
async def image_mode_handler(callback: CallbackQuery, state: FSMContext):
    user = await get_user(callback.from_user.id)
    lang = user["language"] if user else "uz"

    feature_image = await get_setting("feature_image")
    if feature_image != "1":
        await callback.answer(t(lang, "image_disabled"), show_alert=True)
        return

    if not user["is_premium"]:
        await callback.answer(t(lang, "btn_premium"), show_alert=True)
        return

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t(lang, "cancel"), callback_data="main_menu")]
    ])
    await callback.message.edit_text(t(lang, "image_prompt"), reply_markup=kb)
    await state.set_state(UserStates.waiting_image)

@router.message(UserStates.waiting_image)
async def image_generate_handler(message: Message, state: FSMContext):
    user = await get_user(message.from_user.id)
    lang = user["language"] if user else "uz"

    thinking_msg = await message.answer(t(lang, "image_generating"))
    try:
        client = openai.AsyncOpenAI(api_key=OPENAI_API_KEY)
        response = await client.images.generate(
            model="dall-e-3",
            prompt=message.text,
            size="1024x1024",
            quality="standard",
            n=1
        )
        image_url = response.data[0].url
        await thinking_msg.delete()
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=t(lang, "back"), callback_data="main_menu")]
        ])
        await message.answer_photo(image_url, reply_markup=kb)
    except Exception as e:
        await thinking_msg.delete()
        await message.answer(t(lang, "image_error"))

    await state.clear()

@router.message(F.text & ~F.text.startswith("/"))
async def message_handler(message: Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state:
        return

    bot_active = await get_setting("bot_active")
    if bot_active != "1":
        await message.answer(t("uz", "bot_disabled"))
        return

    user = await get_user(message.from_user.id)
    if not user:
        await message.answer("/start bosing")
        return

    lang = user["language"]

    if user["is_blocked"]:
        await message.answer(t(lang, "blocked"))
        return

    subscribed = await check_subscription(message.bot, message.from_user.id)
    if not subscribed:
        channels = await get_channels()
        kb = await subscription_keyboard(lang, channels, message.bot)
        ch_text = "\n".join([f"• {ch['channel_name']}" for ch in channels])
        await message.answer(t(lang, "subscribe_required", channels=ch_text), reply_markup=kb)
        return

    feature_chat = await get_setting("feature_chat")
    if feature_chat != "1":
        await message.answer(t(lang, "feature_disabled"))
        return

    if not user["is_premium"]:
        daily_limit = int(await get_setting("daily_limit"))
        daily_count = await get_daily_count(message.from_user.id)
        if daily_count >= daily_limit:
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text=t(lang, "btn_premium"), callback_data="premium")]
            ])
            await message.answer(t(lang, "limit_reached", limit=daily_limit), reply_markup=kb)
            return

    thinking_msg = await message.answer(t(lang, "thinking"))

    try:
        client = anthropic.AsyncAnthropic(api_key=ANTHROPIC_API_KEY)
        response = await client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=2048,
            messages=[{"role": "user", "content": message.text}]
        )
        answer = response.content[0].text
        await thinking_msg.delete()
        await increment_daily_count(message.from_user.id)

        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=t(lang, "back"), callback_data="main_menu")]
        ])

        if len(answer) > 4000:
            parts = [answer[i:i+4000] for i in range(0, len(answer), 4000)]
            for i, part in enumerate(parts):
                if i == len(parts) - 1:
                    await message.answer(part, reply_markup=kb, parse_mode=None)
                else:
                    await message.answer(part, parse_mode=None)
        else:
            await message.answer(answer, reply_markup=kb, parse_mode=None)

    except Exception as e:
        await thinking_msg.delete()
        await message.answer(t(lang, "error"))
