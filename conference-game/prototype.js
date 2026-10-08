const state = {
  talks: [],
  groups: [],
  quotes: [],
  clips: {},
  deck: [],
  round: 0,
  scores: [0, 0],
  teams: ["Team One", "Team Two"],
  currentQuote: null,
  currentTalk: null,
  clip: null,
};

const $ = (id) => document.getElementById(id);
const shuffle = (list) => [...list].sort(() => Math.random() - 0.5);
const clock = (seconds) => `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, "0")}`;

async function loadContent() {
  try {
    const [talkResponse, activityResponse, clipResponse] = await Promise.all([
      fetch("./talks.json"),
      fetch("./activity.json"),
      fetch("./clips.json"),
    ]);
    if (!talkResponse.ok || !activityResponse.ok || !clipResponse.ok) throw new Error("Could not load the local activity files.");
    state.talks = await talkResponse.json();
    state.clips = await clipResponse.json();
    const activity = await activityResponse.json();
    state.groups = activity.groups;
    state.quotes = activity.quotes;
    state.activity = activity;
    populateGroups();
    const speakerCount = new Set(state.talks.map((talk) => talk.speaker)).size;
    $("loadMessage").textContent = `${state.talks.length} talks · ${speakerCount} speakers · ${state.quotes.length} excerpt cards ready`;
    $("startButton").disabled = false;
  } catch (error) {
    $("loadMessage").textContent = `${error.message} Run Start-ConferenceGame.ps1 to open the game.`;
    $("loadMessage").classList.add("error");
  }
}

function populateGroups() {
  for (const group of state.groups) {
    const option = document.createElement("option");
    option.value = group.id;
    option.textContent = group.name;
    $("groupSelect").append(option);
  }
}

function startGame() {
  const groupId = $("groupSelect").value;
  const available = groupId === "all" ? state.quotes : state.quotes.filter((quote) => quote.groupId === groupId);
  if (!available.length) {
    $("loadMessage").textContent = "There are no quote cards for that topic yet.";
    $("loadMessage").classList.add("error");
    return;
  }
  state.teams = [$("teamOneName").value.trim() || "Team One", $("teamTwoName").value.trim() || "Team Two"];
  state.scores = [0, 0];
  const requestedValue = $("roundSelect").value;
  const requested = requestedValue === "all" ? available.length : (Number(requestedValue) || 6);
  state.deck = shuffle(available).slice(0, Math.min(requested, available.length));
  state.round = 0;
  $("teamOneLabel").textContent = state.teams[0];
  $("teamTwoLabel").textContent = state.teams[1];
  updateScores();
  $("welcome").classList.add("hidden");
  $("game").classList.remove("hidden");
  renderRound();
}

function updateScores() {
  $("teamOneScore").textContent = state.scores[0];
  $("teamTwoScore").textContent = state.scores[1];
}

function getGroup(id) {
  return state.groups.find((group) => group.id === id);
}

function resetMedia() {
  const video = $("clipPlayer");
  video.pause();
  video.removeAttribute("src");
  video.load();
  video.classList.add("hidden");
  $("mediaPlaceholder").classList.remove("hidden");
  $("playOverlay").classList.remove("hidden");
  $("speakerStill").classList.add("hidden");
  $("clipSpeakerLabel").textContent = "A speaker from the current set";
  state.clip = null;
}

function renderRound() {
  if (state.round >= state.deck.length) {
    finishGame();
    return;
  }
  state.currentQuote = state.deck[state.round];
  state.currentTalk = state.talks.find((talk) => talk.id === state.currentQuote.speakerId);
  const group = getGroup(state.currentQuote.groupId);
  if (!state.currentTalk || !group) {
    state.round += 1;
    renderRound();
    return;
  }

  state.clip = { start: state.currentQuote.start, end: state.currentQuote.end };
  const video = $("clipPlayer");
  const extracted = state.clips[state.currentQuote.id];
  state.clip.playbackStart = 0;
  state.clip.playbackEnd = extracted ? extracted.duration : state.currentQuote.end - state.currentQuote.start;
  video.src = extracted ? extracted.path : state.currentTalk.video;
  video.load();
  $("mediaPlaceholder").classList.add("hidden");
  video.classList.add("hidden");
  $("playOverlay").classList.remove("hidden");
  $("groupPill").textContent = group.name;
  $("topicHeading").textContent = "Who shared this passage?";
  document.querySelector(".listen-hint").textContent = "Listen closely, then choose a speaker.";
  $("clipTimeLabel").textContent = `${clock(state.clip.start)}–${clock(state.clip.end)}`;
  $("clipSpeakerLabel").textContent = "A conference talk excerpt";
  $("answer").classList.add("hidden");
  $("finished").classList.add("hidden");
  $("choices").classList.remove("hidden");
  $("choices").replaceChildren();
  const otherSpeakers = new Map(
    state.talks
      .filter((talk) => talk.speaker !== state.currentTalk.speaker)
      .map((talk) => [talk.speaker, talk]),
  );
  const others = shuffle([...otherSpeakers.values()]).slice(0, 3);
  for (const talk of shuffle([state.currentTalk, ...others])) {
    const button = document.createElement("button");
    button.className = "choice";
    button.textContent = talk.speaker;
    button.addEventListener("click", () => chooseAnswer(button, talk));
    $("choices").append(button);
  }
  $("roundLabel").textContent = `ROUND ${state.round + 1} OF ${state.deck.length}`;
  $("roundProgress").style.width = `${(state.round / state.deck.length) * 100}%`;
}

