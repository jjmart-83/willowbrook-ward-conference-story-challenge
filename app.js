"use strict";
const content = window.CONFERENCE_CONTENT;
const rules = window.ConferenceRules;
const STORAGE_KEY = "conference-story-challenge:v1";
const $ = id => document.getElementById(id);
const escapeHTML = value => String(value).replace(/[&<>"']/g, char => ({"&":"&amp;", "<":"&lt;", ">":"&gt;", '"':"&quot;", "'":"&#39;"}[char]));
const clone = value => JSON.parse(JSON.stringify(value));
const clock = seconds => `${Math.floor(Math.max(0, Math.ceil(seconds)) / 60)}:${String(Math.max(0, Math.ceil(seconds)) % 60).padStart(2, "0")}`;
const topicFor = card => content.topics.find(topic => topic.id === card.topic);
const cardFor = id => content.cards.find(card => card.id === id);
let game = null, saved = null, practice = null, storageAvailable = true;
let lastTick = performance.now(), lastSave = 0;
let playbackRequest = 0, pendingMedia = null;
const mediaUrls = new Set();
const teamNames = content.topics.map(topic => topic.group);
const iconPaths = {
  following: '<path d="M12 48c1-9 20-5 20-14s-16-5-16-13 13-11 26-9"/><path d="m36 7 8 5-6 7"/><circle cx="12" cy="49" r="3"/>',
  identity: '<path d="M32 49S9 36 9 23c0-12 16-15 23-3 7-12 23-9 23 3 0 13-23 26-23 26Z"/><path d="m32 8 1-5M12 10l-3-4m42 4 3-4"/>',
  revelation: '<circle cx="32" cy="32" r="23"/><path d="m24 40 5-15 11-1-5 15-11 1Z"/><path d="M32 9v6m0 34v6M9 32h6m34 0h6"/>',
  hope: '<path d="M7 45h50M17 45V26h30v19M24 45V32h16v13M13 26l19-15 19 15"/><path d="M32 11V6m-13 8-3-4m29 4 3-4"/>',
  covenants: '<path d="M7 21h19l8 7 5-5h18v20H42l-8 8-20-12H7V21Z"/><path d="m26 21 9-5 10 5M34 28l-8 7 6 4 7-6m-7 6 5 4m-3 8 5-6m-20-8 7 7"/>',
  serving: '<path d="M7 38h12l8 5h15c6 0 6 7 0 7H22L7 44V38Z"/><path d="m45 49 12-11c3-4-2-7-5-4l-11 9M36 33S24 26 24 18c0-7 9-9 12-3 4-6 12-4 12 3 0 8-12 15-12 15Z"/>'
};
const icon = id => `<svg viewBox="0 0 64 64" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${iconPaths[id]}</svg>`;

function notify(message) { $("notice").textContent = message; $("notice").hidden = false; }
function save() {
  if (!game) return;
  saved = clone(game);
  try { localStorage.setItem(STORAGE_KEY, JSON.stringify(saved)); $("saveStatus").textContent = "Saved on this browser · backups travel with you."; }
  catch { storageAvailable = false; $("saveStatus").textContent = "Browser saving unavailable. Use Save a backup before leaving."; }
}
function loadSaved() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return;
    const candidate = JSON.parse(raw);
    if (rules.validate(candidate, content)) saved = candidate;
    else notify("The saved game could not be read. You can start a new game or load a backup.");
  } catch { storageAvailable = false; notify("Browser saving is unavailable. You can still play and save a backup."); }
}
function focusGame() { $("main").focus({preventScroll: true}); window.scrollTo({top: 0, behavior: "instant"}); }
function pauseMedia() {
  playbackRequest++;
  pendingMedia?.abort(); pendingMedia = null;
  document.querySelectorAll("video").forEach(video => video.pause());
}
function releaseMedia() {
  pauseMedia();
  for (const url of mediaUrls) URL.revokeObjectURL(url);
  mediaUrls.clear();
}
async function playGameClip(video, clip, errorPanel, fullscreen = false, onEnd = null) {
  pauseMedia();
  const request = playbackRequest, controller = new AbortController();
  pendingMedia = controller;
  const selected = () => request === playbackRequest && video.isConnected && !video.closest("[hidden]");
  const leaveFullscreen = () => { if (document.fullscreenElement === video) document.exitFullscreen().catch(() => {}); };
  const failed = () => { if (!selected()) return; leaveFullscreen(); errorPanel.hidden = false; video.hidden = true; };
  errorPanel.hidden = true; video.hidden = false; video.src = clip.path;
  video.preload = "auto";
  video.playsInline = !(fullscreen || document.fullscreenElement === video || video.webkitDisplayingFullscreen);
  video.onerror = failed;
  video.onended = () => { if (selected() && !onEnd?.()) leaveFullscreen(); };
  // Request full screen while the preview click still supplies user activation.
  if (fullscreen && video.requestFullscreen) video.requestFullscreen().catch(() => {});
  else if (fullscreen && video.webkitEnterFullscreen) {
    try { video.webkitEnterFullscreen(); } catch { /* Native playback also opens full screen when playsInline is false. */ }
  }
  try {
    if (location.protocol !== "file:") {
      // GitHub Pages supports byte ranges. Older local static servers may send
      // the full file instead; a Blob makes their entire timeline seekable.
      const response = await fetch(clip.path, {headers: {Range: "bytes=0-0"}, signal: controller.signal});
      if (!response.ok) throw new Error("The clip could not be loaded.");
      if (response.status === 200) {
        const blob = await response.blob();
        if (!selected()) return;
        const url = URL.createObjectURL(blob); mediaUrls.add(url); video.src = url;
      } else await response.body?.cancel();
    }
    if (!selected()) return;
    await video.play();
  } catch (error) {
    if (error.name !== "AbortError" && selected() && (video.error || error.name !== "NotAllowedError")) failed();
  } finally { if (pendingMedia === controller) pendingMedia = null; }
}
function openModal(title, html) {
  pauseMedia();
  $("modalTitle").textContent = title;
  $("modalBody").innerHTML = html;
  if (!$("modal").open) $("modal").showModal();
}
function closeModal() { pauseMedia(); $("modal").close(); $("modalBody").replaceChildren(); lastTick = performance.now(); }
function confirmAction(title, message, label, action) {
  openModal(title, `<p>${escapeHTML(message)}</p><div class="dialog-actions"><button class="button primary" id="confirmAction">${escapeHTML(label)}</button><button class="button secondary" id="cancelAction">Keep current game</button></div>`);
  $("confirmAction").onclick = () => { closeModal(); action(); };
  $("cancelAction").onclick = closeModal;
}
function renderTeamFields() {
  $("teamFields").innerHTML = Array.from({length: Number($("teamCount").value)}, (_, index) => `<label class="field"><span class="team-dot topic-${content.topics[index].id}"></span>Team ${index + 1}<input id="teamName${index}" value="${escapeHTML(teamNames[index])}" maxlength="36" required><small>${escapeHTML(content.topics[index].label)}</small></label>`).join("");
  document.querySelectorAll("#teamFields input").forEach((input, index) => input.oninput = () => { teamNames[index] = input.value; });
}
function showSetup() {
  releaseMedia(); practice = null;
  if (game) { game.sessionRunning = false; if (game.active) game.active.running = false; save(); }
  game = null;
  $("setup").hidden = false; $("game").hidden = true;
  $("resumePanel").hidden = !saved;
  if (saved) $("resumeDescription").textContent = `${saved.teams.length} teams · ${saved.rounds.length} clues played${saved.active ? " · clue in progress" : ""} · ${saved.screen === "closing" ? "at the closing" : clock(saved.minutes * 60 - saved.elapsed) + " remaining"}`;
  focusGame();
}
function startGame() {
  const names = Array.from({length: Number($("teamCount").value)}, (_, index) => $("teamName" + index).value.trim() || `Team ${index + 1}`);
  game = rules.newGame(names, Number($("sessionLength").value), $("balancedSelection").checked);
  practice = null; lastTick = performance.now(); save(); render(); focusGame();
}
function resumeGame() {
  if (!saved) return;
  game = clone(saved); practice = null;
  if (game.active) game.active.running = false;
  game.sessionRunning = game.screen !== "closing";
  lastTick = performance.now(); save(); render(); focusGame();
}
function renderScores() {
  $("scoreboard").style.setProperty("--teams", game.teams.length);
  const current = game.rounds.length % game.teams.length;
  $("scoreboard").innerHTML = game.teams.map((team, index) => `<div class="team-score${index === current && ["board", "clue"].includes(game.screen) ? " active" : ""}"><div><span>${escapeHTML(team.name)}</span>${index === current && ["board", "clue"].includes(game.screen) ? '<small>CHOOSING TEAM</small>' : ''}</div><strong>${team.score.toLocaleString()}</strong></div>`).join("");
}
function render() {
  releaseMedia();
  $("setup").hidden = true; $("game").hidden = false;
  for (const [view, screen] of [["boardView", "board"], ["clueView", "clue"], ["finalView", "final"], ["closingView", "closing"]]) $(view).hidden = game.screen !== screen;
  $("roundLabel").textContent = `${game.rounds.length} OF ${game.target} PLANNED CLUES · ${game.teams.length} ${game.teams.length === 1 ? "TEAM" : "TEAMS"}`;
  $("gameHeading").textContent = {board: "Choose your next story.", clue: "One story. Every team.", final: "Make the connection.", closing: "Take the message with you."}[game.screen];
  renderScores();
  if (game.screen === "board") renderBoard();
  if (game.screen === "clue") renderClue();
  if (game.screen === "final") renderFinal();
  if (game.screen === "closing") renderClosing();
  updateClocks();
}
function renderBoard() {
  const counts = rules.coverage(game, content), allowed = rules.allowedTopics(game, content);
  const turn = game.teams[game.rounds.length % game.teams.length];
  const complete = game.rounds.length === content.cards.length;
  $("selectionHint").textContent = complete ? "Every story has been played. Ready for the final connection?" : `${turn.name}, choose ${allowed.length === 1 ? content.topics.find(topic => topic.id === allowed[0]).label : allowed.length < 6 ? "one of the highlighted topics" : "any topic"} and a point value.`;
  let html = content.topics.map(topic => `<div class="board-category topic-${topic.id}" title="${escapeHTML(topic.question)}">${icon(topic.id)}<h2>${escapeHTML(topic.label)}</h2><p>${escapeHTML(topic.group)}</p><div class="coverage-dots" aria-label="${counts[topic.id]} of 5 played">${[0,1,2,3,4].map(index => `<i class="${index < counts[topic.id] ? "played" : ""}"></i>`).join("")}</div></div>`).join("");
  for (const value of [100, 200, 300, 400, 500]) {
    html += content.topics.map(topic => {
      const card = content.cards.find(card => card.topic === topic.id && card.value === value);
      const used = game.rounds.some(round => round.id === card.id), locked = !used && !allowed.includes(topic.id);
      return `<button class="board-cell${used ? " used" : locked ? " locked" : ""}" data-card="${card.id}" ${locked ? "disabled" : ""} aria-label="${escapeHTML(topic.label)}, ${value} points${used ? ", played; review answer" : locked ? ", available after other topics" : ""}">${value}</button>`;
    }).join("");
  }
  $("boardGrid").innerHTML = html;
  document.querySelectorAll("[data-card]").forEach(button => button.onclick = () => {
    const id = button.dataset.card;
    if (game.rounds.some(round => round.id === id)) reviewCard(cardFor(id));
    else if (rules.select(game, content, id)) { save(); render(); focusGame(); }
  });
  const covered = Object.values(counts).filter(count => count >= 2).length;
  $("coverageNote").textContent = `${covered} of 6 topics played at least twice. ${game.balanced && game.rounds.length < 12 ? "Balanced selection opens the whole board after 12 clues." : "Played squares open their answer for review."}`;
  $("undoButton").disabled = !game.rounds.length;
  $("targetNote").hidden = game.rounds.length < game.target && game.elapsed < game.minutes * 60;
  $("targetNote").textContent = complete ? "All 30 clues are complete. Finish together with the final connection." : "You have reached your planned stopping point. Move to the final connection, or keep playing if there is time.";
}
function mediaHTML(card, revealed = false) {
  if (!card.clips?.length) return "";
  const player = '<video id="storyVideo" controls playsinline preload="none" hidden></video><p id="mediaError" class="media-error" hidden>Video unavailable. Continue with the clue and use the full story on the answer reveal.</p>';
  if (!revealed) return `<details class="media-details"><summary>Optional video hint</summary><div class="clip-select">${card.clips.map((clip, index) => `<button data-clip="${index}">▶ Source excerpt ${index + 1} <small>· ${clock(clip.duration)}</small></button>`).join("")}</div>${player}<p class="media-caption">Play a source excerpt if teams need help recalling the story.</p></details>`;
  const sheet = content.clipPreviewSheet;
  return `<section class="revealed-clips" aria-label="Conference video clips"><p class="eyebrow">CONFERENCE CLIPS</p><p class="media-caption">Click a preview to play full screen.${card.clips.length > 1 ? " The remaining clips play in sequence." : ""}</p><div class="clip-previews">${card.clips.map((clip, index) => {
    const x = (clip.previewIndex % sheet.columns) * 100 / (sheet.columns - 1);
    const y = Math.floor(clip.previewIndex / sheet.columns) * 100 / (sheet.rows - 1);
    return `<button class="clip-preview" data-clip="${index}" aria-label="Play ${escapeHTML(clip.title)} in full screen"><span class="clip-preview-frame" aria-hidden="true" style="background-image:url('${escapeHTML(sheet.path)}');background-size:${sheet.columns * 100}% ${sheet.rows * 100}%;background-position:${x}% ${y}%"><span class="preview-play">▶</span><span class="preview-duration">${clock(clip.duration)}</span></span><span class="clip-preview-title">${escapeHTML(clip.title)}</span></button>`;
  }).join("")}</div><p id="clipStatus" class="media-caption" aria-live="polite" hidden></p>${player}${card.storyId === "bednar-passport" ? '<p class="media-caption">Keep the adversity limit and stamp explanation with the story.</p>' : ""}</section>`;
}
function wireMedia(card) {
  const revealed = game.active?.phase === "reveal";
  const playAt = (index, enterFullscreen = false) => {
    const video = $("storyVideo"), clip = card.clips[index];
    const status = $("clipStatus");
    if (status) {
      status.hidden = false;
      status.textContent = `Clip ${index + 1} of ${card.clips.length}: ${clip.title}`;
      document.querySelectorAll("#clueView [data-clip]").forEach(button => {
        if (Number(button.dataset.clip) === index) button.setAttribute("aria-current", "true");
        else button.removeAttribute("aria-current");
      });
    }
    playGameClip(video, clip, $("mediaError"), enterFullscreen, revealed ? () => {
      if (index + 1 < card.clips.length) { playAt(index + 1); return true; }
      status.textContent = "Clips finished. You can replay any preview.";
      document.querySelectorAll("#clueView [data-clip]").forEach(button => button.removeAttribute("aria-current"));
      return false;
    } : null);
  };
  document.querySelectorAll("#clueView [data-clip]").forEach(button => button.onclick = () => {
    if (game.active) game.active.running = false;
    updateClocks(); save();
    playAt(Number(button.dataset.clip), revealed);
  });
  const details = document.querySelector("#clueView .media-details");
  if (details) details.addEventListener("toggle", () => { if (!details.open) pauseMedia(); });
}
function renderClue() {
  const card = cardFor(game.active.id), topic = topicFor(card), phase = game.active.phase;
  const main = phase === "story" ? `<p class="eyebrow">REMEMBER THIS CONFERENCE STORY?</p><h2 id="clueHeading">First, a story reminder.</h2><p class="retelling">${escapeHTML(card.intro)}</p><p class="story-note">From ${escapeHTML(card.speaker)}'s conference address.</p>` : phase === "question" ? `<p class="eyebrow">DISCUSS. WRITE. REVEAL TOGETHER.</p><h2 id="clueHeading" class="question-text">${escapeHTML(card.question)}</h2><p class="story-note">Every team writes an answer. Equivalent wording is welcome.</p><button class="text-button" id="rereadButton">Read the clue again</button>` : `<p class="eyebrow">THE ANSWER · ${escapeHTML(card.title)}</p><h2 id="clueHeading">What a strong answer includes.</h2><ul class="answer-list">${card.answerCriteria.map(answer => `<li>${escapeHTML(answer)}</li>`).join("")}</ul>${takeawayHTML(card)}<p class="story-note">${escapeHTML(card.question)}</p><details class="story-recap"><summary>The full story</summary><p>${escapeHTML(card.retelling)}</p></details><details class="source-context"><summary>Source context</summary><p class="qualification">${escapeHTML(card.context)}</p></details>`;
  const side = phase === "question" ? `<div class="timer-panel"><p class="eyebrow">TEAM ANSWER TIME</p><div id="answerClock" class="answer-clock" role="timer">${clock(game.active.remaining)}</div><div class="timer-buttons"><button class="button secondary" id="answerPause">Pause</button><button class="text-button" id="answerReset">Reset</button></div><p id="timerNote" class="timer-note">Discuss and write your answer.</p></div>${mediaHTML(card)}` : `${phase === "story" ? `<img src="${escapeHTML(card.image)}" alt="${escapeHTML(card.speaker)}'s conference speaker card">` : ""}<div><p class="eyebrow">SHARED BY</p><p class="source-name">${escapeHTML(card.speaker)}</p><small>${escapeHTML(card.session)}</small></div>${phase === "reveal" ? mediaHTML(card, true) : ""}${phase === "reveal" ? `<a class="source-link" target="_blank" rel="noopener" href="${escapeHTML(card.sourceUrl)}">Official session sources ↗</a>` : ""}`;
  $("clueView").innerHTML = `<div class="clue-top"><span class="clue-badge topic-${topic.id}">${escapeHTML(topic.label)} · ${card.value}</span><div class="clue-steps">${["story", "question", "reveal"].map((step, index) => `<span class="${step === phase ? "current" : ""}">${index + 1} ${step === "reveal" ? "Answer" : step === "story" ? "Clue" : "Question"}</span>`).join("")}</div></div><div class="clue-card card"><div class="clue-main">${main}</div><aside class="clue-side topic-${topic.id}">${side}</aside></div>${phase === "reveal" ? scoringHTML(card) : ""}<div class="clue-controls"><button id="cancelClue" class="text-button">← Return to board${phase === "reveal" ? " without scoring" : ""}</button>${phase === "story" ? '<button id="questionButton" class="button primary">Show the question →</button>' : phase === "question" ? '<button id="revealButton" class="button primary">Reveal the answer →</button>' : '<button id="completeButton" class="button primary" disabled>Save scores & next team →</button>'}</div>`;
  $("cancelClue").onclick = () => { game.active = null; game.screen = "board"; save(); render(); focusGame(); };
  if (phase === "story") $("questionButton").onclick = () => { game.active.phase = "question"; game.active.running = true; lastTick = performance.now(); save(); render(); focusGame(); };
  if (phase === "question") {
    $("answerPause").onclick = () => { if (game.active.remaining <= 0) return; game.active.running = !game.active.running; lastTick = performance.now(); save(); updateClocks(); };
    $("answerReset").onclick = () => { game.active.remaining = rules.answerSeconds(card.value); game.active.running = true; lastTick = performance.now(); save(); updateClocks(); };
    $("rereadButton").onclick = () => openModal("The clue", `<p class="retelling">${escapeHTML(card.intro)}</p><div class="dialog-actions"><button id="backToQuestion" class="button primary">Back to the question</button></div>`);
    $("rereadButton").addEventListener("click", () => { $("backToQuestion").onclick = closeModal; });
    $("revealButton").onclick = () => { game.active.phase = "reveal"; game.active.running = false; save(); render(); focusGame(); };
  }
  if (phase === "reveal") wireScoring(card);
  wireMedia(card);
}
function scoringHTML(card) {
  return `<section class="scoring-panel"><div class="scoring-head"><h3>How did each team do?</h3><p>Full: all required parts · Half: substantially correct but incomplete · Zero: unsupported</p></div><div class="award-grid">${game.teams.map((team, index) => `<div class="award-team"><span class="award-name">${escapeHTML(team.name)}</span><div class="award-options" role="group" aria-label="Points for ${escapeHTML(team.name)}">${[[0,"Zero"],[card.value / 2,"Half"],[card.value,"Full"]].map(([value, label]) => `<button data-team="${index}" data-award="${value}" class="${game.active.awards[index] === value ? "selected" : ""}" aria-pressed="${game.active.awards[index] === value}">${value}<small>${label}</small></button>`).join("")}</div></div>`).join("")}</div><p class="story-note">Choose an award for every team before saving. Points are applied once.</p></section>`;
}
function wireScoring() {
  const ready = () => { $("completeButton").disabled = game.active.awards.some(award => award === null); };
  document.querySelectorAll("[data-award]").forEach(button => button.onclick = () => {
    const index = Number(button.dataset.team), value = Number(button.dataset.award);
    game.active.awards[index] = value;
    document.querySelectorAll(`[data-team="${index}"]`).forEach(option => { const selected = Number(option.dataset.award) === value; option.classList.toggle("selected", selected); option.setAttribute("aria-pressed", selected); });
    save(); ready();
  });
  ready();
  $("completeButton").onclick = () => { if (rules.complete(game, content)) { save(); render(); focusGame(); } };
}
function reviewCard(card) {
  const round = game.rounds.find(round => round.id === card.id);
  openModal(`${topicFor(card).label} · ${card.value} · Played`, `<p>${escapeHTML(card.question)}</p><ul>${card.answerCriteria.map(answer => `<li>${escapeHTML(answer)}</li>`).join("")}</ul>${takeawayHTML(card)}<details class="source-context"><summary>Source context</summary><p class="qualification">${escapeHTML(card.context)}</p></details><p class="guide-note">${game.teams.map((team, index) => `${escapeHTML(team.name)}: ${round.awards[index]}`).join(" · ")}<br>Use Edit scores for a correction.</p>`);
}
function takeawayHTML(card) {
  return `<div class="takeaway"><p class="eyebrow">TAKEAWAY</p><p>${escapeHTML(card.takeaway)}</p></div>`;
}
function renderFinal() {
  const story = cardFor("hope-500");
  $("finalView").innerHTML = `<div class="final-card card"><p class="eyebrow">COOPERATIVE FINAL · NO EXTRA POINTS</p><h2>One story. More than one message.</h2><p class="retelling">${escapeHTML(story.retelling)}</p><p class="story-note">Shared by ${escapeHTML(story.speaker)}.</p><p class="final-question">Connect this story to two different topics. For each, name a detail from the story and explain why it fits.</p><p>Take two minutes together, then hear a few teams' ideas.</p><div class="closing-actions"><button class="button secondary" id="finalExamplesButton">Show possible connections</button><button class="button primary" id="closingButton">Scores & a next step →</button></div><div id="finalExamples" class="final-examples" hidden><p><strong>Find Strength:</strong> Ted stayed beside Dunn while the race remained difficult. Help can sustain us without removing the challenge.</p><p><strong>Help Others:</strong> Ted carried the pack and water. Practical care and encouragement can show love.</p><p>Other supported connections are welcome. Give the story detail and explain the connection.</p></div></div><button class="text-button" id="returnBoard">← Keep playing the board</button>`;
  $("finalExamplesButton").onclick = () => { $("finalExamples").hidden = !$("finalExamples").hidden; $("finalExamplesButton").textContent = $("finalExamples").hidden ? "Show possible connections" : "Hide possible connections"; };
  $("closingButton").onclick = () => { game.screen = "closing"; game.sessionRunning = false; save(); render(); focusGame(); };
  $("returnBoard").onclick = () => { game.screen = "board"; save(); render(); focusGame(); };
}
function renderClosing() {
  const ranking = [...game.teams].sort((a, b) => b.score - a.score), top = ranking[0].score;
  const leaders = ranking.filter(team => team.score === top);
  $("closingView").innerHTML = `<div class="closing-card card"><p class="eyebrow">${game.rounds.length} STORIES SHARED · MANY WAYS TO LIVE THEM</p><h2>Carry one good idea into your week.</h2><p>${top === 0 ? "Thanks for taking part. Your ideas matter beyond the points." : leaders.length > 1 ? "Shared first place: " + leaders.map(team => escapeHTML(team.name)).join(", ") + "." : escapeHTML(leaders[0].name) + " finishes with the most points."} Celebrate the ideas and care every team brought.</p><div class="podium">${ranking.map(team => `<div class="podium-item${team.score === top && top > 0 ? " winner" : ""}"><span>${escapeHTML(team.name)}</span><strong>${team.score.toLocaleString()}</strong></div>`).join("")}</div><p class="eyebrow">DALLIN H. OAKS'S CLOSING INVITATION</p><div class="next-step-grid"><div class="next-step"><span>01</span><h3>Study.</h3><p>Choose one conference message to return to.</p></div><div class="next-step"><span>02</span><h3>Ponder prayerfully.</h3><p>Consider what the message means in your life.</p></div><div class="next-step"><span>03</span><h3>Act in faith.</h3><p>Choose one specific step to take this week.</p></div></div><p>Your next step can stay private. Take a quiet moment to choose it.</p><div class="closing-actions"><button class="button secondary" id="closingClipButton">▶ Play closing invitation · ${clock(content.closingClip.duration)}</button><button class="button secondary" id="closingBoardButton">Return to the board</button><button class="button primary" id="newGameButton">Set up another game →</button></div><video id="closingVideo" controls playsinline preload="none" hidden></video><p id="closingMediaError" class="media-error" hidden>Video unavailable. Use the study, ponder prayerfully, and act in faith invitation above.</p></div>`;
  $("closingClipButton").onclick = () => playGameClip($("closingVideo"), content.closingClip, $("closingMediaError"));
  $("closingBoardButton").onclick = () => { game.screen = "board"; save(); render(); focusGame(); };
  $("newGameButton").onclick = showSetup;
}
function updateClocks() {
  if (!game) return;
  $("sessionTime").textContent = clock(game.minutes * 60 - game.elapsed);
  $("sessionPause").textContent = game.sessionRunning ? "Ⅱ" : "▶";
  $("sessionPause").setAttribute("aria-label", game.sessionRunning ? "Pause activity clock" : "Resume activity clock");
  if (game.active?.phase === "question" && $("answerClock")) {
    const active = game.active, expired = active.remaining <= 0;
    $("answerClock").textContent = clock(active.remaining); $("answerClock").classList.toggle("time-up", expired);
    $("answerPause").textContent = active.running ? "Pause" : "Resume";
    $("answerPause").disabled = expired;
    $("timerNote").textContent = expired ? "Time is up. Reveal team answers together." : active.running ? "Discuss and write your answer." : "Timer paused. Resume when everyone is ready.";
  }
  if (game.screen === "board" && game.elapsed >= game.minutes * 60) {
    $("targetNote").hidden = false;
    $("targetNote").textContent = "Activity time is up. Move to the final connection when you are ready.";
  }
}
function editScores() {
  if (!game) return;
  openModal("Correct the scores", `<p>Enter each team's corrected total. The completed clues and selecting order stay in place.</p><form id="scoreForm">${game.teams.map((team, index) => `<label class="score-edit-row"><span>${escapeHTML(team.name)}</span><input type="number" id="correctScore${index}" value="${team.score}" min="0" max="1000000" step="1" required></label>`).join("")}<div class="dialog-actions"><button type="submit" class="button primary">Save corrected totals</button></div></form>`);
  $("scoreForm").onsubmit = event => {
    event.preventDefault();
    const scores = game.teams.map((_, index) => Number($("correctScore" + index).value));
    if (scores.some(value => !Number.isSafeInteger(value) || value < 0 || value > 1000000)) return;
    if (game.adjustments.length + game.teams.length > 500) { notify("Too many score corrections in this session. Save a backup before starting a new game."); return; }
    game.teams.forEach((team, index) => { const delta = scores[index] - team.score; if (delta) game.adjustments.push({team: index, delta}); team.score = scores[index]; });
    closeModal(); save(); render();
  };
}
function exportGame() {
  if (!game && !saved) return;
  save();
  const blob = new Blob([JSON.stringify(game || saved, null, 2)], {type: "application/json"});
  const url = URL.createObjectURL(blob), link = document.createElement("a");
  link.href = url; link.download = "conference-story-challenge-save.json"; link.click();
  setTimeout(() => URL.revokeObjectURL(url), 3000);
}
function practiceClue() {
  practice = "story";
  openModal("Practice · no points", `<p class="retelling">${escapeHTML(content.practice.retelling)}</p><div class="dialog-actions"><button id="practiceQuestion" class="button primary">Show practice question →</button></div>`);
  $("practiceQuestion").onclick = () => {
    practice = "question";
    openModal("Practice · everyone answers", `<p class="retelling">${escapeHTML(content.practice.question)}</p><p class="guide-note">Talk together and write a sentence. The host can reveal the answer when everyone is ready.</p><div class="dialog-actions"><button id="practiceReveal" class="button primary">Reveal possible answer →</button></div>`);
    $("practiceReveal").onclick = () => {
      practice = "reveal";
      openModal("Practice · a strong answer", `<ul>${content.practice.answerCriteria.map(answer => `<li>${escapeHTML(answer)}</li>`).join("")}</ul><p class="guide-note">In the game, the host awards full, half, or zero points to every team. This practice leaves all 30 board clues available.</p><div class="dialog-actions"><button id="practiceDone" class="button primary">Ready to set up →</button></div>`);
      $("practiceDone").onclick = () => { practice = null; closeModal(); $("setupTitle").scrollIntoView({block: "center"}); };
    };
  };
}
function showGuide() {
  openModal("A story for every team", `<ol><li><strong>Choose a clue.</strong> Selection rotates after every clue. With six teams, each opens its assigned topic. Balanced selection covers each topic twice before opening the whole board.</li><li><strong>Read the reminder.</strong> The short introduction brings a conference story to mind. Use the optional video hint if teams need help recalling it. The complete account appears after the answer reveal.</li><li><strong>Answer together.</strong> Show the question; its timer starts automatically. Pause or reset it as needed, and ask every team to write an answer on paper or a whiteboard. Reveal team answers together.</li><li><strong>Reveal and score.</strong> Full points for all required parts; half for a substantially correct but incomplete answer; zero for an unsupported answer. Accept equivalent wording and sound applications. Select an award for every team, then save.</li><li><strong>Finish together.</strong> Use Final connection at your planned stopping point, then take a private next step. The final is cooperative and adds no points.</li></ol><p class="guide-note">100 → 20 sec · 200 → 25 sec · 300 → 35 sec · 400 → 45 sec · 500 → 60 sec<br>One host controls this screen. Each browser runs its own game. Progress saves here; a backup lets you continue on another device. Keyboard: Tab to controls, Enter to activate, Esc to close a dialog.</p>`);
}
function printGuide() {
  $("printGuide").innerHTML = `<h1>${escapeHTML(content.title)}</h1><div class="host-rules"><p>October 2026 · Host guide · ${content.cards.length} clues · Up to six teams</p><p>Every team answers every clue. Rotate selection. Read the short clue introduction, show the question (the timer starts automatically), and reveal together. Pause or reset the timer as needed. Use a source clip as an optional hint when needed. Save the complete retelling for the answer reveal. Full value for all required parts; half for a substantially correct incomplete answer; zero for incorrect or unsupported. Accept equivalent wording and supported applications. Names and exact quotations are not required.</p><p>First 6 picks: assigned categories. Next 6: bring all categories to two played. 40 minutes: 12 clues. 50 minutes: 18 clues. 60–70 minutes: up to 30. The final is cooperative and unscored. Each team needs paper or a whiteboard.</p><p>Timers: 100 = 20 sec; 200 = 25 sec; 300 = 35 sec; 400 = 45 sec; 500 = 60 sec.</p></div>${content.topics.map(topic => `<section class="print-category"><h2>${escapeHTML(topic.label)} · ${escapeHTML(topic.group)}</h2><p>${escapeHTML(topic.question)}</p>${content.cards.filter(card => card.topic === topic.id).map(card => `<article><h3>${card.value} · ${escapeHTML(card.title)}</h3><p><strong>Read before the question:</strong> ${escapeHTML(card.intro)}</p><p><strong>Question:</strong> ${escapeHTML(card.question)}</p><ul>${card.answerCriteria.map(answer => `<li>${escapeHTML(answer)}</li>`).join("")}</ul><p><strong>Takeaway:</strong> ${escapeHTML(card.takeaway)}</p><p class="print-limit"><strong>Source context:</strong> ${escapeHTML(card.context)}</p><p><strong>Full story for the reveal:</strong> ${escapeHTML(card.retelling)}</p><p>Source: ${escapeHTML(card.speaker)} · ${escapeHTML(card.session)}</p></article>`).join("")}</section>`).join("")}<section class="print-category"><h2>Final connection</h2><p>${escapeHTML(cardFor("hope-500").retelling)}</p><p>Connect the story to two different topics. Name a detail and explain the connection for each. Examples: Find Strength—help while the race remains difficult; Help Others—carrying the pack and water. Accept other supported connections. No points.</p><h2>A private next step</h2><p>Return to one message. Study, ponder prayerfully, and act in faith, following Dallin H. Oaks's closing invitation. A participant's next step can stay private.</p></section>`;
  window.print();
}

