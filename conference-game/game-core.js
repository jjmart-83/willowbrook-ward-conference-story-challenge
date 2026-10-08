/* Shared game rules. Runs in the browser and in Node for rule checks. */
(function (root) {
  "use strict";
  const VERSION = 1;
  const answerSeconds = value => ({100: 20, 200: 25, 300: 35, 400: 45, 500: 60}[value] || 35);
  function newGame(names, minutes = 50, balanced = true) {
    return {version: VERSION, teams: names.map(name => ({name, score: 0})), minutes,
      target: minutes === 40 ? 12 : minutes === 70 ? 30 : 18, balanced,
      rounds: [], adjustments: [], active: null, screen: "board", elapsed: 0, sessionRunning: true};
  }
  function coverage(game, content) {
    return Object.fromEntries(content.topics.map(topic => [topic.id,
      game.rounds.filter(round => content.cards.find(card => card.id === round.id)?.topic === topic.id).length]));
  }
  function allowedTopics(game, content) {
    if (!game.balanced || game.rounds.length >= 12) return content.topics.map(topic => topic.id);
    if (game.teams.length === 6 && game.rounds.length < 6) return [content.topics[game.rounds.length].id];
    const counts = coverage(game, content);
    const minimum = Math.min(...Object.values(counts));
    return content.topics.filter(topic => counts[topic.id] === minimum).map(topic => topic.id);
  }
  function select(game, content, id) {
    const card = content.cards.find(card => card.id === id);
    if (!card || game.active || game.rounds.some(round => round.id === id) || !allowedTopics(game, content).includes(card.topic)) return false;
    game.active = {id, phase: "story", awards: game.teams.map(() => null), remaining: answerSeconds(card.value), running: false};
    game.screen = "clue";
    return true;
  }
  function complete(game, content) {
    const active = game.active;
    const card = content.cards.find(card => card.id === active?.id);
    if (!card || active.phase !== "reveal" || active.awards.length !== game.teams.length ||
      active.awards.some(value => ![0, card.value / 2, card.value].includes(value))) return false;
    const round = {id: active.id, awards: [...active.awards]};
    game.teams.forEach((team, index) => { team.score += round.awards[index]; });
    game.rounds.push(round);
    game.active = null;
    game.screen = "board";
    return true;
  }
  function undo(game) {
    if (game.active || !game.rounds.length) return false;
    const round = game.rounds.pop();
    game.teams.forEach((team, index) => {
      const result = team.score - round.awards[index];
      // A manual correction may have lowered the total below this clue's award.
      if (result < 0) game.adjustments.push({team: index, delta: -result});
      team.score = Math.max(0, result);
    });
    game.screen = "board";
    return true;
  }
  function validate(game, content) {
    if (!game || game.version !== VERSION || !Array.isArray(game.teams) || game.teams.length < 1 || game.teams.length > 6 ||
      !game.teams.every(team => team && typeof team.name === "string" && team.name.trim().length > 0 && team.name.length <= 36 && Number.isSafeInteger(team.score) && team.score >= 0) ||
      ![40, 50, 70].includes(game.minutes) || game.target !== ({40: 12, 50: 18, 70: 30}[game.minutes]) || typeof game.balanced !== "boolean" ||
      !Array.isArray(game.rounds) || game.rounds.length > 30 || !Array.isArray(game.adjustments) || game.adjustments.length > 500 ||
      !Number.isFinite(game.elapsed) || game.elapsed < 0 || game.elapsed > 604800 || typeof game.sessionRunning !== "boolean" ||
      !["board", "clue", "final", "closing"].includes(game.screen)) return false;
    const cardMap = new Map(content.cards.map(card => [card.id, card]));
    const used = new Set();
    const totals = game.teams.map(() => 0);
    for (const round of game.rounds) {
      const card = cardMap.get(round?.id);
      if (!card || used.has(round.id) || !Array.isArray(round.awards) || round.awards.length !== totals.length ||
        round.awards.some(value => ![0, card.value / 2, card.value].includes(value))) return false;
      used.add(round.id);
      round.awards.forEach((value, index) => { totals[index] += value; });
    }
    for (const adjustment of game.adjustments) {
      if (!adjustment || !Number.isInteger(adjustment.team) || adjustment.team < 0 || adjustment.team >= totals.length ||
        !Number.isSafeInteger(adjustment.delta) || Math.abs(adjustment.delta) > 1000000) return false;
      totals[adjustment.team] += adjustment.delta;
    }
    if (!game.teams.every((team, index) => team.score === totals[index])) return false;
    if (game.active !== null) {
      const active = game.active, card = cardMap.get(active?.id);
      if (!card || used.has(active.id) || game.screen !== "clue" || !["story", "question", "reveal"].includes(active.phase) ||
        !Array.isArray(active.awards) || active.awards.length !== totals.length ||
        active.awards.some(value => value !== null && ![0, card.value / 2, card.value].includes(value)) ||
        !Number.isFinite(active.remaining) || active.remaining < 0 || active.remaining > answerSeconds(card.value) ||
        typeof active.running !== "boolean") return false;
    } else if (game.screen === "clue") return false;
    return true;
  }
  const api = {VERSION, answerSeconds, newGame, coverage, allowedTopics, select, complete, undo, validate};
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else root.ConferenceRules = api;
})(typeof globalThis !== "undefined" ? globalThis : this);
