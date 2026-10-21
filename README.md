# Foto otchyot sanovchi bot (aiogram 3)

Savdo agentlari do'konlarga poster yopishtirib, guruhga rasm tashlaydi.
Bot guruhda **jim turadi**: har bir rasmni 1 ta foto otchyot deb sanaydi, hisobotni esa
**shaxsiy chatda** botni guruhga qo'shgan odamga (va adminlarga) beradi:
kunlik, haftalik (dushanba–yakshanba), oylik (1-sanadan) — fakt / plan / %.

Hisobotda agent `Ism (@username)` ko'rinishida, username bo'lmasa `Ism (id 123)`.
Sanash har doim Telegram ID bo'yicha, shuning uchun username o'zgarsa ham hisob bo'linmaydi.

## 1. Sozlash
`.env` faylida:
```
BOT_TOKEN=...              # @BotFather dan
ADMIN_IDS=123456789        # hisobotlarni oladigan adminlar (ixtiyoriy; guruhga qo'shgan odam avtomatik)
DEFAULT_WEEKLY_PLAN=100    # har bir agent uchun haftalik plan
REPORT_TIME=21:00          # har kuni shu vaqtda adminlarga shaxsiy hisobot (bo'sh = o'chiq)
TIMEZONE=Asia/Tashkent
DUP_NOTIFY=1               # takror rasm tashlansa adminga darhol shaxsiy xabar
REACT_EMOJI=               # bo'sh = guruhda jim; emoji yozilsa sanalgan rasmga reaksiya qo'yadi
```

## 2. Ishga tushirish
```bash
./run.sh
```
(Mac'da doimiy ishlashi uchun pastdagi launchd bo'limiga qarang.)

## 3. Guruhga ulash
1. Botga shaxsiy chatda `/start` bosing (shunda u sizga yoza oladi).
2. Botni agentlar guruhiga qo'shing va **admin** qiling. Aks holda Telegram botga oddiy rasmlarni ko'rsatmaydi.
3. Bot sizga shaxsiy chatda "guruhga qo'shildi" deb yozadi. Endi shu yerda `/bugun`, `/hafta` yozing.

Guruhga qo'shgan odam o'sha guruhning "egasi" bo'ladi: hisobotlar unga boradi.
`ADMIN_IDS` dagi odamlar va guruh adminlari ham hisobot so'ray oladi.

## Buyruqlar (shaxsiy chatda)
| Buyruq | Vazifasi |
|--------|----------|
| `/bugun`, `/kecha` | Kim nechta rasm tashlagan |
| `/hafta` | Shu hafta (dushanba–yakshanba): fakt / plan (%) |
| `/hafta oldingi`, `/hafta 15.10.2026` | O'tgan hafta / shu sana kirgan hafta |
| `/oy` | Shu oy (1-sanadan oxirigacha): fakt / plan (%) |
| `/oy oldingi`, `/oy sentabr`, `/oy 9`, `/oy 09.2025` | Boshqa oy |
| `/hisobot 01.10.2026 15.10.2026` | Ixtiyoriy davr |
| `/guruhlar` | Bir nechta guruh bo'lsa, qaysi biri bo'yicha hisobot berishni tanlash |
| `/mening` | Agent o'z natijasini ko'radi |

## Admin buyruqlari (shaxsiy chatda)
Agent `@username` yoki Telegram ID bilan ko'rsatiladi (u guruhga kamida 1 ta rasm tashlagan bo'lishi kerak).

| Buyruq | Vazifasi |
|--------|----------|
| `/plan` | Joriy planlarni ko'rish |
| `/plan 100` | Umumiy haftalik plan |
| `/plan @username 120` | Shu agent uchun alohida plan (`0` — umumiyga qaytarish) |
| `/ism @username Muhammadillo` | Hisobotlarda shu ism chiqadi (`-` — Telegram ismiga qaytarish) |
| `/agent_off @username`, `/agent_on @username` | Agentni hisobotlardan yashirish / qaytarish |

Guruhda ham (jimgina): agent xabariga reply qilib `+ism Muhammadillo` yoki `-ism` — bot guruhga
javob yozmaydi, tasdiqni adminga shaxsiy chatda yuboradi.

## Qanday sanaydi
- Guruhdagi har bir rasm (albom ichidagi har bir rasm ham) = 1 ta otchyot. Fayl sifatida yuborilgan rasm ham.
- Bir xil rasm 2–3 marta tashlansa faqat birinchisi sanaladi. Bot rasm mazmunini solishtiradi
  (perceptual hash), shuning uchun forward, qayta yuborish yoki galereyadan qayta yuklash ham ushlanadi.
  Admin shaxsiy chatda "takror" xabarini oladi (kim, asl rasm kimniki, havolalar), hisobotda `⚠️ takror: N`.
- Takror oxirgi 90 kun ichidagi rasmlar bilan solishtiriladi (`DUP_DAYS`), chegara `DUP_THRESHOLD`.
  Rasm kesilsa yoki boshqa burchakdan olinsa yangi rasm deb sanaladi.
- Oylik plan haftalik plandan hisoblanadi: `haftalik × kunlar / 7`.
- O'chirilgan rasmlar haqida Telegram botga xabar bermaydi, ular hisobda qoladi.
- Bot o'chiq turganda tashlangan rasmlar keyingi ishga tushganda sanaladi (24 soatgacha).