$("topicMosaic").innerHTML = content.topics.map(topic => `<div class="mosaic-tile topic-${topic.id}">${icon(topic.id)}<span>${escapeHTML(topic.label)}</span></div>`).join("");
renderTeamFields(); loadSaved(); showSetup();
$("teamCount").onchange = renderTeamFields;
$("setupForm").onsubmit = event => { event.preventDefault(); if (saved) confirmAction("Start a fresh game?", "Starting replaces the saved game on this browser. Save a backup from the current game if you want to keep it.", "Start fresh", startGame); else startGame(); };
$("resumeButton").onclick = resumeGame;
$("practiceButton").onclick = practiceClue;
$("guideButton").onclick = showGuide;
$("modalClose").onclick = closeModal;
$("modal").addEventListener("cancel", () => { pauseMedia(); lastTick = performance.now(); });
$("homeButton").onclick = showSetup;
$("scoresButton").onclick = editScores;
$("exportButton").onclick = exportGame;
$("printButton").onclick = printGuide;
$("undoButton").onclick = () => { if (rules.undo(game)) { save(); render(); } };
$("finalButton").onclick = () => { game.screen = "final"; save(); render(); focusGame(); };
$("sessionPause").onclick = () => { game.sessionRunning = !game.sessionRunning; lastTick = performance.now(); save(); updateClocks(); };
$("fullscreenButton").onclick = async () => {
  try { if (document.fullscreenElement) await document.exitFullscreen(); else await document.documentElement.requestFullscreen(); }
  catch { notify("Use your browser's full-screen command on this device."); }
};
document.addEventListener("fullscreenchange", () => $("fullscreenButton").setAttribute("aria-label", document.fullscreenElement ? "Exit full screen" : "Enter full screen"));
$("importButton").onclick = () => { $("importFile").value = ""; $("importFile").click(); };
$("importFile").onchange = async event => {
  const file = event.target.files[0]; if (!file) return;
  try {
    if (file.size > 200000) throw new Error("This file is too large to be a game backup.");
    const candidate = JSON.parse(await file.text());
    if (!rules.validate(candidate, content)) throw new Error("This backup does not contain a valid Conference Story Challenge game.");
    const apply = () => { saved = clone(candidate); resumeGame(); };
    if (saved || game) confirmAction("Load this backup?", "This will replace the current saved game on this browser.", "Load backup", apply); else apply();
  } catch (error) { notify(error instanceof SyntaxError ? "The backup is not a readable JSON file." : error.message); }
};
window.addEventListener("pagehide", () => { if (game?.active) game.active.running = false; save(); });
setInterval(() => {
  const now = performance.now(), delta = Math.max(0, (now - lastTick) / 1000); lastTick = now;
  if (!game || $("modal").open) return;
  if (game.sessionRunning) game.elapsed += delta;
  if (game.active?.running && game.active.phase === "question") {
    game.active.remaining = Math.max(0, game.active.remaining - delta);
    if (!game.active.remaining) game.active.running = false;
  }
  updateClocks();
  if (now - lastSave >= 2000) { save(); lastSave = now; }
}, 250);
