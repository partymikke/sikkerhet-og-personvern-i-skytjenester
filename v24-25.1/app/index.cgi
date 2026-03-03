#!/bin/sh

# ============================================================
# Enkel CGI for Allpodd
# ✔ logging
# ✔ input-validering
# ✔ sikker XML-håndtering
# ============================================================

# ============================================================
# HTTP HEADER
# ============================================================
echo "Content-Type: text/plain; charset=utf-8"
echo

# ============================================================
# Kun POST
# ============================================================
if [ "$REQUEST_METHOD" != "POST" ]; then
  exit 0
fi

# ============================================================
# CONTENT LENGTH FIX
# ============================================================
CONTENT_LENGTH=$HTTP_CONTENT_LENGTH$CONTENT_LENGTH

# ============================================================
# LES BODY
# ============================================================
KROPP=$(head -c "$CONTENT_LENGTH")

# ============================================================
# URL decode (enkel)
# ============================================================
urldecode() {
  printf '%s' "$1" | sed 's/+/ /g; s/%40/@/g'
}

# ============================================================
# XML escape
# ============================================================
xml_escape() {
  printf '%s' "$1" | sed \
    -e 's/&/\&amp;/g' \
    -e 's/</\&lt;/g' \
    -e 's/>/\&gt;/g' \
    -e 's/"/\&quot;/g' \
    -e "s/'/\&apos;/g"
}

# ============================================================
# Mask epost
# ============================================================
mask_email() {
  printf '%s' "$1" | sed 's/^\(.\).*\(@.*\)$/\1***\2/; t; s/.*/***/'
}

# ============================================================
# PARSE INPUT
# ============================================================
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

# ============================================================
# INPUT-VALIDERING
# ============================================================

# epost må finnes
if [ -z "$E" ]; then
  echo "Epost mangler"
  exit 0
fi

# passord må finnes (for alle unntatt Liste)
if [ "$H" != "Liste" ] && [ -z "$P" ]; then
  echo "Passord mangler"
  exit 0
fi

# ============================================================
# LOGGING (SENSITIV-SIKKER)
# ============================================================
MASKED_EMAIL=$(mask_email "$E")
echo "app: request mottatt - epost=$MASKED_EMAIL handling=$H" >&2

# ============================================================
# ESCAPE DATA
# ============================================================
E_ESC=$(xml_escape "$E")
P_ESC=$(xml_escape "$P")
K_ESC=$(xml_escape "$K")
O_ESC=$(xml_escape "$O")
T_ESC=$(xml_escape "$T")
X_ESC=$(xml_escape "$X")

# ============================================================
# PSEUDONYM-DB
# ============================================================
XML_PN="<pseudonym>
<epost>${E_ESC}</epost>
<passord>${P_ESC}</passord>
</pseudonym>"

URL_PN="allpodd:83"

echo "PN kall til: $URL_PN (masked=$MASKED_EMAIL)" >&2

N=$(curl -s -d "$XML_PN" "$URL_PN")

if [ -z "$N" ]; then
  echo "Pseudonym mangler!"
  exit 0
fi

# ============================================================
# BIDRAG-DB
# ============================================================
XML_B="<bidrag>
<navn>$(xml_escape "$N")</navn>
<passord>${P_ESC}</passord>
<kommentar>${K_ESC}</kommentar>
<offentlig_nokkel>${O_ESC}</offentlig_nokkel>
<tittel>${T_ESC}</tittel>
<tekst>${X_ESC}</tekst>
</bidrag>"

URL_B="allpodd:82"

echo "BIDRAG kall til: $URL_B - handling=$H" >&2

# ============================================================
# HANDLING
# ============================================================
case "$H" in

  Ny)
    # ⚠️ kan feile hvis finnes fra før
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

  *)
    echo "Ukjent handling" >&2
    ;;
esac

exit 0
