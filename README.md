# Foto otchyot sanovchi bot (aiogram 3)

Savdo agentlari do'konlarga poster yopishtirib, guruhga rasm tashlaydi.
Bot har bir rasmni **1 ta foto otchyot** deb sanaydi va agent bo'yicha
kunlik, haftalik, oylik hisobot chiqaradi (plan / fakt / %).

## 1. Sozlash
`.env` faylida:
```
BOT_TOKEN=...              # @BotFather dan
DEFAULT_WEEKLY_PLAN=100    # har bir agent uchun haftalik plan
REPORT_TIME=21:00          # har kuni shu vaqtda avtomatik hisobot (bo'sh = o'chiq)
TIMEZONE=Asia/Tashkent
REACT_EMOJI=👍             # sanalgan rasmga reaksiya (bo'sh = o'chiq)
```

## 2. Ishga tushirish
```bash
./run.sh
```
yoki qo'lda:
```bash
python3 -m venv venv
./venv/bin/pip install -r requirements.txt
./venv/bin/python bot.py
```

## 3. Guruhga ulash
1. Botni agentlar guruhiga qo'shing.
2. Botni guruhda **admin** qiling. Aks holda Telegram botga oddiy rasmlarni ko'rsatmaydi.
   (Muqobil: @BotFather da `/setprivacy` → Disable.)
3. Agentlar odatdagidek rasm tashlaydi, bot sanab boradi va har rasmga 👍 qo'yadi.

## Buyruqlar (guruhda)
| Buyruq | Vazifasi |
|--------|----------|
| `/bugun` | Bugun kim nechta rasm tashlagan |
| `/kecha` | Kechagi hisobot |
| `/hafta` | Shu hafta (dushanba–yakshanba): fakt / plan (%) |
| `/hafta oldingi`, `/hafta 15.10.2026` | O'tgan hafta / shu sana kirgan hafta |
| `/oy` | Shu oy (1-sanadan oxirigacha): fakt / plan (%) |
| `/oy oldingi`, `/oy sentabr`, `/oy 9`, `/oy 09.2025` | Boshqa oy |
| `/hisobot 01.10.2026 15.10.2026` | Ixtiyoriy davr |
| `/mening` | O'z natijalarim (shaxsiy chatda ham ishlaydi) |

## Admin buyruqlari
Guruh adminlari va `.env` dagi `ADMIN_IDS` admin hisoblanadi.

| Buyruq | Vazifasi |
|--------|----------|
| `/plan` | Joriy planlarni ko'rish |
| `/plan 100` | Umumiy haftalik plan |
| `/plan 120` (agent xabariga reply) | Shu agent uchun alohida plan |
| `/plan 0` (reply) | Agentni umumiy planga qaytarish |
| `/agent_off` (reply) | Agentni hisobotlardan yashirish (ishdan ketganlar uchun) |
| `/agent_on` (reply) | Qaytarish |
| `+ism Muhammadillo` (reply) | Agentga ism berish, hisobotlarda shu ism chiqadi. Berilmasa Telegram ismi ishlatiladi |
| `-ism` (reply) | Telegram ismiga qaytarish |

## Qanday sanaydi
- Guruhdagi har bir rasm (albom ichidagi har bir rasm ham) = 1 ta otchyot.
- Fayl sifatida yuborilgan rasm (siqilmagan) ham sanaladi.
- Bir xil rasm 2–3 marta tashlansa faqat birinchisi sanaladi. Bot rasm mazmunini solishtiradi
  (perceptual hash), shuning uchun forward, qayta yuborish yoki galereyadan qayta yuklash ham ushlanadi.
  Takror rasmga bot "avval yuborilgan" deb javob beradi (kim, qachon, asl rasmga havola)
  va hisobotda agent yonida `⚠️ takror: N` chiqadi.
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
| `imghash.py` | Rasm barmoq izi (takrorlarni aniqlash) |
| `dates.py` | Sana yordamchilari (hafta, oy, Toshkent vaqti) |
| `reports.py` | Hisobot matnlari |
| `scheduler.py` | Har kuni avtomatik hisobot |
| `import_history.py` | Eski tarixdagi rasmlarni import qilish |
| `handlers/photos.py` | Rasmlarni sanash |
| `handlers/stats.py` | Hisobot buyruqlari |
| `handlers/admin.py` | Plan va agent boshqaruvi |
| `handlers/names.py` | `+ism` / `-ism` — agent ismini berish |
| `handlers/group.py` | Guruhga qo'shilganda / chiqarilganda |
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
