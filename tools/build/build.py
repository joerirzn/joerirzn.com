#!/usr/bin/env python3
"""Build the static JOERIRZN site: optimise images, copy media, render HTML."""
import json, re, shutil, unicodedata, html
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]  # project root (this file lives in tools/build/)
SP = Path(__file__).resolve().parent
SITE = ROOT / 'site'
A = SITE / 'assets'
MEDIA = ROOT / 'media'
LIVE = SP / 'liveraw'
DOMAIN = 'https://joerirzn.com'
TODAY = '2026-09-29'
# Behold feed URL for the Instagram previews under Connect, e.g. 'https://feeds.behold.so/AbC123xyz'.
# Leave empty to hide the block.
INSTAGRAM_FEED = 'https://feeds.behold.so/Ba41bk2ruhuOZjTUoZS8'
# Web3Forms access key for the floating contact form (free, sent to contact@joerirzn.com).
# Empty: the form opens the visitor's mail app with the message filled in instead.
FORM_KEY = '71368b36-5919-42d7-90d6-9e25fffcf5f1'

for d in ['img', 'video', 'logos', 'fonts', 'icons', 'css', 'js']:
    (A / d).mkdir(parents=True, exist_ok=True)


def esc(s):
    return html.escape(s, quote=True)


def slugify(s):
    s = s.replace('Ɐ', 'A').replace('&', ' and ')
    s = unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode()
    s = re.sub(r'[^a-zA-Z0-9]+', '-', s).strip('-').lower()
    return re.sub(r'-+', '-', s)


# ---------------------------------------------------------------- images
def load(src):
    im = Image.open(src)
    im.load()
    if im.mode in ('P', 'LA', 'RGBA', 'PA'):
        im = im.convert('RGBA')
        if im.getchannel('A').getextrema()[0] == 255:
            im = im.convert('RGB')
    else:
        im = im.convert('RGB')
    return im


def fit_crop(im, ar, crop=None):
    if crop:
        x, y, w, h = crop
        return im.crop((round(x), round(y), round(x + w), round(y + h)))
    W, H = im.size
    if abs(W / H - ar) / ar < 0.012:
        return im
    if W / H > ar:  # too wide
        nw = round(H * ar)
        x = (W - nw) // 2
        return im.crop((x, 0, x + nw, H))
    nh = round(W / ar)
    y = (H - nh) // 2
    return im.crop((0, y, W, y + nh))


MANIFEST = {}


def process(src, folder, name, bw, bh, crop=None, scales=(1.5, 3), q=80):
    """Crop to box aspect bw:bh (canvas units) and write WebP variants."""
    key = (str(src), folder, name, bw, bh, crop)
    if key in MANIFEST:
        return MANIFEST[key]
    out_dir = A / 'img' / folder
    out_dir.mkdir(parents=True, exist_ok=True)
    im = fit_crop(load(src), bw / bh, crop)
    widths = []
    for s in scales:
        w = min(round(bw * s), im.width)
        if not widths or w > widths[-1] * 1.15:
            widths.append(w)
    variants = []
    for w in widths:
        h = round(w * im.height / im.width)
        fn = out_dir / f'{name}-{w}.webp'
        if not fn.exists():
            im.resize((w, h), Image.LANCZOS).save(fn, 'WEBP', quality=q, method=6)
        variants.append(('/' + str(fn.relative_to(SITE)), w, h))
    MANIFEST[key] = variants
    return variants


FULL = {}


def full(src, max_side=1800, q=82):
    """Uncropped, large WebP of the original work for the lightbox (loaded on demand)."""
    key = str(src)
    if key in FULL:
        return FULL[key]
    out_dir = A / 'img' / 'full'
    out_dir.mkdir(parents=True, exist_ok=True)
    fn = out_dir / f'{slugify(Path(key).stem)}.webp'
    if fn.exists():
        with Image.open(fn) as im:
            w, h = im.size
    else:
        im = load(src)
        im.thumbnail((max_side, max_side), Image.LANCZOS)
        im.save(fn, 'WEBP', quality=q, method=6)
        w, h = im.size
    FULL[key] = ('/' + str(fn.relative_to(SITE)), w, h)
    return FULL[key]


def zoom(inner, src, cls='lb-link'):
    """Wrap a thumbnail in a link to its full-size image; JS turns it into a lightbox."""
    fp, fw, fh = full(src)
    return f'<a class="{cls}" href="{fp}" data-lb data-w="{fw}" data-h="{fh}">{inner}</a>'


def sizes_attr(bw, mob):
    return f'(max-width: 768px) {mob}vw, min({bw / 1024 * 100:.1f}vw, {round(bw * 2500 / 1024)}px)'


def img_tag(variants, alt, bw, mob=88, eager=False, cls='', extra=''):
    src, w, h = variants[0]
    srcset = ', '.join(f'{p} {vw}w' for p, vw, _ in variants)
    load_attr = 'fetchpriority="high"' if eager else 'loading="lazy"'
    c = f' class="{cls}"' if cls else ''
    return (f'<img{c} src="{src}" srcset="{srcset}" sizes="{sizes_attr(bw, mob)}" '
            f'width="{w}" height="{h}" alt="{esc(alt)}" {load_attr} decoding="async"{extra}>')


def picture(desk, mobile, alt, bw, eager=False):
    """Art-directed image: separate crop below 768px."""
    msrc = ', '.join(f'{p} {vw}w' for p, vw, _ in mobile)
    _, mw, mh = mobile[0]
    return (f'<picture><source media="(max-width: 768px)" srcset="{msrc}" sizes="88vw" '
            f'width="{mw}" height="{mh}">{img_tag(desk, alt, bw, 88, eager)}</picture>')


# ---------------------------------------------------------------- alt text
def clean_title(fname):
    t = Path(fname).stem
    t = re.sub(r'^Artwork_', '', t)
    t = re.sub(r'^WO_', '', t)
    t = re.sub(r'\s+(V\d+|\d{1,2})$', '', t)
    t = re.sub(r'(_Full|_IG_\d| Without Text)$', '', t)
    t = t.replace('---', ' – ').replace('-', ' ') if '---' in t else t
    t = re.sub(r'\s+-\s+', ' – ', t)
    return re.sub(r'\s+', ' ', t).strip()


