const libraryState = { clips: [], topics: new Map(), cards: [], storyIds: new Set(), audits: new Map() };
const element = (tag, text, className) => {
  const node = document.createElement(tag);
  if (text) node.textContent = text;
  if (className) node.className = className;
  return node;
};
const time = (seconds) => `${Math.floor(seconds / 60)}:${String(Math.floor(seconds % 60)).padStart(2, "0")}`;
const link = (label, href) => {
  const node = element("a", label);
  node.href = href;
  return node;
};
function renderClip(clip) {
  const card = element("article");
  card.id = clip.id;
  card.append(element("p", `${clip.label} · ${clip.session}`, "attribution"));
  card.append(element("h2", clip.title));
  const tags = element("div", null, "tags");
  for (const topic of clip.topics) tags.append(element("span", libraryState.topics.get(topic)?.label || topic, "tag"));
  if (clip.duration > 90) tags.append(element("span", "Longer reference excerpt", "tag"));
  if (clip.storyId && clip.kind === "teaching") tags.append(element("span", "Story context", "tag"));
  const audit = libraryState.audits.get(clip.id);
  if (audit) {
    const label = { high: "Inspect first", medium: "Inspection suggested", low: "No automatic flags" }[audit.priority];
    tags.append(element("span", label, `tag priority-${audit.priority}`));
  }
  card.append(tags);
  card.append(element("p", `Original video ${time(clip.start)}–${time(clip.end)} · ${time(clip.duration)} excerpt`, "range"));
  const video = element("video");
  video.controls = true;
  video.preload = "none";
  video.playsInline = true;
  video.src = clip.path;
  video.setAttribute("aria-label", `${clip.title}, ${clip.speaker}`);
  video.addEventListener("play", () => {
    for (const other of document.querySelectorAll("video")) if (other !== video) other.pause();
  });
  card.append(video, element("p", clip.rationale));
  if (clip.qualifications?.length) {
    const context = element("details", null, "context");
    context.append(element("summary", "Keep the context"));
    const list = element("ul");
    for (const qualification of clip.qualifications) list.append(element("li", qualification));
    context.append(list);
    card.append(context);
  }
  if (audit) {
    const speech = element("details", null, "context");
    speech.append(element("summary", `Speech screen: ${audit.summary}`));
    speech.append(element("p", `Expected content: ${audit.expectedMeaning}`));
    for (const flag of audit.flags) speech.append(element("p", flag.reason));
    speech.append(element("p", "This is a machine screen. Listen before deciding whether a flag is a transcription error or a clip problem."));
    const links = element("div", null, "source-links");
    const playbackStatus = element("p", null, "range");
    playbackStatus.setAttribute("role", "status");
    playbackStatus.hidden = true;
    let playbackRequest = 0;
    for (const [label, start] of [["Play opening", 0], ["Play last 10 seconds", Math.max(0, clip.duration - 10)]]) {
      const button = element("button", label);
      button.type = "button";
      button.addEventListener("click", async () => {
        const request = ++playbackRequest;
        playbackStatus.hidden = true;
        if (start > 0) {
          playbackStatus.textContent = "Loading clip…";
          playbackStatus.hidden = false;
        }
        try {
          await playClipAt(video, start);
          if (request === playbackRequest) playbackStatus.hidden = true;
        } catch (error) {
          if (request !== playbackRequest) return;
          playbackStatus.textContent = "Could not play this clip. Open the video from the source links.";
          playbackStatus.hidden = false;
        }
      });
      links.append(button);
    }
    if (audit.rawPath?.endsWith(".json")) links.append(link("Whisper transcript", audit.rawPath.replace(/\.json$/, ".txt")));
    links.append(link("Inspection report", `clip-speech-review.html#${clip.id}`));
    speech.append(playbackStatus, links);
    card.append(speech);
  }
  const sources = element("div", null, "source-links");
  sources.append(link("Talk notes", `../Conference%20Review.md#talk-${clip.talkId}`));
  sources.append(link("Original video", clip.sourceVideo));
  const download = link("Download clip", clip.path);
  download.download = clip.path.split("/").pop();
  sources.append(download);
  if (clip.storyId) sources.append(link("Story and image prompt", `../Conference%20Story%20Catalog.md#${clip.storyId}`));
  card.append(sources);
  if (clip.storyId || audit?.companionIds?.length) {
    const companions = libraryState.clips.filter(other => other.id !== clip.id && ((clip.storyId && other.storyId === clip.storyId) || audit?.companionIds?.includes(other.id)));
    if (companions.length) {
      card.append(element("p", "Related story context", "attribution"));
      for (const companion of companions) {
        const related = link(companion.title, `#${companion.id}`);
        related.addEventListener("click", () => {
          for (const id of ["search", "session", "topic", "kind", "inspection"]) document.getElementById(id).value = "";
          applyFilters();
        });
        const paragraph = element("p");
        paragraph.append(related);
        card.append(paragraph);
      }
    }
  }
  return card;
}
function applyFilters() {
  const search = document.getElementById("search").value.toLowerCase().trim();
  const session = document.getElementById("session").value;
  const topic = document.getElementById("topic").value;
  const kind = document.getElementById("kind").value;
  const inspection = document.getElementById("inspection").value;
  let count = 0;
  const visibleTalks = new Set();
  libraryState.clips.forEach((clip, index) => {
    const matchesKind = !kind || clip.kind === kind || (kind === "story" && clip.storyId && libraryState.storyIds.has(clip.storyId));
    const priority = libraryState.audits.get(clip.id)?.priority;
    const matchesInspection = !inspection || priority === inspection || (inspection === "flagged" && ["high", "medium"].includes(priority));
    const visible = (!session || clip.sessionId === session) && (!topic || clip.topics.includes(topic)) && matchesKind && matchesInspection && (!search || `${clip.label} ${clip.title} ${clip.rationale} ${clip.storyId || ""}`.toLowerCase().includes(search));
    libraryState.cards[index].hidden = !visible;
    if (visible) { count++; visibleTalks.add(clip.talkId); }
    else libraryState.cards[index].querySelector("video").pause();
  });
  document.getElementById("resultCount").textContent = `${count} of ${libraryState.clips.length} excerpts · ${visibleTalks.size} addresses`;
}
async function loadLibrary() {
  try {
    const response = await fetch("clip-library.json");
    if (!response.ok) throw new Error("The prepared clip library could not be loaded.");
    const data = await response.json();
    libraryState.clips = data.clips;
    libraryState.storyIds = new Set(data.clips.filter(clip => clip.kind === "story" && clip.storyId).map(clip => clip.storyId));
    libraryState.topics = new Map(data.topics.map(t => [t.id, t]));
    try {
      const auditResponse = await fetch("speech-audit/analysis.json");
      if (auditResponse.ok) {
        const auditData = await auditResponse.json();
        const current = new Map(data.clips.map(c => [c.id, c.sourceFingerprint]));
        libraryState.audits = new Map(auditData.clips.filter(a => a.sourceFingerprint === current.get(a.id)).map(a => [a.id, a]));
      }
    } catch { /* The clip library remains usable before a speech screen is prepared. */ }
    for (const session of data.sessions) {
      const option = element("option", session.label);
      option.value = session.id;
      document.getElementById("session").append(option);
    }
    for (const topic of data.topics) {
      const option = element("option", `${topic.label} — ${topic.group}`);
      option.value = topic.id;
      document.getElementById("topic").append(option);
    }
    const container = document.getElementById("clips");
    libraryState.cards = data.clips.map(renderClip);
    container.append(...libraryState.cards);
    applyFilters();
    const target = document.getElementById(decodeURIComponent(location.hash.slice(1)));
    if (target) target.scrollIntoView();
  } catch (error) {
    document.getElementById("resultCount").textContent = `${error.message} Open this page through the root game launcher.`;
  }
}
document.getElementById("filters").addEventListener("submit", event => event.preventDefault());
document.getElementById("filters").addEventListener("input", applyFilters);
document.getElementById("filters").addEventListener("change", applyFilters);
loadLibrary();
