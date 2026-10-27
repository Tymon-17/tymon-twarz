#!/usr/bin/env bash
# Uruchamia stronę demo FlashHead za hasłem, na porcie 7860.
#   plik     — gradio_app.py (portret + gotowe audio -> wideo)
#   strumien — gradio_app_streaming.py (demo na żywo)
set -euo pipefail
TRYB="${1:-plik}"
cd /workspace/SoulX-FlashHead
# shellcheck disable=SC1091
set +u; source .venv/bin/activate; set -u
case "$TRYB" in
  plik) ZRODLO=gradio_app.py ;;
  strumien) ZRODLO=gradio_app_streaming.py ;;
  *) echo "Nieznany tryb: $TRYB (plik | strumien)"; exit 1 ;;
esac
[ -f "$ZRODLO" ] || { echo "Brak $ZRODLO w repozytorium FlashHead."; exit 1; }
python /workspace/tymon-twarz/zabezpiecz.py "$ZRODLO" tymon_demo.py
pkill -f tymon_demo.py 2>/dev/null || true
sleep 1
export GRADIO_SERVER_NAME=0.0.0.0 GRADIO_SERVER_PORT=7860 GRADIO_ANALYTICS_ENABLED=False
nohup python tymon_demo.py > /workspace/twarz-demo.log 2>&1 &
echo
echo "Strona demo startuje w tle (tryb: $TRYB). Pierwsze wczytanie modeli trwa ok. 1–2 min."
echo "Otwórz w RunPod: Connect -> HTTP Service [Port 7860]. Login: tymon, hasło: twoje DEMO_HASLO."
echo "Dziennik strony: tail -f /workspace/twarz-demo.log"
