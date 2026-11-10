// SIF Ventures site behaviour. The hero drawing stays still; its flow runs on hover (CSS).
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

})();
