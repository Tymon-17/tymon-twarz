#!/usr/bin/env bash
# Uruchamia silnik twarzy na porcie 7860 (zawsze tylko jedna rzecz naraz — karta jest jedna).
#   usluga   — okienko dla aplikacji Tymona (domyślnie)               -> dziennik /workspace/twarz-usluga.log
#   plik     — strona demo autorów: portret + gotowe audio -> wideo   -> dziennik /workspace/twarz-demo.log
#   strumien — strona demo autorów na żywo                            -> dziennik /workspace/twarz-demo.log
set -euo pipefail
TRYB="${1:-usluga}"
cd /workspace/SoulX-FlashHead
# shellcheck disable=SC1091
set +u; source .venv/bin/activate; set -u

# Pamięć kompilacji (torch.compile) na wolumenie: pierwsza kompilacja trwała 147 s,
# kolejne maszyny biorą gotowe kawałki stąd.
mkdir -p /workspace/cache/inductor /workspace/cache/triton
export TORCHINDUCTOR_CACHE_DIR=/workspace/cache/inductor TRITON_CACHE_DIR=/workspace/cache/triton

pkill -f tymon_demo.py 2>/dev/null || true
pkill -f tymon-twarz/usluga.py 2>/dev/null || true
sleep 2

case "$TRYB" in
  usluga)
    nohup python /workspace/tymon-twarz/usluga.py > /workspace/twarz-usluga.log 2>&1 &
    echo
    echo "Usługa twarzy startuje w tle (model: ${TWARZ_MODEL:-lite}). Wczytanie modelu trwa ok. 1–2 min."
    if [ -n "${TYMON_ADRES:-}" ]; then
      echo "Sama zgłosi Tymonowi swój adres (${TYMON_ADRES}). W aplikacji Tymona twarz włączy się po chwili."
    else
      echo "UWAGA: brak TYMON_ADRES w ustawieniach poda — Tymon nie dowie się, gdzie jest twarz."
    fi
    echo "Dziennik: tail -f /workspace/twarz-usluga.log"
    ;;
  plik|strumien)
    if [ "$TRYB" = plik ]; then ZRODLO=gradio_app.py; else ZRODLO=gradio_app_streaming.py; fi
    [ -f "$ZRODLO" ] || { echo "Brak $ZRODLO w repozytorium FlashHead."; exit 1; }
    python /workspace/tymon-twarz/zabezpiecz.py "$ZRODLO" tymon_demo.py
    export GRADIO_SERVER_NAME=0.0.0.0 GRADIO_SERVER_PORT=7860 GRADIO_ANALYTICS_ENABLED=False
    nohup python tymon_demo.py > /workspace/twarz-demo.log 2>&1 &
    echo
    echo "Strona demo startuje w tle (tryb: $TRYB). Pierwsze wczytanie modeli trwa ok. 1–2 min."
    echo "Otwórz w RunPod: Connect -> HTTP Service [Port 7860]. Login: tymon, hasło: twoje DEMO_HASLO."
    echo "Dziennik strony: tail -f /workspace/twarz-demo.log"
    echo "Powrót do Tymona: bash /workspace/tymon-twarz/uruchom.sh usluga"
    ;;
  *) echo "Nieznany tryb: $TRYB (usluga | plik | strumien)"; exit 1 ;;
esac
