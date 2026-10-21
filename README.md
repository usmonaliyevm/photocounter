# Telegram Bot (aiogram 3)

## 1. Token olish
1. Telegramda **@BotFather** ga kiring.
2. `/newbot` buyrug'ini yuboring, nom va username bering.
3. Berilgan tokenni nusxalab oling.

## 2. Tokenni qo'yish
`.env` faylini oching va tokenni yozing:
```
BOT_TOKEN=123456789:AAAA...
ADMIN_IDS=            # ixtiyoriy: o'z ID ingiz (/id buyrug'i orqali bilib olasiz)
```

## 3. Ishga tushirish
```bash
./run.sh
```
yoki qo'lda:
```bash
python3 -m venv venv
./venv/bin/pip install -r requirements.txt
./venv/bin/python bot.py
```

## Fayllar
| Fayl | Vazifasi |
|------|----------|
| `bot.py` | Kirish nuqtasi, polling |
| `config.py` | `.env` dan token va adminlar |
| `keyboards.py` | Tugmalar |
| `handlers/start.py` | /start, /help, /id |
| `handlers/menu.py` | Menyu tugmalari, inline callback |
| `handlers/echo.py` | Rasm, fayl va boshqa xabarlar |

## Yangi funksiya qo'shish
`handlers/` ichida yangi fayl yarating, `router = Router()` e'lon qiling va
`handlers/__init__.py` da `router.include_router(...)` qatorini qo'shing
(`echo` routeridan **oldin**).