async function playExcerpt() {
  const video = $("clipPlayer");
  if (!state.clip) return;
  video.classList.remove("hidden");
  $("mediaPlaceholder").classList.add("hidden");
  const begin = async () => {
    video.currentTime = state.clip.playbackStart;
    $("playOverlay").classList.add("hidden");
    try {
      await video.play();
    } catch {
      $("playOverlay").classList.remove("hidden");
    }
  };
  if (video.readyState >= 1) await begin();
  else video.addEventListener("loadedmetadata", begin, { once: true });
}

function stopAtClipEnd() {
  if (!state.clip) return;
  const video = $("clipPlayer");
  if (video.currentTime >= state.clip.playbackEnd) {
    video.pause();
    $("playOverlay").classList.remove("hidden");
  }
}

function chooseAnswer(button, chosenTalk) {
  const correct = chosenTalk.id === state.currentTalk.id;
  const video = $("clipPlayer");
  video.pause();
  video.classList.add("hidden");
  $("playOverlay").classList.add("hidden");
  $("mediaPlaceholder").classList.add("hidden");
  for (const choice of $("choices").querySelectorAll("button")) {
    choice.disabled = true;
    if (choice.textContent === state.currentTalk.speaker) choice.classList.add("correct");
  }
  if (!correct) button.classList.add("incorrect");
  $("choices").classList.add("hidden");
  $("answer").classList.remove("hidden");
  $("answerStatus").textContent = correct ? "That's right — good listening." : "Not this time. Here's the speaker.";
  $("answerStatus").classList.toggle("wrong", !correct);
  $("speakerName").textContent = state.currentTalk.speaker;
  $("speakerStill").src = state.currentTalk.image;
  $("speakerStill").alt = `Speaker identification from ${state.currentTalk.speaker}'s video`;
  $("speakerStill").classList.remove("hidden");
  $("timestamp").textContent = `Clip source · ${clock(state.clip.start)}–${clock(state.clip.end)}`;
  $("quoteText").textContent = `“${state.currentQuote.text}”`;
  const group = getGroup(state.currentQuote.groupId);
  $("discussionQuestion").textContent = group.question;
  $("quotePrompt").textContent = state.currentQuote.prompt || group.followUp;
  $("clipSpeakerLabel").textContent = state.currentTalk.speaker;
}

function finishGame() {
  $("choices").classList.add("hidden");
  $("answer").classList.add("hidden");
  $("finished").classList.remove("hidden");
  $("topicHeading").textContent = "Round complete.";
  $("roundLabel").textContent = "FINISHED";
  $("roundProgress").style.width = "100%";
  $("finalScores").textContent = `${state.teams[0]}: ${state.scores[0]} points · ${state.teams[1]}: ${state.scores[1]} points. Take the best ideas into the discussion.`;
  resetMedia();
}

$("startButton").disabled = true;
$("startButton").addEventListener("click", startGame);
$("playButton").addEventListener("click", playExcerpt);
$("clipPlayer").addEventListener("timeupdate", stopAtClipEnd);
$("clipPlayer").addEventListener("ended", () => $("playOverlay").classList.remove("hidden"));
$("nextButton").addEventListener("click", () => {
  state.round += 1;
  resetMedia();
  renderRound();
});
$("againButton").addEventListener("click", () => {
  $("game").classList.add("hidden");
  $("welcome").classList.remove("hidden");
});
$("teamOnePoint").addEventListener("click", () => { state.scores[0] += 1; updateScores(); });
$("teamTwoPoint").addEventListener("click", () => { state.scores[1] += 1; updateScores(); });

loadContent();
