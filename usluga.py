"""Silnik twarzy Tymona — usługa dla aplikacji (v2, 28.10.2026, Sweterek).

Zamiast strony demo: małe „okienko” HTTP na porcie 7860, z którym rozmawia serwer Tymona (Vercel).
Silnik nie zna Tymona — dostaje tylko portret i dźwięk, oddaje film (bez dźwięku; dźwięk gra aplikacja).

Wywołania (każde wymaga nagłówka x-haslo = DEMO_HASLO):
  GET  /zdrowie   -> {"gotowy": bool, "model": "lite|pro", "portret": sha256|null}
  POST /portret   body = JPG/PNG              -> {"portret": sha256}   (ustawia twarz, zeruje ruch)
  POST /mow       body = MP3/WAV, nagłówek x-portret = sha256 portretu
                  -> video/mp4 512x512, 25 kl./s, bez dźwięku; 409 gdy portret inny niż ustawiony
Ruch głowy płynie dalej między kolejnymi /mow (silnik pamięta ostatnie klatki i 8 s dźwięku),
więc kolejne zdania jednej odpowiedzi łączą się bez skoku.

Ustawienia (zmienne środowiska poda):
  DEMO_HASLO      — wymagane (min. 10 znaków); to samo hasło wpisane w Vercel jako TWARZ_HASLO
  TYMON_ADRES     — np. https://tymon.vercel.app; jeśli jest, usługa co 60 s zgłasza Tymonowi swój adres
  TWARZ_MODEL     — lite (domyślnie, szybki) albo pro (ładniejszy, wolniejszy)
  TWARZ_FACE_CROP — 1 = wytnij twarz z portretu (więcej szczegółów ust), 0 = cały kadr (domyślnie)
  TWARZ_SEED      — liczba, domyślnie 9999
  TWARZ_BEZCZYNNOSC_MIN — po tylu minutach bez /mow maszyna sama się zatrzymuje (domyślnie 20)

v3 (28.10, list Tymona):
  • ROZGRZEWKA: pierwszy film po starcie kompilował się 147 s. Teraz zaraz po wczytaniu modelu
    usługa robi sama 2 s filmu z szarym portretem i ciszą, i dopiero potem melduje gotowość.
    Pamięć kompilacji leży na wolumenie (uruchom.sh), więc kolejne maszyny rozgrzewają się szybciej.
  • SAMOWYŁĄCZENIE: druga linia obrony obok strażnika w Vercelu — po TWARZ_BEZCZYNNOSC_MIN
    minutach bez zdania maszyna zatrzymuje się sama (runpodctl, klucz poda od RunPod).
Logi: tylko liczby i kody, bez treści.
"""
import hashlib
import io
import hmac
import json
import os
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request
from collections import deque

import numpy as np
from flask import Flask, Response, jsonify, request

# Kod FlashHead leży w bieżącym katalogu (uruchom.sh robi cd /workspace/SoulX-FlashHead),
# a Python domyślnie szuka modułów obok tego pliku — dopisujemy bieżący katalog.
sys.path.insert(0, os.getcwd())

HASLO = os.environ.get("DEMO_HASLO", "")
if len(HASLO) < 10:
    sys.exit("BRAK albo za krótkie DEMO_HASLO (min. 10 znaków) — nie uruchamiam usługi bez hasła.")
MODEL = os.environ.get("TWARZ_MODEL", "lite").strip().lower()
if MODEL not in ("lite", "pro"):
    sys.exit("TWARZ_MODEL musi być lite albo pro.")
FACE_CROP = os.environ.get("TWARZ_FACE_CROP", "0").strip() == "1"
SEED = int(os.environ.get("TWARZ_SEED", "9999"))
TYMON_ADRES = os.environ.get("TYMON_ADRES", "").strip().rstrip("/")
POD_ID = os.environ.get("RUNPOD_POD_ID", "").strip()
PORT = 7860
MAKS_DZWIEK_B = 3 * 1024 * 1024     # jedno zdanie z ElevenLabs to zwykle < 300 KB
MAKS_PORTRET_B = 8 * 1024 * 1024
MAKS_DZWIEK_S = 60.0
BEZCZYNNOSC_S = int(os.environ.get("TWARZ_BEZCZYNNOSC_MIN", "20")) * 60
ostatnia_aktywnosc = time.time()

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = MAKS_PORTRET_B

