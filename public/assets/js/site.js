// SIF Ventures site behaviour: mobile menu, the hero network, and card light.
(function () {
  var reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  /* ---------- Mobile menu ---------- */
  var menu = document.querySelector(".menu");
  if (menu) {
    menu.addEventListener("click", function (e) {
      if (e.target.closest("a")) menu.removeAttribute("open");
    });
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape" && menu.hasAttribute("open")) {
        menu.removeAttribute("open");
        menu.querySelector("summary").focus();
      }
    });
    document.addEventListener("click", function (e) {
      if (menu.hasAttribute("open") && !menu.contains(e.target)) menu.removeAttribute("open");
    });
  }

  /* ---------- Hero network ----------
     Members are nodes, introductions are edges. Gold nodes send a signal along an edge
     to a neighbour, which may pass it on: the route an introduction takes. */
  var GOLD = "221,178,73";
  var MIST = "244,245,247";
  var LINK = 150;

  function Network(hero) {
    var canvas = document.createElement("canvas");
    canvas.className = "hero-net";
    canvas.setAttribute("aria-hidden", "true");
    hero.insertBefore(canvas, hero.firstChild);
    var ctx = canvas.getContext("2d");
    var w = 0, h = 0, nodes = [], pulses = [], raf = 0, running = false, lastSpawn = 0;
    var pointer = { x: -1e4, y: -1e4 };

    function build() {
      var rect = hero.getBoundingClientRect();
      var dpr = Math.min(window.devicePixelRatio || 1, 2);
      w = rect.width; h = rect.height;
      canvas.width = Math.round(w * dpr); canvas.height = Math.round(h * dpr);
      canvas.style.width = w + "px"; canvas.style.height = h + "px";
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      var count = Math.max(24, Math.min(96, Math.round((w * h) / 13000)));
      nodes = [];
      for (var i = 0; i < count; i++) {
        var gold = Math.random() < 0.1;
        nodes.push({
          x: Math.random() * w, y: Math.random() * h,
          vx: (Math.random() - 0.5) * 0.14, vy: (Math.random() - 0.5) * 0.14,
          r: gold ? 2 : Math.random() < 0.2 ? 1.6 : 1.1, gold: gold, phase: Math.random() * 6.28
        });
      }
      pulses = [];
      draw(performance.now());
    }

    function neighbour(n, exclude) {
      var best = null, bestD = LINK * LINK;
      for (var i = 0; i < nodes.length; i++) {
        var m = nodes[i];
        if (m === n || m === exclude) continue;
        var dx = m.x - n.x, dy = m.y - n.y, d = dx * dx + dy * dy;
        if (d < bestD && Math.random() < 0.7) { best = m; bestD = d; }
      }
      return best;
    }

    function spawn(t) {
      var golds = nodes.filter(function (n) { return n.gold; });
      if (!golds.length) return;
      var a = golds[Math.floor(Math.random() * golds.length)];
      var b = neighbour(a);
      if (b) pulses.push({ a: a, b: b, t0: t, dur: 1300 + Math.random() * 500, hops: 3 });
    }

    function draw(t) {
      ctx.clearRect(0, 0, w, h);
      var i, j, a, b;
      if (!reduce) {
        for (i = 0; i < nodes.length; i++) {
          a = nodes[i];
          a.x += a.vx; a.y += a.vy;
          if (a.x < 0 || a.x > w) a.vx *= -1;
          if (a.y < 0 || a.y > h) a.vy *= -1;
        }
      }
      ctx.lineWidth = 1;
      for (i = 0; i < nodes.length; i++) {
        a = nodes[i];
        for (j = i + 1; j < nodes.length; j++) {
          b = nodes[j];
          var dx = a.x - b.x, dy = a.y - b.y, d2 = dx * dx + dy * dy;
          if (d2 > LINK * LINK) continue;
          var k = 1 - Math.sqrt(d2) / LINK;
          var mx = (a.x + b.x) / 2 - pointer.x, my = (a.y + b.y) / 2 - pointer.y;
          var near = Math.max(0, 1 - Math.sqrt(mx * mx + my * my) / 230);
          ctx.strokeStyle = near > 0.04
            ? "rgba(" + GOLD + "," + (k * (0.22 + near * 0.55)).toFixed(3) + ")"
            : "rgba(" + MIST + "," + (k * 0.22).toFixed(3) + ")";
          ctx.beginPath(); ctx.moveTo(a.x, a.y); ctx.lineTo(b.x, b.y); ctx.stroke();
        }
      }
      for (i = 0; i < nodes.length; i++) {
        a = nodes[i];
        ctx.fillStyle = a.gold ? "rgba(" + GOLD + ",0.95)" : "rgba(" + MIST + ",0.55)";
        ctx.beginPath(); ctx.arc(a.x, a.y, a.r, 0, 6.2832); ctx.fill();
        if (a.gold && !reduce) {
          var p = (Math.sin(t / 1100 + a.phase) + 1) / 2;
          ctx.strokeStyle = "rgba(" + GOLD + "," + (0.32 * (1 - p)).toFixed(3) + ")";
          ctx.beginPath(); ctx.arc(a.x, a.y, a.r + 3 + p * 9, 0, 6.2832); ctx.stroke();
        }
      }
      if (reduce) return;
      if (t - lastSpawn > 900) { spawn(t); lastSpawn = t; }
      var next = [];
      for (i = 0; i < pulses.length; i++) {
        var s = pulses[i], u = (t - s.t0) / s.dur;
        if (u >= 1) {
          if (s.hops > 1 && Math.random() < 0.75) {
            var c = neighbour(s.b, s.a);
            if (c) next.push({ a: s.b, b: c, t0: t, dur: s.dur, hops: s.hops - 1 });
          }
          continue;
        }
        var e = u < 0.5 ? 2 * u * u : 1 - Math.pow(-2 * u + 2, 2) / 2;
        var x = s.a.x + (s.b.x - s.a.x) * e, y = s.a.y + (s.b.y - s.a.y) * e;
        var tx = s.a.x + (s.b.x - s.a.x) * Math.max(0, e - 0.18), ty = s.a.y + (s.b.y - s.a.y) * Math.max(0, e - 0.18);
        var grad = ctx.createLinearGradient(tx, ty, x, y);
        grad.addColorStop(0, "rgba(" + GOLD + ",0)");
        grad.addColorStop(1, "rgba(" + GOLD + ",0.85)");
        ctx.strokeStyle = grad; ctx.lineWidth = 1.5;
        ctx.beginPath(); ctx.moveTo(tx, ty); ctx.lineTo(x, y); ctx.stroke();
        ctx.fillStyle = "rgba(" + GOLD + ",1)";
        ctx.beginPath(); ctx.arc(x, y, 1.8, 0, 6.2832); ctx.fill();
        next.push(s);
      }
      pulses = next;
    }

    function frame(t) { draw(t); raf = requestAnimationFrame(frame); }
    function start() { if (!running && !reduce) { running = true; raf = requestAnimationFrame(frame); } }
    function stop() { running = false; cancelAnimationFrame(raf); }

    build();
    var resizeTimer;
    if ("ResizeObserver" in window) {
      var lastW = w;
      new ResizeObserver(function () {
        clearTimeout(resizeTimer);
        resizeTimer = setTimeout(function () {
          if (Math.abs(hero.getBoundingClientRect().width - lastW) > 1) { lastW = hero.getBoundingClientRect().width; build(); }
        }, 150);
      }).observe(hero);
    }
    if ("IntersectionObserver" in window) {
      new IntersectionObserver(function (entries) {
        entries[0].isIntersecting && !document.hidden ? start() : stop();
      }).observe(hero);
    } else { start(); }
    document.addEventListener("visibilitychange", function () { document.hidden ? stop() : start(); });
    hero.addEventListener("pointermove", function (e) {
      var r = hero.getBoundingClientRect();
      pointer.x = e.clientX - r.left; pointer.y = e.clientY - r.top;
    });
    hero.addEventListener("pointerleave", function () { pointer.x = pointer.y = -1e4; });
  }

  try {
    document.querySelectorAll(".hero").forEach(function (hero) { Network(hero); });
  } catch (err) { /* the hero reads fine without its network */ }

  /* ---------- Card light: a soft glow and gold edge that follow the pointer ---------- */
  if (!reduce && window.matchMedia("(hover: hover)").matches) {
    document.querySelectorAll(".card, .partners a").forEach(function (el) {
      el.classList.add("spot");
      el.addEventListener("pointermove", function (e) {
        var r = el.getBoundingClientRect();
        el.style.setProperty("--mx", e.clientX - r.left + "px");
        el.style.setProperty("--my", e.clientY - r.top + "px");
      });
    });
  }
})();
