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
  document.querySelectorAll(".hero").forEach(function (hero) {
    var art = hero.querySelector(".hero-art");
    if (!art) return;
    hero.addEventListener("pointermove", function (e) {
      var r = hero.getBoundingClientRect();
      var x = (e.clientX - r.left) / r.width - 0.5;
      var y = (e.clientY - r.top) / r.height - 0.5;
      art.style.setProperty("--px", (x * -18).toFixed(1) + "px");
      art.style.setProperty("--py", (y * -12).toFixed(1) + "px");
    });
    hero.addEventListener("pointerleave", function () {
      art.style.setProperty("--px", "0px");
      art.style.setProperty("--py", "0px");
    });
  });
})();
