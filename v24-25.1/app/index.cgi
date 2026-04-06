#!/bin/sh

# Enkel CGI med fokus på trygg databehandling (GDPR)
 
# Forteller klient hva slags svar vi sender (åpenhet)
echo "Content-Type: text/plain; charset=utf-8"
echo

# Tillater kun POST/GET for kontroll på input (GDPR kontroll)
if [ "$REQUEST_METHOD" != "POST" ] && [ "$REQUEST_METHOD" != "GET" ]; then
  echo "Feil metode: $REQUEST_METHOD" >&2
  exit 0
fi

# Sørger for riktig lengde på data (unngår feil)
CONTENT_LENGTH=$HTTP_CONTENT_LENGTH$CONTENT_LENGTH

# Leser kun data hvis nødvendig (dataminimering GDPR)
if [ "$REQUEST_METHOD" = "POST" ]; then
  KROPP=$(head -c "$CONTENT_LENGTH")
else
  KROPP=""
fi

# Gjør URL-data lesbart før behandling
urldecode() {
  printf '%s' "$1" | sed 's/+/ /g; s/%40/@/g'
}

# Hindrer injeksjon og beskytter systemet (GDPR sikkerhet)
xml_escape() {
  printf '%s' "$1" | sed \
    -e 's/&/\&amp;/g' \
    -e 's/</\&lt;/g' \
    -e 's/</\&lt;/g' \
    -e 's/>/\&gt;/g' \
    -e 's/"/\&quot;/g' \
    -e "s/'/\&apos;/g"
}

# Skjuler epost i logger (GDPR dataminimering)
mask_email() {
  printf '%s' "$1" | sed 's/^\(.\).*\(@.*\)$/\1***\2/; t; s/.*/***/'
}

# Leser ut nødvendige inputfelt (dataminimering)
TMP="/tmp/body.$$"
printf '%s\n' "$KROPP" | tr '&' '\n' > "$TMP"

E="" P="" K="" O="" T="" X="" H=""

while IFS= read -r pair; do
  [ -z "$pair" ] && continue

  key=${pair%%=*}
  val=${pair#*=}
  val=$(urldecode "$val")

  case "$key" in
    epost) E="$val" ;;
    passord) P="$val" ;;
    kommentar) K="$val" ;;
    offentlig_nokkel) O="$val" ;;
    tittel) T="$val" ;;
    tekst) X="$val" ;;
    handling) H="$val" ;;
  esac
done < "$TMP"

rm -f "$TMP"

# Sjekker at nødvendige data finnes (GDPR riktighet)
if [ -z "$E" ]; then
  echo "Epost mangler"
  exit 0
fi

if [ "$H" != "Liste" ] && [ -z "$P" ]; then
  echo "Passord mangler"
  exit 0
fi

# Logger hendelse med minst mulig persondata (GDPR ansvarlighet)
MASKED_EMAIL=$(mask_email "$E")
echo "app: request mottatt - epost=$MASKED_EMAIL handling=$H" >&2

# Gjør data trygt før videre bruk (GDPR sikkerhet)
E_ESC=$(xml_escape "$E")
P_ESC=$(xml_escape "$P")
K_ESC=$(xml_escape "$K")
O_ESC=$(xml_escape "$O")
T_ESC=$(xml_escape "$T")
X_ESC=$(xml_escape "$X")

# Bruker pseudonym i stedet for ekte identitet (GDPR pseudonymisering)
XML_PN="<pseudonym>
<epost>${E_ESC}</epost>
<passord>${P_ESC}</passord>
</pseudonym>"

URL_PN="http://allpodd:83/cgi-bin/index.cgi"

echo "PN kall til: $URL_PN (masked=$MASKED_EMAIL)" >&2

N=$(curl -s -d "$XML_PN" "$URL_PN")

if [ -z "$N" ]; then
  echo "Pseudonym mangler!"
  exit 0
fi

# Lagrer bidrag uten direkte identitet (GDPR dataminimering)
XML_B="<bidrag>
<navn>$(xml_escape "$N")</navn>
<passord>${P_ESC}</passord>
<kommentar>${K_ESC}</kommentar>
<offentlig_nokkel>${O_ESC}</offentlig_nokkel>
<tittel>${T_ESC}</tittel>
<tekst>${X_ESC}</tekst>
<handling>${H}</handling>
</bidrag>"

URL_B="http://allpodd:82/cgi-bin/index.cgi"

echo "BIDRAG kall til: $URL_B - handling=$H" >&2

# Lar bruker opprette, endre, slette egne data (GDPR rettigheter)
case "$H" in

  Ny)
    curl -s -X POST -d "$XML_B" "$URL_B"
    ;;

  Endre)
    curl -s -X PUT -d "$XML_B" "$URL_B"
    ;;

  Slett)
    curl -s -X DELETE -d "$XML_B" "$URL_B"
    ;;

  Liste)
    curl -s "$URL_B"
    ;;

  Min)
    curl -s -X POST -d "$XML_B" "$URL_B"
    ;;

  *)
    echo "Ukjent handling" >&2
    ;;
esac

exit 0
