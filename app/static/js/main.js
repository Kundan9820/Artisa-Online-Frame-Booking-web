document.addEventListener("DOMContentLoaded", function () {
  // Auto-dismiss flash messages after 5s
  document.querySelectorAll(".alert-dismissible").forEach(function (el) {
    setTimeout(function () {
      var alert = bootstrap.Alert.getOrCreateInstance(el);
      if (alert) alert.close();
    }, 6000);
  });

  // Quantity steppers (works for any [data-qty-input] group)
  document.querySelectorAll("[data-qty-decrease]").forEach(function (btn) {
    btn.addEventListener("click", function () {
      var input = document.getElementById(btn.dataset.qtyDecrease);
      var val = parseInt(input.value || "1", 10);
      if (val > 1) input.value = val - 1;
    });
  });
  document.querySelectorAll("[data-qty-increase]").forEach(function (btn) {
    btn.addEventListener("click", function () {
      var input = document.getElementById(btn.dataset.qtyIncrease);
      var val = parseInt(input.value || "1", 10);
      input.value = val + 1;
    });
  });

  // Product gallery: click thumbnail to swap main image
  document.querySelectorAll("[data-thumb]").forEach(function (thumb) {
    thumb.addEventListener("click", function () {
      var mainImg = document.getElementById("product-main-image");
      if (mainImg) mainImg.src = thumb.dataset.thumb;
      document.querySelectorAll("[data-thumb]").forEach(function (t) {
        t.classList.remove("border-brand-active");
      });
      thumb.classList.add("border-brand-active");
    });
  });

  // Live-updating cart total on quantity change forms (progressive enhancement,
  // still fully works without JS since each stepper's form can be submitted).
  document.querySelectorAll("form[data-cart-qty-form]").forEach(function (form) {
    var input = form.querySelector("input[type=number]");
    if (input) {
      input.addEventListener("change", function () {
        form.submit();
      });
    }
  });
});