stan = {"gotowy": False, "blad": None, "portret": None}
blokada = threading.Lock()          # karta graficzna robi jedną rzecz naraz
pipeline = None
P = None                            # parametry z infer_params.yaml
dzwiek_dq = None                    # ostatnie 8 s dźwięku (ciągłość ruchu między zdaniami)


def log(*czesci):
    print(time.strftime("%H:%M:%S"), "TWARZ", *czesci, flush=True)


def sprawdz_haslo():
    dane = request.headers.get("x-haslo", "")
    return hmac.compare_digest(dane.encode("utf-8"), HASLO.encode("utf-8"))


@app.before_request
def wymagaj_hasla():
    if not sprawdz_haslo():
        return jsonify({"blad": "haslo"}), 401
    return None


def wczytaj_model():
    global pipeline, P
    try:
        from flash_head.inference import get_infer_params, get_pipeline
        t0 = time.time()
        pipeline = get_pipeline(world_size=1, ckpt_dir="models/SoulX-FlashHead-1_3B",
                                model_type=MODEL, wav2vec_dir="models/wav2vec2-base-960h")
        P = get_infer_params()
        log(f"model={MODEL} wczytany ms={int((time.time() - t0) * 1000)}")
        rozgrzej()
        stan["gotowy"] = True
    except Exception as e:  # noqa: BLE001 — chcemy zobaczyć każdy błąd w /zdrowie
        stan["blad"] = type(e).__name__
        log(f"BLAD wczytania modelu: {type(e).__name__}: {e}")


def rozgrzej():
    """Jeden krótki film „na sucho”, żeby kompilacja nie spadła na pierwsze zdanie Tymona."""
    from PIL import Image
    t0 = time.time()
    try:
        bufor = io.BytesIO()
        Image.new("RGB", (512, 512), (128, 128, 128)).save(bufor, format="PNG")
        with blokada:
            ustaw_portret(bufor.getvalue())
            generuj_klatki(np.zeros(2 * P["sample_rate"], dtype=np.float32))
        log(f"rozgrzewka ms={int((time.time() - t0) * 1000)}")
    except Exception as e:  # noqa: BLE001 — rozgrzewka nie może zablokować usługi
        log(f"rozgrzewka nieudana ({type(e).__name__}) ms={int((time.time() - t0) * 1000)}")
    finally:
        stan["portret"] = None  # prawdziwy portret dośle Tymon (409 -> /portret)


def pilnuj_bezczynnosci():
    """Po BEZCZYNNOSC_S bez zdań: zatrzymaj tę maszynę (RunPod daje podowi własny klucz)."""
    while True:
        time.sleep(30)
        if not stan["gotowy"] or not POD_ID:
            continue
        cisza = time.time() - ostatnia_aktywnosc
        if cisza < BEZCZYNNOSC_S:
            continue
        log(f"bezczynnosc s={int(cisza)} — zatrzymuje maszyne")
        for polecenie in (["runpodctl", "pod", "stop", POD_ID], ["runpodctl", "stop", "pod", POD_ID]):
            try:
                wynik = subprocess.run(polecenie, capture_output=True, timeout=60)
                log(f"{' '.join(polecenie[:3])} kod={wynik.returncode}")
                if wynik.returncode == 0:
                    return
            except Exception as e:  # noqa: BLE001
                log(f"{' '.join(polecenie[:3])} wyjatek={type(e).__name__}")
        time.sleep(300)  # nie udało się — spróbujemy za 5 min (strażnik w Vercelu i tak czuwa)


