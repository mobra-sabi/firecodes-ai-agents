# Soluție: Acces Chat de pe Windows

**Problema:** Eroare `ERR_CONNECTION_RESET` sau `ERR_SOCKET_NOT_CONNECTED` când accesezi `localhost:8083/chat` de pe Windows.

## 🔍 CAUZA PROBLEMEI

Serverul FastAPI rulează pe serverul Linux (`/srv/hf/ai_agents`), nu pe mașina ta Windows locală. Când accesezi `localhost:8083` sau `127.0.0.1:8083` de pe Windows, încerci să accesezi serverul local (Windows), nu serverul Linux unde rulează aplicația.

## ✅ SOLUȚIA

### Folosește IP-ul serverului în loc de localhost:

**În loc de:**
- ❌ `http://localhost:8083/chat`
- ❌ `http://127.0.0.1:8083/chat`

**Folosește:**
- ✅ `http://192.168.1.125:8083/chat`

## 🔧 VERIFICĂRI

### 1. Serverul rulează pe Linux:
```bash
# Pe serverul Linux:
curl http://127.0.0.1:8083/health
```

### 2. Portul este deschis pentru conexiuni externe:
```bash
# Serverul rulează pe 0.0.0.0:8083 (accesibil din rețea)
```

### 3. Firewall (dacă e necesar):
```bash
# Dacă firewall blochează, permite portul 8083:
sudo ufw allow 8083/tcp
# sau
sudo firewall-cmd --add-port=8083/tcp --permanent
```

## 📱 ACCESARE CHAT

### Opțiunea 1: Browser Windows
Deschide în browser:
```
http://192.168.1.125:8083/chat
```

### Opțiunea 2: SSH Tunnel (dacă e necesar)
Dacă nu poți accesa direct din cauza firewall-ului, poți crea un tunel SSH:
```bash
# Pe Windows (PowerShell sau CMD):
ssh -L 8083:localhost:8083 user@192.168.1.125

# Apoi accesează:
http://localhost:8083/chat
```

### Opțiunea 3: Schimbă IP-ul dacă se schimbă
Dacă IP-ul serverului se schimbă, verifică din nou:
```bash
# Pe serverul Linux:
hostname -I
```

## 🚨 TROUBLESHOOTING

### Dacă tot nu funcționează:

1. **Verifică conectivitatea:**
```bash
# Pe Windows (PowerShell):
Test-NetConnection -ComputerName 192.168.1.125 -Port 8083
```

2. **Verifică firewall Windows:**
- Firewall-ul Windows poate bloca conexiuni externe
- Permite conexiuni pentru browser-ul tău

3. **Verifică firewall server:**
```bash
# Pe serverul Linux:
sudo ufw status
```

4. **Verifică dacă serverul ascultă pe toate interfețele:**
```bash
# Pe serverul Linux:
netstat -tuln | grep 8083
# Trebuie să vezi: 0.0.0.0:8083 (nu doar 127.0.0.1:8083)
```

---

**IP Server:** `192.168.1.125`  
**Port:** `8083`  
**URL Chat:** `http://192.168.1.125:8083/chat`


