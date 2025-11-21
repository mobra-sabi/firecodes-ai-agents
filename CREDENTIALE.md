# 🔑 CREDENTIALE ACCES PLATFORMĂ

## 📋 UTILIZATORI DISPONIBILI

### **Utilizator Admin (Recomandat)**
```
Email: admin@example.com
Password: admin123
```

### **Utilizator Existente**

1. **george.neculai@tehnica-antifoc.ro**
   - Password: `password123` (resetată)
   - Role: user

2. **test999@example.com**
   - Password: necunoscută (hash-uită)
   - Role: user

3. **test888@example.com**
   - Password: necunoscută (hash-uită)
   - Role: user

4. **newuser@example.com**
   - Password: necunoscută (hash-uită)
   - Role: user

---

## 🔧 RESETARE PAROLĂ

Pentru a reseta parola unui utilizator sau a crea unul nou:

```bash
cd /srv/hf/ai_agents

# Resetează parola pentru un utilizator existent
python3 reset_user_password.py <email> <new_password>

# Creează un utilizator nou
python3 reset_user_password.py <email> <new_password> --create

# Listează toți utilizatorii
python3 reset_user_password.py --list
```

**Exemple**:
```bash
# Resetează parola pentru george.neculai@tehnica-antifoc.ro
python3 reset_user_password.py george.neculai@tehnica-antifoc.ro newpassword123

# Creează un utilizator admin nou
python3 reset_user_password.py admin@example.com admin123 --create
```

---

## 🌐 ACCES PLATFORMĂ

### **URL Frontend**
```
https://sandwich-show-purchasing-vocabulary.trycloudflare.com
```

**Notă**: URL-ul cloudflared se schimbă la fiecare restart. Verifică log-ul:
```bash
cd /srv/hf/ai_agents
tail -5 logs/cloudflared_5173.log | grep "https://"
```

### **API Backend**
```
http://localhost:8090
http://localhost:8090/docs  (Swagger UI)
```

### **Auth API** (dacă rulează separat)
```
http://localhost:5001
http://localhost:5001/docs
```

---

## 🔐 DEMO MODE (Frontend)

Frontend-ul are și un mod demo cu credentiale hardcodate:
```
Email: admin@example.com
Password: admin123
```

**Notă**: Acestea funcționează doar în frontend, nu în backend real.

---

## ⚠️ IMPORTANT

- Parolele sunt hash-uite cu bcrypt în baza de date
- Nu poți vedea parolele existente, doar să le resetezi
- Utilizatorii noi au role "user" implicit
- Pentru role "admin", trebuie să modifici manual în MongoDB

---

**Ultima actualizare**: 19 Noiembrie 2025

