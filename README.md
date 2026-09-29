# JOERIRZN.com – statische website

De map `site/` is de complete website. Alleen die map hoeft online. `media/` en `logos/` zijn de originele bronbestanden en worden niet gebruikt door de site.

```
site/
├── index.html              Home
├── artworks/index.html     /artworks/
├── branding/index.html     /branding/
├── video/index.html        /video/
├── packaging/index.html    /packaging/
├── 3d/index.html           /3d/
├── 404.html
├── sitemap.xml, robots.txt, site.webmanifest
└── assets/
    ├── css/style.css       alle opmaak
    ├── js/main.js          menu, video's, YouTube, teller, packaging-scroll
    ├── img/                geoptimaliseerde WebP-afbeeldingen (2 formaten per beeld)
    ├── video/              mp4's
    ├── logos/              klantlogo's (SVG)
    ├── fonts/              Roboto (lokaal, geen Google Fonts nodig)
    └── icons/              favicons
```

## Lokaal bekijken

De links zijn absoluut (`/artworks/`), dus open de site via een lokale server en niet door `index.html` dubbel te klikken:

```sh
cd site
python3 -m http.server 8000
# open http://localhost:8000
```

## Online zetten

Upload de inhoud van `site/` naar een statische host, bijvoorbeeld Netlify, Vercel, Cloudflare Pages of GitHub Pages (alle vier gratis). Stel daarna het domein `joerirzn.com` in bij de host en verwijs de DNS ernaartoe.
De URL's zijn dezelfde als op Readymag (`/artworks/`, `/branding/`, `/video/`, `/packaging/`, `/3d/`), dus bestaande links en Google-resultaten blijven werken.

Na livegang: meld `https://joerirzn.com/sitemap.xml` aan in Google Search Console.

## Een artwork toevoegen

Elk artwork heeft drie bestanden nodig: twee kleine voor het grid en één grote voor de lightbox.

1. Maak de WebP-versies (vervang `nieuwe-titel` door een korte naam zonder spaties):
   ```sh
   cwebp -q 80 -resize 234 0  "media/Artworks/Nieuwe Titel.jpg" -o site/assets/img/artworks/nieuwe-titel-234.webp
   cwebp -q 80 -resize 468 0  "media/Artworks/Nieuwe Titel.jpg" -o site/assets/img/artworks/nieuwe-titel-468.webp
   cwebp -q 82 -resize 1800 0 "media/Artworks/Nieuwe Titel.jpg" -o site/assets/img/full/nieuwe-titel.webp
   ```
   De eerste twee zijn voor het grid, de derde is de scherpe versie die in de lightbox opent.
   Is je origineel kleiner dan 1800px, laat dan `-resize 1800 0` weg.
2. Kopieer in `site/artworks/index.html` een bestaande regel uit de lijst. Die ziet er zo uit (ingekort):
   ```html
   <li><a class="lb-link" href="/assets/img/full/nieuwe-titel.webp" data-lb data-w="1800" data-h="1800">
     <img src="/assets/img/artworks/nieuwe-titel-234.webp"
          srcset="/assets/img/artworks/nieuwe-titel-234.webp 234w, /assets/img/artworks/nieuwe-titel-468.webp 468w"
          … alt="Artiest – Titel – cover artwork by Joeri RZN" …></a></li>
   ```
3. Pas aan:
   - `href`: de grote versie in `assets/img/full/`.
   - `data-w` en `data-h`: de breedte en hoogte van die grote versie in pixels (bij een vierkant van 1800px: `1800` en `1800`).
     Hiermee zet de lightbox het werk meteen in de juiste verhouding neer.
   - `src` en `srcset`: de twee kleine versies.
   - `alt`: de naam van het werk. Die leest Google en wie een schermlezer gebruikt.
4. De plek in de lijst bepaalt de volgorde, zowel in het grid als bij het bladeren in de lightbox.
   Het grid is 5 kolommen breed; houd het aantal een veelvoud van 5 voor een volle onderste rij.

Werken op de andere categoriepagina's (Branding, 3D, Packaging) werken op dezelfde manier: elk werk is een link
met `data-lb`, `data-w` en `data-h` naar de grote versie in `assets/img/full/`.

## Instagram-previews (onder Connect op home)

De 6 nieuwste posts worden live opgehaald via [Behold](https://behold.so) en werken vanzelf bij.

1. Maak een gratis account op behold.so, koppel @joerirzn en maak een feed aan (type **JSON**).
2. Kopieer de feed-URL, die ziet eruit als `https://feeds.behold.so/AbC123xyz`.
3. Open `site/index.html`, zoek `data-feed="…"` en zet de URL tussen de aanhalingstekens.

De feed is ingesteld op `https://feeds.behold.so/Ba41bk2ruhuOZjTUoZS8`.
Als de feed niet laadt, blijft het blok onzichtbaar. Het gratis plan van Behold ververst ongeveer één keer per dag.

## Build-script (voor ontwikkelaars)

`tools/build/build.py` genereert alle pagina's in `site/` en de geoptimaliseerde afbeeldingen.
Het leest de originele bestanden uit `media/` en `logos/`. `media/` staat niet in git vanwege de grootte (324 MB),
dus bewaar die map zelf goed als je de site opnieuw wilt kunnen bouwen.

```sh
python3 tools/build/build.py   # vereist Python 3 met Pillow (pip3 install pillow)
```

De stijl (`site/assets/css/style.css`) en scripts (`site/assets/js/main.js`) worden niet gegenereerd en pas je direct aan.
