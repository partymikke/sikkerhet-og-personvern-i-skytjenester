#!/bin/sh

# CGI backend for Allpodd applikasjon

# Sender HTTP-header til klient
echo "Content-Type: text/plain; charset=utf-8"
echo

# Tillater kun POST og GET forespørsler
if [ "$REQUEST_METHOD" != "POST" ] && [ "$REQUEST_METHOD" != "GET" ]; then
  echo "Feil metode: $REQUEST_METHOD" >&2
  exit 0
fi

# Fikser content-length fra httpd bug
CONTENT_LENGTH=$HTTP_CONTENT_LENGTH$CONTENT_LENGTH

# Leser body kun ved POST request
if [ "$REQUEST_METHOD" = "POST" ]; then
  KROPP=$(head -c "$CONTENT_LENGTH")
else
  KROPP=""
fi

# Dekoder URL-encoded input data
urldecode() {
  printf '%s' "$1" | sed 's/+/ /g; s/%40/@/g'
}

# Escaper XML spesialtegn i input
xml_escape() {
  printf '%s' "$1" | sed \
    -e 's/&/\&amp;/g' \
    -e 's/</\&lt;/g' \
    -e 's/>/\&gt;/g' \
    -e 's/"/\&quot;/g' \
    -e "s/'/\&apos;/g"
}

# Maskerer epost for sikker logging
mask_email() {
  printf '%s' "$1" | sed 's/^\(.\).*\(@.*\)$/\1***\2/; t; s/.*/***/'
}

# Parser form-data til variabler
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

# Validerer at epost er sendt inn
if [ -z "$E" ]; then
  echo "Epost mangler"
  exit 0
fi

# Krever passord unntatt ved Liste
if [ "$H" != "Liste" ] && [ -z "$P" ]; then
  echo "Passord mangler"
  exit 0
fi

# Logger request med maskert epost
MASKED_EMAIL=$(mask_email "$E")
echo "app: request mottatt - epost=$MASKED_EMAIL handling=$H" >&2

# Escaper alle input før videre bruk
E_ESC=$(xml_escape "$E")
P_ESC=$(xml_escape "$P")
K_ESC=$(xml_escape "$K")
O_ESC=$(xml_escape "$O")
T_ESC=$(xml_escape "$T")
X_ESC=$(xml_escape "$X")

# Lager XML for pseudonym-db kall
XML_PN="<pseudonym>
<epost>${E_ESC}</epost>
<passord>${P_ESC}</passord>
</pseudonym>"

URL_PN="http://allpodd:83/cgi-bin/index.cgi"

# Logger kall til pseudonym-db
echo "PN kall til: $URL_PN (masked=$MASKED_EMAIL)" >&2

N=$(curl -s -d "$XML_PN" "$URL_PN")

# Stopper hvis pseudonym mangler
if [ -z "$N" ]; then
  echo "Pseudonym mangler!"
  exit 0
fi

# Lager XML for bidrag-db kall
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

# Logger kall til bidrag-db
echo "BIDRAG kall til: $URL_B - handling=$H" >&2

# Utfører handling basert på input
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
