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
| `/oy` | Shu oy: fakt / plan (%) |
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

## Qanday sanaydi
- Guruhdagi har bir rasm (albom ichidagi har bir rasm ham) = 1 ta otchyot.
- Fayl sifatida yuborilgan rasm (siqilmagan) ham sanaladi.
- Bir xil rasm qayta yuborilsa (forward yoki takror) sanalmaydi, bot ogohlantiradi.
- Oylik plan haftalik plandan hisoblanadi: `haftalik × kunlar / 7`.
- O'chirilgan rasmlar haqida Telegram botga xabar bermaydi, ular hisobda qoladi.
- Bot o'chiq turganda tashlangan rasmlar keyingi ishga tushganda sanaladi (24 soatgacha).

## Fayllar
| Fayl | Vazifasi |
|------|----------|
| `bot.py` | Kirish nuqtasi, polling, buyruqlar menyusi |
| `config.py` | `.env` sozlamalari |
| `db.py` | SQLite baza (`data.db`) |
| `dates.py` | Sana yordamchilari (hafta, oy, Toshkent vaqti) |
| `reports.py` | Hisobot matnlari |
| `scheduler.py` | Har kuni avtomatik hisobot |
| `handlers/photos.py` | Rasmlarni sanash |
| `handlers/stats.py` | Hisobot buyruqlari |
| `handlers/admin.py` | Plan va agent boshqaruvi |
| `handlers/group.py` | Guruhga qo'shilganda / chiqarilganda |
| `handlers/start.py` | /start, /help, /id |
