// Only the first card is shown without JavaScript; choose once per page visit.
document.querySelectorAll('[data-game-pick]').forEach((wrap) => {
  const cards = [...wrap.querySelectorAll('.game-pick')];
  const pick = Math.floor(Math.random() * cards.length);
  cards.forEach((card, index) => { card.hidden = index !== pick; });
});
