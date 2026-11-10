// SIF Ventures site behaviour: the mobile menu, and a slight drift of the hero drawing
// toward the pointer so the drawing feels like an object in space.
(function () {
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

  var reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  var fine = window.matchMedia("(hover: hover) and (pointer: fine)").matches;
  if (reduce || !fine) return;
  // The drawing eases toward the pointer every frame instead of jumping to it.
  document.querySelectorAll(".hero").forEach(function (hero) {
    var art = hero.querySelector(".hero-art");
    if (!art) return;
    var tx = 0, ty = 0, x = 0, y = 0, raf = 0;
    function step() {
      x += (tx - x) * 0.06;
      y += (ty - y) * 0.06;
      art.style.setProperty("--px", x.toFixed(2) + "px");
      art.style.setProperty("--py", y.toFixed(2) + "px");
      raf = Math.abs(tx - x) > 0.05 || Math.abs(ty - y) > 0.05 ? requestAnimationFrame(step) : 0;
    }
    function aim(nx, ny) { tx = nx; ty = ny; if (!raf) raf = requestAnimationFrame(step); }
    hero.addEventListener("pointermove", function (e) {
      var r = hero.getBoundingClientRect();
      aim(((e.clientX - r.left) / r.width - 0.5) * -18, ((e.clientY - r.top) / r.height - 0.5) * -12);
    });
    hero.addEventListener("pointerleave", function () { aim(0, 0); });
  });
})();
