#!/usr/bin/env bash
# ============================================================
# Tymon — silnik twarzy (v1 27.10, v3 28.10, v5 29.10.2026, Sweterek)
# Instaluje SoulX-FlashHead (portret + dźwięk -> mówiąca twarz) na maszynie RunPod
# i uruchamia usługę dla aplikacji Tymona. Bez kluczy w kodzie. Bez publicznych linków.
#
# v3: maszynę stawia APLIKACJA (API RunPod) i ten skrypt rusza sam przy starcie poda.
# Wszystko, co ciężkie, leży na WOLUMENIE SIECIOWYM pod /workspace: Python, biblioteki,
# modele, pamięć kompilacji. Pierwszy start instaluje (ok. 15 min), każdy następny tylko
# sprawdza znaczniki i od razu uruchamia usługę.
#
# Ręcznie (w terminalu poda):
#   curl -fsSL https://raw.githubusercontent.com/Tymon-17/tymon-twarz/main/start.sh | bash
# Tryby po instalacji:
#   bash /workspace/tymon-twarz/uruchom.sh usluga     # okienko dla aplikacji Tymona (domyślnie)
#   bash /workspace/tymon-twarz/uruchom.sh plik       # strona demo: wideo z gotowego pliku audio
#   bash /workspace/tymon-twarz/uruchom.sh strumien   # demo strumieniowe (na żywo)
# Dziennik: /workspace/twarz-instalacja.log
# ============================================================
set -euo pipefail
LOG=/workspace/twarz-instalacja.log
mkdir -p /workspace
exec > >(tee "$LOG") 2>&1
# Python zarządzany przez uv leży NA WOLUMENIE (inaczej środowisko z wolumenu nie miałoby
# interpretera na nowej maszynie); pamięć podręczna pobrań — na dysku maszyny.
export UV_PYTHON_INSTALL_DIR=/workspace/.uv-python UV_PYTHON_PREFERENCE=only-managed
export UV_CACHE_DIR=/root/.cache/uv UV_LINK_MODE=copy
krok() { echo; echo "==> $(date '+%H:%M:%S') $*"; }

