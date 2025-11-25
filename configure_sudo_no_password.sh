#!/bin/bash
# Script pentru configurare sudo fără parolă pentru utilizatorul mobra

echo "══════════════════════════════════════════════════════════════"
echo "  🔧 Configurare Sudo Fără Parolă"
echo "══════════════════════════════════════════════════════════════"
echo ""

USERNAME="mobra"
SUDOERS_FILE="/etc/sudoers.d/${USERNAME}_nopasswd"

echo "Utilizator: $USERNAME"
echo "Fișier configurare: $SUDOERS_FILE"
echo ""

# Verifică dacă fișierul există deja
if [ -f "$SUDOERS_FILE" ]; then
    echo "⚠️  Fișierul $SUDOERS_FILE există deja."
    echo "Conținut actual:"
    cat "$SUDOERS_FILE"
    echo ""
    read -p "Vrei să-l suprascrii? (y/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "❌ Anulat."
        exit 1
    fi
fi

# Creează configurarea sudoers
echo "📝 Creare configurare sudoers..."
sudo tee "$SUDOERS_FILE" > /dev/null <<EOF
# Configurare sudo fără parolă pentru $USERNAME
# Creat automat la $(date)

$USERNAME ALL=(ALL) NOPASSWD: ALL
EOF

# Setează permisiunile corecte (0440)
sudo chmod 0440 "$SUDOERS_FILE"

# Verifică sintaxa
echo ""
echo "🔍 Verificare sintaxă sudoers..."
if sudo visudo -c -f "$SUDOERS_FILE" 2>/dev/null; then
    echo "✅ Sintaxă corectă!"
else
    echo "❌ EROARE: Sintaxă incorectă în $SUDOERS_FILE"
    echo "Ștergere fișier pentru siguranță..."
    sudo rm -f "$SUDOERS_FILE"
    exit 1
fi

echo ""
echo "══════════════════════════════════════════════════════════════"
echo "  ✅ Configurare Completă!"
echo "══════════════════════════════════════════════════════════════"
echo ""
echo "📋 Configurare aplicată:"
echo "   $USERNAME ALL=(ALL) NOPASSWD: ALL"
echo ""
echo "🧪 Testare:"
echo "   Rulează: sudo whoami"
echo "   Ar trebui să returneze: root (fără să ceară parolă)"
echo ""
echo "⚠️  NOTĂ DE SECURITATE:"
echo "   Această configurare permite utilizatorului $USERNAME"
echo "   să ruleze orice comandă sudo fără parolă."
echo "   Asigură-te că acest lucru este acceptabil pentru securitatea sistemului."
echo ""

