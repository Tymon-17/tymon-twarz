#!/usr/bin/env bash
# ============================================================
# Tymon — silnik twarzy, prototyp v1 (27.10.2026, Sweterek)
# Instaluje SoulX-FlashHead (portret + dźwięk -> mówiąca twarz) na maszynie RunPod
# i uruchamia stronę demo za hasłem. Bez kluczy w kodzie. Bez publicznych linków.
#
# Użycie (w terminalu poda):
#   curl -fsSL https://raw.githubusercontent.com/Tymon-17/tymon-twarz/main/start.sh | bash
# Tryby po instalacji:
#   bash /workspace/tymon-twarz/uruchom.sh plik       # wideo z gotowego pliku audio (domyślnie)
#   bash /workspace/tymon-twarz/uruchom.sh strumien   # demo strumieniowe (na żywo)
# Dziennik: /workspace/twarz-instalacja.log
# ============================================================
set -euo pipefail
LOG=/workspace/twarz-instalacja.log
mkdir -p /workspace
exec > >(tee -a "$LOG") 2>&1
krok() { echo; echo "==> $(date '+%H:%M:%S') $*"; }

krok "Sprawdzam hasło strony demo (zmienna DEMO_HASLO w ustawieniach poda)"
if [ -z "${DEMO_HASLO:-}" ] || [ ${#DEMO_HASLO} -lt 10 ]; then
  echo "BRAK albo za krótkie DEMO_HASLO (min. 10 znaków). Ustaw je w Edit Pod -> Environment Variables i uruchom ponownie."
  exit 1
fi

krok "Karta graficzna"
nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv || { echo "Brak karty NVIDIA na tej maszynie."; exit 1; }

krok "Pobieram skrypty Tymona (tymon-twarz)"
cd /workspace
if [ -d tymon-twarz/.git ]; then git -C tymon-twarz pull -q; else git clone -q --depth 1 https://github.com/Tymon-17/tymon-twarz.git; fi

krok "Narzędzia systemowe (ffmpeg, git)"
export DEBIAN_FRONTEND=noninteractive
(apt-get update -qq && apt-get install -y -qq ffmpeg git >/dev/null) || echo "UWAGA: apt nie zadziałał — sprawdzam, czy ffmpeg już jest"
command -v ffmpeg >/dev/null || { echo "Brak ffmpeg."; exit 1; }
pip install -q uv

krok "Pobieram SoulX-FlashHead"
if [ ! -d SoulX-FlashHead/.git ]; then git clone -q --depth 1 https://github.com/Soul-AILab/SoulX-FlashHead.git; fi
cd SoulX-FlashHead
echo "wersja FlashHead: $(git rev-parse --short HEAD)"

krok "Środowisko Pythona 3.10 i biblioteki (kilka minut)"
[ -d .venv ] || uv venv -q -p 3.10 .venv
# shellcheck disable=SC1091
set +u; source .venv/bin/activate; set -u
uv pip install -q -r requirements.txt
# PyTorch dokładnie w wersji z instrukcji autorów (CUDA 12.8) — po requirements, żeby nic go nie nadpisało.
uv pip install -q --reinstall-package torch --reinstall-package torchvision torch==2.7.1 torchvision==0.22.1 --index-url https://download.pytorch.org/whl/cu128
uv pip install -q "gradio==5.50.0" huggingface_hub ninja

krok "FlashAttention (gotowa paczka; budowanie od zera trwałoby godzinę)"
if ! python -c "import flash_attn" 2>/dev/null; then
  ABI=$(python -c "import torch;print('TRUE' if torch._C._GLIBCXX_USE_CXX11_ABI else 'FALSE')")
  WHL="https://github.com/Dao-AILab/flash-attention/releases/download/v2.8.0.post2/flash_attn-2.8.0.post2+cu12torch2.7cxx11abi${ABI}-cp310-cp310-linux_x86_64.whl"
  uv pip install -q "$WHL" || { echo "UWAGA: gotowa paczka nie weszła — buduję (długo)"; uv pip install flash_attn==2.8.0.post2 --no-build-isolation; }
fi
python -c "import torch, flash_attn; print('torch', torch.__version__, 'cuda', torch.version.cuda, 'gpu', torch.cuda.is_available(), 'flash_attn', flash_attn.__version__)"

krok "Modele (ok. kilku GB, raz)"
python - <<'PY'
from huggingface_hub import snapshot_download
for repo, cel in [("Soul-AILab/SoulX-FlashHead-1_3B", "models/SoulX-FlashHead-1_3B"),
                  ("facebook/wav2vec2-base-960h", "models/wav2vec2-base-960h")]:
    print("pobieram", repo)
    snapshot_download(repo, local_dir=cel)
print("modele gotowe")
PY

krok "Instalacja skończona. Uruchamiam stronę demo (tryb: plik)"
bash /workspace/tymon-twarz/uruchom.sh plik