def ustaw_portret(dane: bytes) -> str:
    """Przygotowuje portret i zeruje ruch (start od twarzy z portretu)."""
    global dzwiek_dq
    from flash_head.inference import get_base_data
    sha = hashlib.sha256(dane).hexdigest()
    with tempfile.TemporaryDirectory() as kat:
        sciezka = os.path.join(kat, "portret.png")
        with open(sciezka, "wb") as f:
            f.write(dane)
        get_base_data(pipeline, cond_image_path_or_dir=sciezka, base_seed=SEED, use_face_crop=FACE_CROP)
    dlugosc = P["sample_rate"] * P["cached_audio_duration"]
    dzwiek_dq = deque([0.0] * dlugosc, maxlen=dlugosc)
    stan["portret"] = sha
    return sha


def dekoduj_dzwiek(dane: bytes) -> np.ndarray:
    """MP3/WAV -> mono float32 16 kHz (ffmpeg)."""
    wynik = subprocess.run(
        ["ffmpeg", "-hide_banner", "-loglevel", "error", "-i", "pipe:0",
         "-f", "f32le", "-ac", "1", "-ar", str(P["sample_rate"]), "pipe:1"],
        input=dane, capture_output=True, check=True, timeout=30)
    return np.frombuffer(wynik.stdout, dtype=np.float32).copy()


def generuj_klatki(dzwiek: np.ndarray) -> np.ndarray:
    """Tryb strumieniowy autorów, z pamięcią między wywołaniami. Zwraca (T, 512, 512, 3) uint8."""
    from flash_head.inference import get_audio_embedding, run_pipeline
    sr, fps = P["sample_rate"], P["tgt_fps"]
    frame_num, motion = P["frame_num"], P["motion_frames_num"]
    slice_len = frame_num - motion
    probki_na_kawalek = slice_len * sr // fps
    koniec = P["cached_audio_duration"] * fps
    poczatek = koniec - frame_num

    ile_klatek = int(np.ceil(len(dzwiek) * fps / sr))
    reszta = len(dzwiek) % probki_na_kawalek
    if reszta:
        dzwiek = np.concatenate([dzwiek, np.zeros(probki_na_kawalek - reszta, dtype=np.float32)])
    kawalki = dzwiek.reshape(-1, probki_na_kawalek)

    klatki = []
    for kawalek in kawalki:
        dzwiek_dq.extend(kawalek.tolist())
        emb = get_audio_embedding(pipeline, np.array(dzwiek_dq), poczatek, koniec)
        wideo = run_pipeline(pipeline, emb)[motion:]
        klatki.append(wideo.cpu().numpy().astype(np.uint8))
    return np.concatenate(klatki, axis=0)[:ile_klatek]


def zakoduj_mp4(klatki: np.ndarray) -> bytes:
    t, h, w, _ = klatki.shape
    with tempfile.TemporaryDirectory() as kat:
        cel = os.path.join(kat, "twarz.mp4")
        subprocess.run(
            ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
             "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{w}x{h}", "-r", str(P["tgt_fps"]), "-i", "pipe:0",
             "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "21", "-pix_fmt", "yuv420p",
             "-movflags", "+faststart", cel],
            input=klatki.tobytes(), check=True, timeout=60)
        with open(cel, "rb") as f:
            return f.read()


@app.get("/zdrowie")
def zdrowie():
    return jsonify({"gotowy": stan["gotowy"], "model": MODEL, "portret": stan["portret"],
                    "blad": stan["blad"], "wersja": "v3"})


@app.post("/portret")
def portret():
    if not stan["gotowy"]:
        return jsonify({"blad": "laduje"}), 503
    dane = request.get_data()
    if not dane or len(dane) > MAKS_PORTRET_B:
        return jsonify({"blad": "portret"}), 400
    global ostatnia_aktywnosc
    ostatnia_aktywnosc = time.time()
    with blokada:
        t0 = time.time()
        try:
            sha = ustaw_portret(dane)
        except Exception as e:  # noqa: BLE001
            log(f"BLAD portretu: {type(e).__name__}")
            return jsonify({"blad": "portret"}), 400
        log(f"portret ustawiony ms={int((time.time() - t0) * 1000)} bajty={len(dane)}")
    return jsonify({"portret": sha})


