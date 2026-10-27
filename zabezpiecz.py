"""Kopia demo FlashHead z dwoma bezpiecznikami (27.10.2026, Sweterek):
1. hasło na stronie (login „tymon”, hasło ze zmiennej DEMO_HASLO), 2. żadnych publicznych linków
(share=True -> share=False), adres 0.0.0.0 dla proxy RunPod. Oryginał zostaje nietknięty."""
import re
import sys

zrodlo, cel = sys.argv[1], sys.argv[2]
s = open(zrodlo, encoding="utf-8").read()
s = s.replace("share=True", "share=False")
s = re.sub(r"server_name\s*=\s*[\"'](127\.0\.0\.1|localhost)[\"']", 'server_name="0.0.0.0"', s)
# Port zawsze 7860 — ten, który wystawiamy w RunPod.
s = re.sub(r"server_port\s*=\s*\d+", "server_port=7860", s)
if ".launch(" not in s:
    sys.exit("Nie znalazłam wywołania .launch( — nie uruchamiam strony bez hasła.")
if "auth=" not in s:
    s = s.replace(".launch(", '.launch(auth=("tymon", __import__("os").environ["DEMO_HASLO"]), ')
open(cel, "w", encoding="utf-8").write(s)
print(f"zabezpieczona kopia: {cel} (hasło: tak, publiczny link: nie)")
