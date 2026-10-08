(() => {
  const sources = new WeakMap();
  const blobUrls = new Set();
  let latestRequest = 0;

  const canSeekTo = (video, position) => {
    for (let index = 0; index < video.seekable.length; index++) {
      if (position >= video.seekable.start(index) && position <= video.seekable.end(index)) return true;
    }
    return false;
  };

  function loadMetadata(video, reload = false) {
    if (!reload && video.readyState >= 1) return Promise.resolve();
    return new Promise((resolve, reject) => {
      const cleanup = () => {
        video.removeEventListener("loadedmetadata", ready);
        video.removeEventListener("error", failed);
      };
      const ready = () => { cleanup(); resolve(); };
      const failed = () => { cleanup(); reject(new Error("This clip could not be loaded.")); };
      video.addEventListener("loadedmetadata", ready);
      video.addEventListener("error", failed);
      video.preload = "auto";
      video.load();
    });
  }

  function seek(video, position) {
    return new Promise((resolve, reject) => {
      const cleanup = () => {
        video.removeEventListener("seeked", ready);
        video.removeEventListener("error", failed);
      };
      const ready = () => { cleanup(); resolve(); };
      const failed = () => { cleanup(); reject(new Error("This section could not be played.")); };
      video.addEventListener("seeked", ready);
      video.addEventListener("error", failed);
      video.currentTime = position;
      if (!video.seeking) ready();
    });
  }

  async function completeSource(video) {
    let source = sources.get(video);
    if (!source) {
      source = { originalUrl: video.currentSrc || video.src, blobPromise: null };
      sources.set(video, source);
    }
    if (!source.blobPromise) {
      // A server without byte-range support can expose only time zero as
      // seekable. Fetch the complete selected file before seeking in that case.
      source.blobPromise = fetch(source.originalUrl)
        .then(response => {
          if (!response.ok) throw new Error("This clip could not be downloaded for playback.");
          return response.blob();
        })
        .then(blob => {
          const url = URL.createObjectURL(blob);
          blobUrls.add(url);
          return url;
        })
        .catch(error => { source.blobPromise = null; throw error; });
    }
    return source.blobPromise;
  }

  window.playClipAt = async (video, seconds) => {
    if (!Number.isFinite(seconds) || seconds < 0) throw new Error("Choose a valid playback time.");
    const request = ++latestRequest;
    const stillSelected = () => request === latestRequest && video.isConnected && !video.closest("[hidden]");
    video.pause();
    for (const other of document.querySelectorAll("video")) if (other !== video) other.pause();
    if (!stillSelected()) return false;
    if (seconds === 0) {
      video.currentTime = 0;
      await video.play();
      return true;
    }

    await loadMetadata(video);
    if (!stillSelected()) return false;
    let position = Math.min(seconds, Math.max(0, video.duration - 0.05));
    if (!canSeekTo(video, position)) {
      const url = await completeSource(video);
      if (!stillSelected()) return false;
      video.src = url;
      await loadMetadata(video, true);
      if (!stillSelected()) return false;
      position = Math.min(seconds, Math.max(0, video.duration - 0.05));
    }
    if (!canSeekTo(video, position)) throw new Error("The requested section is not available yet. Try again.");
    await seek(video, position);
    if (!stillSelected()) return false;
    if (Math.abs(video.currentTime - position) > 0.5) throw new Error("The requested section could not be reached.");
    await video.play();
    return true;
  };

  // Native controls also count as a newer playback choice.
  document.addEventListener("play", event => {
    if (!(event.target instanceof HTMLMediaElement)) return;
    latestRequest++;
    for (const other of document.querySelectorAll("video")) if (other !== event.target) other.pause();
  }, true);
  window.addEventListener("pagehide", event => {
    latestRequest++;
    if (event.persisted) return;
    for (const url of blobUrls) URL.revokeObjectURL(url);
    blobUrls.clear();
  });
})();
