#!/bin/sh

# ============================================================
# BIDRAG-DB CGI
# ============================================================

DB="/var/www/bidrag.db"
sqlite3 "$DB" "DELETE FROM Bidrag WHERE created_at < datetime('now','-30 days');"
# ============================================================
# CONTENT LENGTH FIX
# ============================================================
CONTENT_LENGTH=$HTTP_CONTENT_LENGTH$CONTENT_LENGTH

# ============================================================
# LOGGING
# ============================================================
echo "bidrag-db: request received" >&2

# ============================================================
# GET = LISTE (HTML OUTPUT)
# ============================================================
if [ "$REQUEST_METHOD" = "GET" ]; then
    echo "Content-Type: text/plain"
    echo

    sqlite3 -separator '|' "$DB" "SELECT tittel, tekst FROM Bidrag;" | \
    while IFS='|' read -r tittel tekst
    do
        echo "tittel = \"$tittel\""
        echo "tekst  = \"$tekst\""
        echo "----------------------"
    done

    exit 0
fi

# ============================================================
# HTTP HEADER
# ============================================================
echo "Content-Type: text/plain; charset=utf-8"
echo

# ============================================================
# LES BODY
# ============================================================
KR=$(head -c "$CONTENT_LENGTH")

# ============================================================
# PARSE XML
# ============================================================
N=$(echo "$KR" | xmllint --xpath "string(/bidrag/navn)" - 2>/dev/null)
P=$(echo "$KR" | xmllint --xpath "string(/bidrag/passord)" - 2>/dev/null)
K=$(echo "$KR" | xmllint --xpath "string(/bidrag/kommentar)" - 2>/dev/null)
O=$(echo "$KR" | xmllint --xpath "string(/bidrag/offentlig_nokkel)" - 2>/dev/null)
T=$(echo "$KR" | xmllint --xpath "string(/bidrag/tittel)" - 2>/dev/null)
X=$(echo "$KR" | xmllint --xpath "string(/bidrag/tekst)" - 2>/dev/null)
HND=$(echo "$KR" | xmllint --xpath "string(/bidrag/handling)" - 2>/dev/null)

# ============================================================
# INPUT-VALIDERING
# ============================================================
if [ -z "$N" ]; then
    echo "Pseudonym mangler!"
    exit 0
fi

if [ "$REQUEST_METHOD" != "GET" ] && [ -z "$P" ]; then
    echo "Passord mangler!"
    exit 0
fi

# ============================
# MIN kommentar
# ============================
if [ "$HND" = "Min" ]; then
    sqlite3 -separator '|' "$DB" "
        SELECT tittel, tekst, kommentar FROM Bidrag WHERE pseudonym='$N';
    " | while IFS='|' read -r tittel tekst kommentar
    do
        echo "tittel = \"$tittel\""
        echo "tekst  = \"$tekst\""
        echo "kommentar = \"$kommentar\""
        echo "----------------------"
    done
    exit 0
fi
# ============================================================
# NY (POST)
# ============================================================
if [ "$REQUEST_METHOD" = "POST" ]; then

    EXISTS=$(sqlite3 "$DB" "SELECT COUNT(*) FROM Bidrag WHERE pseudonym='$N';")

    if [ "$EXISTS" != "0" ]; then
        echo "Finnes allerede!"
        exit 0
    fi

    S=$(for i in $(seq 11); do echo -n $(($RANDOM % 10)); done)

    H=$(mkpasswd -m sha-256 -S "$S" "$P" | cut -f4 -d'$')

    sqlite3 "$DB" "
        INSERT INTO Bidrag
        VALUES ('$N','$S','$H','$K','$O','$T','$X')
    "

    echo "OK"
    exit 0
fi

# ============================================================
# HENT SALT
# ============================================================
S=$(sqlite3 "$DB" "SELECT salt FROM Bidrag WHERE pseudonym='$N';")

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
H2=$(sqlite3 "$DB" "SELECT passordhash FROM Bidrag WHERE pseudonym='$N';")

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
    sqlite3 "$DB" "DELETE FROM Bidrag WHERE pseudonym='$N';"
    echo "Slettet"
    exit 0
fi

# ============================================================
# PUT (ENDRE)
# ============================================================
if [ "$REQUEST_METHOD" = "PUT" ]; then
    sqlite3 "$DB" "
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
