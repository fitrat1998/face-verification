# Face Auth — Yuz orqali autentifikatsiya

## Fayl tuzilmasi
```
face_auth/
├── app.py              ← Flask backend
├── templates/
│   └── index.html      ← Frontend UI
├── known_faces/        ← Saqlangan yuzlar (avtomatik yaratiladi)
└── users.json          ← Foydalanuvchilar bazasi (avtomatik)
```

## O'rnatish

```bash
pip install flask flask-cors opencv-python opencv-contrib-python numpy Pillow
```

## Ishga tushirish

```bash
cd face_auth
python app.py
```

Keyin brauzerda oching: **http://localhost:5050**

## Ishlash tartibi

### Ro'yxatdan o'tish:
1. "Ro'yxat" tabini bosing
2. Ismingizni kiriting
3. Kameraga qarang (yuz aniqlanguncha)
4. "Ro'yxatdan o'tish" tugmasini bosing

### Kirish:
1. "Kirish" tabida kameraga qarang
2. Yuz aniqlanganda "Yuz bilan kirish" tugmasini bosing
3. Tizim yuzingizni tahlil qiladi

## API endpointlar

| Method | URL | Vazifa |
|--------|-----|--------|
| POST | /api/register | Yangi foydalanuvchi qo'shish |
| POST | /api/login | Yuz orqali kirish |
| POST | /api/detect | Yuzni aniqlash (real-time) |
| GET | /api/users | Foydalanuvchilar ro'yxati |
| POST | /api/logout | Chiqish |

## Sozlamalar (app.py da)

- `THRESHOLD = 0.92` — moslik chegarasi (92%). Oshirish = qattiqroq, kamaytirish = yumshoqroq
- `minSize=(80, 80)` — minimal yuz o'lchami pikselda
