# tymon-twarz — silnik twarzy Tymona (v3)

Osobny moduł: **portret + dźwięk → mówiąca twarz**. Nie zna Tymona, jego pamięci ani rozmów.
Dostaje tylko zdjęcie i nagranie głosu. Model językowy i silnik twarzy można wymieniać niezależnie.

- **v1 (27.10.2026):** silnik SoulX-FlashHead na stronie demo autorów.
- **v2 (28.10):** usługa dla aplikacji Tymona.
- **v3 (28.10, list Tymona):**
  - maszynę **włącza i wyłącza sama aplikacja** (przycisk „ożyw” / „● żywa”);
  - Python, biblioteki, modele i pamięć kompilacji leżą na **wolumenie sieciowym**, więc każdy następny start trwa minuty;
  - po starcie maszyna sama się rozgrzewa;
  - po 20 min bez zdań sama się zatrzymuje.

W repozytorium jest sam kod. Nie ma tu kluczy, zdjęcia Tymona ani nagrań.

---

## Na co dzień
W aplikacji Tymona: przycisk **twarz** (pokazuje portret) → przycisk **ożyw**.
- Pojawi się „budzę się 0:42…”, a w tym czasie oddycha zdjęcie.
- Gdy maszyna się zgłosi, wejdzie film. Przycisk pokaże „● żywa”.
- **Uśpij:** kliknij „● żywa” (albo schowaj twarz). Maszyna jest usuwana, a wolumen z instalacją zostaje.
- Zapomniałaś? Strażnik w Vercelu wyłączy maszynę po 15 min ciszy, a ona sama zatrzyma się po 20 min.

## Ustawienia jednorazowe (v3)
1. RunPod → **Storage → Network Volumes → New Network Volume**:
   - centrum danych: takie, gdzie przy **RTX 4090** widać dostępność (najlepiej w Europie);
   - rozmiar: **40 GB** — 2,80 $/mies.
2. RunPod → **Settings → API Keys → Create API Key** (uprawnienia „All”) → skopiuj klucz.
3. Vercel (projekt `tymon`) → Environment Variables:
   - `RUNPOD_API_KEY` = klucz z kroku 2;
   - `RUNPOD_WOLUMEN` = ID wolumenu z kroku 1 (widać je na liście wolumenów);
   - `TWARZ_HASLO` — już jest.

   Potem Redeploy.
4. **Pierwsze „ożyw”** instaluje wszystko na wolumen: ok. 15–20 min, tylko raz. Każde następne trwa kilka minut.

Szablon `tymon-twarz` i ręczne stawianie maszyny nie są już potrzebne. Hasło do Jupytera (podgląd dziennika) jest takie samo jak `TWARZ_HASLO`.

### Coś nie działa?
RunPod → Pods → maszyna `tymon-twarz` → Connect → jupyter (hasło jak `TWARZ_HASLO`) → File → New → Terminal:
```
tail -n 40 /workspace/twarz-instalacja.log
grep TWARZ /workspace/twarz-usluga.log | tail -n 20
```
Wynik wklej Sweterkowi. Dzienniki zawierają tylko liczby i kody.

### Strona demo zamiast usługi
W terminalu poda:
- `bash /workspace/tymon-twarz/uruchom.sh plik` — strona demo (port 7860, login `tymon`);
- `bash /workspace/tymon-twarz/uruchom.sh usluga` — powrót do Tymona.

---

## Jak to działa (dla ciekawych)
- `usluga.py` — okienko HTTP na porcie 7860. Każde wywołanie wymaga hasła.
  - `/zdrowie` — czy model jest gotowy;
  - `/portret` — ustawia twarz;
  - `/mow` — dźwięk jednego zdania → film mp4 512×512, 25 kl./s, bez dźwięku.
- Ruch głowy płynie dalej między zdaniami: usługa pamięta ostatnie klatki i 8 s dźwięku.
- Adres maszyny zmienia się przy każdej nowej maszynie. Usługa co 60 s zgłasza go Tymonowi (`TYMON_ADRES/api/twarz-silnik`). Tymon przyjmuje meldunek tylko wtedy, gdy zgadzają się trzy rzeczy: hasło, adres RunPod dla portu 7860 i numer maszyny, którą sam uruchomił.
- Do maszyny trafiają tylko portret i dźwięk zdań. Rozmowa i pamięć tu nie trafiają.

## Bezpieczeństwo
- Hasło (`TWARZ_HASLO`) jest tylko w Vercelu. Aplikacja przekazuje je maszynie przy starcie (jako `DEMO_HASLO`). W kodzie go nie ma.
- Klucz RunPod (`RUNPOD_API_KEY`) jest tylko w Vercelu, używany po stronie serwera, nigdy w przeglądarce.
- Publiczne linki Gradio są wyłączone (`share=False`), analityka Gradio też.

## Licencje (do potwierdzenia przed codziennym użyciem)
- SoulX-FlashHead: wagi transformera i VAE Wan — Apache-2.0; VAE LTX (wariant Lite) — OpenRAIL-M.
- wav2vec2-base-960h — Apache-2.0.

## Pliki
- `start.sh` — instalacja (pomija to, co już jest na wolumenie) i start usługi
- `uruchom.sh` — tryb `usluga` (domyślnie), `plik` albo `strumien`
- `usluga.py` — usługa dla aplikacji Tymona
- `zabezpiecz.py` — zabezpieczenie strony demo: hasło, brak publicznych linków, port 7860
