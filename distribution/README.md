# AstroForge — avvio rapido

## 1. Installa Docker Desktop (una volta sola)

Scarica e installa da: https://www.docker.com/products/docker-desktop/

Durante l'installazione lascia tutte le opzioni di default. Al termine, apri
Docker Desktop e aspetta che l'icona nella barra in alto (Mac) o in basso a
destra (Windows) smetta di muoversi: significa che è pronto.

## 2. Avvia AstroForge

Nella cartella `distribution`, fai doppio click sul file giusto per il tuo
computer:

- **Windows** → `avvia.bat`
- **Mac** → `avvia.command`
- **Linux** → `avvia.sh`

Si aprirà una finestra nera (il terminale): è normale, mostra cosa sta
succedendo. La prima volta impiega un paio di minuti per scaricare tutto;
le volte successive è molto più veloce.

Quando è tutto pronto si aprirà la dashboard di AstroForge direttamente in
quella finestra.

## 3. Usa la dashboard

Tasti principali:

| Tasto | Cosa fa |
|---|---|
| `h` | Home |
| `a` | Elenco asteroidi |
| `c` | Grafici |
| `p` | Avvia analisi |
| `l` | Log |
| `q` | Esci |

## 4. Per chiudere tutto

Premi `q` nella dashboard: la finestra si occuperà da sola di spegnere tutti
i servizi. Puoi anche chiudere semplicemente la finestra del terminale.

## Problemi comuni

- **"Docker non è installato"**: torna al punto 1.
- **La finestra si chiude subito con un errore**: assicurati che Docker
  Desktop sia aperto e completamente avviato prima di lanciare lo script.
- **Va tutto lentissimo la prima volta**: normale, sta scaricando le
  immagini da internet. Serve una connessione decente.
