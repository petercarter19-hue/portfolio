(() => {
  const controls = document.querySelector("[data-preview-controls]");
  if (!controls) return;

  const submitReview = () => controls.requestSubmit();
  controls.querySelectorAll("select").forEach((select) => {
    select.addEventListener("change", submitReview);
  });
  controls
    .querySelector('input[name="largeText"]')
    ?.addEventListener("change", submitReview);
})();
