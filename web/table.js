'use strict';
const $ = id => document.getElementById(id);
const embedded = location.pathname.startsWith('/embed/');
let registry, live = null, busy = false, revealed = false;
const shoes = {};
let displayedCards = null, displayedPositions = null;
const motionPreference = window.matchMedia('(prefers-reduced-motion: reduce)');
function artSource(card) {
  return $('animate').checked ? card.art : (card.static_art || card.art);
}
function resolvedArt(source) { return source; }
const status = text => { $('status').textContent = text; };
function shuffleArray(items) {
  const copy = [...items];
  for (let i = copy.length - 1; i > 0; i--) {
    const number = crypto.getRandomValues(new Uint32Array(1))[0] % (i + 1);
    [copy[i], copy[number]] = [copy[number], copy[i]];
  }
  return copy;
}
function node(tag, text, className) {
  const element = document.createElement(tag);
  if (text !== undefined) element.textContent = text;
  if (className) element.className = className;
  return element;
}
function positions() {
  const chosen = $('spread').value;
  return chosen === 'custom' ? $('custom').value.split('|').map(p => p.trim()) : registry.spreads[chosen];
}
function deckState() {
  if (live) return live.decks.find(d => d.id === $('deck').value);
  return shoes[$('deck').value];
}
function backs() {
  revealed = false;
  displayedCards = null; displayedPositions = null;
  $('reading').hidden = true;
  $('cards').replaceChildren();
  const names = positions() || ['Focus'];
  for (const name of names.slice(0, 10)) {
    const slot = node('div', undefined, 'card-slot');
    const card = node('div', undefined, 'card');
    const art = node('img');
    art.src = live?.backs?.[$('deck').value] || registry?.decks?.[$('deck').value]?.card_back || '/assets/theme/card-back.webp';
    art.alt = 'Face-down celestial card: ' + (name || 'Your position');
    card.append(art); slot.append(card, node('small', name || 'Your position')); $('cards').append(slot);
  }
  counts();
}
function counts() {
  const shoe = deckState();
  if (!shoe) return;
  $('remaining').textContent = live ? shoe.remaining : shoe.draw.length;
  $('discard').textContent = live ? shoe.discard : shoe.discard.length;
  $('cycle').textContent = 'Cycle ' + shoe.cycle + ' · finite deck · no automatic reshuffle';
}
function reveal(cards, names) {
  revealed = true;
  displayedCards = cards; displayedPositions = names;
  $('cards').replaceChildren(); $('meanings').replaceChildren();
  cards.forEach((card, index) => {
    const slot = node('div', undefined, 'card-slot');
    const face = node('div', undefined, 'card');
    const art = node('img');
    const source = artSource(card);
    art.src = resolvedArt(source && (source.startsWith('https://') || source.startsWith('/assets/')) ? source : '/assets/theme/card-back.webp');
    art.onerror = () => { if (card.static_art && art.dataset.fallback !== '1') { art.dataset.fallback = '1'; art.src = resolvedArt(card.static_art); } };
    art.alt = names[index] + ': ' + card.name;
    face.append(art, node('span', card.name, 'card-name'));
    slot.append(face, node('small', names[index])); $('cards').append(slot);
    const meaning = node('article', undefined, 'meaning');
    meaning.append(node('small', names[index].toUpperCase()), node('h3', card.name), node('p', card.meaning));
    $('meanings').append(meaning);
  });
  $('reading').hidden = false;
  counts();
}
function values() {
  const val = {deck: {value: {selected_option: {value: $('deck').value}}}, spread: {value: {selected_option: {value: $('spread').value === 'custom' ? 'single' : $('spread').value}}}, custom: {value: {value: $('spread').value === 'custom' ? $('custom').value : ''}}, time: {value: {selected_time: $('time').value}}, zone: {value: {value: $('zone').value}}};
  return val;
}
function surfaceText(surface) {
  if (surface.errors) return Object.values(surface.errors).join(' ');
  return (surface.view?.blocks || []).filter(b => b.type === 'section').map(b => b.text.text).join(' ');
}
async function refreshLive() {
  const response = await fetch('/api/table', {credentials: 'same-origin', cache: 'no-store'});
  if (!response.ok) return false;
  live = await response.json();
  registry.spreads = live.spreads;
  $('mode').textContent = 'Live channel table · ' + live.channel;
  $('connect').textContent = 'Leave live table';
  const current = $('deck').value;
  $('deck').replaceChildren();
  live.decks.forEach(deck => { const option = node('option', deck.name); option.value = deck.id; $('deck').append(option); });
  if (live.decks.some(d => d.id === current)) $('deck').value = current;
  const chosen = $('spread').value;
  $('spread').replaceChildren();
  Object.keys(live.spreads).forEach(name => { const option = node('option', name.replaceAll('-', ' ')); option.value = name; $('spread').append(option); });
  const custom = node('option', 'Custom spread'); custom.value = 'custom'; $('spread').append(custom);
  if ([...$('spread').options].some(o => o.value === chosen)) $('spread').value = chosen;
  counts(); return true;
}
function lock(value) {
  busy = value;
  for (const id of ['draw', 'shuffle', 'daily']) $(id).disabled = value || embedded;
}
async function ritual(mode) {
  if (busy || embedded) return;
  const names = positions();
  if (!names?.length || names.length > 10 || names.some(p => !p || p.length > 100)) {
    status('Give your spread 1–10 nonempty positions, up to 100 characters each.'); return;
  }
  lock(true);
  try {
    if (live) {
      const sid = live.rituals[mode]; // capture before any asynchronous operation
      const response = await fetch('/api/ritual', {method: 'POST', credentials: 'same-origin', headers: {'Content-Type': 'application/json', 'X-CSRF-Token': live.csrf}, body: JSON.stringify({ritual: sid, values: values()})});
      const result = await response.json();
      if (!response.ok) throw new Error(result.error || 'The table is busy. Retry the same action.');
      status(result.text || surfaceText(result.surface));
      if (result.cards) reveal(result.cards, result.positions);
      if (!result.surface?.errors) await refreshLive();
    } else if (mode === 'draw') {
      const shoe = deckState();
      if (shoe.draw.length < names.length) { status('The deck rests: too few cards remain. Explicitly shuffle to begin a new cycle.'); return; }
      const cards = names.map(() => { const id = shoe.draw.pop(); shoe.discard.push(id); const card = registry.cards.find(c => c.id === id); const base = '/assets/decks/' + $('deck').value + '/' + id;
        return {...card, art: base + '.' + (registry.decks[$('deck').value].art_format || 'png'), static_art: base + '.png'}; });
      reveal(cards, names); status('Demo reading revealed. Your Slack deck is untouched.');
    } else if (mode === 'shuffle') {
      const shoe = deckState(); shoe.draw = shuffleArray(registry.decks[$('deck').value].cards); shoe.discard = []; shoe.cycle++; backs(); status('Demo deck shuffled. A new cycle begins; your Slack deck is untouched.');
    } else {
      try { new Intl.DateTimeFormat('en', {timeZone: $('zone').value}); } catch { status('Choose a valid IANA time zone. No ritual was scheduled.'); return; }
      status('Demo only: ' + $('time').value + ' ' + $('zone').value + '. No real schedule was created. Use Daily ritual in Slack, or connect a live table.');
    }
  } catch (error) { status(error.message); }
  finally { lock(false); }
}
$('choices').addEventListener('submit', e => e.preventDefault());
$('deck').addEventListener('change', backs);
$('spread').addEventListener('change', () => { $('custom-wrap').hidden = $('spread').value !== 'custom'; backs(); });
$('custom').addEventListener('input', backs);
$('draw').addEventListener('click', () => ritual('draw'));
$('shuffle').addEventListener('click', () => { if (!busy) { $('confirm').returnValue = ''; $('confirm').showModal(); } });
$('confirm').addEventListener('close', () => { if ($('confirm').returnValue === 'shuffle') ritual('shuffle'); else status('You left the deck as it was. No cards were consumed.'); });
$('reset-view').addEventListener('click', backs);
$('daily').addEventListener('click', () => $('schedule').showModal());
$('schedule-cancel').addEventListener('click', () => { $('schedule').close(); status('You left the table. No schedule was created.'); });
$('schedule-form').addEventListener('submit', e => { e.preventDefault(); $('schedule').close(); ritual('schedule'); });
$('connect').addEventListener('click', async () => {
  if (!live) { $('login').showModal(); return; }
  try {
    const response = await fetch('/api/logout', {method: 'POST', credentials: 'same-origin', headers: {'Content-Type': 'application/json', 'X-CSRF-Token': live.csrf}, body: '{}'});
    if (!response.ok) throw new Error('Could not close the live session. Try again.');
    location.reload();
  } catch (error) { status(error.message); }
});
$('login-cancel').addEventListener('click', () => { $('login-code').value = ''; $('login').close(); });
$('login-form').addEventListener('submit', async e => {
  e.preventDefault();
  try {
    const response = await fetch('/api/login', {method: 'POST', credentials: 'same-origin', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({code: $('login-code').value})});
    $('login-code').value = '';
    const result = await response.json();
    if (!response.ok) throw new Error(result.error);
    await refreshLive(); $('login').close(); backs(); status('Your verified Slack channel table is open.');
  } catch (error) { $('login-error').textContent = error.message; }
});
$('animate').addEventListener('change', () => { if (displayedCards) reveal(displayedCards, displayedPositions); });
motionPreference.addEventListener('change', e => { $('animate').checked = !e.matches; if (displayedCards) reveal(displayedCards, displayedPositions); });
async function init() {
  $('animate').checked = !motionPreference.matches;
  registry = await (await fetch('/web/demo.json')).json();
  $('deck').replaceChildren();
  for (const [id, spec] of Object.entries(registry.decks)) {
    shoes[id] = {draw: shuffleArray(spec.cards), discard: [], cycle: 1};
    const option = node('option', spec.name); option.value = id; $('deck').append(option);
  }
  if (embedded) {
    $('mode').textContent = 'Read-only embedded preview · no channel data or mutations';
    $('connect').hidden = true;
    lock(false);
    $('whisper').textContent = 'A glimpse of the parlor. Open /tarot in Slack to begin your own ritual.';
  } else { await refreshLive(); }
  backs();
}
init().catch(() => { lock(true); status('The illustrated table could not load. Your Slack deck is untouched.'); });
