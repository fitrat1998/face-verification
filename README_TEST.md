# Face Auth — lokal test qo'llanmasi

## 1. O'rnatish (faqat bir marta)

```bash
cd face-api
pip install flask flask-cors opencv-contrib-python pillow numpy
```

> Eslatma: `opencv-contrib-python` muhim — oddiy `opencv-python` emas,
> chunki LBPH face recognizer faqat `contrib` paketida bor.

## 2. Serverni ishga tushirish

```bash
cd face-api
python3 app.py
```

Konsolda shu chiqishi kerak:
```
Running on http://0.0.0.0:5001
```

## 3. Brauzerda test qilish

Brauzerda oching:

```
http://localhost:5001/
```

(Agar server boshqa kompyuterda/serverda bo'lsa: `http://SERVER_IP:5001/`)

### Test qadamlari:

1. Brauzer kamerangizga ruxsat so'raydi — **Allow** bosing.
2. "User ID" maydoniga ixtiyoriy nom kiriting (masalan: `ali`).
3. **"📷 Ro'yxatdan o'tkazish"** tugmasini bosing — yuzingiz saqlanadi.
   - Yaxshi natija uchun shu tugmani 4-5 marta turli burchak/holatda bosing
     (model qancha ko'p namuna ko'rsa, shuncha yaxshi ishlaydi).
4. **"✅ Tekshirish (Login)"** tugmasini bosing — agar siz bo'lsangiz
   "Moslik topildi" deb yashil natija chiqadi.
5. Boshqa odam kamera oldida turib "Tekshirish" tugmasini bossa,
   "Moslik topilmadi" chiqishi kerak.

## 4. Muhim eslatmalar

- Bu **test/demo** versiyasi — ishlatilgan algoritm (OpenCV LBPH)
  productionga tavsiya etilmaydi (pastroq aniqlik). Faqat arxitekturani
  sinash uchun.
- Real foydalanish uchun foto-spoofing himoyasi (ekrandan rasm ko'rsatib
  aldash) yo'q — bu ham faqat test versiyasi ekanini ko'rsatadi.
- Ma'lumotlar `face-api/face_data/` papkasida saqlanadi. O'chirish uchun:
  ```bash
  rm -rf face-api/face_data/*
  ```

## 5. Agar ishlamasa

| Muammo | Yechim |
|---|---|
| Kamera ochilmaydi | Brauzer sozlamalarida saytga camera ruxsatini tekshiring. Chrome/Firefox `localhost`ni avtomatik xavfsiz deb hisoblaydi. |
| "Connection refused" | Server ishlamayapti — `python3 app.py` qayta ishga tushiring. |
| "Yuz topilmadi" doimo chiqadi | Yorug'likni oshiring, kameraga yaqinroq va to'g'ridan keling. |
| CORS xatosi | `flask-cors` o'rnatilganini tekshiring: `pip show flask-cors` |
