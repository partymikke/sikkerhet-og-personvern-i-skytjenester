#!/bin/sh

DB=../bidrag.db

# HTTP header
cat <<EOF
Access-Control-Allow-Origin: http://localhost:8080
Access-Control-Allow-Credentials: true
Access-Control-Allow-Methods: GET,POST,PUT,DELETE
Access-Control-Allow-Headers: Content-Type
Content-Type:text/plain;charset=utf-8

EOF

#!/bin/sh

# ============================================================
# BIDRAG-DB CGI
# ✔ logging
# ✔ input-validering
# ✔ passord-sikkerhet
# ============================================================

DB="../bidrag.db"

# ============================================================
# HTTP HEADER
# ============================================================
cat <<EOF
Content-Type: text/plain; charset=utf-8

EOF

# ============================================================
# CONTENT LENGTH FIX
# ============================================================
CONTENT_LENGTH=$HTTP_CONTENT_LENGTH$CONTENT_LENGTH

# ============================================================
# LOGGING (ALLTID!)
# ============================================================
echo "bidrag-db: request received" >&2

# ============================================================
# GET = LISTE
# ============================================================
if [ "$REQUEST_METHOD" = "GET" ]; then
    sqlite3 -line $DB "SELECT tittel, tekst FROM Bidrag"
    exit 0
fi

# ============================================================
# LES BODY
# ============================================================
KR=$(head -c "$CONTENT_LENGTH")

# ============================================================
# PARSE XML (xmllint)
# ============================================================
N=$(echo "$KR" | xmllint --xpath "string(/bidrag/navn)" - 2>/dev/null)
P=$(echo "$KR" | xmllint --xpath "string(/bidrag/passord)" - 2>/dev/null)
K=$(echo "$KR" | xmllint --xpath "string(/bidrag/kommentar)" - 2>/dev/null)
O=$(echo "$KR" | xmllint --xpath "string(/bidrag/offentlig_nokkel)" - 2>/dev/null)
T=$(echo "$KR" | xmllint --xpath "string(/bidrag/tittel)" - 2>/dev/null)
X=$(echo "$KR" | xmllint --xpath "string(/bidrag/tekst)" - 2>/dev/null)

# ============================================================
# INPUT-VALIDERING
# ============================================================

# navn må finnes
if [ -z "$N" ]; then
    echo "Pseudonym mangler!"
    exit 0
fi

# passord må finnes (ikke for GET)
if [ "$REQUEST_METHOD" != "GET" ] && [ -z "$P" ]; then
    echo "Passord mangler!"
    exit 0
fi

# ============================================================
# NY (POST)
# ============================================================
if [ "$REQUEST_METHOD" = "POST" ]; then

    # Sjekk om finnes fra før (hindrer UNIQUE crash)
    EXISTS=$(sqlite3 $DB "SELECT COUNT(*) FROM Bidrag WHERE pseudonym='$N';")

    if [ "$EXISTS" != "0" ]; then
        echo "Finnes allerede!"
        exit 0
    fi

    # Lag salt
    S=$(for i in $(seq 11); do echo -n $(($RANDOM % 10)); done)

    # Hash passord
    H=$(mkpasswd -m sha-256 -S "$S" "$P" | cut -f4 -d'$')

    # Sett inn
    sqlite3 $DB "
        INSERT INTO Bidrag 
        VALUES ('$N','$S','$H','$K','$O','$T','$X')
    "

    echo "OK"
    exit 0
fi

# ============================================================
# HENT SALT
# ============================================================
S=$(sqlite3 $DB "SELECT salt FROM Bidrag WHERE pseudonym='$N';")

if [ -z "$S" ]; then
    echo "Bruker finnes ikke!"
    exit 0
fi

# ============================================================
# HASH INPUT PASSORD
# ============================================================
H1=$(mkpasswd -m sha-256 -S "$S" "$P" | cut -f4 -d'$')

# ============================================================
# HENT LAGRET HASH
# ============================================================
H2=$(sqlite3 $DB "SELECT passordhash FROM Bidrag WHERE pseudonym='$N';")

# ============================================================
# SAMMENLIGN PASSORD
# ============================================================
if [ "$H1" != "$H2" ]; then
    echo "Feil passord!"
    exit 0
fi

# ============================================================
# DELETE
# ============================================================
if [ "$REQUEST_METHOD" = "DELETE" ]; then
    sqlite3 $DB "DELETE FROM Bidrag WHERE pseudonym='$N';"
    echo "Slettet"
    exit 0
fi

# ============================================================
# PUT (ENDRE)
# ============================================================
if [ "$REQUEST_METHOD" = "PUT" ]; then
    sqlite3 $DB "
        UPDATE Bidrag SET
        kommentar='$K',
        offentlig_nokkel='$O',
        tittel='$T',
        tekst='$X'
        WHERE pseudonym='$N'
    "
    echo "Oppdatert"
    exit 0
fi
