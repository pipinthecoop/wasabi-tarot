'use strict';
const $ = id => document.getElementById(id);
const motion = matchMedia('(prefers-reduced-motion: reduce)');
let cards = [], filtered = [], index = 0, opener = null;
const dialog = $('card-detail');
function node(tag, text, className) {
  const element = document.createElement(tag);
  if (text !== undefined) element.textContent = text;
  if (className) element.className = className;
  return element;
}
function category(card) { return card.id.startsWith('major-') ? 'major' : card.id.split('-')[0]; }
function label(card) { const suit = category(card); return suit === 'major' ? 'Major Arcana' : suit[0].toUpperCase() + suit.slice(1); }
function image(card) {
  const art = node('img');
  art.src = '/assets/decks/crt/' + card.id + ($('animate').checked ? '.gif' : '.png');
  art.alt = card.name + ': original green CRT tarot artwork';
  art.width = 600; art.height = 900;
  art.onerror = () => { if (art.dataset.fallback !== '1') { art.dataset.fallback = '1'; art.src = '/assets/decks/crt/' + card.id + '.png'; } };
  return art;
}
function close() { if (dialog.open) dialog.close(); }
function details() {
  const card = filtered[index];
  const frame = node('button', undefined, 'focus-art');
  frame.setAttribute('aria-label', 'Return to the deck'); frame.append(image(card));
  frame.addEventListener('click', close);
  const name = node('h2', card.name, 'card-name'); name.id = 'detail-name';
  $('detail-content').replaceChildren(frame, name, node('small', label(card)), node('p', card.meaning, 'detail-meaning'));
  $('detail-index').textContent = (index + 1) + ' / ' + filtered.length;
}
function open(card, trigger) {
  if (dialog.open) { close(); return; }
  opener = trigger; index = filtered.findIndex(item => item.id === card.id);
  trigger.setAttribute('aria-expanded', 'true'); details(); dialog.showModal();
}
function navigate(delta) { index = (index + delta + filtered.length) % filtered.length; details(); }
function render() {
  close();
  const term = $('search').value.trim().toLocaleLowerCase();
  filtered = cards.filter(card => ($('suit').value === 'all' || category(card) === $('suit').value) && (card.name + ' ' + card.meaning).toLocaleLowerCase().includes(term));
  $('gallery').replaceChildren();
  for (const card of filtered) {
    const item = node('article', undefined, 'gallery-card');
    const button = node('button', undefined, 'gallery-art');
    button.dataset.card = card.id;
    button.setAttribute('aria-label', 'Enlarge ' + card.name);
    button.setAttribute('aria-haspopup', 'dialog'); button.setAttribute('aria-expanded', 'false');
    const art = image(card); art.loading = 'lazy'; button.append(art);
    button.addEventListener('click', () => open(card, button));
    item.append(button, node('h2', card.name, 'card-name'), node('small', label(card))); $('gallery').append(item);
  }
  $('count').textContent = filtered.length + ' of ' + cards.length + ' cards';
  $('empty').hidden = filtered.length !== 0;
}
$('filters').addEventListener('submit', e => e.preventDefault());
$('search').addEventListener('input', render); $('suit').addEventListener('change', render);
$('animate').addEventListener('change', () => { if (dialog.open) details(); for (const item of document.querySelectorAll('.gallery-art')) { const card = cards.find(card => card.id === item.dataset.card); const art = image(card); art.loading = 'lazy'; item.replaceChildren(art); } });
motion.addEventListener('change', e => { $('animate').checked = !e.matches; $('animate').dispatchEvent(new Event('change')); });
$('close').addEventListener('click', close);
$('previous').addEventListener('click', () => navigate(-1)); $('next').addEventListener('click', () => navigate(1));
dialog.addEventListener('click', e => { if (!e.target.closest('.gallery-navigation')) close(); });
dialog.addEventListener('keydown', e => { if (e.key === 'ArrowRight' || e.key === 'ArrowLeft') { e.preventDefault(); navigate(e.key === 'ArrowRight' ? 1 : -1); } });
dialog.addEventListener('close', () => { if (opener) { opener.setAttribute('aria-expanded', 'false'); if (opener.isConnected) opener.focus({preventScroll:true}); } opener = null; });
async function init() {
  $('animate').checked = !motion.matches;
  const registry = await (await fetch('/web/demo.json')).json();
  cards = registry.cards.filter(card => registry.decks.crt.cards.includes(card.id)); render();
}
init().catch(() => { $('count').textContent = 'The deck could not load. Please refresh to try again.'; });