# ---------------------------------------------------------------- static assets
def copy_static():
    # fonts
    for f in (SP / 'fonts').glob('*.woff2'):
        shutil.copy(f, A / 'fonts' / f.name)
    # client logos (SVG exported from the current site)
    logo_map = {
        'home-8-77x29.svg': 'warner-music-group', 'home-7-69x29.svg': 'warner-music-benelux',
        'home-4-92x34.svg': 'warner-chappell-music', 'home-1-39x39.svg': 'atlantic-records',
        'home-9-97x27.svg': 'spinnin-records', 'home-5-97x28.svg': 'spinnin-deep',
        'home-2-84x36.svg': 'musical-freedom', 'home-10-86x27.svg': 'cloud-9',
        'home-6-91x28.svg': 'splice', 'home-11-96x23.svg': 'future-rave',
        'home-12-110x20.svg': 'zalando', 'home-3-60x33.svg': 'pgltm',
    }
    for src, name in logo_map.items():
        svg = (SP / 'svg' / src).read_text()
        svg = svg.replace(' role="img"', '')
        (A / 'logos' / f'{name}.svg').write_text(svg)
    # videos
    vids = {
        'pgltm-website.mp4': SP / 'video' / 'pgltm-website-720.m4v',
        'innerjoin-intro.mp4': MEDIA / 'Branding & Identity/Innerjoin/Innerjoin Intro Video.mp4',
        'mp4-player.mp4': MEDIA / '3D Projects/MP4/MP4 Video.mp4',
        'battery.mp4': MEDIA / '3D Projects/Battery/Battery Animation.mp4',
        'gameboy-color-pokemon.mp4': MEDIA / '3D Projects/Gameboy Color Pokémon/Gameboy Color Pokémon Video.mp4',
    }
    for name, src in vids.items():
        dst = A / 'video' / name
        if not dst.exists():
            shutil.copy(src, dst)
    # favicons + og image
    # logos/favicon.png: rounded black square with transparent corners. Browser icons keep the
    # transparency; the Apple touch icon gets a solid background because iOS rounds it itself.
    fav = Image.open(ROOT / 'logos/favicon.png').convert('RGBA')
    for size, name in [(32, 'favicon-32.png'), (192, 'icon-192.png'), (512, 'icon-512.png')]:
        fav.resize((size, size), Image.LANCZOS).save(A / 'icons' / name, optimize=True)
    bg = Image.new('RGBA', fav.size, (0, 0, 0, 255))
    bg.alpha_composite(fav)
    bg.convert('RGB').resize((180, 180), Image.LANCZOS).save(A / 'icons' / 'apple-touch-icon.png', optimize=True)
    # classic /favicon.ico at the site root, which some browsers and crawlers request directly
    fav.save(SITE / 'favicon.ico', sizes=[(16, 16), (32, 32), (48, 48)])
    og = Image.new('RGB', (1200, 630), (0, 0, 0))
    logo = load(ROOT / 'logos/RZN-3D.png')
    logo.thumbnail((1080, 520), Image.LANCZOS)
    og.paste(logo, ((1200 - logo.width) // 2, (630 - logo.height) // 2), logo if logo.mode == 'RGBA' else None)
    og.save(A / 'img' / 'og-image.jpg', quality=86, optimize=True)


# ---------------------------------------------------------------- icons (inline SVG)
def icon_svg(file, w, h):
    svg = (SP / 'svg' / file).read_text()
    svg = re.sub(r'<path d="M0 0H29V29H0V0Z" fill="black"></path>', '', svg)
    svg = re.sub(r'<rect width="24" height="18" fill="black"></rect>', '', svg)
    svg = svg.replace('#999999', 'currentColor').replace(' role="img"', ' aria-hidden="true" focusable="false"')
    svg = svg.replace('<svg ', f'<svg width="{w}" height="{h}" ', 1)
    return re.sub(r'\s*\n\s*', '', svg)


ICON = {}
TRI = ('<svg viewBox="0 0 15 12" aria-hidden="true" focusable="false"><path d="M1.59 9.46A1.66 1.66 0 0 0 3 12h9a1.66 1.66 0 0 0 '
       '1.41-2.54L9.09 2.54a1.88 1.88 0 0 0-3.18 0Z" fill="none" stroke="currentColor" stroke-width="0.6" '
       'vector-effect="non-scaling-stroke" transform="translate(0 -.5)"/></svg>')


# ---------------------------------------------------------------- page chrome
NAV = [('/#work', 'Work', 'work'), ('/#about', 'About', 'about'), ('/#contact', 'Connect', 'contact')]
SOCIAL = [
    ('mailto:contact@joerirzn.com', 'Email', 'mail'),
    ('https://www.instagram.com/joerirzn', 'Instagram', 'instagram'),
    ('https://www.tiktok.com/@joerirzn', 'TikTok', 'tiktok'),
    ('https://www.linkedin.com/in/joeriroozen', 'LinkedIn', 'linkedin'),
]


def head(page):
    url = DOMAIN + page['path']
    ld = ''.join(f'<script type="application/ld+json">{json.dumps(x, ensure_ascii=False, separators=(",", ":"))}</script>\n'
                 for x in page.get('jsonld', []))
    return f'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{esc(page['title'])}</title>
<meta name="description" content="{esc(page['desc'])}">
<link rel="canonical" href="{url}">
<meta name="author" content="Joeri Roozen">
<meta name="theme-color" content="#000000">
<meta name="color-scheme" content="dark">
<meta property="og:type" content="website">
<meta property="og:site_name" content="JOERIRZN">
<meta property="og:locale" content="en_US">
<meta property="og:title" content="{esc(page['title'])}">
<meta property="og:description" content="{esc(page['desc'])}">
<meta property="og:url" content="{url}">
<meta property="og:image" content="{DOMAIN}/assets/img/og-image.jpg">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:image:alt" content="RZN logo">
<meta name="twitter:card" content="summary_large_image">
<link rel="icon" href="/favicon.ico" sizes="any">
<link rel="icon" href="/assets/icons/favicon-32.png" sizes="32x32" type="image/png">
<link rel="icon" href="/assets/icons/icon-192.png" sizes="192x192" type="image/png">
<link rel="apple-touch-icon" href="/assets/icons/apple-touch-icon.png">
<link rel="preload" href="/assets/fonts/roboto-latin.woff2" as="font" type="font/woff2" crossorigin>
{page.get('preload', '')}<link rel="stylesheet" href="/assets/css/style.css">
<script src="/assets/js/main.js" defer></script>
{ld}</head>
'''


def section_head(title, meta='', num=None, hid=None):
    n = f'<span class="section-head__num">{num}</span>' if num else ''
    i = f' id="{hid}"' if hid else ''
    m = f'<span class="section-head__meta">{meta}</span>' if meta else ''
    return (f'<div class="section-head">{n}<h2 class="section-head__title"{i}>{title}</h2>'
            f'<span class="section-head__line" aria-hidden="true"></span>{m}</div>')


def header():
    links = ''.join(f'<li><a href="{h}" data-spy="{k}">{t}</a></li>' for h, t, k in NAV)
    menu = '<li><a href="/">Home</a></li>' + ''.join(f'<li><a href="{h}">{t}</a></li>' for h, t, _ in NAV)
    return f'''<a class="skip-link" href="#main">Skip to content</a>
<header class="site-header">
  <div class="site-header__inner">
    <a class="site-header__logo" href="/" aria-label="JOERIRZN home">{ICON['logo_white']}</a>
    <nav class="site-nav" aria-label="Sections"><ul>{links}</ul></nav>
    <button class="menu-toggle" type="button" aria-expanded="false" aria-controls="site-menu" aria-label="Open menu">
      <span class="menu-toggle__dots" aria-hidden="true"><i></i><i></i><i></i></span>
    </button>
  </div>
</header>
<nav class="site-menu" id="site-menu" aria-label="Main">
  <ul>{menu}</ul>
</nav>
''' + quick_contact()


QC_STEPS = ('Nice to meet you', 'Tell me a bit more', 'Your message')
QC_TYPES = ('Brand / Company', 'Agency / Studio', 'Creator / Artist', 'Music / Entertainment', 'Events', 'Just me', 'Other')
QC_TOPICS = ('Artwork', 'Branding', 'Video & Motion', 'Packaging', '3D', 'Something else')


def chips(name, kind, values):
    return ''.join(f'<label class="qc__chip"><input type="{kind}" name="{name}" value="{esc(v)}"><span>{esc(v)}</span></label>'
                   for v in values)


def quick_contact():
    """Floating contact button (bottom right) that opens a small form in three steps above it."""
    return f'''<div class="quick-contact" data-key="{esc(FORM_KEY)}">
  <div class="quick-contact__inner">
    <div class="quick-contact__panel" id="quick-contact" role="dialog" aria-labelledby="qc-title">
      <form class="qc" action="https://api.web3forms.com/submit" method="post" novalidate data-step="1">
        <div class="qc__head">
          <p class="qc__title" id="qc-title">Get in touch</p>
          <p class="qc__count" aria-hidden="true"><span class="qc__count-num">1</span>/{len(QC_STEPS)}</p>
        </div>
        <div class="qc__progress" aria-hidden="true">{'<i></i>' * len(QC_STEPS)}</div>
        <p class="qc__lead">Questions, ideas or just saying hi. I’ll get back to you soon.</p>
        <div class="qc__step" role="group" aria-labelledby="qc-s1">
          <p class="qc__label" id="qc-s1">Nice to meet you</p>
          <label class="visually-hidden" for="qc-name">Name</label>
          <input id="qc-name" name="name" type="text" autocomplete="name" placeholder="Name" required>
          <label class="visually-hidden" for="qc-email">Email</label>
          <input id="qc-email" name="email" type="email" autocomplete="email" placeholder="Email" required>
        </div>
        <div class="qc__step" role="group" aria-labelledby="qc-s2" hidden>
          <p class="qc__label" id="qc-s2">Tell me a bit more</p>
          <label class="visually-hidden" for="qc-business">Company or project</label>
          <input id="qc-business" name="business" type="text" autocomplete="organization" placeholder="Company or project (optional)">
          <p class="qc__sub" id="qc-type">What describes you best?</p>
          <div class="qc__chips" role="radiogroup" aria-labelledby="qc-type">{chips('business_type', 'radio', QC_TYPES)}</div>
        </div>
        <div class="qc__step" role="group" aria-labelledby="qc-s3" hidden>
          <p class="qc__label" id="qc-s3">Your message</p>
          <p class="qc__sub" id="qc-topics">What’s it about? (optional)</p>
          <div class="qc__chips" role="group" aria-labelledby="qc-topics">{chips('topics', 'checkbox', QC_TOPICS)}</div>
          <label class="visually-hidden" for="qc-message">Message</label>
          <textarea id="qc-message" name="message" rows="4" placeholder="Your message" required></textarea>
        </div>
        <input class="visually-hidden" type="checkbox" name="botcheck" tabindex="-1" autocomplete="off" aria-hidden="true">
        <div class="qc__nav">
          <button class="qc__back" type="button" hidden>Back</button>
          <button class="qc__send" type="submit">Next</button>
        </div>
        <p class="qc__status" role="status" aria-live="polite"></p>
      </form>
    </div>
    <div class="quick-contact__bar">
      <button class="quick-contact__nudge" type="button" tabindex="-1" aria-hidden="true">Questions or ideas? Say hi</button>
      <button class="quick-contact__toggle" type="button" aria-expanded="false" aria-controls="quick-contact">
        <span class="quick-contact__dot" aria-hidden="true"></span><span class="quick-contact__label">Get in touch</span>
      </button>
    </div>
  </div>
</div>
'''


def footer(home=False):
    ext = ' target="_blank" rel="noopener me"'
    socials = ''.join(f'<li><a href="{h}"{ext}>{ICON[i]}<span>{t}</span></a></li>' for h, t, i in SOCIAL[1:])
    # phones show an Email button instead of the big address (hidden on desktop via CSS)
    socials = f'<li class="site-contact__email"><a href="mailto:contact@joerirzn.com">{ICON["mail"]}<span>Email</span></a></li>' + socials
    head = section_head('Connect', 'Email &amp; socials', '04', 'contact-title')
    # the Connect block only lives on the homepage; category pages go straight to the footer
    contact = f'''<section class="site-contact" id="contact" aria-labelledby="contact-title">
  {head}
  <p class="site-contact__lead">Always up for new projects and creative collaborations.</p>
  <a class="site-contact__mail" href="mailto:contact@joerirzn.com">contact@joerirzn.com</a>
  <ul class="site-contact__socials" aria-label="Social media">{socials}</ul>
  <div class="insta" data-feed="{esc(INSTAGRAM_FEED)}" hidden>
    <div class="insta__head">
      <span>Latest on Instagram</span>
      <a href="https://www.instagram.com/joerirzn" target="_blank" rel="noopener me">@joerirzn <span aria-hidden="true">↗</span></a>
    </div>
    <ul class="insta__grid" aria-label="Latest Instagram posts"></ul>
  </div>
</section>
''' if home else ''
    return contact + f'''<footer class="site-footer">
  <div class="site-footer__inner">
    <a class="site-footer__logo" href="/" aria-label="JOERIRZN home">{ICON['logo_grey']}</a>
    <nav class="site-footer__nav" aria-label="Footer">
      <ul>
        <li class="site-footer__heading">Work</li>
        <li><a href="/artworks/">Artworks</a></li>
        <li><a href="/branding/">Branding &amp; Identity</a></li>
        <li><a href="/video/">Video &amp; Motion</a></li>
        <li><a href="/packaging/">Packaging</a></li>
        <li><a href="/3d/">3D Projects</a></li>
        <li><a href="/websites/">Websites</a></li>
      </ul>
      <ul>
        <li class="site-footer__heading">Info</li>
        <li><a href="/#work">Selected Work</a></li>
        <li><a href="/#about">About Me</a></li>
        <li><a href="/#contact">Connect</a></li>
      </ul>
      <ul>
        <li class="site-footer__heading">Connect</li>
        <li><a href="mailto:contact@joerirzn.com">Email</a></li>
        <li><a href="https://www.instagram.com/joerirzn"{ext}>Instagram</a></li>
        <li><a href="https://www.tiktok.com/@joerirzn"{ext}>TikTok</a></li>
        <li><a href="https://www.linkedin.com/in/joeriroozen"{ext}>LinkedIn</a></li>
      </ul>
    </nav>
  </div>
  <div class="site-footer__bottom">
    <p>© {TODAY[:4]} JOERIRZN</p>
    <a href="#main" class="site-footer__top" aria-label="Back to top"><span aria-hidden="true">↑</span></a>
  </div>
</footer>
</body>
</html>
'''


def write_page(page, main):
    out = SITE / page['path'].strip('/') / 'index.html' if page['path'] != '/' else SITE / 'index.html'
    if page.get('file'):
        out = SITE / page['file']
    out.parent.mkdir(parents=True, exist_ok=True)
    body_cls = f' class="page-{page["slug"]}"'
    out.write_text(head(page) + f'<body{body_cls}>\n' + header() + f'<main id="main">\n{main}\n</main>\n' + footer(page['slug'] == 'home'))
    print('wrote', out.relative_to(ROOT))


def breadcrumb(name, path):
    return {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": 1, "name": "Home", "item": DOMAIN + '/'},
        {"@type": "ListItem", "position": 2, "name": name, "item": DOMAIN + path}]}


def collection(name, path, desc):
    return {"@context": "https://schema.org", "@type": "CollectionPage", "name": f"{name} – JOERIRZN",
            "url": DOMAIN + path, "description": desc,
            "author": {"@type": "Person", "name": "Joeri Roozen", "alternateName": "Joeri RZN", "url": DOMAIN + '/'}}


# ---------------------------------------------------------------- layout helpers
def tile(src, folder, alt, bw, bh, mob, crop=None, cls='tile'):
    name = slugify(Path(str(src)).stem)
    v = process(src, folder, name, bw, bh, crop)
    return zoom(img_tag(v, alt, bw, mob), src, cls)


def video_tile(file, poster_v, label, bw, mob, href=None, cls='tile tile--video'):
    p = poster_v[0][0]
    v = (f'<video muted loop playsinline preload="none" poster="{p}" data-src="/assets/video/{file}" '
         f'aria-label="{esc(label)}"></video>')
    if href:
        return f'<a class="{cls}" href="{href}" target="_blank" rel="noopener" aria-label="{esc(label)} (opens website)">{v}</a>'
    return (f'<div class="{cls}" data-lb data-video="/assets/video/{file}" role="button" tabindex="0" '
            f'aria-label="Play video: {esc(label)}">{v}</div>')


def row(items, widths, h, wrap=False, cls=''):
    cols = ' '.join(f'{w}fr' for w in widths)
    total = sum(widths) + 10 * (len(widths) - 1)
    style = f'--cols:{cols};--ar:{total}/{h}'
    c = 'row' + (' row--wrap' if wrap else '') + (f' {cls}' if cls else '')
    if wrap:  # 2x2 on phones
        cw = widths[0]
        style += f';--mar:{2 * cw + 10}/{2 * h + 10}'
    return f'<div class="{c}" style="{style}">\n  ' + '\n  '.join(items) + '\n</div>'


def section(title, rows, sid, extra=''):
    return (f'<section class="project" aria-labelledby="{sid}">\n<h2 class="section-label" id="{sid}">{title}{extra}</h2>\n'
            + '\n'.join(rows) + '\n</section>')


def page_head(label, card_key, bw=824, bh=157):
    framed = (LIVE / f'header-{card_key}.jpg').exists()
    desk = process(LIVE / f'header-{card_key}.jpg', 'headers', f'header-{card_key}', bw, bh) if framed else CARDS[card_key]['d']
    mob = CARDS[card_key]['m']
    return f'''<header class="page-head card{' card--framed' if framed else ''}" style="view-transition-name: card-{card_key}">
  {picture(desk, mob, '', bw, eager=True)}
  <a class="page-head__back" href="/#work" aria-label="Back to selected work">{TRI}</a>
  <span class="card__shade" aria-hidden="true"></span>
  <h1 class="card__label">{label}</h1>
</header>'''


# ---------------------------------------------------------------- build
copy_static()

logo_w = process(ROOT / 'logos/RZN-White.png', 'brand', 'rzn-white', 46, 12, scales=(3, 6))
logo_g = process(LIVE / 'rzn-footer.png', 'brand', 'rzn-grey', 157, 41, scales=(2, 4))
ICON['logo_white'] = f'<img src="{logo_w[0][0]}" srcset="{logo_w[0][0]} 1x, {logo_w[-1][0]} 2x" width="46" height="12" alt="JOERIRZN">'
ICON['logo_grey'] = f'<img src="{logo_g[0][0]}" srcset="{logo_g[0][0]} 1x, {logo_g[-1][0]} 2x" width="157" height="41" alt="JOERIRZN" loading="lazy">'
ICON['mail'] = icon_svg('home-16-27x15.svg', 27, 15)
ICON['instagram'] = icon_svg('home-13-29x26.svg', 29, 26)
ICON['tiktok'] = icon_svg('home-14-26x26.svg', 26, 26)
ICON['linkedin'] = icon_svg('home-15-28x26.svg', 28, 26)
ICON['lock'] = icon_svg('home-19-23x23.svg', 23, 23)

# category cards (desktop + mobile art direction)
CARD_SIZES = {'artworks': (824, 157), 'branding': (324, 157), 'video': (490, 157),
              'packaging': (491, 157), '3d': (323, 157), 'websites': (824, 157), 'archive': (824, 158)}
CARDS = {}
for k, (bw, bh) in CARD_SIZES.items():
    CARDS[k] = {
        'd': process(LIVE / f'card-{k}.png', 'cards', f'card-{k}', bw, bh, scales=(1.5, 3), q=82),
        'm': process(LIVE / f'card-{k}-m.png', 'cards', f'card-{k}-m', 342, 191, scales=(1.5, 3), q=82),
    }

PERSON = {"@type": "Person", "@id": DOMAIN + "/#joeri", "name": "Joeri Roozen", "alternateName": "Joeri RZN",
          "jobTitle": "Graphic & Brand Designer, 3D & Motion Designer, Art Director",
          "description": "Dutch creative designer specializing in visual design, branding, motion, 3D and digital experiences.",
          "url": DOMAIN + "/", "email": "mailto:contact@joerirzn.com", "image": DOMAIN + "/assets/img/og-image.jpg",
          "nationality": {"@type": "Country", "name": "Netherlands"},
          "knowsAbout": ["Graphic design", "Brand identity", "Cover art", "Motion design", "3D design", "Art direction"],
          "sameAs": ["https://www.instagram.com/joerirzn", "https://www.tiktok.com/@joerirzn", "https://www.linkedin.com/in/joeriroozen"]}

# ---------------------------------------------------------------- HOME
hero = process(ROOT / 'logos/RZN-3D.png', 'brand', 'rzn-3d', 825, 395, scales=(1.5, 3), q=82)
portrait = process(LIVE / 'joeri-roozen-portrait.jpg', 'about', 'joeri-roozen', 324, 368, scales=(1.5, 3))


def card(k, label, href=None, meta=''):
    bw, _ = CARD_SIZES[k]
    pic = picture(CARDS[k]['d'], CARDS[k]['m'], '', bw)
    m = f'<span class="card__meta">{meta}</span>' if meta else ''
    if href:
        return (f'<a class="card card--link" href="{href}" style="view-transition-name: card-{k}">'
                f'{pic}<span class="card__shade" aria-hidden="true"></span><span class="card__label">{label}</span>{m}</a>')
    return (f'<div class="card card--locked">{pic}<span class="card__lock">{ICON["lock"]}</span>'
            f'<span class="card__label">{label}</span>{m}</div>')


CLIENTS = [('warner-music-group', 'Warner Music Group', 77, 29), ('warner-music-benelux', 'Warner Music Benelux', 69, 29),
           ('warner-chappell-music', 'Warner Chappell Music', 92, 34), ('atlantic-records', 'Atlantic Records', 39, 39),
           ('spinnin-records', "Spinnin' Records", 97, 27), ('spinnin-deep', "Spinnin' Deep", 97, 28),
           ('musical-freedom', 'Musical Freedom Records', 84, 36), ('cloud-9', 'Cloud 9', 86, 27),
           ('splice', 'Splice', 91, 28), ('future-rave', 'Future Rave', 96, 23), ('zalando', 'Zalando', 110, 20),
           ('pgltm', 'Pretty Girls Like Trap Music', 60, 33)]


def client_list(hidden=False):
    lis = ''.join(f'<li style="--lw:{w}"><img src="/assets/logos/{f}.svg" width="{w}" height="{h}" '
                  f'alt="{"" if hidden else esc(n)}" loading="lazy"></li>' for f, n, w, h in CLIENTS)
    lis += '<li class="clients__more">&amp; more</li>'
    aria = ' aria-hidden="true"' if hidden else ''
    return f'<ul class="clients__set"{aria}>{lis}</ul>'


SHOW_ARCHIVE = False  # set to True to show the locked 'Archive – Coming soon' card again
SKILLS = ['Cover Artwork', 'Graphic Design', 'Branding &amp; Identity', 'Logo Design', 'Event Posters',
          'Art Direction', 'Creative Direction', 'Packaging', '3D', 'Motion']

home_main = f'''<section class="hero" aria-label="Intro">
  {img_tag(hero, 'RZN – 3D logo of Joeri RZN', 825, 88, eager=True, cls='hero__logo')}
  <h1 class="hero__title"><span>Graphic &amp;</span> <span>Brand Design(er)</span> <span>3D /// Motion</span> <span>Art · Direct-or</span> <span>Joeri RZN</span></h1>
  <a class="hero__arrow" href="#work" aria-label="Scroll to selected work">{TRI}</a>
</section>

<section class="home-section" id="work" aria-labelledby="work-title">
  {section_head('Selected work', '6 categories', '01', 'work-title')}
  <div class="cards">
    {card('artworks', 'Artworks', '/artworks/', '75 selected · <span data-artworks>1200</span>+ made')}
    <div class="cards__row" style="--cols:324fr 490fr">
      {card('branding', 'Branding &amp; Identity', '/branding/', '7 projects')}
      {card('video', 'Video &amp; Motion', '/video/', '8 videos')}
    </div>
    <div class="cards__row" style="--cols:491fr 323fr">
      {card('packaging', 'Packaging', '/packaging/', '2 projects')}
      {card('3d', '3D Projects', '/3d/', '6 projects')}
    </div>
    {card('websites', 'Websites', '/websites/', '3 websites')}
    {card('archive', 'Archive', None, 'Coming soon') if SHOW_ARCHIVE else ''}
  </div>
</section>

<section class="home-section" id="clients" aria-labelledby="clients-title">
  {section_head('Worked with', 'In-house &amp; freelance', '02', 'clients-title')}
  <div class="clients">
    <div class="clients__track">{client_list()}{client_list(hidden=True)}</div>
  </div>
</section>

<section class="home-section" id="about" aria-labelledby="about-title">
  {section_head('About me', 'Joeri Roozen', '03', 'about-title')}
  <div class="about">
    <div class="about__photo">{img_tag(portrait, 'Portrait of Joeri Roozen (Joeri RZN) wearing a green leather jacket', 324, 88)}</div>
    <div class="about__body">
      <p class="about__lead">My name is Joeri Roozen (JOERI RZN). I’m a Dutch creative designer specializing in visual design, branding, motion, 3D and digital experiences.</p>
      <div class="about__text">
        <p>For over five years I’ve worked with artists, labels and brands such as Warner Music, Spinnin’ Records and many others to create visuals across a wide range of creative projects.</p>
        <p>What started over 12 years ago as curiosity inside Photoshop grew into a creative career built around constantly evolving, experimenting and pushing ideas further with every project.</p>
        <p>From artworks and visualizers to branding, motion and creative concepts. I focus on creating visuals that feel distinct, modern and purposeful.</p>
      </div>
      <ul class="about__stats">
        <li><strong>5+</strong><span>Years with artists, labels &amp; brands</span></li>
        <li><strong>12+</strong><span>Years of designing</span></li>
        <li><strong><span data-artworks>1200</span>+</strong><span>Artworks made</span></li>
      </ul>
      <ul class="about__skills" aria-label="Disciplines">{''.join(f'<li>{x}</li>' for x in SKILLS)}</ul>
    </div>
  </div>
</section>'''

write_page({'path': '/', 'slug': 'home',
            'title': 'JOERIRZN | Graphic Designer & Art Director',
            'desc': 'Portfolio of Joeri Roozen (Joeri RZN), a Dutch creative designer specializing in cover artwork, branding, motion, 3D and digital experiences for artists, labels and brands like Warner Music and Spinnin’ Records.',
            'preload': f'<link rel="preload" as="image" href="{hero[0][0]}" imagesrcset="{", ".join(f"{p} {w}w" for p, w, _ in hero)}" imagesizes="{sizes_attr(825, 88)}">\n',
            'jsonld': [{"@context": "https://schema.org", **PERSON},
                       {"@context": "https://schema.org", "@type": "WebSite", "name": "JOERIRZN", "url": DOMAIN + "/",
                        "author": {"@id": DOMAIN + "/#joeri"}}]}, home_main)

# ---------------------------------------------------------------- ARTWORKS
matches = json.load(open(SP / 'matches.json'))
art = sorted([m for m in matches if m['page'] == 'artworks' and m['w'] == 156], key=lambda m: (round(m['y'] / 20), m['x']))
assert len(art) == 75, len(art)
art_items = []
for m in art:
    src = ROOT / m['match']
    title = clean_title(m['match'])
    v = process(src, 'artworks', slugify(Path(m['match']).stem), 156, 156)
    art_items.append(f'<li>{zoom(img_tag(v, f"{title} – cover artwork by Joeri RZN", 156, 29), src)}</li>')

art_desc = 'A selection of single and album cover artworks by Joeri RZN for Tiësto, David Guetta, AFROJACK, CYRIL, Spinnin’ Records, Musical Freedom and more. Over 1200 artworks made.'
art_main = f'''{page_head('Artworks', 'artworks')}
<section class="art-grid-wrap" aria-label="Artworks">
<ul class="art-grid">
{chr(10).join(art_items)}
</ul>
<p class="counter">Over <span class="counter__num" data-artworks data-count="1200">1200</span> artworks made</p>
</section>'''
write_page({'path': '/artworks/', 'slug': 'artworks', 'title': 'Artworks | JOERIRZN',
            'desc': art_desc, 'jsonld': [breadcrumb('Artworks', '/artworks/'), collection('Artworks', '/artworks/', art_desc)]},
           art_main)

# ---------------------------------------------------------------- BRANDING
B = MEDIA / 'Branding & Identity'
P = B / 'Pretty Girls Like Trap Music'
IJ = B / 'Innerjoin'
TL = B / 'Tiësto Leather Artworks'
ADE = B / "Spinnin' Deep ADE 2025"
ETB = B / 'Easy, The Bucket'
ZW = B / 'ZWⱯRT'
DA = B / 'Dastic'


def poster_for(video_path, folder, name, bw, bh):
    return process(SP / 'posters' / f'{name}.jpg', folder, f'{name}-poster', bw, bh)


# on phones these three rows merge into one 3-column grid (.row-group); wide tiles span 2 columns
pg = section('Pretty Girls Like Trap Music', ['<div class="row-group">' + '\n'.join([
    row([tile(P / '1_Valentines Cover.jpg', 'branding', 'PGLTM Valentine’s cover – pink heart lollipop', 198, 245, 21),
         tile(P / '2_PGLTM-Posters_01.jpg', 'branding', 'Pretty Girls Like Trap Music event posters', 408, 245, 44, cls='tile tile--span2'),
         tile(P / '3_Hot Girl Dump.jpg', 'branding', 'PGLTM “Hot Girl Dump” social post', 196, 245, 21)], [198, 408, 196], 245),
    row([tile(P / '4_Imani.jpg', 'branding', 'PGLTM editorial layouts – Imani’s Y2K, what do I wear', 407, 253, 44, cls='tile tile--span2'),
         tile(P / '5_Bathroom Talks.jpg', 'branding', 'PGLTM “Bathroom Talks” artwork', 199, 253, 21),
         video_tile('pgltm-website.mp4', poster_for(None, 'branding', 'pgltm-website', 196, 253),
                    'Pretty Girls Like Trap Music website', 196, 21, href='https://prettygirlsliketrapmusic.nl/')],
        [407, 199, 196], 253),
    row([tile(P / '7_Zalando Posters.jpg', 'branding', 'Zalando × PGLTM posters', 198, 248, 21),
         tile(P / '8_Zalando-Cars_01.jpg', 'branding', 'Zalando × PGLTM taxi campaign – “our space to be”', 408, 248, 44, cls='tile tile--span2'),
         tile(P / '9_PGR.jpg', 'branding', 'Pretty Girl Rotation playlist artwork', 198, 248, 21)], [198, 408, 198], 248),
]) + '</div>'], 'pgltm')

bb = [(IJ / f'Innerjoin Brandbook 0{i}.png', f'Innerjoin brandbook page {i}') for i in (1, 2, 5, 4, 3, 6)]
bb_html = ''.join(tile(p, 'branding', a, 198, 111, 21) for p, a in bb)
ij = section('Innerjoin', [
    row([tile(IJ / 'Innerjoin White, Black BG.jpg', 'branding', 'Innerjoin logo, white on black', 198, 198, 44),
         tile(IJ / 'ELOQ, n4tee - Devotion.jpg', 'branding', 'ELOQ, n4tee – Devotion (Innerjoin release artwork)', 199, 198, 44),
         tile(IJ / 'Ben Van Kuringen - All This Love.jpg', 'branding', 'Ben van Kuringen – All This Love (Innerjoin release artwork)', 199, 198, 44),
         tile(IJ / 'Syll - Tempo Oco.jpg', 'branding', 'Syll – Tempo Oco (Innerjoin release artwork)', 198, 198, 44)],
        [198, 199, 199, 198], 198, wrap=True),
    row([f'<div class="sub sub--3x2">{bb_html}</div>',
         video_tile('innerjoin-intro.mp4', poster_for(None, 'branding', 'innerjoin-intro', 197, 232),
                    'Innerjoin brand intro video', 197, 21)], [616, 197], 232),
], 'innerjoin')

tl = section('Tiësto “Leather” Artworks', [
    row([tile(TL / 'Tiësto & Rafael Cerato - Cool N Calm EP.jpg', 'branding', 'Tiësto & Rafael Cerato – Cool N Calm EP, leather artwork', 199, 199, 44),
         tile(TL / 'Tiësto & Oscar L - Flex.jpg', 'branding', 'Tiësto & Oscar L – Flex, leather artwork', 199, 199, 44),
         tile(TL / 'Tiësto & Undercatt - Shadows.jpg', 'branding', 'Tiësto & Undercatt – Shadows, leather artwork', 199, 199, 44),
         tile(TL / 'Tiësto & Dyzen - All Right.jpg', 'branding', 'Tiësto & Dyzen – All Right, leather artwork', 199, 199, 44)],
        [199, 199, 199, 199], 199, wrap=True),
], 'tiesto')

ade = section('Spinnin’ Deep ADE – 2025', [
    row([tile(ADE / 'Main.jpg', 'branding', 'Spinnin’ Deep ADE 2025 key visual – Friday Oct 24', 407, 248, 88),
         tile(ADE / 'Construction Fences DEEP.jpg', 'branding', 'Spinnin’ Deep ADE 2025 construction fence banners', 407, 248, 88)],
        [407, 407], 248, cls='row--stack'),
    row([tile(ADE / f'{n} 207x175.jpg', 'branding', f'Spinnin’ Deep ADE 2025 – {n.replace("Adam Sellouk", "Adam Sellouk")} artist visual', 198, 167, 44)
         for n in ('Adam Sellouk', 'Curol', 'Unfazed', 'Nitefreak')], [198, 198, 198, 198], 167, wrap=True),
], 'ade')

small = [(ETB / 'Easy The Bucket Profile Photo.jpg', 'Easy, The Bucket logo'),
         (ETB / 'Easy The Bucket Available.jpg', 'Easy, The Bucket “Available” post'),
         (ETB / 'Easy The Bucket Retouched Bleached Jeans.jpg', 'Easy, The Bucket “Retouched Bleached Jeans” post'),
         (ETB / 'Easy The Bucket Waistband Collection.jpg', 'Easy, The Bucket “Waistband Collection” post')]
etb = section('Easy, The Bucket', [
    row([tile(ETB / 'Easy The Bucket Menu 1.jpg', 'branding', 'Easy, The Bucket – what’s on the menu poster', 199, 250, 44),
         tile(ETB / 'Easy The Bucket Menu 2.jpg', 'branding', 'Easy, The Bucket – retouched bleach jeans & waistband collection menu', 199, 250, 44),
         '<div class="sub sub--2x2">' + ''.join(tile(p, 'branding', a, 94, 120, 21) for p, a in small) + '</div>',
         tile(ETB / 'Easy The Bucket Market.jpg', 'branding', 'Easy, The Bucket archive sale poster', 199, 250, 44)],
        [199, 199, 198, 199], 250, wrap=True),
], 'etb')

banner = process(LIVE / 'zwart-banner-outline.jpg', 'branding', 'zwart-banner-outline', 824, 128)
zw = section('ZWⱯRT', [
    row([tile(ZW / 'ZWVRT White_BlackBG.jpg', 'branding', 'ZWART logo, white on black', 198, 198, 44),
         tile(ZW / 'POLTERGST - Sonne V5.jpg', 'branding', 'POLTERGST – Sonne (ZWART release artwork)', 198, 198, 44),
         tile(ZW / 'Reggio, KNTRLVRLST, Moji - Papi V1.jpg', 'branding', 'Reggio, KNTRLVRLST, Moji – Papi (ZWART release artwork)', 198, 198, 44),
         tile(ZW / 'RayRay & Reggio - Turbulence V1.jpg', 'branding', 'RayRay & Reggio – Turbulence (ZWART release artwork)', 198, 198, 44)],
        [198, 198, 198, 198], 198, wrap=True),
    row([zoom(img_tag(banner, "ZWART outline logo banner", 824, 88), LIVE / 'zwart-banner-outline.jpg', 'tile')], [824], 128),
], 'zwart')

da = section('Dastic', [
    row([tile(DA / 'Dastic_Logo_01.jpg', 'branding', 'Dastic logo design', 198, 198, 44),
         tile(DA / 'Dastic_Logo_03.jpg', 'branding', 'Dastic logo detail', 198, 198, 44),
         tile(DA / 'Dastic_Logo_02.jpg', 'branding', 'Dastic – Honest artwork', 198, 198, 44),
         tile(LIVE / 'dastic-04.jpg', 'branding', 'Dastic logo on sky artwork', 198, 198, 44)],
        [198, 198, 198, 198], 198, wrap=True),
], 'dastic')

br_desc = 'Brand identity projects by Joeri RZN: Pretty Girls Like Trap Music × Zalando, Innerjoin, Tiësto “Leather” artworks, Spinnin’ Deep ADE 2025, Easy, The Bucket, ZWART and Dastic.'
write_page({'path': '/branding/', 'slug': 'branding', 'title': 'Branding & Identity | JOERIRZN',
            'desc': br_desc, 'jsonld': [breadcrumb('Branding & Identity', '/branding/'),
                                        collection('Branding & Identity', '/branding/', br_desc)]},
           page_head('Branding &amp; Identity', 'branding') + '\n' + '\n'.join([pg, ij, tl, ade, etb, zw, da]))

# ---------------------------------------------------------------- VIDEO
YT = [('TvrS1yhDE0c', 'Best Of Spinnin’ Records Summer 2024 – Summer Day Mix'),
      ('qQ01Wxt0SsI', 'Afro House Mix 2024 – Spinnin’ Records'),
      ('FWilUwLjSQg', 'Spinnin’ Records Workout Mix 2024'),
      ('pYDfAJjo_5k', 'Spinnin’ Records ADE Mix 2024'),
      ('3MDVqc-dnTY', 'Spinnin’ Records Best of 2024 – End of Year Mix'),
      ('sq2PHg3Grcg', 'Best Of Spinnin’ Records Summer 2024 – Summer Night Mix'),
      ('em15XOvnGzo', 'Skandal – Die Saus (Lyric Video)'),
      ('5naZTW34Iqg', 'Kidd Bo – ISHA (Lyric Video)')]
yt_items = []
for vid, title in YT:
    v = process(SP / 'yt' / f'{vid}.jpg', 'video', f'yt-{vid}', 407, 230, scales=(1.5, 3))
    yt_items.append(f'''<li><button class="yt" type="button" data-id="{vid}" aria-label="Play video: {esc(title)}">
  {img_tag(v, f"{title} – video by Joeri RZN", 407, 88)}
  <span class="yt__play" aria-hidden="true"></span>
</button><p class="visually-hidden">{esc(title)}</p></li>''')
vid_desc = 'Motion design, 3D visualizers and lyric videos by Joeri RZN for Spinnin’ Records, Zurich Musiq and 100Inc.'
write_page({'path': '/video/', 'slug': 'video', 'title': 'Video & Motion | JOERIRZN', 'desc': vid_desc,
            'jsonld': [breadcrumb('Video & Motion', '/video/'), collection('Video & Motion', '/video/', vid_desc)]},
           page_head('Video &amp; Motion', 'video') + f'''
<section aria-label="Videos">
<ul class="video-grid">
{chr(10).join(yt_items)}
</ul>
</section>''')

# ---------------------------------------------------------------- PACKAGING
S25 = MEDIA / "3D Projects/Spinnin' Records 25 Years/Spinnin' Records 25 Years Render.jpg"


def ptile(src, name, alt, w, h, crop=None):
    v = process(src, 'packaging', name, w, h, crop)
    return f'<li class="hrow__item" style="--iw:{w};--ih:{h}">{zoom(img_tag(v, alt, w, round(w / 466 * 100)), src)}</li>'


# Packaging: fixed rows like Branding (wide shot full width, the rest side by side; nothing cropped)
pk_spinnin = section('Spinnin’ Sessions', [
    row([tile(S25, 'packaging', 'Spinnin’ Sessions vinyl packaging – chrome Spinnin’ Records logo with stickers', 824, 385, 88, (2, 0, 2312, 1080))], [824], 385),
    row([tile(LIVE / 'spinnin-sessions-gatefold.jpg', 'packaging', 'Spinnin’ Records gatefold vinyl sleeve, black', 287, 230, 44),
         tile(LIVE / 'spinnin-sessions-vinyl-angle.jpg', 'packaging', 'Spinnin’ Sessions vinyl sleeve, angled view', 287, 230, 44),
         tile(LIVE / 'spinnin-sessions-collage.png', 'packaging', 'Spinnin’ Sessions vinyl packaging, front and back', 230, 230, 88)],
        [287, 287, 230], 230, cls='row--pk-trio'),
], 'spinnin-sessions')
pk_cyril = section('CYRIL – From Down Under To The World', [
    row([tile(LIVE / 'cyril-from-down-under-front.jpg', 'packaging', 'CYRIL – From Down Under To The World, vinyl sleeve front', 407, 221, 88),
         tile(LIVE / 'cyril-from-down-under-back.jpg', 'packaging', 'CYRIL – From Down Under To The World, vinyl sleeve back', 407, 221, 88)],
        [407, 407], 221, cls='row--pk-stack'),
], 'cyril')
pk_desc = 'Vinyl and physical packaging design by Joeri RZN, including Spinnin’ Sessions and CYRIL – From Down Under To The World.'
write_page({'path': '/packaging/', 'slug': 'packaging', 'title': 'Packaging | JOERIRZN', 'desc': pk_desc,
            'jsonld': [breadcrumb('Packaging', '/packaging/'), collection('Packaging', '/packaging/', pk_desc)]},
           page_head('Packaging', 'packaging') + '\n' + '\n'.join([pk_spinnin, pk_cyril]))

# ---------------------------------------------------------------- 3D
D = MEDIA / '3D Projects'
three = [
    row([tile(D / 'PS1/PS1 Render 01.png', '3d', 'Sony PlayStation 1 – 3D render, top view', 198, 269, 44, (43, 0, 994, 1350)),
         tile(D / 'PS1/PS1 Render 02.png', '3d', 'Sony PlayStation 1 – 3D render, front view', 198, 269, 44, (43, 0, 994, 1350)),
         tile(D / 'PS1/PS1 Render 03.png', '3d', 'Sony PlayStation 1 – 3D render, close-up', 198, 269, 44, (85, 0, 995, 1350)),
         tile(D / 'PS1/PS1 Poster.jpg', '3d', 'PlayStation Plus magazine cover with 3D PS1 render', 198, 269, 44)],
        [198, 198, 198, 198], 269, wrap=True),
    row([tile(D / 'Nintendo Gameboy Music/Gameboy Render 1.png', '3d', 'Game Boy cartridges with rap album covers – 3D render', 198, 198, 29),
         tile(D / 'Nintendo Gameboy Music/Gameboy Render 2.png', '3d', 'Game Boy cartridges – 3D render close-up', 198, 198, 29),
         zoom(img_tag(process(D / "Nintendo Gameboy Music/Gameboy Render 1.png", "3d", "gameboy-render-1-wide", 406, 198, (227, 523, 1692, 825)), "Game Boy music cartridges – 3D render detail", 406, 58), D / "Nintendo Gameboy Music/Gameboy Render 1.png", 'tile')],
        [198, 198, 406], 198),
    row([tile(D / 'Nocta Dice/Nocta Dice 5.png', '3d', 'Nocta dice – 3D render close-up', 198, 198, 44),
         tile(D / 'Nocta Dice/Nocta Dice 4.png', '3d', 'Nocta dice – three dice 3D render', 198, 198, 44),
         tile(D / 'Nocta Dice/Nocta Dice 2.png', '3d', 'Nocta dice – macro 3D render', 198, 198, 44),
         tile(D / 'Nocta Dice/Nocta Dice 1.png', '3d', 'Nocta die – single 3D render', 198, 198, 44)],
        [198, 198, 198, 198], 198, wrap=True),
    row([video_tile('mp4-player.mp4', poster_for(None, '3d', 'mp4-player', 408, 506), 'MP4 player – 3D animation', 408, 44),
         '<div class="sub sub--mp4">'
         + tile(D / 'MP4/MP4 CRG Render 01.jpg', '3d', 'Teal MP4 player – 3D render', 198, 248, 21, (605, 0, 4790, 6000))
         + tile(D / 'MP4/MP4 CRG Render 03.jpg', '3d', 'Teal MP4 player – 3D render, macro', 198, 248, 21, (605, 0, 4791, 6000))
         + tile(D / 'MP4/MP4 CRG Render 02.jpg', '3d', 'MP4 player screen “Now playing” – 3D render detail', 406, 248, 44, (590, 1546, 4791, 2926), cls='tile tile--wide')
         + '</div>'], [408, 406], 506),
    row([tile(S25, '3d', 'Spinnin’ Records 25 years – chrome logo 3D render', 407, 198, 58, (48, 0, 2220, 1080)),
         tile(D / 'Battery/Battery Render.jpg', '3d', 'Battery – 3D product render', 198, 198, 29, (0, 270, 2160, 2160)),
         video_tile('battery.mp4', poster_for(None, '3d', 'battery', 198, 198), 'Battery – 3D animation', 198, 29)],
        [407, 198, 198], 198),
    row([video_tile('gameboy-color-pokemon.mp4', poster_for(None, '3d', 'gameboy-color-pokemon', 198, 248), 'Game Boy Color Pokémon edition boxes – 3D animation', 198, 44),
         tile(D / 'Gameboy Color Pokémon/Gameboy Color Pokémon Render 01.jpg', '3d', 'Game Boy Color Pokémon edition boxes – 3D render', 198, 248, 44),
         tile(D / 'Gameboy Color Pokémon/Gameboy Color Pokémon Render 02.jpg', '3d', 'Falling Game Boy Color boxes – 3D render', 198, 248, 44),
         tile(D / 'Gameboy Color Pokémon/Gameboy Color Pokémon Render 03.jpg', '3d', 'Game Boy Color box close-up – 3D render', 198, 248, 44)],
        [198, 198, 198, 198], 248, wrap=True),
]
d3_desc = '3D renders and animations by Joeri RZN: PlayStation 1, Game Boy music cartridges, Nocta dice, MP4 player, battery and Pokémon Game Boy Color.'
write_page({'path': '/3d/', 'slug': '3d', 'title': '3D Projects | JOERIRZN', 'desc': d3_desc,
            'jsonld': [breadcrumb('3D Projects', '/3d/'), collection('3D Projects', '/3d/', d3_desc)]},
           page_head('3D Projects', '3d') + '\n<section class="project project--flush" aria-label="3D projects">\n' + '\n'.join(three)
           + '\n</section>\n<p class="explore">Explore more 3D work in <a href="/artworks/"><strong>artwork projects</strong></a></p>')

# ---------------------------------------------------------------- WEBSITES
# Each site: a scroll-through video of the desktop version (recorded from the live site), with
# three screenshots stacked next to it: the hero and two clear sections of the site.
def website(key, name, url, sid, sections):
    desk = video_tile(f'web-{key}-desk.mp4', poster_for(None, 'websites', f'web-{key}-desk', 618, 387),
                      f'{name} website – desktop scroll-through', 618, 88)
    stack = ('<div class="sub sub--web">'
             + ''.join(tile(LIVE / f'web-{key}-s{i + 1}.jpg', 'websites', f'{name} website – {what}', 196, 122, 29)
                       for i, what in enumerate(('hero',) + sections))
             + '</div>')
    link = (f'<a class="section-label__link" href="{url}" target="_blank" rel="noopener">Visit site <span aria-hidden="true">↗</span></a>'
            if url else '<span class="section-label__link">This website</span>')
    return section(name, [row([desk, stack], [618, 196], 387, cls='row--web')], sid, link)


web_desc = 'Websites designed and built by Joeri RZN: joerirzn.com, Pretty Girls Like Trap Music and Naliovia.'
write_page({'path': '/websites/', 'slug': 'websites', 'title': 'Websites | JOERIRZN', 'desc': web_desc,
            'jsonld': [breadcrumb('Websites', '/websites/'), collection('Websites', '/websites/', web_desc)]},
           page_head('Websites', 'websites') + '\n' + '\n'.join([
               website('joerirzn', 'JOERIRZN', None, 'joerirzn-site', ('selected work', 'about me')),
               website('pgltm', 'Pretty Girls Like Trap Music', 'https://prettygirlsliketrapmusic.nl/', 'pgltm-site', ('about us', 'what we do and FAQ')),
               website('naliovia', 'Naliovia', 'https://naliovia.com/', 'naliovia', ('selected work', 'about me')),
           ]))

# ---------------------------------------------------------------- 404
write_page({'path': '/404', 'file': '404.html', 'slug': 'notfound', 'title': 'Page not found | JOERIRZN',
            'desc': 'This page does not exist. Explore the portfolio of Joeri RZN.'},
           '<section class="notfound"><h1>404</h1><p>This page doesn’t exist (anymore).</p><p><a href="/">Back to home</a></p></section>')

# ---------------------------------------------------------------- sitemap / robots
urls = ['/', '/artworks/', '/branding/', '/video/', '/packaging/', '/3d/', '/websites/']
(SITE / 'sitemap.xml').write_text('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
                                  + ''.join(f'  <url><loc>{DOMAIN}{u}</loc><lastmod>{TODAY}</lastmod></url>\n' for u in urls) + '</urlset>\n')
(SITE / 'robots.txt').write_text(f'User-agent: *\nAllow: /\n\nSitemap: {DOMAIN}/sitemap.xml\n')
# no web app manifest: it made Chrome offer to "install" the site as an app
print('done')
