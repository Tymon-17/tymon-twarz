"""Pomiar kompilacji twarzy (v4, 29.10.2026, Sweterek; zamówienie Tymona).

Uruchom w terminalu poda (Jupyter -> Terminal), gdy twarz w aplikacji świeci „● żywa”:
    python /workspace/tymon-twarz/pomiar.py

Prosi działającą usługę (port 7860) o pomiar: te same nagrania testowe najpierw z kompilacją
(torch.compile), potem bez niej. Hasło bierze sam z ustawień poda (DEMO_HASLO) — nic nie wpisujesz
i nic nie jest wypisywane. Wynik: tabelka na ekranie i plik /workspace/pomiar-kompilacji-*.txt.
Trwa zwykle 2–6 minut. W tym czasie nie pisz do Tymona (karta jest zajęta pomiarem).
"""
import json
import os
import time
import urllib.error
import urllib.request


def haslo() -> str:
    h = os.environ.get("DEMO_HASLO", "")
    if h:
        return h
    # Terminal Jupytera nie zawsze dziedziczy zmienne poda — wtedy czytamy je z procesu startowego.
    try:
        with open("/proc/1/environ", "rb") as f:
            for para in f.read().split(b"\0"):
                if para.startswith(b"DEMO_HASLO="):
                    return para.split(b"=", 1)[1].decode()
    except OSError:
        pass
    return ""


def main() -> None:
    h = haslo()
    if not h:
        print("Nie widzę DEMO_HASLO w ustawieniach poda — pomiar nie ruszy.")
        return
    print("Pomiar ruszył (2–6 min). Nie zamykaj tego okna i nie pisz teraz do Tymona…", flush=True)
    zad = urllib.request.Request("http://127.0.0.1:7860/pomiar", data=b"{}", method="POST",
                                 headers={"x-haslo": h, "content-type": "application/json"})
    t0 = time.time()
    try:
        with urllib.request.urlopen(zad, timeout=1200) as odp:
            wynik = json.loads(odp.read())
    except urllib.error.HTTPError as e:
        try:
            wynik = json.loads(e.read())
        except Exception:  # noqa: BLE001
            wynik = {"blad": f"http_{e.code}"}
    except Exception as e:  # noqa: BLE001
        print(f"Usługa nie odpowiedziała ({type(e).__name__}). Czy twarz świeci „● żywa”?")
        return

    linie = [f"POMIAR KOMPILACJI  {time.strftime('%Y-%m-%d %H:%M')}  model={wynik.get('model')}  "
             f"karta={wynik.get('karta')}  calosc_s={int(time.time() - t0)}"]
    if wynik.get("blad"):
        linie.append(f"BLAD: {wynik['blad']}  (pełny opis: grep 'TWARZ' /workspace/twarz-usluga.log | tail -20)")
    if wynik.get("uwaga"):
        linie.append(f"uwaga: {wynik['uwaga']}")
    linie.append("")
    linie.append(f"{'tryb':<16}{'dzwiek_ms':>10}{'render_ms':>11}{'mp4_ms':>8}{'wsp':>7}{'wsp_z_mp4':>11}")
    for t in wynik.get("tryby", []):
        for z in t["zdania"]:
            linie.append(f"{t['tryb']:<16}{z['dzwiek_ms']:>10}{z['render_ms']:>11}{z['mp4_ms']:>8}"
                         f"{z['wsp']:>7.2f}{z['wsp_z_mp4']:>11.2f}")
        suma_d = sum(z["dzwiek_ms"] for z in t["zdania"]) or 1
        suma_r = sum(z["render_ms"] for z in t["zdania"])
        linie.append(f"{t['tryb']:<16} RAZEM wsp={suma_r / suma_d:.2f}  rozgrzewka_ms={t['rozgrzewka_ms']}  "
                     f"pamiec_karty_mb={t['pamiec_karty_mb']}")
        linie.append("")
    linie.append("wsp = render / długość dźwięku. Poniżej 1,00 = film powstaje szybciej, niż trwa zdanie.")
    tekst = "\n".join(linie)
    print("\n" + tekst)
    plik = f"/workspace/pomiar-kompilacji-{time.strftime('%Y%m%d-%H%M')}.txt"
    try:
        with open(plik, "w", encoding="utf-8") as f:
            f.write(tekst + "\n")
        print(f"\nZapisane: {plik}")
    except OSError:
        print("\n(Nie udało się zapisać pliku — wystarczy tabelka z ekranu.)")
    print("Skopiuj całą tabelkę z ekranu i wklej ją Sweterkowi.")


if __name__ == "__main__":
    main()
