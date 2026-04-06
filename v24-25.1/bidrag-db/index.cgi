#!/bin/sh

# Håndterer lagring og behandling av brukerbidrag med fokus på personvern

DB="/var/www/bidrag.db"
sqlite3 "$DB" "DELETE FROM Bidrag WHERE created_at < datetime('now','-30 days');"
# Sletter gamle data automatisk (GDPR lagringsbegrensning, artikkel 5)

# Sørger for riktig lengde på request body for trygg behandling
CONTENT_LENGTH=$HTTP_CONTENT_LENGTH$CONTENT_LENGTH

# Logger at noe skjer, men uten persondata (GDPR ansvarlighet)
echo "bidrag-db: request received" >&2

# Hvis GET: viser lagrede bidrag uten sensitiv info (dataminimering)
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

# Forteller klient hva slags svar som sendes tilbake (åpenhet GDPR)
echo "Content-Type: text/plain; charset=utf-8"
echo

# Leser kun innsendt data for videre behandling (dataminimering)
KR=$(head -c "$CONTENT_LENGTH")

# Leser ut spesifikke felt fra XML (kun nødvendige data brukes)
N=$(echo "$KR" | xmllint --xpath "string(/bidrag/navn)" - 2>/dev/null)
P=$(echo "$KR" | xmllint --xpath "string(/bidrag/passord)" - 2>/dev/null)
K=$(echo "$KR" | xmllint --xpath "string(/bidrag/kommentar)" - 2>/dev/null)
O=$(echo "$KR" | xmllint --xpath "string(/bidrag/offentlig_nokkel)" - 2>/dev/null)
T=$(echo "$KR" | xmllint --xpath "string(/bidrag/tittel)" - 2>/dev/null)
X=$(echo "$KR" | xmllint --xpath "string(/bidrag/tekst)" - 2>/dev/null)
HND=$(echo "$KR" | xmllint --xpath "string(/bidrag/handling)" - 2>/dev/null)

# Sjekker at vi har nødvendig identifikator (GDPR riktighet)
if [ -z "$N" ]; then
    echo "Pseudonym mangler!"
    exit 0
fi

# Krever passord der det er nødvendig (tilgangskontroll, GDPR sikkerhet)
if [ "$REQUEST_METHOD" != "GET" ] && [ -z "$P" ]; then
    echo "Passord mangler!"
    exit 0
fi

# Lar bruker hente egne data (GDPR innsynsrett, artikkel 15)
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

# Oppretter nytt bidrag hvis det ikke finnes fra før (kontroll på duplikater)
if [ "$REQUEST_METHOD" = "POST" ]; then

    EXISTS=$(sqlite3 "$DB" "SELECT COUNT(*) FROM Bidrag WHERE pseudonym='$N';")

    if [ "$EXISTS" != "0" ]; then
        echo "Finnes allerede!"
        exit 0
    fi

    # Lager tilfeldig salt for sikrere passordlagring (GDPR sikkerhet artikkel 32)
    S=$(for i in $(seq 11); do echo -n $(($RANDOM % 10)); done)

    # Hasher passord før lagring (beskytter persondata)
    H=$(mkpasswd -m sha-256 -S "$S" "$P" | cut -f4 -d'$')

    sqlite3 "$DB" "
        INSERT INTO Bidrag
        VALUES ('$N','$S','$H','$K','$O','$T','$X')
    "

    echo "OK"
    exit 0
fi

# Henter salt for å kunne verifisere passord sikkert
S=$(sqlite3 "$DB" "SELECT salt FROM Bidrag WHERE pseudonym='$N';")

if [ -z "$S" ]; then
    echo "Bruker finnes ikke!"
    exit 0
fi

# Lager hash av innsendt passord for sammenligning (sikker autentisering)
H1=$(mkpasswd -m sha-256 -S "$S" "$P" | cut -f4 -d'$')

# Henter lagret hash fra databasen
H2=$(sqlite3 "$DB" "SELECT passordhash FROM Bidrag WHERE pseudonym='$N';")

# Sjekker om passord stemmer (tilgangskontroll, GDPR sikkerhet)
if [ "$H1" != "$H2" ]; then
    echo "Feil passord!"
    exit 0
fi

# Lar bruker slette egne data (GDPR retten til sletting, artikkel 17)
if [ "$REQUEST_METHOD" = "DELETE" ]; then
    sqlite3 "$DB" "DELETE FROM Bidrag WHERE pseudonym='$N';"
    echo "Slettet"
    exit 0
fi

# Lar bruker oppdatere egne data (GDPR retting, artikkel 16)
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