## Fayllar
| Fayl | Vazifasi |
|------|----------|
| `bot.py` | Kirish nuqtasi, polling, buyruqlar menyusi |
| `config.py` | `.env` sozlamalari |
| `db.py` | SQLite baza (`data.db`) |
| `access.py` | Kim qaysi guruh hisobotini ko'ra oladi, guruh tanlash |
| `dates.py` | Sana yordamchilari (hafta, oy, Toshkent vaqti) |
| `imghash.py` | Rasm barmoq izi (takrorlarni aniqlash) |
| `reports.py` | Hisobot matnlari |
| `scheduler.py` | Har kuni adminlarga avtomatik hisobot |
| `import_history.py` | Eski tarixdagi rasmlarni import qilish |
| `handlers/photos.py` | Rasmlarni jimgina sanash, takrorni adminga xabar qilish |
| `handlers/stats.py` | Hisobot buyruqlari, guruh tanlash |
| `handlers/admin.py` | Plan va agent boshqaruvi |
| `handlers/names.py` | Agentga ism berish |
| `handlers/group.py` | Guruhga qo'shilganda egasini eslab qolish |
| `handlers/start.py` | /start, /help, /id |

## Eski rasmlarni import qilish
Bot guruhga qo'shilgunga qadar tashlangan rasmlarni Telegram botga bermaydi.
Ularni o'z akkauntingiz orqali o'qib, bazaga qo'shish uchun `import_history.py` bor.

**1-usul (tavsiya): akkaunt orqali, avtomatik**
1. https://my.telegram.org ga kiring → *API development tools* → ilova yarating.
2. `api_id` va `api_hash` ni `.env` dagi `TG_API_ID=` va `TG_API_HASH=` qatorlariga yozing.
3. Terminalda:
```bash
cd /Users/max/Projects/telegram_bot
./venv/bin/python import_history.py --dry-run     # avval sanab ko'rish (bazaga yozmaydi)
./venv/bin/python import_history.py               # import (bot ulangan barcha guruhlar, to'liq tarix)
./venv/bin/python import_history.py --since 01.10.2026   # faqat shu sanadan boshlab
```
Birinchi safar telefon raqam va Telegramdan kelgan kodni so'raydi (akkauntingiz guruhda bo'lishi kerak).

**2-usul: Telegram Desktop eksporti**
Telegram Desktop → guruh → ⋮ → *Export chat history* → Format: **JSON**, *Photos* belgilangan.
```bash
./venv/bin/python import_history.py export ~/Downloads/ChatExport_2026-10-21
```

Skriptni qayta ishga tushirish xavfsiz: avval sanalgan xabarlar qayta sanalmaydi.
Takror rasmlar bot bilan bir xil qoida bo'yicha aniqlanadi. Import paytida botni to'xtatish shart emas.

## Mac'da doimiy ishlashi (launchd)
Bot `launchd` orqali ishlaydi: tizimga kirganda o'zi ishga tushadi, to'xtab qolsa
10 soniyadan keyin o'zi qayta ishga tushadi. Sozlama fayli:
`~/Library/LaunchAgents/uz.telegram-bot.photo-counter.plist` (nusxasi `deploy/` ichida).

```bash
# Holatini ko'rish (state = running bo'lishi kerak)
launchctl print gui/$(id -u)/uz.telegram-bot.photo-counter | grep -E "state|pid"

# Jonli log
tail -f ~/Library/Logs/telegram-bot.log

# To'xtatish (qayta ishga tushmaydi)
launchctl bootout gui/$(id -u)/uz.telegram-bot.photo-counter

# Qayta ishga tushirish (yoki birinchi marta o'rnatish)
./deploy/mac-install.sh

# Kod o'zgargandan keyin qayta yuklash
launchctl kickstart -k gui/$(id -u)/uz.telegram-bot.photo-counter
```

Uyqu: bot `caffeinate` orqali ishga tushadi, shuning uchun u ishlab turganda Mac
bo'sh qolsa ham uxlamaydi (displey o'chishi mumkin, bu zarar qilmaydi).
Lekin noutbuk qopqog'i yopilsa yoki Mac qo'lda uxlatilsa / o'chirilsa bot to'xtaydi.
Mac'ni zaryadda, qopqog'i ochiq holda qoldiring.

Diqqat: `./run.sh` bilan qo'lda ishga tushirmang, launchd nusxasi bilan to'qnashadi
("Conflict: terminated by other getUpdates request").

## Windows noutbukda ishlatish
Kod Windows'da ham xuddi shunday ishlaydi. Ko'chirish tartibi:

1. Windows'ga Python o'rnating: https://www.python.org/downloads/ (3.11 yoki yangiroq).
   O'rnatishda **"Add python.exe to PATH"** belgisini qo'ying.
2. Mac'dagi botni to'xtating (ikki nusxa bir vaqtda ishlamasligi kerak):
   ```bash
   launchctl bootout gui/$(id -u)/uz.telegram-bot.photo-counter
   ```
3. Loyiha papkasini Windows'ga ko'chiring: `venv/` papkasidan **tashqari** hammasi,
   jumladan `.env` (token) va `data.db` (hisoblar). Masalan `C:\telegram_bot` ga.
4. `deploy\windows\install-task.ps1` faylini o'ng tugma → **Run with PowerShell**.
   Agar skriptlar taqiqlangan desa, PowerShell'da bir marta:
   `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`
5. Tayyor: bot tizimga kirganda o'zi ishga tushadi, to'xtab qolsa 1 daqiqada qayta ishga tushadi,
   oynasiz fon rejimida ishlaydi. Zaryadda turganda noutbuk uxlamaydi (qopqoq yopilsa uxlaydi:
   Sozlamalar → Power → "When I close the lid" → *Do nothing*).

Qo'lda ishga tushirish: `deploy\windows\run.bat`. Log: `bot.log`.
