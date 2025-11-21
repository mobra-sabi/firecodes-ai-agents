# 🌐 ACCES FRONTEND - INSTRUCȚIUNI

**Status**: ✅ Frontend rulează pe `0.0.0.0:5173` (accesibil extern)

---

## 📍 OPȚIUNI DE ACCES

### **Opțiunea 1: Cloudflared Tunnel (RECOMANDAT)**
Frontend-ul este disponibil prin tunnel cloudflared:

```
https://sandwich-show-purchasing-vocabulary.trycloudflare.com
```

**⚠️ NOTĂ**: URL-ul cloudflared se schimbă la fiecare restart. Verifică log-ul pentru URL-ul curent:
```bash
cd /srv/hf/ai_agents
tail -5 logs/cloudflared_5173.log | grep "https://"
```

**Avantaje**:
- ✅ Funcționează imediat, fără configurare
- ✅ Accesibil de oriunde
- ✅ HTTPS automat


---

### **Opțiunea 2: SSH Tunnel (de pe Windows)**

Dacă ești conectat la server prin SSH, poți crea un tunnel SSH:

**Pe Windows (PowerShell sau CMD)**:
```bash
ssh -L 5173:localhost:5173 mobra@viezure
```

Apoi accesează în browser:
```
http://localhost:5173
```

**Sau cu Putty**:
1. Connection → SSH → Tunnels
2. Source port: `5173`
3. Destination: `localhost:5173`
4. Click "Add"
5. Conectează-te la server
6. Accesează `http://localhost:5173` în browser

---

### **Opțiunea 3: Acces Direct (dacă serverul este accesibil în rețea)**

Dacă serverul viezure este accesibil în rețeaua ta:

```
http://[IP_SERVER]:5173
```

Pentru a găsi IP-ul serverului:
```bash
hostname -I
# sau
ip addr show | grep "inet " | grep -v "127.0.0.1"
```

**⚠️ ATENȚIE**: Asigură-te că:
- Firewall-ul permite conexiuni pe port 5173
- Serverul este accesibil din rețeaua ta

---

## 🔧 VERIFICARE STATUS

**Verifică dacă frontend-ul rulează**:
```bash
ps aux | grep vite | grep 5173
```

**Verifică portul**:
```bash
netstat -tlnp | grep 5173
# sau
ss -tlnp | grep 5173
```

Ar trebui să vezi: `0.0.0.0:5173` (nu `127.0.0.1:5173`)

**Test local pe server**:
```bash
curl http://localhost:5173
```

---

## 🚀 REPORNIRE FRONTEND

Dacă frontend-ul nu funcționează:

```bash
cd /srv/hf/ai_agents/frontend-pro
npm run dev -- --host 0.0.0.0 --port 5173
```

Sau în background:
```bash
cd /srv/hf/ai_agents/frontend-pro
nohup npm run dev -- --host 0.0.0.0 --port 5173 > ../logs/frontend.log 2>&1 &
```

**⚠️ IMPORTANT**: Frontend-ul este configurat cu `allowedHosts` în `vite.config.js` pentru a permite accesul prin cloudflared. Dacă primești eroarea "Blocked request", verifică că `vite.config.js` conține:
```javascript
allowedHosts: [
  'localhost',
  '.localhost',
  '.trycloudflare.com',  // Permite toate domeniile cloudflared
]
```

---

## 📝 NOTE

- Frontend-ul rulează pe port **5173**
- Backend API rulează pe port **8090**
- Cloudflared tunnel este activ pentru port 5173
- Frontend-ul este configurat cu `--host 0.0.0.0` pentru acces extern

---

**Ultima actualizare**: 19 Noiembrie 2025