krok "Sprawdzam hasło strony demo (zmienna DEMO_HASLO w ustawieniach poda)"
if [ -z "${DEMO_HASLO:-}" ] || [ ${#DEMO_HASLO} -lt 10 ]; then
  echo "BRAK albo za krótkie DEMO_HASLO (min. 10 znaków). Ustaw je w Edit Pod -> Environment Variables i uruchom ponownie."
  exit 1
fi

krok "Karta graficzna"
if command -v nvidia-smi >/dev/null; then
  nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv || { echo "Brak karty NVIDIA na tej maszynie."; exit 1; }
else
  echo "UWAGA: obraz nie ma nvidia-smi — kartę sprawdzi dopiero PyTorch niżej"
fi

# v5 (29.10): działa też na MAŁYM obrazie (runpod/base, ok. 0,7 GB zamiast ok. 10 GB) — wszystko,
# czego obraz nie ma, doinstalowuje sam. ffmpeg leży na WOLUMENIE (/workspace/bin, raz), więc
# kolejne starty nie czekają na apt. Narzędzia PRZED pobraniem skryptów (git może nie być w obrazie).
krok "Narzędzia systemowe (ffmpeg, git, gcc, uv)"
export DEBIAN_FRONTEND=noninteractive
export PATH=/workspace/bin:$PATH
mkdir -p /workspace/bin
if ! ffmpeg -version >/dev/null 2>&1 && command -v xz >/dev/null; then
  echo "ffmpeg na wolumen (raz)…"
  ( set -e; T=$(mktemp -d); curl -fsSL "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-linux64-gpl.tar.xz" | tar -xJ -C "$T"
    cp "$T"/ffmpeg-*/bin/ffmpeg "$T"/ffmpeg-*/bin/ffprobe /workspace/bin/; rm -rf "$T" ) || echo "UWAGA: ffmpeg z sieci nie wszedł — spróbuję apt"
fi
BRAKI=()
ffmpeg -version >/dev/null 2>&1 || BRAKI+=(ffmpeg)
command -v git >/dev/null || BRAKI+=(git)
command -v gcc >/dev/null || BRAKI+=(gcc)          # torch.compile (Triton) buduje małe moduły w C
LDC=$(command -v ldconfig || echo /sbin/ldconfig)
"$LDC" -p 2>/dev/null | grep -q 'libGL.so.1' || BRAKI+=(libgl1)   # opencv
"$LDC" -p 2>/dev/null | grep -q 'libglib-2.0.so.0' || BRAKI+=(GLIB)
if [ ${#BRAKI[@]} -gt 0 ]; then
  echo "doinstalowuję z apt: ${BRAKI[*]}"
  apt-get update -qq || true
  for P in "${BRAKI[@]}"; do
    if [ "$P" = GLIB ]; then apt-get install -y -qq libglib2.0-0t64 >/dev/null 2>&1 || apt-get install -y -qq libglib2.0-0 >/dev/null 2>&1 || echo "UWAGA: brak glib"
    else apt-get install -y -qq "$P" >/dev/null 2>&1 || echo "UWAGA: apt nie zainstalował $P"; fi
  done
else
  echo "wszystko jest — bez apt"
fi
ffmpeg -version >/dev/null 2>&1 || { echo "Brak ffmpeg."; exit 1; }
command -v git >/dev/null || { echo "Brak git."; exit 1; }
if ! command -v uv >/dev/null; then
  pip install -q uv 2>/dev/null || python3 -m pip install -q uv 2>/dev/null \
    || { curl -LsSf https://astral.sh/uv/install.sh | sh >/dev/null; export PATH=$HOME/.local/bin:$PATH; }
fi
command -v uv >/dev/null || { echo "Brak uv."; exit 1; }

krok "Pobieram skrypty Tymona (tymon-twarz)"
cd /workspace
if [ -d tymon-twarz/.git ]; then git -C tymon-twarz pull -q; else git clone -q --depth 1 https://github.com/Tymon-17/tymon-twarz.git; fi

krok "Pobieram SoulX-FlashHead"
if [ ! -d SoulX-FlashHead/.git ]; then git clone -q --depth 1 https://github.com/Soul-AILab/SoulX-FlashHead.git; fi
cd SoulX-FlashHead
echo "wersja FlashHead: $(git rev-parse --short HEAD)"

krok "Środowisko Pythona 3.10 i biblioteki"
ZNACZNIK_SRODOWISKA=.venv/.tymon-gotowe-v3
if [ -f "$ZNACZNIK_SRODOWISKA" ] && .venv/bin/python -c "import torch, flash_attn" 2>/dev/null; then
  echo "już zainstalowane (wolumen) — pomijam"
  # shellcheck disable=SC1091
  set +u; source .venv/bin/activate; set -u
else
[ -x .venv/bin/python ] || uv venv -q -p 3.10 .venv
# shellcheck disable=SC1091
set +u; source .venv/bin/activate; set -u
# Lista autorów ma sprzeczność: nvidia-nccl-cu12==2.27.3, a xformers 0.0.31 -> torch 2.7.1 wymaga nccl 2.26.2.
# NCCL służy tylko do pracy na wielu kartach, więc tę jedną linię pomijamy (zostaje wersja z torcha).
# opencv < 5: autorzy pisali kod pod serię 4.x.
REQ=/workspace/tymon-wymagania.txt
{ grep -v '^nvidia-nccl' requirements.txt; echo; } > "$REQ"
printf 'opencv-python<5\nopencv-python-headless<5\nopencv-contrib-python<5\n' > /workspace/tymon-ograniczenia.txt
# Wszystko jednym poleceniem: PyTorch 2.7.1 pod CUDA 12.8 (jak w instrukcji autorów) + reszta bibliotek.
uv pip install -q -r "$REQ" -c /workspace/tymon-ograniczenia.txt \
  "torch==2.7.1+cu128" "torchvision==0.22.1+cu128" "gradio==5.50.0" huggingface_hub hf_transfer ninja \
  --extra-index-url https://download.pytorch.org/whl/cu128 --index-strategy unsafe-best-match
python -c "import cv2, mediapipe, decord, xformers, xfuser; print('biblioteki OK, opencv', cv2.__version__)" \
  || echo "UWAGA: któraś biblioteka się nie ładuje (wyżej szczegóły) — instalacja idzie dalej"

krok "FlashAttention (gotowa paczka; budowanie od zera trwałoby godzinę)"
if ! python -c "import flash_attn" 2>/dev/null; then
  ABI=$(python -c "import torch;print('TRUE' if torch._C._GLIBCXX_USE_CXX11_ABI else 'FALSE')")
  WHL="https://github.com/Dao-AILab/flash-attention/releases/download/v2.8.0.post2/flash_attn-2.8.0.post2+cu12torch2.7cxx11abi${ABI}-cp310-cp310-linux_x86_64.whl"
  uv pip install -q "$WHL" || { echo "UWAGA: gotowa paczka nie weszła — buduję (długo)"; uv pip install flash_attn==2.8.0.post2 --no-build-isolation; }
fi
python -c "import torch, flash_attn; print('torch', torch.__version__, 'cuda', torch.version.cuda, 'gpu', torch.cuda.is_available(), 'flash_attn', flash_attn.__version__)"
touch "$ZNACZNIK_SRODOWISKA"
fi

krok "Modele (ok. kilku GB, raz)"
if [ -f models/.tymon-gotowe ]; then
  echo "już są (wolumen) — pomijam"
else
# Szablon RunPod włącza szybkie pobieranie (HF_HUB_ENABLE_HF_TRANSFER=1); bez paczki hf_transfer wyłączamy je.
python -c "import hf_transfer" 2>/dev/null || export HF_HUB_ENABLE_HF_TRANSFER=0
python - <<'PY'
from huggingface_hub import snapshot_download
for repo, cel in [("Soul-AILab/SoulX-FlashHead-1_3B", "models/SoulX-FlashHead-1_3B"),
                  ("facebook/wav2vec2-base-960h", "models/wav2vec2-base-960h")]:
    print("pobieram", repo)
    snapshot_download(repo, local_dir=cel)
print("modele gotowe")
PY
touch models/.tymon-gotowe
fi

krok "Gotowe. Uruchamiam usługę twarzy dla Tymona"
bash /workspace/tymon-twarz/uruchom.sh usluga
