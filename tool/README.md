# French Proxy Tool — IP française pour IXBrowser

Trouve des proxies FRANÇAIS **vivants** (testés en VRAI : l'IP de sortie est vérifiée
à travers le proxy via `ip-api.com`) puis sert-les à IXBrowser.

## Pourquoi pas une extension Chrome ?

Chrome/Chromium (et donc IXBrowser) interdit à une extension de router le trafic
par un proxy : `chrome.proxy` est limité en MV3, et le `fetch` d'une extension ne
passe jamais par le proxy (l'IP de sortie ne peut pas être vérifiée). C'est la
solution 100% fiable : IXBrowser gère lui-même le proxy par profil.

## Mode 1 — Trouver une liste de proxies FR

Double-clic sur `trouver_proxies_fr.bat` (ou) :

```
python french_proxy_tool.py list --count 8
```

Résultat : `proxies_fr.txt` (un `ip:port` par ligne) + affichage à l'écran.

Puis dans IXBrowser : **Profil → Paramètres → Proxy → type HTTP → colle `ip:port`**.
Utilise une IP différente par profil.

## Mode 2 — Serveur local avec rotation automatique

Double-clic sur `serveur_ip_fr.bat` (ou) :

```
python french_proxy_tool.py serve --port 8080 --count 15
```

Puis dans IXBrowser, pour CHAQUE profil : **proxy type HTTP → `127.0.0.1:8080`**.
Chaque nouvelle connexion sort par une IP française différente (rotation).
IP fraîche à chaque compte, automatiquement.

## Vérifier une IP

Ouvre dans le profil IXBrowser : `http://ip-api.com/json` → le pays doit être `FR`.

## Avertissement honnête

Les proxies FR gratuits sont rares (1 à 3 vivants à un instant T) et meurent en
quelques minutes. Le mode `list` peut prendre 2 à 5 minutes. Pour de gros volumes
de comptes, un petit lot de proxies payants (~2-5 €/mois) reste la seule solution
stable — mais pour du test/usage léger, cet outil suffit.
