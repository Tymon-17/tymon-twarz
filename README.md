# tymon-twarz — silnik twarzy Tymona (prototyp v1)

Osobny moduł: **portret + dźwięk → mówiąca twarz**. Nie zna Tymona, jego pamięci ani rozmów.
Dostaje tylko zdjęcie i nagranie głosu. Model językowy i silnik twarzy można wymieniać niezależnie.

**v1 (27.10.2026):** silnik **SoulX-FlashHead** (1,3 mld parametrów, jedno zdjęcie + dźwięk,
wersja Lite do ~96 klatek/s na RTX 4090). Strona demo autorów, uruchomiona za hasłem i bez publicznych linków.
Kolejne wersje: Ditto i MuseTalk do porównania, potem stany (słucha / cisza / mówi) i strumień.

W repozytorium jest sam kod. Nie ma tu kluczy, zdjęcia Tymona ani nagrań — te wgrywasz tylko na stronie demo, na czas próby.

---

## Jak uruchomić (dla Oli, krok po kroku)

### 0. Przygotuj (raz)
- **Portret Tymona** (to samo kanoniczne zdjęcie, JPG/PNG).
- **Trzy nagrania głosu Tymona z ElevenLabs** (MP3 albo WAV, po 10–30 sekund): spokojne, emocjonalne, ciche.

### 1. Maszyna w RunPod
1. RunPod → **Pods** → **Deploy**.
2. Wybierz **Secure Cloud** i kartę **RTX 4090** (24 GB). Jeśli jest filtr „CUDA version” — 12.8 lub nowsza.
3. Szablon (Template): **Runpod Pytorch** (dowolna aktualna wersja).
4. Kliknij **Edit Template** i ustaw:
   - **Container Disk:** 20 GB
   - **Volume Disk:** 40 GB (ścieżka `/workspace`)
   - **Expose HTTP Ports:** dopisz `7860` (zostaw `8888`)
   - **Environment Variables:** klucz `DEMO_HASLO`, wartość: twoje hasło do strony demo, min. 10 znaków
     (inne niż hasło do Tymona).
5. Typ: **On-Demand** (nie Spot) → **Deploy**.

### 2. Instalacja (raz na maszynę, ok. 15–25 min)
1. Gdy pod ma status **Running**: **Connect** → **Jupyter Lab** (port 8888) → **Terminal**
   (albo przycisk **Web Terminal**, jeśli jest).
2. Wklej i zatwierdź Enterem:
   ```
   curl -fsSL https://raw.githubusercontent.com/Tymon-17/tymon-twarz/main/start.sh | bash
   ```
3. Poczekaj, aż na końcu pojawi się: **„Strona demo startuje w tle”**.

### 3. Próba
1. **Connect** → **HTTP Service [Port 7860]**. Login: `tymon`, hasło: twoje `DEMO_HASLO`.
2. Wgraj portret i pierwsze nagranie → generuj. Potem dwa pozostałe.
3. Zanotuj dla każdego nagrania: długość nagrania, ile trwało generowanie, jak wyglądają usta,
   oczy, ruch głowy (i czy nos został krzywy 🙂).
4. Demo na żywo (opcjonalnie): w terminalu `bash /workspace/tymon-twarz/uruchom.sh strumien`,
   potem odśwież stronę 7860. Powrót: `bash /workspace/tymon-twarz/uruchom.sh plik`.

### 4. Koniec próby — ważne dla kosztów
- **Stop** — maszyna stoi, dysk zostaje (40 GB ≈ 0,27 $ dziennie). Następnym razem bez instalacji:
  Start → terminal → `bash /workspace/tymon-twarz/uruchom.sh plik`.
- **Terminate** — wszystko usunięte (także zdjęcie i nagrania), nic nie kosztuje.
  Następnym razem instalacja od nowa. **Jeśli przez 2 dni nie testujesz — Terminate.**

### Coś nie działa?
W terminalu:
```
tail -n 40 /workspace/twarz-instalacja.log
tail -n 40 /workspace/twarz-demo.log
```
i wklej Sweterkowi wynik.

---

## Bezpieczeństwo
- Strona demo działa tylko z hasłem (`DEMO_HASLO` w ustawieniach poda, nie w kodzie).
- Publiczne linki Gradio są wyłączone (`share=False`), analityka Gradio wyłączona.
- Oryginalne pliki FlashHead nie są zmieniane; uruchamiana jest zabezpieczona kopia (`zabezpiecz.py`).

## Licencje (do potwierdzenia przed codziennym użyciem)
- SoulX-FlashHead: wagi transformera i VAE Wan — Apache-2.0; VAE LTX (wariant Lite) — OpenRAIL-M.
- wav2vec2-base-960h — Apache-2.0.

## Pliki
- `start.sh` — instalacja + pierwsze uruchomienie
- `uruchom.sh` — uruchomienie strony (tryb `plik` albo `strumien`)
- `zabezpiecz.py` — hasło, brak publicznych linków, port 7860
