const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const rules = require('../game-core.js');
const context = {window: {}};
vm.runInNewContext(fs.readFileSync(path.join(__dirname, '../game-content.js'), 'utf8'), context);
const content = JSON.parse(JSON.stringify(context.window.CONFERENCE_CONTENT));
let checks = 0;
function check(value, message) { assert.ok(value, message); checks++; }
for (const count of [1, 2, 3, 4, 5, 6]) {
  const game = rules.newGame(Array.from({length: count}, (_, index) => 'Team ' + (index + 1)));
  check(rules.validate(game, content), `New ${count}-team game validates`);
  for (let pick = 0; pick < 30; pick++) {
    const allowed = rules.allowedTopics(game, content);
    const card = content.cards.find(card => allowed.includes(card.topic) && !game.rounds.some(round => round.id === card.id));
    check(!!card, 'Balanced selection never runs out of eligible clues');
    if (count === 6 && pick < 6) check(card.topic === content.topics[pick].id, 'First six picks use assigned categories');
    check(rules.select(game, content, card.id), 'Clue opens');
    check(!rules.complete(game, content), 'Story cannot be scored');
    game.active.phase = 'reveal';
    check(!rules.complete(game, content), 'Every team needs an explicit award');
    game.active.awards = game.teams.map((_, index) => index % 3 === 0 ? card.value : index % 3 === 1 ? card.value / 2 : 0);
    check(rules.validate(game, content), 'Draft scoring survives a save');
    check(rules.complete(game, content), 'All-team scoring commits');
    check(!rules.complete(game, content), 'Points cannot be applied twice');
    check(rules.validate(game, content), 'Completed scoring validates');
    if (pick === 11) check(Object.values(rules.coverage(game, content)).every(value => value === 2), 'First 12 clues cover all six categories twice');
  }
  check(new Set(game.rounds.map(round => round.id)).size === 30, 'All 30 clues can be played exactly once');
  for (let i = 0; i < 30; i++) check(rules.undo(game), 'Undo restores a completed clue');
  check(game.teams.every(team => team.score === 0), 'Undo restores original scores');
}
const game = rules.newGame(['Leader'], 40, false);
check(rules.select(game, content, 'covenants-500'), 'Open selection permits any category');
game.active.phase = 'reveal'; game.active.awards = [500]; rules.complete(game, content);
game.adjustments.push({team: 0, delta: -500}); game.teams[0].score = 0;
check(rules.undo(game) && game.teams[0].score === 0, 'Undo after manual correction keeps scores nonnegative');
check(rules.validate(game, content), 'Correction and undo remain a consistent backup');
for (const invalid of [null, {}, {...game, teams: [null]}, {...game, teams: [{name: 'Leader', score: 500}]}, {...game, rounds: [{id: 'unknown', awards: [100]}]}, {...game, screen: 'clue'}, {...game, elapsed: -1}]) check(!rules.validate(invalid, content), 'Invalid backups are rejected');
for (const card of content.cards) {
  check(card.intro && card.intro !== card.retelling && card.retelling && card.context && card.clips.length, `${card.id} separates its clue introduction from the complete retelling`);
  check(typeof card.takeaway==='string' && card.takeaway.length>20 && card.takeaway!==card.context, `${card.id} has a main takeaway separate from source cautions`);
  for (const relative of [card.image, ...card.clips.map(clip => clip.path)]) check(fs.existsSync(path.join(__dirname, '..', relative)), 'Referenced media exists');
  check(card.clips.every(clip=>Number.isInteger(clip.previewIndex) && clip.previewIndex>=0 && clip.previewIndex<content.clipPreviewSheet.columns*content.clipPreviewSheet.rows),'Every clip has a first-frame preview');
  check(card.clips.every(clip=>clip.previewTime===(clip.start<2?2:0)), 'Opening fades use a two-second preview without altering the source clip');
}
check(fs.existsSync(path.join(__dirname,'..',content.clipPreviewSheet.path)),'First-frame preview image exists');
// These are the details the easy clues ask teams to recall, not introduction material.
const recallDetails = {
  'following-100': ['peach', 'peaches'],
  'following-200': ['scripture', 'Book of Mormon', 'purpose', 'happier', 'wanted to stay'],
  'identity-100': ['nothing', 'already loved'],
  'identity-200': ['recognition', 'respect', 'worth', 'concern', 'belonging', 'matter'],
  'revelation-100': ['magazine'],
  'revelation-200': ['look again', 'okay', 'asked whether'],
  'hope-100': ['oatmeal', 'milk', 'hot', 'cold'],
  'hope-200': ['peace', 'assurance', 'Spirit', 'practical', 'assistance'],
  'covenants-100': ['baptism', 'baptized'],
  'covenants-200': ['ordinances', 'covenants', 'blessings'],
  'serving-100': ['unbuttoned', 'unbutton', 'sleeve', 'lapel'],
  'serving-200': ['love', 'personally', 'by name']
};
for (const [id, details] of Object.entries(recallDetails)) {
  const intro = content.cards.find(card => card.id === id).intro.toLowerCase();
  check(details.every(detail => !new RegExp('\\b' + detail.toLowerCase() + '\\b').test(intro)), `${id} keeps its tested recall details out of the introduction`);
}
console.log(`Passed ${checks} game-rule and content checks.`);