@app.post("/mow")
def mow():
    if not stan["gotowy"]:
        return jsonify({"blad": "laduje"}), 503
    if not stan["portret"] or request.headers.get("x-portret", "") != stan["portret"]:
        return jsonify({"blad": "portret", "portret": stan["portret"]}), 409
    dane = request.get_data()
    if not dane or len(dane) > MAKS_DZWIEK_B:
        return jsonify({"blad": "dzwiek"}), 400
    global ostatnia_aktywnosc
    ostatnia_aktywnosc = time.time()
    with blokada:
        t0 = time.time()
        try:
            dzwiek = dekoduj_dzwiek(dane)
        except Exception:  # noqa: BLE001
            return jsonify({"blad": "dzwiek"}), 400
        sekundy = len(dzwiek) / P["sample_rate"]
        if sekundy <= 0.05 or sekundy > MAKS_DZWIEK_S:
            return jsonify({"blad": "dlugosc"}), 400
        t1 = time.time()
        try:
            klatki = generuj_klatki(dzwiek)
            t2 = time.time()
            mp4 = zakoduj_mp4(klatki)
        except Exception as e:  # noqa: BLE001
            log(f"BLAD renderu: {type(e).__name__}: {e}")
            return jsonify({"blad": "render"}), 500
        t3 = time.time()
    ms = lambda a, b: int((b - a) * 1000)  # noqa: E731
    log(f"mow dzwiek_ms={int(sekundy * 1000)} klatki={len(klatki)} dekod_ms={ms(t0, t1)} "
        f"render_ms={ms(t1, t2)} mp4_ms={ms(t2, t3)} mp4_kb={len(mp4) // 1024}")
    odp = Response(mp4, mimetype="video/mp4")
    odp.headers["x-render-ms"] = str(ms(t1, t2))
    odp.headers["x-calosc-ms"] = str(ms(t0, t3))
    odp.headers["x-dzwiek-ms"] = str(int(sekundy * 1000))
    odp.headers["Cache-Control"] = "no-store"
    return odp


def zglaszaj_adres():
    """Co 60 s mówi Tymonowi, pod jakim adresem jest twarz (adres poda zmienia się przy każdej maszynie)."""
    if not TYMON_ADRES or not POD_ID:
        log("bez zgłaszania adresu (brak TYMON_ADRES albo RUNPOD_POD_ID)")
        return
    if not TYMON_ADRES.startswith("https://"):
        log("TYMON_ADRES musi zaczynać się od https:// — nie zgłaszam")
        return
    adres = f"https://{POD_ID}-{PORT}.proxy.runpod.net"
    while True:
        try:
            cialo = json.dumps({"adres": adres, "gotowy": stan["gotowy"], "model": MODEL}).encode()
            zad = urllib.request.Request(f"{TYMON_ADRES}/api/twarz-silnik", data=cialo, method="POST",
                                         headers={"content-type": "application/json", "x-haslo": HASLO})
            with urllib.request.urlopen(zad, timeout=10) as odp:
                kod = odp.status
        except urllib.error.HTTPError as e:
            kod = e.code
        except Exception as e:  # noqa: BLE001
            kod = type(e).__name__
        log(f"zgloszenie adresu kod={kod} gotowy={stan['gotowy']}")
        time.sleep(60)


if __name__ == "__main__":
    threading.Thread(target=wczytaj_model, daemon=True).start()
    threading.Thread(target=zglaszaj_adres, daemon=True).start()
    threading.Thread(target=pilnuj_bezczynnosci, daemon=True).start()
    log(f"usluga startuje port={PORT} model={MODEL} face_crop={int(FACE_CROP)}")
    app.run(host="0.0.0.0", port=PORT, threaded=True)
