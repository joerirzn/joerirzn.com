(() => {
  const doc = document;
  const body = doc.body;
  const reduceMotion = matchMedia('(prefers-reduced-motion: reduce)').matches;
  const hasIO = 'IntersectionObserver' in window;

  // Page transitions: hide card borders + labels right before the outgoing snapshot is taken,
  // and undo it whenever the page is shown again (incl. restores from the back/forward cache)
  // Only the card that is being opened (or returned to) takes part in the morph; the others
  // lose their transition name so no stray frames float through the animation.
  const vtCards = [...doc.querySelectorAll('a.card--link')];
  const pathOf = (href) => new URL(href, location.href).pathname;
  vtCards.forEach((c) => { c.dataset.vt = c.style.viewTransitionName; });
  const onlyCard = (path) => vtCards.forEach((c) => {
    const on = Boolean(path) && pathOf(c.href) === path;
    c.style.viewTransitionName = on ? c.dataset.vt : 'none';
    const shade = c.querySelector('.card__shade');
    if (shade) shade.style.viewTransitionName = on ? 'card-shade' : 'none';
  });
  const allCards = () => vtCards.forEach((c) => {
    c.style.viewTransitionName = c.dataset.vt;
    const shade = c.querySelector('.card__shade');
    if (shade) shade.style.viewTransitionName = 'none';
  });
  vtCards.forEach((c) => c.addEventListener('click', (e) => {
    if (e.metaKey || e.ctrlKey || e.shiftKey || e.button > 0) return; // new tab: no transition
    onlyCard(pathOf(c.href));
  }));

  addEventListener('pageswap', (e) => {
    if (!e.viewTransition) return;
    doc.documentElement.classList.add('vt-leaving');
    try { sessionStorage.setItem('rzn-vt-from', location.pathname); } catch (err) { /* storage blocked */ }
  });
  addEventListener('pagereveal', (e) => {
    doc.documentElement.classList.remove('vt-leaving');
    if (!vtCards.length) return;
    let from = null;
    try { from = sessionStorage.getItem('rzn-vt-from'); } catch (err) { /* storage blocked */ }
    if (e.viewTransition && from) {
      onlyCard(from);
      if (e.viewTransition.types && from !== '/') e.viewTransition.types.add('back');
      e.viewTransition.finished.finally(allCards);
    } else {
      allCards();
    }
  });
  addEventListener('pageshow', () => doc.documentElement.classList.remove('vt-leaving'));

  // Footer height as a CSS variable, used to let Connect + footer fill the last screen (see CSS)
  const footerEl = doc.querySelector('.site-footer');
  if (footerEl) {
    const setFooterH = () => doc.documentElement.style.setProperty('--footer-h', `${footerEl.offsetHeight}px`);
    setFooterH();
    addEventListener('resize', setFooterH);
  }

  // Smooth scrolling for in-page links, but only once the page has loaded (see CSS)
  const enableSmooth = () => requestAnimationFrame(() => doc.documentElement.classList.add('smooth-scroll'));
  if (doc.readyState === 'complete') enableSmooth(); else addEventListener('load', enableSmooth);

  // Category page back arrow always leads home. If the entry right before this one is the
  // homepage, go back in history so the browser restores the exact scroll position and the
  // banner folds back into its card; otherwise follow the link to /#work.
  const backLink = doc.querySelector('.page-head__back');
  if (backLink) {
    let fromHome = false;
    try {
      const ref = new URL(doc.referrer);
      fromHome = ref.origin === location.origin && ref.pathname === '/';
    } catch (err) { /* no referrer */ }
    // mark only this history entry; in-page jumps create new entries without the mark
    if (fromHome) history.replaceState({ ...(history.state || {}), rznFromHome: true }, '');
    backLink.addEventListener('click', (e) => {
      if (history.state && history.state.rznFromHome) {
        e.preventDefault();
        history.back();
      }
    });
  }

  // Footer arrow (and the RZN logos on the homepage): scroll to the top without a reload or history entry.
  // On other pages the logos keep their normal link to the homepage.
  const topLinks = [...doc.querySelectorAll('.site-footer__top')];
  if (body.classList.contains('page-home')) topLinks.push(...doc.querySelectorAll('.site-header__logo, .site-footer__logo'));
  topLinks.forEach((link) => {
    link.addEventListener('click', (e) => {
      e.preventDefault();
      if (body.classList.contains('menu-open')) doc.querySelector('.menu-toggle')?.click();
      window.scrollTo({ top: 0, behavior: reduceMotion ? 'auto' : 'smooth' });
      const main = doc.getElementById('main');
      if (main) {
        main.setAttribute('tabindex', '-1');
        main.focus({ preventScroll: true });
      }
    });
  });

  // Scroll reveal: elements below the fold fade + rise in when they enter the viewport.
  // Anything already on screen at load stays as is (no clash with page transitions or the hero).
  const REVEAL = [
    '.section-head', '.section-label',
    '.cards > .card', '.cards__row > .card', '.clients',
    '.about__photo', '.about__lead', '.about__text p', '.about__stats li', '.about__skills',
    '.site-contact__lead', '.site-contact__mail', '.site-contact__socials',
    '.art-grid li', '.row > .tile', '.row > .sub', '.video-grid li', '.hrow', '.counter', '.explore',
    // the footer is left out: it sits too close to the bottom edge to ever scroll fully into view
  ].join(',');
  // Skip when returning via back/forward or landing on an anchor (e.g. /#work): the page isn't
  // at the top then, and the card that folds back in must be visible straight away.
  const navType = (performance.getEntriesByType('navigation')[0] || {}).type;
  const skipReveal = navType === 'back_forward' || Boolean(location.hash);
  if (hasIO && !reduceMotion && !skipReveal) {
    const pending = [...doc.querySelectorAll(REVEAL)].filter((el) => el.getBoundingClientRect().top > window.innerHeight);
    pending.forEach((el) => el.setAttribute('data-reveal', ''));
    const revealIO = new IntersectionObserver((entries) => {
      const shown = entries.filter((e) => e.isIntersecting).map((e) => e.target);
      // stagger items that enter together, top-left first
      shown
        .map((el) => ({ el, r: el.getBoundingClientRect() }))
        .sort((a, b) => (Math.round(a.r.top / 20) - Math.round(b.r.top / 20)) || (a.r.left - b.r.left))
        .forEach(({ el }, i) => {
          const delay = Math.min(i * 70, 420);
          el.style.setProperty('--reveal-delay', `${delay}ms`);
          el.classList.add('is-revealed');
          revealIO.unobserve(el);
          setTimeout(() => {
            el.removeAttribute('data-reveal');
            el.classList.remove('is-revealed');
            el.style.removeProperty('--reveal-delay');
          }, 1000 + delay);
        });
    }, { rootMargin: '0px 0px -8% 0px', threshold: 0.08 });
    pending.forEach((el) => revealIO.observe(el));
  }

  // Menu overlay
  const toggle = doc.querySelector('.menu-toggle');
  const menu = doc.getElementById('site-menu');
  if (toggle && menu) {
    const setOpen = (open) => {
      body.classList.toggle('menu-open', open);
      toggle.setAttribute('aria-expanded', String(open));
      toggle.setAttribute('aria-label', open ? 'Close menu' : 'Open menu');
    };
    toggle.addEventListener('click', () => setOpen(toggle.getAttribute('aria-expanded') !== 'true'));
    menu.addEventListener('click', (e) => { if (e.target.closest('a')) setOpen(false); });
    doc.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && body.classList.contains('menu-open')) {
        setOpen(false);
        toggle.focus();
      }
    });
  }

  // Header nav "flashlight": a soft light glides over the menu text and follows the scroll position
  const navList = doc.querySelector('.site-nav ul');
  const spyLinks = [...doc.querySelectorAll('.site-nav a[data-spy]')];
  const spySections = spyLinks.map((a) => doc.getElementById(a.dataset.spy));
  if (navList && spyLinks.length && spySections.every(Boolean)) {
    const navEl = navList.parentElement;
    navList.classList.add('has-spot');
    const clamp = (v) => Math.max(0, Math.min(1, v));
    const ease = (t) => t * t * t * (t * (t * 6 - 15) + 10); // smootherstep
    let spotX = null;
    let active = -1;
    let frame = 0;
    let lastTime = 0;

    const targetX = () => {
      const centers = spyLinks.map((a) => a.offsetLeft + a.offsetWidth / 2);
      const probe = window.scrollY + window.innerHeight * 0.5;
      // measure from each section's heading, not from the empty space above it
      const tops = spySections.map((s) => (s.querySelector('.section-head') || s).getBoundingClientRect().top + window.scrollY);
      const atBottom = window.innerHeight + window.scrollY >= doc.documentElement.scrollHeight - 4;
      const last = centers.length - 1;
      let index = 0;
      let x;
      if (atBottom) {
        index = last;
        x = centers[last];
      } else if (probe < tops[0]) {
        // above the first section: the light waits just left of the menu and slides in
        index = -1;
        const t = ease(clamp((probe - (tops[0] - window.innerHeight * 0.5)) / (window.innerHeight * 0.5)));
        x = centers[0] - 160 * (1 - t);
      } else {
        while (index < last && probe >= tops[index + 1]) index++;
        if (index === last) {
          x = centers[last];
        } else {
          // stay on the current item until the next heading nears the middle of the screen, then glide
          const glide = window.innerHeight * 0.28;
          const t = clamp(1 - (tops[index + 1] - probe) / glide);
          x = centers[index] + (centers[index + 1] - centers[index]) * ease(t);
        }
      }
      if (index !== active) {
        active = index;
        spyLinks.forEach((a, i) => {
          if (i === index) a.setAttribute('aria-current', 'location');
          else a.removeAttribute('aria-current');
        });
      }
      return x;
    };

    const render = (now = performance.now()) => {
      const target = targetX();
      const dt = lastTime ? Math.min((now - lastTime) / 1000, 0.05) : 0;
      lastTime = now;
      // frame-rate independent easing: the light trails the scroll by roughly a quarter second
      const follow = 1 - Math.exp(-dt * 7);
      spotX = spotX === null || reduceMotion ? target : spotX + (target - spotX) * follow;
      navEl.style.setProperty('--spot-x', `${spotX.toFixed(1)}px`);
      if (Math.abs(target - spotX) > 0.2) {
        frame = requestAnimationFrame(render);
      } else {
        frame = 0;
        lastTime = 0;
      }
    };
    const request = () => { if (!frame) frame = requestAnimationFrame(render); };
    addEventListener('scroll', request, { passive: true });
    addEventListener('resize', request);
    render();
  }

  // "Worked with" marquee: auto-scrolls, can be dragged/flung, then eases back to its base speed
  const marquee = doc.querySelector('.clients');
  if (marquee && !reduceMotion) {
    const track = marquee.querySelector('.clients__track');
    const set = track.firstElementChild;
    const LOOP_SECONDS = 45;
    let width = set.offsetWidth;
    let x = 0;
    let velocity = -width / LOOP_SECONDS;
    let dragging = false;
    let visible = true;
    let lastX = 0;
    let lastMoveTime = 0;
    let lastFrame = performance.now();

    marquee.classList.add('is-interactive');
    marquee.querySelectorAll('img').forEach((img) => { img.draggable = false; });
    addEventListener('resize', () => { width = set.offsetWidth; });
    if (hasIO) new IntersectionObserver(([e]) => { visible = e.isIntersecting; }).observe(marquee);

    const frame = (now) => {
      const dt = Math.min((now - lastFrame) / 1000, 0.05);
      lastFrame = now;
      if (!dragging && visible) {
        const base = -width / LOOP_SECONDS;
        velocity += (base - velocity) * (1 - Math.exp(-dt * 1.4));
        x += velocity * dt;
      }
      x %= width;
      if (x > 0) x -= width;
      track.style.transform = `translate3d(${x}px, 0, 0)`;
      requestAnimationFrame(frame);
    };
    requestAnimationFrame(frame);

    marquee.addEventListener('pointerdown', (e) => {
      if (e.button !== 0) return;
      dragging = true;
      lastX = e.clientX;
      lastMoveTime = e.timeStamp;
      velocity = 0;
      marquee.setPointerCapture(e.pointerId);
      marquee.classList.add('is-dragging');
    });
    marquee.addEventListener('pointermove', (e) => {
      if (!dragging) return;
      const dx = e.clientX - lastX;
      const dt = Math.max(e.timeStamp - lastMoveTime, 1) / 1000;
      x += dx;
      velocity = velocity * 0.25 + (dx / dt) * 0.75;
      lastX = e.clientX;
      lastMoveTime = e.timeStamp;
    });
    const release = (e) => {
      if (!dragging) return;
      dragging = false;
      marquee.classList.remove('is-dragging');
      if (e.timeStamp - lastMoveTime > 100) velocity = 0; // held still before letting go
      velocity = Math.max(-5000, Math.min(5000, velocity));
    };
    marquee.addEventListener('pointerup', release);
    marquee.addEventListener('pointercancel', release);
    marquee.addEventListener('lostpointercapture', release);
  }

  // Muted looping videos: load when near the viewport, play only while visible
  const videos = doc.querySelectorAll('video[data-src]');
  if (hasIO) {
    const io = new IntersectionObserver((entries) => {
      entries.forEach(({ target: video, isIntersecting }) => {
        if (isIntersecting) {
          if (!video.getAttribute('src')) video.src = video.dataset.src;
          if (!reduceMotion) video.play().catch(() => {});
        } else if (!video.paused) {
          video.pause();
        }
      });
    }, { rootMargin: '150px 0px' });
    videos.forEach((v) => io.observe(v));
  } else {
    videos.forEach((v) => { v.src = v.dataset.src; v.autoplay = true; });
  }

  // YouTube: only load the player after a click (faster pages, no tracking until then)
  doc.querySelectorAll('.yt[data-id]').forEach((btn) => {
    btn.addEventListener('click', () => {
      const frame = doc.createElement('iframe');
      frame.src = `https://www.youtube-nocookie.com/embed/${btn.dataset.id}?autoplay=1&rel=0&playsinline=1`;
      frame.title = btn.getAttribute('aria-label').replace(/^Play video: /, '');
      frame.allow = 'accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share';
      frame.allowFullscreen = true;
      frame.referrerPolicy = 'strict-origin-when-cross-origin';
      const wrap = doc.createElement('div');
      wrap.className = 'yt';
      wrap.append(frame);
      btn.replaceWith(wrap);
    });
  });

  // Artworks made: 1200 on 29 Sep 2026, plus one for every day since
  const ARTWORKS_BASE = 1200;
  const ARTWORKS_BASE_DATE = new Date(2026, 8, 29);
  const artworksMade = ARTWORKS_BASE + Math.max(0, Math.floor((Date.now() - ARTWORKS_BASE_DATE) / 86400000));
  doc.querySelectorAll('[data-artworks]').forEach((el) => {
    el.textContent = artworksMade;
    if (el.hasAttribute('data-count')) el.dataset.count = artworksMade;
  });

  // About stats (5+, 12+, 1200+): count up from 0 when they scroll into view, a little staggered.
  // The real numbers are in the HTML, so without JS or with reduced motion they simply show as is.
  const stats = doc.querySelector('.about__stats');
  if (stats && hasIO && !reduceMotion) {
    const nums = [...stats.querySelectorAll('strong')].map((strong) => {
      let el = strong.querySelector('[data-artworks]');
      if (!el) {
        // wrap the leading number ("5" of "5+") so only the digits change
        const node = strong.firstChild;
        const m = node && node.nodeType === 3 && node.textContent.match(/^(\d+)(.*)$/);
        if (!m) return null;
        el = doc.createElement('span');
        el.textContent = m[1];
        node.textContent = m[2];
        strong.insertBefore(el, node);
      }
      const target = Number(el.textContent);
      el.textContent = '0';
      return { el, target };
    }).filter(Boolean);
    // vertical motion blur: one SVG blur filter per number, strong while counting fast, sharp at the end
    const svgNS = 'http://www.w3.org/2000/svg';
    const svg = doc.createElementNS(svgNS, 'svg');
    svg.setAttribute('aria-hidden', 'true');
    svg.style.cssText = 'position:absolute;width:0;height:0;overflow:hidden';
    nums.forEach((n, i) => {
      const filter = doc.createElementNS(svgNS, 'filter');
      filter.id = `count-blur-${i}`;
      filter.setAttribute('x', '-10%'); filter.setAttribute('width', '120%');
      filter.setAttribute('y', '-50%'); filter.setAttribute('height', '200%');
      const blur = doc.createElementNS(svgNS, 'feGaussianBlur');
      blur.setAttribute('stdDeviation', '0 0');
      filter.append(blur);
      svg.append(filter);
      n.blur = blur;
      n.el.style.display = 'inline-block';
    });
    body.append(svg);
    const MAX_BLUR = 7;   // px of vertical blur at full speed
    const io = new IntersectionObserver(([entry]) => {
      if (!entry.isIntersecting) return;
      io.disconnect();
      nums.forEach(({ el, target, blur }, i) => {
        const start = performance.now() + i * 120;
        const duration = 1800;
        el.style.filter = `url(#count-blur-${i})`;
        const step = (now) => {
          const p = Math.min(Math.max((now - start) / duration, 0), 1);
          el.textContent = Math.round(target * (1 - Math.pow(1 - p, 4)));   // ease-out quart
          const speed = Math.pow(1 - p, 3);                                    // derivative of ease-out quart, 1 -> 0
          const started = now >= start;
          blur.setAttribute('stdDeviation', `0 ${(started ? MAX_BLUR * speed : 0).toFixed(2)}`);
          if (p < 1) requestAnimationFrame(step);
          else el.style.filter = '';
        };
        requestAnimationFrame(step);
      });
    }, { threshold: 0.5 });
    io.observe(stats);
  }

  // Artwork counter
  const counter = doc.querySelector('[data-count]');
  if (counter && hasIO && !reduceMotion) {
    const target = Number(counter.dataset.count);
    const io = new IntersectionObserver(([entry]) => {
      if (!entry.isIntersecting) return;
      io.disconnect();
      const start = performance.now();
      const duration = 1600;
      const step = (now) => {
        const p = Math.min((now - start) / duration, 1);
        counter.textContent = Math.round(target * (1 - Math.pow(1 - p, 3)));
        if (p < 1) requestAnimationFrame(step);
      };
      requestAnimationFrame(step);
    }, { threshold: 0.6 });
    io.observe(counter);
  }

  // Packaging: rows slide horizontally while scrolling (desktop)
  const rows = doc.querySelectorAll('.hrow');
  if (rows.length && !reduceMotion) {
    const phone = matchMedia('(max-width: 768px)');
    let frame = 0;
    const update = () => {
      frame = 0;
      rows.forEach((row) => {
        const track = row.firstElementChild;
        if (phone.matches) { track.style.removeProperty('--shift'); return; }
        const dir = Number(row.dataset.dir);
        let shift = dir * window.scrollY * 1.17;
        if (dir < 0) {
          shift = Math.max(shift, -(track.scrollWidth - row.clientWidth));
        } else {
          const gap = parseFloat(getComputedStyle(track).columnGap) || 0;
          shift = Math.min(shift, track.firstElementChild.offsetWidth + gap);
        }
        track.style.setProperty('--shift', `${shift}px`);
      });
    };
    const request = () => { if (!frame) frame = requestAnimationFrame(update); };
    addEventListener('scroll', request, { passive: true });
    addEventListener('resize', request);
    update();
  }

  // Lightbox: click a work on a category page to see it large; browse with arrows, keys or swipe
  const lbItems = [...doc.querySelectorAll('[data-lb]')];
  if (lbItems.length) {
    const box = doc.createElement('div');
    box.className = 'lightbox';
    box.setAttribute('role', 'dialog');
    box.setAttribute('aria-modal', 'true');
    box.setAttribute('aria-label', 'Image viewer');
    box.hidden = true;
    box.innerHTML = `
      <div class="lightbox__stage"><div class="lightbox__media"></div></div>
      <p class="lightbox__count" aria-live="polite"></p>
      <button class="lightbox__btn lightbox__close" type="button" aria-label="Close"><span aria-hidden="true"></span></button>
      <button class="lightbox__btn lightbox__prev" type="button" aria-label="Previous"><span aria-hidden="true"></span></button>
      <button class="lightbox__btn lightbox__next" type="button" aria-label="Next"><span aria-hidden="true"></span></button>`;
    body.append(box);
    const stage = box.querySelector('.lightbox__stage');
    const media = box.querySelector('.lightbox__media');
    const count = box.querySelector('.lightbox__count');
    const [btnClose, btnPrev, btnNext] = ['close', 'prev', 'next'].map((n) => box.querySelector(`.lightbox__${n}`));
    let index = -1;
    let opener = null;
    const preloaded = new Set();

    const info = (el) => {
      const img = el.querySelector('img');
      const video = el.dataset.video;
      return {
        video,
        full: el.getAttribute('href'),
        thumb: img ? img.currentSrc || img.src : el.querySelector('video')?.poster,
        alt: img ? img.alt : (el.getAttribute('aria-label') || '').replace(/^Play video: /, ''),
        w: Number(el.dataset.w) || (img ? img.naturalWidth : 16),
        h: Number(el.dataset.h) || (img ? img.naturalHeight : 9),
      };
    };
    const preload = (i) => {
      const el = lbItems[(i + lbItems.length) % lbItems.length];
      const url = el && el.getAttribute('href');
      if (url && !el.dataset.video && !preloaded.has(url)) { preloaded.add(url); new Image().src = url; }
    };
    // fit the item inside the stage, keeping its aspect ratio
    const fitSize = (w, h) => {
      const cs = getComputedStyle(stage);
      const aw = stage.clientWidth - parseFloat(cs.paddingLeft) - parseFloat(cs.paddingRight);
      const ah = stage.clientHeight - parseFloat(cs.paddingTop) - parseFloat(cs.paddingBottom);
      const s = Math.min(aw / w, ah / h, 1.6);
      return [Math.round(w * s), Math.round(h * s)];
    };

    const render = (i, fromEl) => {
      index = (i + lbItems.length) % lbItems.length;
      const el = lbItems[index];
      const it = info(el);
      // text first: it affects how much room the image gets
      count.textContent = `${index + 1} / ${lbItems.length}`;
      media.innerHTML = '';
      if (it.video) {
        const v = doc.createElement('video');
        Object.assign(v, { src: it.video, controls: true, autoplay: true, loop: true, playsInline: true, poster: it.thumb || '' });
        v.setAttribute('aria-label', it.alt);
        v.addEventListener('loadedmetadata', () => {
          const [w, h] = fitSize(v.videoWidth, v.videoHeight);
          media.style.width = `${w}px`; media.style.height = `${h}px`;
        });
        media.append(v);
        const [w, h] = fitSize(16, 10);
        media.style.width = `${w}px`; media.style.height = `${h}px`;
      } else {
        // show the sharp thumbnail at once, swap to the full-size image when it has loaded
        const img = doc.createElement('img');
        img.alt = it.alt;
        img.src = it.thumb;
        img.decoding = 'async';
        media.append(img);
        const full = new Image();
        full.onload = () => { if (lbItems[index] === el) img.src = it.full; };
        full.src = it.full;
        const [w, h] = fitSize(it.w, it.h);
        media.style.width = `${w}px`; media.style.height = `${h}px`;
      }
      preload(index + 1); preload(index - 1);

      // zoom out of the clicked tile (FLIP)
      if (fromEl && !reduceMotion && media.animate) {
        const a = fromEl.getBoundingClientRect();
        const b = media.getBoundingClientRect();
        if (a.width && b.width) {
          const sx = a.width / b.width; const sy = a.height / b.height;
          const dx = a.left + a.width / 2 - (b.left + b.width / 2);
          const dy = a.top + a.height / 2 - (b.top + b.height / 2);
          media.animate([
            { transform: `translate(${dx}px, ${dy}px) scale(${sx}, ${sy})`, borderRadius: '8px' },
            { transform: 'none', borderRadius: '4px' },
          ], { duration: 460, easing: 'cubic-bezier(0.22, 0.8, 0.2, 1)' });
        }
      } else if (!reduceMotion && media.animate) {
        media.animate([{ opacity: 0.4 }, { opacity: 1 }], { duration: 220, easing: 'ease-out' });
      }
    };

    const open = (el) => {
      opener = el;
      box.hidden = false;
      doc.documentElement.classList.add('lightbox-open');
      requestAnimationFrame(() => box.classList.add('is-open'));
      render(lbItems.indexOf(el), el);
      btnClose.focus({ preventScroll: true });
    };
    const close = () => {
      if (box.hidden) return;
      box.classList.remove('is-open');
      doc.documentElement.classList.remove('lightbox-open');
      const v = media.querySelector('video'); if (v) v.pause();
      const done = () => { box.hidden = true; media.innerHTML = ''; };
      if (reduceMotion) done(); else setTimeout(done, 250);
      if (opener) opener.focus({ preventScroll: true });
    };
    const go = (d) => render(index + d);

    lbItems.forEach((el) => {
      el.addEventListener('click', (e) => {
        if (e.metaKey || e.ctrlKey || e.shiftKey || e.button > 0) return; // let "open in new tab" work
        e.preventDefault();
        open(el);
      });
      if (el.tagName !== 'A') {
        el.addEventListener('keydown', (e) => {
          if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); open(el); }
        });
      }
    });
    btnClose.addEventListener('click', close);
    btnPrev.addEventListener('click', () => go(-1));
    btnNext.addEventListener('click', () => go(1));
    // click on the dark area (not on the work itself) closes
    box.addEventListener('click', (e) => { if (e.target === box || e.target === stage) close(); });
    doc.addEventListener('keydown', (e) => {
      if (box.hidden) return;
      if (e.key === 'Escape') close();
      else if (e.key === 'ArrowRight') go(1);
      else if (e.key === 'ArrowLeft') go(-1);
      else if (e.key === 'Tab') {
        // keep focus inside the viewer
        const f = [btnClose, btnPrev, btnNext, ...media.querySelectorAll('video')];
        const i = f.indexOf(doc.activeElement);
        e.preventDefault();
        f[(i + (e.shiftKey ? -1 : 1) + f.length) % f.length].focus();
      }
    });
    // swipe on touch screens
    let sx = null; let sy = 0;
    stage.addEventListener('pointerdown', (e) => { if (e.pointerType !== 'mouse') { sx = e.clientX; sy = e.clientY; } });
    stage.addEventListener('pointerup', (e) => {
      if (sx === null) return;
      const dx = e.clientX - sx; const dy = e.clientY - sy; sx = null;
      if (Math.abs(dx) > 50 && Math.abs(dx) > Math.abs(dy) * 1.5) go(dx < 0 ? 1 : -1);
    });
    addEventListener('resize', () => { if (!box.hidden) render(index); });
  }

  // Instagram previews under Connect (Behold JSON feed). Loads when the section comes near,
  // shows the 6 newest posts, and stays hidden if the feed is missing or fails.
  const insta = doc.querySelector('.insta[data-feed]');
  if (insta && insta.dataset.feed) {
    const grid = insta.querySelector('.insta__grid');
    const pick = (p) => {
      const s = p.sizes || {};
      const size = s.medium || s.small || s.large;
      if (size && size.mediaUrl) return size.mediaUrl;
      return p.mediaType === 'VIDEO' ? (p.thumbnailUrl || p.mediaUrl) : (p.mediaUrl || p.thumbnailUrl);
    };
    const load = () => fetch(insta.dataset.feed)
      .then((r) => (r.ok ? r.json() : Promise.reject(r.status)))
      .then((data) => {
        const posts = (Array.isArray(data) ? data : data.posts || []).filter((p) => p.permalink && pick(p)).slice(0, 6);
        if (!posts.length) return;
        grid.textContent = '';
        posts.forEach((p, i) => {
          const li = doc.createElement('li');
          li.className = 'insta__item';
          li.style.setProperty('--i', i);
          const a = doc.createElement('a');
          a.href = p.permalink;
          a.target = '_blank';
          a.rel = 'noopener';
          const text = (p.prunedCaption || p.caption || '').replace(/\s+/g, ' ').trim();
          a.setAttribute('aria-label', `Instagram post${text ? `: ${text.slice(0, 90)}` : ''} (opens Instagram)`);
          const img = doc.createElement('img');
          img.src = pick(p);
          img.alt = '';
          img.loading = 'lazy';
          img.decoding = 'async';
          img.addEventListener('error', () => li.remove());
          a.append(img);
          const kind = p.isReel || p.mediaType === 'VIDEO' ? 'video' : p.mediaType === 'CAROUSEL_ALBUM' ? 'carousel' : '';
          if (kind) {
            const badge = doc.createElement('span');
            badge.className = `insta__badge insta__badge--${kind}`;
            badge.setAttribute('aria-hidden', 'true');
            a.append(badge);
          }
          li.append(a);
          grid.append(li);
        });
        insta.hidden = false;
        requestAnimationFrame(() => insta.classList.add('is-loaded'));
      })
      .catch(() => { /* feed unavailable: keep the block hidden */ });
    // not shown on phones (see CSS), so only fetch on wider screens
    const wide = matchMedia('(min-width: 769px)');
    let started = false;
    const start = () => {
      if (started || !wide.matches) return;
      started = true;
      if (hasIO) {
        const io = new IntersectionObserver(([e]) => { if (e.isIntersecting) { io.disconnect(); load(); } }, { rootMargin: '800px 0px' });
        io.observe(insta.closest('section') || insta);
      } else {
        load();
      }
    };
    start();
    wide.addEventListener('change', start);
  }
})();
