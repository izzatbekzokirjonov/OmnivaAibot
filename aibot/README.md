# 🤖 AI Telegram Bot

Claude AI asosidagi ko'p funksiyali Telegram bot.

---

## ✅ Funksiyalar

- 💬 AI suhbat (Claude Haiku)
- 🎨 Rasm yaratish (DALL-E 3)
- 👤 Oddiy / 💎 Premium tizim
- 🌍 3 til: O'zbek, Rus, Ingliz
- ⭐ Telegram Stars to'lov
- 💳 Kartadan kartaga to'lov
- 📣 Majburiy kanal obunasi
- 🎁 Promokod tizimi
- ⚙️ Admin panel

---

## 🚀 Railway ga Deploy qilish

### 1-qadam: GitHub ga yuklash

1. GitHub.com ga kiring
2. "New repository" bosing
3. Nom bering (masalan: `my-ai-bot`)
4. "Create repository" bosing
5. Fayllarni yuklang:
   - Barcha fayllarni zip dan chiqaring
   - GitHub da "uploading an existing file" bosing
   - Barcha fayllarni yuklang
   - "Commit changes" bosing

### 2-qadam: Railway ga ulash

1. [railway.app](https://railway.app) ga kiring
2. GitHub bilan ro'yxatdan o'ting
3. "New Project" bosing
4. "Deploy from GitHub repo" bosing
5. O'z repozitoriyangizni tanlang

### 3-qadam: Environment Variables sozlash

Railway da "Variables" bo'limiga kiring va quyidagilarni kiriting:

| Kalit | Qiymat |
|-------|--------|
| `BOT_TOKEN` | Telegram bot tokeningiz |
| `ADMIN_IDS` | Sizning Telegram ID ingiz |
| `ANTHROPIC_API_KEY` | Anthropic API kalitingiz |
| `OPENAI_API_KEY` | OpenAI API kalitingiz |

### 4-qadam: Deploy

Railway avtomatik deploy qiladi. "Deployments" bo'limida jarayonni kuzating.

---

## ⚙️ Admin panel buyruqlari

Telegramda botga `/admin` yozing.

### Funksiyalar:
- ✅/❌ AI Suhbat — yoqish/o'chirish
- ✅/❌ Rasm yaratish — yoqish/o'chirish
- ✅/❌ Premium tizim — yoqish/o'chirish
- ✅/❌ Bot holati — to'liq to'xtatish

### Narxlar:
- Premium narxini o'zgartirish
- Telegram Stars narxini o'zgartirish
- Kunlik limitni o'zgartirish

### Kanallar:
- Kanal qo'shish: `@username|Kanal nomi`
- Majburiy obunani yoqish/o'chirish

### Promokodlar:
- **Bepul**: foydalanuvchiga N kunlik premium beradi
- **Chegirma**: narxdan % chegirma

---

## 💳 Karta sozlash

1. Admin panelda "🔧 Karta sozlash" bosing
2. Karta raqamingizni kiriting
3. Karta egasining ismini kiriting

Foydalanuvchi to'lov chekini yuborganda sizga bildirishnoma keladi va bir tugma bilan tasdiqlaysiz.

---

## 📁 Fayl tuzilmasi

```
aibot/
├── bot.py              # Asosiy fayl
├── config.py           # Sozlamalar
├── database.py         # Ma'lumotlar bazasi
├── requirements.txt    # Kutubxonalar
├── Procfile            # Railway uchun
├── .env.example        # ENV namunasi
├── handlers/
│   ├── user.py         # Foydalanuvchi handlerlari
│   └── admin.py        # Admin handlerlari
└── locales/
    └── texts.py        # 3 tildagi matnlar
```

---

## 🆘 Muammo bo'lsa

1. Railway "Logs" bo'limini tekshiring
2. Environment variables to'g'ri kiritilganini tekshiring
3. Bot token yangi ekanligini tekshiring
