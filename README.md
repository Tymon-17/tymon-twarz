# tymon-twarz — silnik twarzy Tymona (v2)

Osobny moduł: **portret + dźwięk → mówiąca twarz**. Nie zna Tymona, jego pamięci ani rozmów.
Dostaje tylko zdjęcie i nagranie głosu. Model językowy i silnik twarzy można wymieniać niezależnie.

- **v1 (27.10.2026):** silnik **SoulX-FlashHead** na stronie demo autorów, za hasłem.
- **v2 (28.10.2026):** **usługa dla aplikacji Tymona**:
  - po włączeniu maszyny twarz sama pojawia się w rozmowie i mówi razem z głosem;
  - strona demo nadal jest dostępna (tryb `plik`).

W repozytorium jest sam kod. Nie ma tu kluczy, zdjęcia Tymona ani nagrań.

---

## Ustawienia jednorazowe

### Szablon w RunPod (`tymon-twarz`)
RunPod → **Templates** → `tymon-twarz` → **Edit**:
- **Container image:** `runpod/pytorch:1.4.1-cu1281-torch280-ubuntu2204`
- **Container disk:** 60 GB, bez wolumenu
- **HTTP ports:** `8888`, `7860`
- **Environment variables:**
  - `DEMO_HASLO` — Twoje hasło do twarzy (min. 10 znaków)
  - `TYMON_ADRES` — adres, pod którym otwierasz Tymona, np. `https://twoj-tymon.vercel.app`
    (bez ukośnika na końcu)
  - (opcjonalnie) `TWARZ_MODEL` = `pro` — ładniejsza, ale wolniejsza; domyślnie `lite`

### Vercel (projekt `tymon`, main)
- Settings → Environment Variables → nowa zmienna **`TWARZ_HASLO`**, wartość **dokładnie taka sama** jak `DEMO_HASLO` → Save → Redeploy.

---

## Rozmowa z twarzą (za każdym razem)
1. RunPod → **Pods** → **Deploy** → szablon `tymon-twarz` → **RTX 4090**, Secure, On-Demand → **Deploy Pod**.
2. **Connect** → **Jupyter Lab** → **File → New → Terminal**, wklej i Enter:
   ```
   curl -fsSL https://raw.githubusercontent.com/Tymon-17/tymon-twarz/main/start.sh | bash
   ```
3. Po ok. 10 min pojawi się napis **„Usługa twarzy startuje w tle”**. Wczytanie modelu trwa jeszcze 1–2 min.
4. W aplikacji Tymona włącz przycisk **twarz**. W ciągu ok. 30 s twarz zacznie mówić filmem zamiast zdjęcia.
5. **Koniec:** RunPod → **Stop** → **⋮ → Terminate**. Po ok. 2,5 min aplikacja sama wraca do zdjęcia.

Maszyna kosztuje ok. **0,90 $ za godzinę**, dopóki istnieje — także wtedy, gdy nic nie mówisz.

### Strona demo zamiast usługi
W terminalu poda:
- `bash /workspace/tymon-twarz/uruchom.sh plik` — strona demo (Connect → HTTP Service 7860, login `tymon`);
- `bash /workspace/tymon-twarz/uruchom.sh usluga` — powrót do Tymona.

### Coś nie działa?
```
tail -n 40 /workspace/twarz-instalacja.log
tail -n 40 /workspace/twarz-usluga.log
```
i wklej Sweterkowi wynik. Dziennik usługi zawiera tylko liczby (czasy, rozmiary), bez treści.

---

## Jak to działa (dla ciekawych)
- `usluga.py` — okienko HTTP na porcie 7860. Każde wywołanie wymaga hasła.
  - `/zdrowie` — czy model jest gotowy;
  - `/portret` — ustawia twarz;
  - `/mow` — dźwięk jednego zdania → film mp4 512×512, 25 kl./s, bez dźwięku.
- Ruch głowy płynie dalej między zdaniami: usługa pamięta ostatnie klatki i 8 s dźwięku.
- Adres maszyny zmienia się przy każdej nowej maszynie. Usługa co 60 s zgłasza go Tymonowi (`TYMON_ADRES/api/twarz-silnik`). Tymon przyjmuje tylko adresy RunPod dla portu 7860.
- Do maszyny trafiają tylko portret i dźwięk zdań. Rozmowa i pamięć tu nie trafiają.

## Bezpieczeństwo
- Hasło (`DEMO_HASLO`) jest wyłącznie w ustawieniach poda i w Vercelu (`TWARZ_HASLO`), nigdy w kodzie.
- Publiczne linki Gradio są wyłączone (`share=False`), analityka Gradio też.

## Licencje (do potwierdzenia przed codziennym użyciem)
- SoulX-FlashHead: wagi transformera i VAE Wan — Apache-2.0; VAE LTX (wariant Lite) — OpenRAIL-M.
- wav2vec2-base-960h — Apache-2.0.

## Pliki
- `start.sh` — instalacja i start usługi
- `uruchom.sh` — tryb `usluga` (domyślnie), `plik` albo `strumien`
- `usluga.py` — usługa dla aplikacji Tymona
- `zabezpiecz.py` — zabezpieczenie strony demo: hasło, brak publicznych linków, port 7860
