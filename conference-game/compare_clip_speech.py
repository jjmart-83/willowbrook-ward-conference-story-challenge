"""Screen independent Whisper.cpp clip transcripts against reviewed source captions.

Run after every clip has a full Whisper JSON and clip-expectations.json is merged:
    python conference-game/compare_clip_speech.py

This creates a machine inspection queue, not confirmed content or edit errors.
Only --allow-partial permits development output with missing/invalid transcripts.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
from difflib import SequenceMatcher
import hashlib
from html import escape
import json
from pathlib import Path
import re
import statistics
import unicodedata
from urllib.parse import quote, unquote

GAME = Path(__file__).resolve().parent
STOP = set("a an the and or but as at by for from in into of on to with that this these those it its is are was were be been being i me my we us our you your he him his she her they them their do does did have has had can could will would should not no so than then there here all each one".split())
INSERTIONS = STOP | {"need", "needs", "must", "first", "only", "always"}
NUMBERS = dict(zip("zero one two three four five six seven eight nine ten eleven twelve".split(), map(str, range(13))))
NUMBERS.update({"first": "1", "second": "2", "third": "3", "fourth": "4", "fifth": "5"})
IRREGULAR = {
    "children": "child", "men": "man", "women": "woman", "came": "come",
    "coming": "come", "knew": "know", "known": "know", "knowing": "know",
    "took": "take", "taken": "take", "taking": "take", "gave": "give",
    "given": "give", "giving": "give", "kept": "keep", "keeping": "keep",
    "felt": "feel", "feeling": "feel", "loved": "love", "loving": "love",
    "loves": "love", "served": "serve", "serving": "serve", "prayer": "pray",
    "prayers": "pray", "repentance": "repent", "willingness": "willing",
    "guided": "guide", "guiding": "guide", "guidance": "guide",
    "saviour": "savior", "strengthen": "strength", "strengthens": "strength",
    "strengthened": "strength", "strengthening": "strength",
    "stronger": "strong", "strongest": "strong", "kinder": "kind", "kindest": "kind",
}
THRESHOLDS = {
    "grossMismatchRecallBelow": 0.18,
    "alignmentInspectRecallBelow": 0.45,
    "missingRegionMinWords": 15,
    "missingRegionMinContentWords": 10,
    "missingRegionMinCaptionSeconds": 6.0,
    "boundaryMinContentWords": 4,
    "boundaryInspectRecallBelow": 0.35,
    "confidenceMeanInspectBelow": 0.65,
    "confidenceLowTokenProbability": 0.50,
    "confidenceLowTokenFractionInspectAbove": 0.25,
}


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def normalize(text):
    text = str(text).replace("\u2019", "'").replace("\u2018", "'")
    text = unicodedata.normalize("NFKD", str(text).lower()).encode("ascii", "ignore").decode()
    for source, replacement in {
        "can't": "can not", "cannot": "can not", "won't": "will not",
        "isn't": "is not", "aren't": "are not", "wasn't": "was not",
        "weren't": "were not", "don't": "do not", "doesn't": "does not",
        "didn't": "did not", "haven't": "have not", "hasn't": "has not",
        "hadn't": "had not", "wouldn't": "would not", "couldn't": "could not",
        "shouldn't": "should not", "we're": "we are", "they're": "they are",
        "you're": "you are", "i'm": "i am", "it's": "it is",
    }.items():
        text = re.sub(r"\b" + re.escape(source) + r"\b", replacement, text)
    text = re.sub(r"\[[^]]*\]|<[^>]*>", " ", text)
    return [NUMBERS.get(word, word) for word in re.findall(r"[a-z0-9]+(?:'[a-z]+)?", text)]


def stem(word):
    word = word.removesuffix("'s")
    if word.endswith("ies") and len(word) > 4:
        word = word[:-3] + "y"
    elif word.endswith(("sses", "ches", "shes", "xes", "zes")) and len(word) > 5:
        word = word[:-2]
    elif word.endswith("s") and not word.endswith(("ss", "us", "is")) and len(word) > 3:
        word = word[:-1]
    if word in IRREGULAR:
        return IRREGULAR[word]
    for suffix in ("ness", "ingly", "edly", "ing", "ed", "ly"):
        if word.endswith(suffix) and len(word) - len(suffix) >= 3:
            base = word[:-len(suffix)]
            if suffix in {"ing", "ingly"} and len(base) > 3 and base[-1:] == base[-2:-1] and base[-1:] not in "lszd":
                base = base[:-1]
            return base
    return word


def seconds(value):
    if isinstance(value, (int, float)):
        return float(value)
    parts = str(value).replace(",", ".").split(":")
    return sum(float(part) * 60 ** index for index, part in enumerate(reversed(parts)))


def parse_captions(path):
    cues = []
    raw = Path(path).read_bytes()
    for block in re.split(r"\r?\n\s*\r?\n", raw.decode("utf-8-sig").strip()):
        lines = block.splitlines()
        if len(lines) < 3 or " --> " not in lines[1]:
            continue
        start, end = lines[1].split(" --> ", 1)
        cues.append({"number": int(lines[0]), "start": seconds(start),
                     "end": seconds(end.split()[0]), "text": " ".join(lines[2:])})
    if not cues:
        raise ValueError(f"No SRT cues parsed: {path}")
    return cues, hashlib.sha256(raw).hexdigest()


def find_boundary(cues, text, time, opening):
    wanted = normalize(text)
    nearby = [c for c in cues if c["start"] <= time + 10 and c["end"] >= time - 10]
    exact = [c for c in nearby if normalize(c["text"]) == wanted]
    if exact:
        return min(exact, key=lambda c: abs((c["start"] if opening else c["end"]) - time)), "exact cue text"
    if wanted and nearby:
        scored = [(SequenceMatcher(None, wanted, normalize(c["text"]), autojunk=False).ratio(), c) for c in nearby]
        score, candidate = max(scored, key=lambda item: item[0])
        if score >= 0.8:
            return candidate, "approximate cue text"
    return None, "timestamp-only fallback"


def caption_window(clip, cues):
    by_number = {c["number"]: c for c in cues}
    numbers = clip.get("sourceCueNumbers", [])
    if len(numbers) == 2 and all(n in by_number for n in numbers):
        first, last = by_number[numbers[0]], by_number[numbers[1]]
        method = "explicit reviewed cue numbers"
    else:
        first, first_method = find_boundary(cues, clip.get("leadCueText", ""), clip["start"], True)
        last, last_method = find_boundary(cues, clip.get("tailCueText", ""), clip["end"], False)
        method = f"opening: {first_method}; ending: {last_method}"
    temporal = [c for c in cues if c["end"] > clip["start"] and c["start"] < clip["end"]]
    if first and last and first["number"] <= last["number"]:
        selected = [c for c in cues if first["number"] <= c["number"] <= last["number"]]
    else:
        selected = temporal
    records = []
    for cue in selected:
        words = normalize(cue["text"])
        overlap = 0
        if records and cue["start"] < records[-1]["cueEnd"]:
            previous = [r["word"] for r in records[-30:]]
            for length in range(min(len(words), len(previous), 30), 2, -1):
                if previous[-length:] == words[:length]:
                    overlap = length
                    break
        for index, word in enumerate(words):
            if index < overlap:
                continue
            records.append({"word": word, "stem": stem(word), "cue": cue["number"],
                            "start": cue["start"] + (cue["end"] - cue["start"]) * index / max(1, len(words)),
                            "end": cue["start"] + (cue["end"] - cue["start"]) * (index + 1) / max(1, len(words)),
                            "cueEnd": cue["end"]})
    return selected, records, {"method": method, "coreCueCount": len(selected),
                               "overlappingTimestampCueCount": len(temporal),
                               "openingCue": first, "endingCue": last}


def read_transcript(path):
    data = load(path)
    if not isinstance(data.get("transcription"), list):
        raise ValueError("Expected Whisper.cpp transcription segment list")
    segments, probabilities = [], []
    for segment in data["transcription"]:
        offsets = segment.get("offsets", {})
        times = segment.get("timestamps", {})
        start = float(offsets["from"]) / 1000 if "from" in offsets else seconds(times.get("from", 0))
        end = float(offsets["to"]) / 1000 if "to" in offsets else seconds(times.get("to", start))
        text = str(segment.get("text", "")).strip()
        if normalize(text):
            segments.append({"start": start, "end": end, "text": text})
        for token in segment.get("tokens", []):
            if not re.search(r"[A-Za-z0-9]", token.get("text", "")) or token.get("text", "").startswith("[_"):
                continue
            probability = token.get("p")
            if isinstance(probability, (int, float)) and 0 <= probability <= 1:
                probabilities.append(float(probability))
    transcript = " ".join(s["text"] for s in segments)
    confidence = {"lexicalTokenCount": len(probabilities),
                  "meanTokenProbability": round(statistics.mean(probabilities), 4) if probabilities else None,
                  "lowTokenFraction": round(sum(p < THRESHOLDS["confidenceLowTokenProbability"] for p in probabilities) / len(probabilities), 4) if probabilities else None,
                  "interpretation": "Decoder token probabilities are machine signals, not calibrated correctness probabilities."}
    return transcript, segments, confidence, {"language": data.get("result", {}).get("language"),
                                              "model": data.get("params", {}).get("model"),
                                              "systeminfo": data.get("systeminfo")}


def match_term(term, words):
    term_text = str(term).replace("\u2019", "'").replace("\u2018", "'")
    parts = re.findall(r"[A-Za-z0-9']+\*?", unicodedata.normalize("NFKD", term_text).encode("ascii", "ignore").decode().lower())
    wanted = []
    for part in parts:
        if part.endswith("*"):
            wanted.append((part[:-1], True))
        else:
            wanted.extend((stem(word), False) for word in normalize(part))
    if not wanted:
        return None
    actual = [stem(w) for w in words]
    for start in range(len(actual)):
        cursor = start
        positions = []
        for target, wildcard in wanted:
            skipped = 0
            found = False
            while cursor < len(actual):
                matched = words[cursor].startswith(target) if wildcard else actual[cursor] == target
                if matched:
                    positions.append(cursor)
                    cursor += 1
                    found = True
                    break
                if positions and words[cursor] in INSERTIONS and skipped < 3:
                    cursor += 1
                    skipped += 1
                    continue
                break
            if not found:
                break
        if len(positions) == len(wanted):
            return {"variant": term, "matchedText": " ".join(words[positions[0]:positions[-1] + 1]),
                    "wordStart": positions[0], "wordEnd": positions[-1] + 1}
    return None


def semantic_checks(expectation, words):
    results = []
    for check in expectation["checks"]:
        groups = []
        for index, alternatives in enumerate(check["conceptGroups"]):
            hits = [hit for variant in alternatives if (hit := match_term(variant, words))]
            groups.append({"index": index, "alternatives": alternatives, "matched": bool(hits), "matches": hits})
        results.append({"id": check["id"], "label": check["label"], "importance": check["importance"],
                        "passed": all(g["matched"] for g in groups), "groups": groups,
                        "missingGroups": [g["index"] for g in groups if not g["matched"]]})
    return results


def alignment(expected, actual, clip):
    a, b = [r["stem"] for r in expected], [stem(w) for w in actual]
    matcher = SequenceMatcher(None, a, b, autojunk=False)
    matches = sum(block.size for block in matcher.get_matching_blocks())
    aligned = {i for block in matcher.get_matching_blocks() for i in range(block.a, block.a + block.size)}
    content = [i for i, r in enumerate(expected) if r["word"] not in STOP]
    regions = []
    for tag, a0, a1, b0, b1 in matcher.get_opcodes():
        missing = expected[a0:a1]
        if tag not in {"delete", "replace"} or not missing:
            continue
        meaningful = sum(r["word"] not in STOP for r in missing)
        start, end = min(r["start"] for r in missing), max(r["end"] for r in missing)
        if len(missing) < THRESHOLDS["missingRegionMinWords"] or meaningful < THRESHOLDS["missingRegionMinContentWords"] or end - start < THRESHOLDS["missingRegionMinCaptionSeconds"]:
            continue
        regions.append({"sourceStart": round(start, 3), "sourceEnd": round(end, 3),
                        "clipApproxStart": round(max(0, start - clip["start"]), 3),
                        "clipApproxEnd": round(min(clip["duration"], end - clip["start"]), 3),
                        "expectedText": " ".join(r["word"] for r in missing),
                        "actualNearbyText": " ".join(actual[max(0, b0 - 8):min(len(actual), b1 + 8)]),
                        "wordCount": len(missing), "contentWordCount": meaningful,
                        "boundaryRegion": a0 < 8 or a1 > len(expected) - 8,
                        "explanation": "A long caption passage was not aligned. Caption recognition, overlap timing, or Whisper omission may explain it; inspect audio before treating it as missing content."})
    metrics = {"expectedWordCount": len(a), "transcriptWordCount": len(b), "matchedWords": matches,
               "expectedWordRecall": round(matches / len(a), 4) if a else None,
               "transcriptWordPrecision": round(matches / len(b), 4) if b else None,
               "sequenceSimilarity": round(matcher.ratio(), 4),
               "expectedContentWordRecall": round(sum(i in aligned for i in content) / len(content), 4) if content else None,
               "transcriptToCaptionWordRatio": round(len(b) / len(a), 4) if a else None}
    return metrics, regions


def boundary_evidence(text, actual_words, opening):
    expected = [stem(w) for w in normalize(text) if w not in STOP]
    width = min(len(actual_words), max(20, len(normalize(text)) * 3))
    sample = actual_words[:width] if opening else actual_words[-width:]
    actual = [stem(w) for w in sample if w not in STOP]
    matched = sum(block.size for block in SequenceMatcher(None, expected, actual, autojunk=False).get_matching_blocks())
    return {"expectedCueText": text, "sampleTranscriptText": " ".join(sample),
            "expectedContentWords": len(expected), "contentWordRecall": round(matched / len(expected), 4) if expected else None,
            "explanation": "Compares a reviewed edge cue with nearby transcript words; SRT cues overlap and Whisper timestamps/punctuation are approximate."}


def trailing_fragment(clip, words, segments):
    tail = normalize(clip.get("tailCueText", ""))
    if len(tail) < 2 or not segments:
        return None
    hit = match_term(" ".join(tail), words)
    if not hit or len(words) - hit["wordEnd"] < 5:
        return None
    ending = segments[-1]["text"].rstrip().rstrip('"\'\u201d\u2019)')
    if re.search(r"[.!?]\s*$", ending):
        return None
    cursor = 0
    approximate_time = None
    for segment in segments:
        count = len(normalize(segment["text"]))
        if cursor <= hit["wordEnd"] <= cursor + count:
            approximate_time = segment["start"] + (segment["end"] - segment["start"]) * (hit["wordEnd"] - cursor) / max(1, count)
            break
        cursor += count
    return {"matchedTailCue": clip["tailCueText"], "matchedTranscriptText": hit["matchedText"],
            "followingWordCount": len(words) - hit["wordEnd"],
            "followingTranscriptText": " ".join(words[hit["wordEnd"]:]),
            "tailMatchApproxClipSeconds": round(approximate_time, 3) if approximate_time is not None else None,
            "actualLastSegment": segments[-1],
            "explanation": "The reviewed tail cue was recognized before at least five additional words, and the transcript ends without sentence-final punctuation. This can indicate a cut next-sentence fragment; Whisper punctuation and approximate word timing require listening."}


def inspect_clip(clip, expectation, cues, raw_path):
    text, segments, confidence, model = read_transcript(raw_path)
    words = normalize(text)
    selected, expected, window = caption_window(clip, cues)
    metrics, missing = alignment(expected, words, clip)
    checks = semantic_checks(expectation, words)
    flags = []
    def flag(code, priority, reason, evidence):
        flags.append({"code": code, "priority": priority, "reason": reason, "evidence": evidence,
                      "status": "machine screen flag; not a confirmed error"})
    if not words:
        flag("empty-transcription", "high", "Whisper returned no lexical speech for a reviewed spoken excerpt.", {"segmentCount": len(segments), "expectedCaptionWords": len(expected)})
    for check in checks:
        if not check["passed"]:
            priority = "high" if check["importance"] == "essential" else "medium"
            absent = [g["alternatives"] for g in check["groups"] if not g["matched"]]
            flag("meaning-check-unmatched", priority, f"{check['label']}: expected {check['importance']} concepts were not found by the term screen. Synonyms, recognition errors, and partial phrasing still require human interpretation.", {"checkId": check["id"], "missingAlternatives": absent})
    recall = metrics["expectedWordRecall"]
    if len(expected) >= 20 and len(words) >= 12 and recall is not None and recall < THRESHOLDS["grossMismatchRecallBelow"]:
        flag("gross-caption-mismatch", "high", "Very little ordered caption text aligns with the independent speech transcript; inspect for a wrong excerpt or substantial recognition failure.", metrics)
    elif len(expected) >= 30 and len(words) >= 12 and recall is not None and recall < THRESHOLDS["alignmentInspectRecallBelow"]:
        flag("weak-caption-alignment", "medium", "Caption and Whisper wording differ substantially. This alone does not establish an incorrect clip.", metrics)
    for region in missing:
        flag("long-caption-region-unmatched", "medium", region["explanation"], region)
    mean, low_fraction = confidence["meanTokenProbability"], confidence["lowTokenFraction"]
    if mean is not None and (mean < THRESHOLDS["confidenceMeanInspectBelow"] or low_fraction > THRESHOLDS["confidenceLowTokenFractionInspectAbove"]):
        flag("uncertain-transcription", "medium", "Decoder token probabilities suggest substantial uncertain recognition; listen rather than accepting this transcript as an exact quotation.", confidence)
    boundaries = {"opening": boundary_evidence(clip.get("leadCueText", ""), words, True),
                  "ending": boundary_evidence(clip.get("tailCueText", ""), words, False)}
    for name, boundary in boundaries.items():
        if clip.get("category") != "legacy-prototype" and boundary["expectedContentWords"] >= THRESHOLDS["boundaryMinContentWords"] and boundary["contentWordRecall"] < THRESHOLDS["boundaryInspectRecallBelow"]:
            flag(f"{name}-cue-unmatched", "medium", f"The reviewed {name} cue is poorly represented near the transcript edge. Inspect whether the cut or overlapping caption timing explains the difference.", boundary)
    fragment = trailing_fragment(clip, words, segments)
    if fragment:
        flag("possible-trailing-next-sentence-fragment", "medium", fragment["explanation"], fragment)
    quote_comparison = None
    if clip.get("expectedQuote"):
        quote_words = normalize(clip["expectedQuote"])
        quote_matcher = SequenceMatcher(None, [stem(w) for w in quote_words], [stem(w) for w in words], autojunk=False)
        matched = sum(block.size for block in quote_matcher.get_matching_blocks())
        quote_comparison = {"expectedQuote": clip["expectedQuote"], "expectedWordCount": len(quote_words),
                            "matchedWords": matched, "expectedWordRecall": round(matched / len(quote_words), 4) if quote_words else None,
                            "interpretation": "Stored quote wording versus independent ASR; differences require listening and do not prove missing meaning."}
        if len(quote_words) >= 8 and matched / len(quote_words) < 0.85:
            flag("stored-quotation-wording-unmatched", "medium", "Less than 85% of the stored prototype quotation aligns in order with the independent transcript. Inspect exact wording before using this as a quotation.", quote_comparison)
        if clip.get("category") == "legacy-prototype" and len(quote_words) >= 8:
            ending_words = quote_words[-8:]
            ending_match = match_term(" ".join(ending_words), words)
            quote_comparison["endingPhrase"] = " ".join(ending_words)
            quote_comparison["endingPhraseMatched"] = bool(ending_match)
            quote_comparison["endingPhraseMatch"] = ending_match
            if not ending_match:
                flag("stored-quotation-ending-unmatched", "medium", "The final eight stored quotation words were not recognized as a phrase anywhere in the independent transcript. Inspect whether the clip ends before the displayed quotation does; ASR wording errors may also explain this finding.", {"expectedEndingPhrase": " ".join(ending_words), "actualLastSegment": segments[-1] if segments else None, "status": "machine screen flag; not a confirmed truncation"})
    if len(words) >= 30:
        repetitions = Counter(tuple(words[i:i + 6]) for i in range(len(words) - 5))
        repeated = [(phrase, count) for phrase, count in repetitions.items() if count >= 4]
        if repeated:
            phrase, count = max(repeated, key=lambda item: item[1])
            flag("repeated-transcript-phrase", "medium", "A six-word phrase repeats at least four times; inspect for Whisper repetition or a genuine spoken refrain.", {"phrase": " ".join(phrase), "count": count})
    priority = "high" if any(f["priority"] == "high" for f in flags) else "medium" if flags else "low"
    first, last = (segments[0], segments[-1]) if segments else (None, None)
    return {"id": clip["id"], "title": clip["title"], "talkId": clip["talkId"], "speaker": clip["speaker"],
            "storyId": clip.get("storyId"), "topics": clip.get("topics", []), "clipPath": clip["path"],
            "category": clip.get("category", "reviewed"), "sourceFingerprint": clip.get("sourceFingerprint"),
            "sourceVideo": clip["sourceVideo"], "sourceCaptions": clip["sourceCaptions"],
            "sourceWindow": {"start": clip["start"], "end": clip["end"], "duration": clip["duration"]},
            "priority": priority, "auditStatus": "machine-inspection-needed" if flags else "no-machine-flags",
            "humanAudioVerified": False, "summary": f"{len(flags)} machine inspection flag(s); {sum(c['passed'] for c in checks)}/{len(checks)} meaning checks matched.",
            "flags": flags, "checks": checks, "expectedMeaning": expectation["expectedMeaning"],
            "companionIds": expectation.get("companionIds", []), "boundaryNote": expectation.get("boundaryNote", ""),
            "captionComparisonMetrics": metrics, "captionWindow": window, "missingRegions": missing,
            "transcriptionConfidence": confidence, "firstTranscript": first, "lastTranscript": last,
            "boundaryComparison": boundaries, "transcript": text,
            "rawPath": relative_path(raw_path), "transcriptionMetadata": model, "storedQuoteComparison": quote_comparison,
            "expectedCaptionText": " ".join(c["text"] for c in selected)}


def relative_path(path):
    try:
        return Path(path).resolve().relative_to(GAME).as_posix()
    except ValueError:
        return str(Path(path).resolve())


def file_sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def verified_metadata(path, clip, actual_sha):
    meta = load(Path(path).with_suffix(".meta.json"))
    if meta.get("clipId") != clip["id"] or meta.get("clipSha256") != actual_sha:
        raise ValueError("Transcript metadata does not identify the current clip bytes")
    if clip.get("sourceFingerprint") and meta.get("sourceFingerprint") != clip["sourceFingerprint"]:
        raise ValueError("Transcript source fingerprint differs from the current library entry")
    if meta.get("initialPrompt") not in (None, ""):
        raise ValueError("Transcript was prompted; independent speech screening requires no initial prompt")
    return meta


def validate_triage(data, clips):
    if not isinstance(data.get("clips"), list):
        raise ValueError("Transcript triage must have a clips list")
    indexed = {}
    for row in data["clips"]:
        if row["id"] in indexed:
            raise ValueError(f"Duplicate transcript triage ID: {row['id']}")
        if row.get("contentAssessment") not in {"supported", "uncertain", "possibly-missing"}:
            raise ValueError(f"Invalid transcript target assessment: {row['id']}")
        if any(not isinstance(row.get(key), bool) for key in ("inspectionRecommended", "openingConcern", "endingConcern")):
            raise ValueError(f"Transcript triage concerns must be booleans: {row['id']}")
        if not row.get("reason") or not re.fullmatch(r"[a-f0-9]{64}", row.get("baseTranscriptSha256", "")):
            raise ValueError(f"Missing transcript triage reason/hash: {row['id']}")
        if not isinstance(row.get("evidence"), dict) or any(not isinstance(row["evidence"].get(edge), str) for edge in ("opening", "ending")):
            raise ValueError(f"Missing transcript triage edge evidence: {row['id']}")
        if "transcriptPath" in row and (not isinstance(row["transcriptPath"], str) or not re.fullmatch(r"[a-f0-9]{64}", row.get("transcriptSha256", ""))):
            raise ValueError(f"Missing current transcript triage path/hash: {row['id']}")
        indexed[row["id"]] = row
    if set(indexed) != {c["id"] for c in clips}:
        raise ValueError("Transcript triage IDs must exactly match all reviewed and included prototype clips")
    return indexed


def apply_transcript_triage(result, triage, base_raw_path):
    if file_sha256(base_raw_path) != triage["baseTranscriptSha256"]:
        raise ValueError(f"Transcript triage is stale for {result['id']}; base JSON SHA-256 differs")
    current_review = "transcriptPath" in triage
    if current_review:
        selected = (GAME / result["rawPath"]).resolve()
        reviewed = (GAME / triage["transcriptPath"]).resolve()
        if selected != reviewed or file_sha256(selected) != triage["transcriptSha256"]:
            raise ValueError(f"Transcript triage is stale for {result['id']}; preferred transcript path/hash differs")
    large_checks_pass = bool(result.get("largerModelRecheck")) and all(check["passed"] for check in result["checks"])
    review = {**triage, "baseTranscriptHashVerified": True,
              "method": "Interpretive comparison of machine transcript with intended content; no human listening",
              "humanAudioVerified": False,
              "selectedTranscriptHashVerified": current_review,
              "baseOnlyUncertaintyClearedByLargerModel": (triage.get("baseReview", {}).get("contentAssessment") == "uncertain" and triage["contentAssessment"] == "supported") if current_review else triage["contentAssessment"] == "uncertain" and large_checks_pass}
    result["transcriptReview"] = review
    def add(code, priority, reason, evidence):
        result["flags"].append({"code": code, "priority": priority, "reason": reason,
                                "evidence": evidence, "origin": "transcript-triage",
                                "status": "interpretive machine-transcript inspection flag; not a confirmed audio error"})
    for edge in ("opening", "ending"):
        if triage[f"{edge}Concern"]:
            add(f"transcript-{edge}-inspection", "medium", triage["reason"],
                {"edge": edge, "transcriptEvidence": triage["evidence"][edge],
                 "baseTranscriptSha256": triage["baseTranscriptSha256"],
                 "explanation": "A review of machine-produced text raised a boundary concern regardless of ASR punctuation; listen to resolve it."})
    if triage["contentAssessment"] == "possibly-missing":
        add("transcript-target-possibly-missing", "high", triage["reason"],
            {"contentAssessment": triage["contentAssessment"], "opening": triage["evidence"]["opening"],
             "ending": triage["evidence"]["ending"], "baseTranscriptSha256": triage["baseTranscriptSha256"],
             "explanation": "Intended content may be absent from the machine transcript; this is not proof of missing audible content."})
    elif triage["contentAssessment"] == "uncertain" and (current_review or not large_checks_pass):
        add("transcript-target-uncertain", "medium", triage["reason"],
            {"contentAssessment": "uncertain", "largerModelRecheckPresent": bool(result.get("largerModelRecheck")),
             "currentMeaningChecksPassed": all(check["passed"] for check in result["checks"]),
             "opening": triage["evidence"]["opening"], "ending": triage["evidence"]["ending"]})
    result["priority"] = "high" if any(f["priority"] == "high" for f in result["flags"]) else "medium" if result["flags"] else "low"
    result["auditStatus"] = "machine-inspection-needed" if result["flags"] else "no-machine-flags"
    result["summary"] = f"{len(result['flags'])} machine inspection flag(s); {sum(c['passed'] for c in result['checks'])}/{len(result['checks'])} meaning checks matched. Transcript target assessment: {triage['contentAssessment']}."


def clock(value):
    return f"{int(value) // 60:02d}:{value % 60:05.2f}"


def safe(value):
    return str(value).replace("|", "\\|").replace("\n", " ")


def render_report(data):
    counts = data["priorityCounts"]
    lines = ["# Clip speech inspection review", "", f"**{data['completedClipCount']}/{data['expectedClipCount']} clips screened independently with Whisper.cpp.** High: {counts['high']}; medium: {counts['medium']}; low: {counts['low']}.", "",
             "This is a machine inspection queue, not a list of confirmed clip errors. A low priority means no configured machine flag, not verified exact wording or finished edit boundaries. Whisper and the supplied captions can both misrecognize words. Listen to flagged selections before changing clips or host answers.", "",
             "[Browser report and playback](clip-speech-review.html) · [Clip library](clip-library.html) · [Review foundation](../Conference%20Review.md#clip-selection) · [Structured analysis](speech-audit/analysis.json) · [Meaning expectations](clip-expectations.json)", "",
             "## What the screen checks", "",
             "- Each meaning check requires all concept groups; listed variants within a group are alternatives. Basic inflection, contractions, numbers, and explicit `*` prefixes are normalized. Limited intervening function words are allowed in phrases. A matching term screen does not prove negation, nuance, or the full claim is correct.",
             "- An unmatched essential concept is high priority; unmatched supporting concepts are medium priority. A synonym or transcription mistake may explain either.",
             "- Ordered caption-word recall below 18% flags a possible gross mismatch; below 45% asks for inspection. These thresholds apply only to passages with sufficient words. Ordinary recognition differences and names are not individually treated as clip errors.",
             "- Unaligned caption regions require at least 15 words, 10 content words, and 6 approximate caption seconds. Cue timings overlap, so reported missing-region times are search hints rather than forced alignment.",
             "- Edge-cue flags require at least four content words and less than 35% nearby recall. Every clip retains its actual first/last transcript segment and expected edge cues, even when no edge is flagged.",
             "- Original prototype edge cues came from all timing-intersecting captions, rather than a reviewed opening/ending. Their ordinary edge-cue mismatch flags are suppressed while the evidence remains available. A missing final eight-word stored quotation phrase asks for inspection; it does not confirm truncation.",
             "- A recognized tail cue followed by at least five additional words and no final sentence punctuation flags a possible trailing next-sentence fragment. Whisper punctuation is imperfect; this is a listening prompt. Stored prototype quotations below 85% ordered word recall also ask for inspection.",
             "- Confidence inspection uses lexical-token mean probability below 0.65 or more than 25% of lexical tokens below 0.50. Special timestamp tokens are excluded. These are decoder signals, not calibrated correctness probabilities.", ""]
    if not data["complete"]:
        lines += ["**Development partial output:** missing/invalid raw transcripts remain and this is not the complete audit.", ""]
    if data["summary"].get("transcriptReview"):
        review = data["summary"]["transcriptReview"]
        lines += [f"**Interpretive machine-transcript target review:** {review['completed']} clips; supported: {review['contentAssessmentCounts']['supported']}; uncertain: {review['contentAssessmentCounts']['uncertain']}; possibly missing: {review['contentAssessmentCounts']['possibly-missing']}. These assessments come from reading independent machine transcripts against intended content, not listening. {data['summary']['largerModelRechecks']} clips received a large-v3 recheck; {review['baseOnlyUncertaintyClearedByLargerModel']} initial uncertain target assessments were cleared by the larger-model review. Boundary flags can remain.", ""]
    for category, label in (("reviewed", "Reviewed clip queue"), ("legacy-prototype", "Legacy prototype clips")):
        rows = [r for r in data["clips"] if r["category"] == category]
        if not rows:
            continue
        lines += [f"## {label}", "", "| Priority | Clip / speaker | Meaning checks | Machine findings |", "| --- | --- | --- | --- |"]
        for row in sorted(rows, key=lambda r: ({"high": 0, "medium": 1, "low": 2}[r["priority"]], r["speaker"], r["title"])):
            findings = "; ".join(dict.fromkeys(f["code"] for f in row["flags"])) or "No configured machine flags"
            passed = sum(c["passed"] for c in row["checks"])
            destination = f"#{quote(row['id'])}" if row["priority"] != "low" else quote(row["clipPath"], safe="/:#?=,&-")
            lines.append(f"| {row['priority'].capitalize()} | [{safe(row['title'])}]({destination}) - {safe(row['speaker'])} | {passed}/{len(row['checks'])} | {safe(findings)} |")
    for row in data["clips"]:
        if row["priority"] == "low":
            continue
        lines += ["", f"<a id=\"{row['id']}\"></a>", "", f"## {row['priority'].capitalize()}: {row['title']}", "",
                  f"**{row['speaker']}** · Original {clock(row['sourceWindow']['start'])}–{clock(row['sourceWindow']['end'])} · [Play clip]({row['clipPath']}) · [Original source]({row['sourceVideo']}#t={row['sourceWindow']['start']},{row['sourceWindow']['end']}) · [Whisper JSON]({row['rawPath']})", "",
                  f"**Expected meaning:** {row['expectedMeaning']}", ""]
        if row["companionIds"]:
            lines += ["**Use with companions:** " + "; ".join(f"[{cid}](clip-library.html#{quote(cid)})" for cid in row["companionIds"]), ""]
        if row["boundaryNote"]:
            lines += [f"**Boundary context:** {row['boundaryNote']}", ""]
        if row.get("transcriptReview"):
            review = row["transcriptReview"]
            evidence_source = "preferred larger-model transcript" if review.get("selectedTranscriptHashVerified") else "base transcript"
            lines += [f"**Transcript target review ({review['contentAssessment']}):** {review['reason']}", "",
                      f"**Opening evidence from {evidence_source}:** {review['evidence']['opening']}", "",
                      f"**Ending evidence from {evidence_source}:** {review['evidence']['ending']}", ""]
            if review["baseOnlyUncertaintyClearedByLargerModel"]:
                lines += ["The initial recognition uncertainty was cleared in the larger-model target review. Any boundary flags remain listening prompts.", ""]
        if row.get("largerModelRecheck"):
            trace = row["largerModelRecheck"]
            lines += [f"**Larger-model recheck:** Current results use [{trace['model']}]({trace['rawPath']}); initial base screen priority was {row['initialScreen']['priority']}. Both used the current clip SHA-256 and no initial prompt.", ""]
        for name, actual_key in (("opening", "firstTranscript"), ("ending", "lastTranscript")):
            actual = row[actual_key]
            actual_label = f"{clock(actual['start'])}–{clock(actual['end'])} into clip: {actual['text']}" if actual else "No lexical transcript segment"
            cue = row["captionWindow"].get("openingCue" if name == "opening" else "endingCue")
            cue_time = f"{clock(cue['start'])}–{clock(cue['end'])} in source" if cue else "Source cue unresolved; range-based comparison"
            lines += [f"**{name.capitalize()} transcript:** {actual_label}", "", f"**Expected {name} cue ({cue_time}):** {row['boundaryComparison'][name]['expectedCueText']}", ""]
        lines += ["**Machine findings:**", ""]
        for flag in row["flags"]:
            evidence = json.dumps(flag["evidence"], ensure_ascii=False, separators=(",", ":"))
            lines += [f"- **{flag['code']} ({flag['priority']}):** {flag['reason']} Evidence: {safe(evidence)}"]
        lines += ["", "**Independent transcript:** " + row["transcript"], ""]
    lines += ["", "All raw transcripts and per-clip confidence/check results remain in the structured analysis. Machine results have not been promoted to human-verified content or corrected source quotations.", ""]
    return "\n".join(lines)


def validate_expectations(data, clips):
    if not isinstance(data.get("clips"), list):
        raise ValueError("Expectations must have a clips list")
    indexed = {}
    for row in data["clips"]:
        if row["id"] in indexed:
            raise ValueError(f"Duplicate expectation ID: {row['id']}")
        if not row.get("expectedMeaning") or not isinstance(row.get("checks"), list) or not row["checks"]:
            raise ValueError(f"Missing expected meaning/checks: {row['id']}")
        check_ids = set()
        for check in row["checks"]:
            if check["id"] in check_ids or check.get("importance") not in {"essential", "supporting"}:
                raise ValueError(f"Invalid/duplicate meaning check: {row['id']}")
            check_ids.add(check["id"])
            groups = check.get("conceptGroups")
            if not isinstance(groups, list) or not groups or any(not isinstance(g, list) or not g or any(not isinstance(term, str) or not normalize(term) for term in g) for g in groups):
                raise ValueError(f"Invalid concept groups: {row['id']}/{check['id']}")
        indexed[row["id"]] = row
    if set(indexed) != {c["id"] for c in clips}:
        raise ValueError("Expectation IDs must exactly match all clip-library IDs")
    return indexed


def render_html_report(data, markdown_path="Clip Speech Review.md"):
    """Render an offline, escaped inspection report without changing comparison results."""
    def text(value):
        return escape(str(value if value is not None else ""), quote=True)
    def url(value):
        return escape(quote(str(value), safe="/:#?=,&%+-"), quote=True)
    def model_name(row):
        name = str(row.get("transcriptionMetadata", {}).get("model", "Whisper.cpp")).replace("\\", "/").split("/")[-1]
        return name.removeprefix("ggml-").removesuffix(".bin")
    def edge_label(segment):
        if not segment:
            return "No lexical transcript segment."
        return f"{clock(segment['start'])}-{clock(segment['end'])} into clip: {segment['text']}"
    flag_titles = {
        "meaning-check-unmatched": "Intended meaning needs inspection",
        "empty-transcription": "No speech recognized",
        "gross-caption-mismatch": "Possible excerpt or recognition mismatch",
        "weak-caption-alignment": "Caption wording differs substantially",
        "long-caption-region-unmatched": "Long caption passage was not recognized",
        "uncertain-transcription": "Speech recognition is uncertain",
        "opening-cue-unmatched": "Opening cue needs inspection",
        "ending-cue-unmatched": "Ending cue needs inspection",
        "possible-trailing-next-sentence-fragment": "Possible cut next sentence",
        "stored-quotation-wording-unmatched": "Displayed quotation wording needs inspection",
        "stored-quotation-ending-unmatched": "Displayed quotation ending needs inspection",
        "repeated-transcript-phrase": "Repeated speech or recognition phrase",
        "transcript-opening-inspection": "Opening raised a transcript-review concern",
        "transcript-ending-inspection": "Ending raised a transcript-review concern",
        "transcript-target-possibly-missing": "Intended content may be missing",
        "transcript-target-uncertain": "Intended content remains uncertain",
    }
    counts = data["priorityCounts"]
    scope = data["summary"]
    rows = sorted(data["clips"], key=lambda r: ({"high": 0, "medium": 1, "low": 2}[r["priority"]], r["speaker"], r["title"]))
    by_id = {r["id"]: r for r in rows}
    parts = ["<!doctype html>", '<html lang="en"><head><meta charset="utf-8">',
             '<meta name="viewport" content="width=device-width, initial-scale=1">',
             '<title>Clip speech inspection review</title><link rel="stylesheet" href="clip-library.css"><script src="clip-playback.js" defer></script>',
             """<style>
main { max-width: 1050px; padding-top: 12px; }
.review-counts { display: flex; flex-wrap: wrap; gap: 10px; margin: 18px 0; }
.review-filter { max-width: 320px; margin-bottom: 18px; }
.review-clip { background: white; border: 1px solid #d5ded7; border-radius: 12px; margin: 16px 0; scroll-margin-top: 16px; }
.review-clip > summary { cursor: pointer; padding: 18px; display: flex; gap: 12px; align-items: baseline; flex-wrap: wrap; }
.review-clip > summary:focus-visible { outline: 3px solid #135e68; outline-offset: 3px; }
.clip-title { font-weight: 700; font-size: 1.1rem; }
.review-body { padding: 0 20px 22px; }
.review-body video { max-width: 780px; display: block; }
.review-body h3 { margin: 24px 0 8px; font-size: 1rem; }
.review-body ul { padding-left: 22px; }
.review-body li { margin-bottom: 12px; }
.review-body .source-links { margin: 12px 0; }
.review-note { background: #f0f4ef; border-radius: 6px; padding: 12px 16px; }
.edge-evidence { border-left: 3px solid #a1b3b0; padding-left: 14px; overflow-wrap: anywhere; }
.full-transcript { margin-top: 18px; padding: 12px; border: 1px solid #d5ded7; border-radius: 6px; }
.full-transcript > summary { cursor: pointer; font-weight: 700; }
.full-transcript p { white-space: pre-wrap; overflow-wrap: anywhere; }
.check-pass { color: #28572f; } .check-inspect { color: #793023; }
#visible-count { color: #52686b; font-size: .9rem; }
</style></head><body>""",
             '<header><p class="eyebrow">CONFERENCE GAME PREPARATION</p><h1>Clip speech inspection review</h1>',
             '<nav aria-label="Review resources"><a href="clip-library.html">Clip library</a><a href="../Conference%20Review.md#clip-selection">Review foundation</a>',
             f'<a href="{url(markdown_path)}">Markdown report</a><a href="speech-audit/analysis.json">Structured audit</a></nav>',
             f'<p>{data["completedClipCount"]}/{data["expectedClipCount"]} clips screened: {scope["reviewed"]["completed"]} reviewed selections and {scope["legacyPrototype"]["completed"]} original prototype clips.</p>',
             '<p class="status-note">These are machine and machine-transcript inspection findings, not confirmed audio errors. Low priority means no configured flag. Listen before treating wording, missing content, or edit boundaries as verified.</p>',
             f'<div class="review-counts"><span class="tag priority-high">High: {counts["high"]}</span><span class="tag priority-medium">Medium: {counts["medium"]}</span><span class="tag">Low: {counts["low"]}</span><span class="tag">Larger-model rechecks: {scope["largerModelRechecks"]}</span></div>',
             '<p class="attribution">Independent English audio transcripts use Whisper.cpp base.en; current SHA-verified large-v3 rechecks are preferred where available. Recognition, punctuation, and timestamps can be wrong. Meaning checks find expected word groups and do not prove the complete claim.</p>']
    review_counts = scope.get("transcriptReview")
    if review_counts:
        assessment = review_counts["contentAssessmentCounts"]
        parts.append(f'<p class="attribution">Interpreted transcript targets: supported {assessment["supported"]}; uncertain {assessment["uncertain"]}; possibly missing {assessment["possibly-missing"]}. These judgments come from machine-produced text and intended content, not listening.</p>')
    if not data["complete"]:
        parts.append('<p class="status-note">Partial development report: required transcripts are still missing or invalid.</p>')
    parts += ['</header><main><label class="review-filter" for="priority-filter">Show priority<select id="priority-filter"><option value="all">All priorities</option><option value="high">High</option><option value="medium">Medium</option><option value="low">Low</option></select></label>',
              f'<p id="visible-count" aria-live="polite">Showing {len(rows)} clips.</p>']
    for row in rows:
        clip_id = row["id"]
        legacy = row["category"] == "legacy-prototype"
        category = "Original prototype" if legacy else "Reviewed selection"
        current_txt = str(Path(row["rawPath"]).with_suffix(".txt")).replace("\\", "/")
        parts += [f'<details class="review-clip" id="{text(clip_id)}" data-priority="{text(row["priority"])}">',
                  f'<summary><span class="tag priority-{text(row["priority"])}">{text(row["priority"].capitalize())}</span><span class="clip-title">{text(row["title"])}</span><span class="attribution">{text(row["speaker"])} - {category}</span></summary>',
                  '<div class="review-body">',
                  f'<video controls preload="none" src="{url(row["clipPath"])}" aria-label="{text(row["title"])}">Your browser does not support video playback. <a href="{url(row["clipPath"])}">Open this clip</a>.</video>',
                  f'<p class="range">Original source {clock(row["sourceWindow"]["start"])}-{clock(row["sourceWindow"]["end"])}; {row["sourceWindow"]["duration"]:.1f} seconds. Selected transcript model: {text(model_name(row))}.</p>',
                  '<div class="source-links">',
                  f'<button type="button" data-play-from="0">Play opening</button><button type="button" data-play-from="{max(0, row["sourceWindow"]["duration"] - 10):.3f}">Play last 10 seconds</button><span class="playback-status" role="status"></span>',
                  f'<a href="{url(row["clipPath"])}">Open video</a><a href="{url(row["sourceVideo"])}#t={row["sourceWindow"]["start"]},{row["sourceWindow"]["end"]}">Original source</a>',
                  f'<a href="{url(current_txt)}">Selected transcript TXT</a><a href="{url(row["rawPath"])}">Transcript JSON</a>',
                  f'<a href="{url(markdown_path)}{("#" + url(clip_id)) if row["priority"] != "low" else ""}">Markdown report</a>']
        if row.get("initialScreen"):
            initial_txt = str(Path(row["initialScreen"]["rawPath"]).with_suffix(".txt")).replace("\\", "/")
            parts.append(f'<a href="{url(initial_txt)}">Initial base transcript TXT</a>')
        if not legacy:
            parts.append(f'<a href="clip-library.html#{url(clip_id)}">Library entry</a>')
        parts += ['</div>', '<h3>Intended meaning</h3>', f'<p>{text(row["expectedMeaning"])}</p>']
        if row.get("storedQuoteComparison"):
            parts += ['<h3>Displayed prototype quotation</h3>', f'<p>{text(row["storedQuoteComparison"]["expectedQuote"])}</p>']
        if row.get("boundaryNote"):
            parts.append(f'<p class="review-note"><strong>Boundary context:</strong> {text(row["boundaryNote"])}</p>')
        if row.get("companionIds"):
            companions = []
            for cid in row["companionIds"]:
                href = f'#{url(cid)}' if cid in by_id else f'clip-library.html#{url(cid)}'
                companions.append(f'<a href="{href}">{text(by_id.get(cid, {}).get("title", cid))}</a>')
            parts.append('<p><strong>Use with companions:</strong> ' + '; '.join(companions) + '</p>')
        review = row.get("transcriptReview")
        if review:
            parts += ['<h3>Transcript target review</h3>', f'<p><strong>{text(review["contentAssessment"].replace("-", " ").capitalize())}:</strong> {text(review["reason"])}</p>',
                      '<div class="edge-evidence">', f'<p><strong>Reviewed opening evidence:</strong> {text(review["evidence"]["opening"])}</p>',
                      f'<p><strong>Reviewed ending evidence:</strong> {text(review["evidence"]["ending"])}</p></div>']
        parts += ['<h3>Inspection findings</h3>']
        if row["flags"]:
            parts.append('<ul>')
            for flag in row["flags"]:
                title = flag_titles.get(flag["code"], flag["code"].replace("-", " ").capitalize())
                parts.append(f'<li><strong>{text(title)} ({text(flag["priority"])}):</strong> {text(flag["reason"])}</li>')
            parts.append('</ul>')
        else:
            parts.append('<p>No configured machine inspection flags. Wording and finished boundaries still need listening before live use.</p>')
        parts += ['<h3>Expected concept checks</h3><ul>']
        for check in row["checks"]:
            status = "Expected terms found" if check["passed"] else "Inspect expected terms"
            parts.append(f'<li class="check-{"pass" if check["passed"] else "inspect"}"><strong>{text(check["label"])}:</strong> {status} ({text(check["importance"])}).')
            absent = [g for g in check["groups"] if not g["matched"]]
            if absent:
                parts.append(' Unrecognized groups: ' + '; '.join(text(' or '.join(g["alternatives"])) for g in absent) + '.')
            parts.append('</li>')
        parts += ['</ul><h3>Opening and ending</h3>', f'<p><strong>ASR opening:</strong> {text(edge_label(row["firstTranscript"]))}</p>',
                  f'<p><strong>Expected opening cue:</strong> {text(row["boundaryComparison"]["opening"]["expectedCueText"])}</p>',
                  f'<p><strong>ASR ending:</strong> {text(edge_label(row["lastTranscript"]))}</p>',
                  f'<p><strong>Expected ending cue:</strong> {text(row["boundaryComparison"]["ending"]["expectedCueText"])}</p>',
                  '<details class="full-transcript"><summary>Read the full selected transcript</summary>', f'<p>{text(row["transcript"])}</p></details>', '</div></details>']
    parts += ["""</main><script>
(() => {
  const filter = document.getElementById('priority-filter');
  const clips = Array.from(document.querySelectorAll('.review-clip'));
  for (const clip of clips) {
    const video = clip.querySelector('video');
    const status = clip.querySelector('.playback-status');
    let playRequest = 0;
    video.addEventListener('play', () => {
      status.textContent = '';
      for (const other of clips) if (other !== clip) other.querySelector('video').pause();
    });
    for (const button of clip.querySelectorAll('[data-play-from]')) {
      button.addEventListener('click', () => {
        const request = ++playRequest;
        status.textContent = 'Loading clip…';
        playClipAt(video, Number(button.dataset.playFrom)).then(() => {
          if (request === playRequest) status.textContent = '';
        }).catch(() => {
          if (request === playRequest) status.textContent = 'Could not play this clip. Try Open video.';
        });
      });
    }
  }
  function applyFilter() {
    let count = 0;
    for (const clip of clips) {
      clip.hidden = filter.value !== 'all' && clip.dataset.priority !== filter.value;
      if (!clip.hidden) count++;
      else clip.querySelector('video').pause();
    }
    document.getElementById('visible-count').textContent = `Showing ${count} clips.`;
  }
  function openHash() {
    let id;
    try { id = decodeURIComponent(location.hash.slice(1)); } catch (_) { return; }
    const target = document.getElementById(id);
    if (!target || !target.classList.contains('review-clip')) return;
    filter.value = 'all';
    applyFilter();
    target.open = true;
    requestAnimationFrame(() => target.scrollIntoView({block: 'start'}));
  }
  filter.addEventListener('change', applyFilter);
  window.addEventListener('hashchange', openHash);
  applyFilter();
  openHash();
})();
</script></body></html>"""]
    return "\n".join(parts) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--library", type=Path, default=GAME / "clip-library.json")
    parser.add_argument("--expectations", type=Path, default=GAME / "clip-expectations.json")
    parser.add_argument("--raw-dir", type=Path, default=GAME / "speech-audit" / "raw")
    parser.add_argument("--recheck-dir", type=Path, default=GAME / "speech-audit" / "rechecks", help="Prefer current-clip SHA-verified large-model transcripts; preserve the initial screen")
    parser.add_argument("--prototype-input", type=Path, default=GAME / "speech-audit" / "prototype-input.json", help="When present, require and separately label these original prototype clips too")
    parser.add_argument("--triage", type=Path, default=GAME / "speech-audit" / "transcript-triage.json", help="Optional complete interpretive transcript review; each base JSON SHA-256 must match before applying concerns")
    parser.add_argument("--json-output", type=Path, default=GAME / "speech-audit" / "analysis.json")
    parser.add_argument("--report-output", type=Path, default=GAME / "Clip Speech Review.md")
    parser.add_argument("--html-output", type=Path, default=GAME / "clip-speech-review.html", help="Playable standalone browser report with stable clip anchors and priority filtering")
    parser.add_argument("--allow-partial", action="store_true", help="Write explicitly partial development analysis; never interpret it as the complete audit")
    args = parser.parse_args()
    try:
        library = load(args.library)
        clips = [{**c, "category": "reviewed"} for c in library["clips"]]
        primary_count = len(clips)
        if len({c["id"] for c in clips}) != len(clips):
            raise ValueError("Duplicate clip-library IDs")
        expectations = validate_expectations(load(args.expectations), clips)
        if args.prototype_input.exists():
            prototype = load(args.prototype_input)
            legacy = [{**c, "category": "legacy-prototype"} for c in prototype["clips"]]
            legacy_expectations = validate_expectations({"clips": prototype["expectations"]}, legacy)
            if set(expectations) & set(legacy_expectations):
                raise ValueError("Prototype IDs overlap reviewed library IDs")
            clips.extend(legacy)
            expectations.update(legacy_expectations)
        triage = validate_triage(load(args.triage), clips) if args.triage.exists() else {}
        unavailable = []
        raw_metadata, actual_hashes = {}, {}
        for clip in clips:
            path = args.raw_dir / f"{clip['id']}.json"
            try:
                read_transcript(path)
                actual_sha = file_sha256((GAME / unquote(clip["path"])).resolve())
                raw_metadata[clip["id"]] = verified_metadata(path, clip, actual_sha)
                actual_hashes[clip["id"]] = actual_sha
            except (OSError, ValueError, KeyError, TypeError) as error:
                unavailable.append({"id": clip["id"], "reason": str(error)})
        if unavailable and not args.allow_partial:
            raise ValueError(f"{len(unavailable)}/{len(clips)} raw transcripts missing/invalid; no final outputs written. Finish transcription or use --allow-partial for development. First unavailable: {unavailable[0]['id']}")
        excluded = {entry["id"] for entry in unavailable}
        cache, results = {}, []
        for clip in clips:
            if clip["id"] in excluded:
                continue
            source = (GAME / unquote(clip["sourceCaptions"])).resolve()
            if source not in cache:
                cache[source] = parse_captions(source)
            cues, digest = cache[source]
            result = inspect_clip(clip, expectations[clip["id"]], cues, args.raw_dir / f"{clip['id']}.json")
            result["transcriptionMetadata"].update(raw_metadata[clip["id"]])
            result["clipSha256"] = actual_hashes[clip["id"]]
            recheck_path = args.recheck_dir / f"{clip['id']}.json"
            if recheck_path.exists():
                try:
                    recheck_meta = verified_metadata(recheck_path, clip, actual_hashes[clip["id"]])
                    if "large" not in str(recheck_meta.get("model", "")).lower():
                        raise ValueError("Recheck metadata does not identify a large model")
                    rechecked = inspect_clip(clip, expectations[clip["id"]], cues, recheck_path)
                    rechecked["transcriptionMetadata"].update(recheck_meta)
                    rechecked["clipSha256"] = actual_hashes[clip["id"]]
                    rechecked["initialScreen"] = {key: result[key] for key in ("priority", "flags", "checks", "captionComparisonMetrics", "transcriptionConfidence", "transcriptionMetadata", "rawPath", "firstTranscript", "lastTranscript", "missingRegions")}
                    rechecked["largerModelRecheck"] = {"rawPath": relative_path(recheck_path), "model": recheck_meta["model"], "clipSha256": actual_hashes[clip["id"]], "verifiedCurrentClip": True}
                    result = rechecked
                except (OSError, ValueError, KeyError, TypeError) as error:
                    result["ignoredRecheck"] = {"rawPath": relative_path(recheck_path), "reason": str(error)}
            result["captionSha256"] = digest
            if triage:
                apply_transcript_triage(result, triage[clip["id"]], args.raw_dir / f"{clip['id']}.json")
            results.append(result)
        counts = Counter(row["priority"] for row in results)
        created_at = datetime.now(timezone.utc).isoformat()
        data = {"schemaVersion": 1, "createdAt": created_at, "generatedAtUtc": created_at,
                "method": {"engine": "Whisper.cpp independent audio transcription", "initialPrompt": None, "comparison": "Reviewed SRT window, grouped concept variants, approximate boundary and decoder-confidence signals", "largerRechecks": "Preferred only with matching current clip SHA-256, matching source fingerprint, no prompt, and large-model metadata", "limits": "Machine screen only; no human listening or confirmed exact quotation/boundary audit"},
                "status": "independent Whisper machine screen; human listening not completed",
                "complete": not unavailable, "expectedClipCount": len(clips), "completedClipCount": len(results),
                "humanAudioVerified": False, "unavailableTranscripts": unavailable,
                "thresholds": THRESHOLDS, "priorityCounts": {key: counts[key] for key in ("high", "medium", "low")},
                "summary": {"reviewed": {"expected": primary_count, "completed": sum(r["category"] == "reviewed" for r in results), "priorityCounts": dict(Counter(r["priority"] for r in results if r["category"] == "reviewed"))},
                            "legacyPrototype": {"expected": len(clips) - primary_count, "completed": sum(r["category"] == "legacy-prototype" for r in results), "priorityCounts": dict(Counter(r["priority"] for r in results if r["category"] == "legacy-prototype"))},
                            "largerModelRechecks": sum(bool(r.get("largerModelRecheck")) for r in results),
                            "transcriptReview": {"completed": sum("transcriptReview" in r for r in results),
                                                 "contentAssessmentCounts": {key: sum(r.get("transcriptReview", {}).get("contentAssessment") == key for r in results) for key in ("supported", "uncertain", "possibly-missing")},
                                                 "baseOnlyUncertaintyClearedByLargerModel": sum(r.get("transcriptReview", {}).get("baseOnlyUncertaintyClearedByLargerModel", False) for r in results)} if triage else None},
                "transcriptTriagePath": relative_path(args.triage) if triage else None,
                "transcriptTriageSha256": file_sha256(args.triage) if triage else None,
                "clips": results}
        report = render_report(data)
        browser_report = render_html_report(data, relative_path(args.report_output))
        for path, content in ((args.json_output, json.dumps(data, ensure_ascii=False, indent=2) + "\n"), (args.report_output, report), (args.html_output, browser_report)):
            path.parent.mkdir(parents=True, exist_ok=True)
            temporary = path.with_suffix(path.suffix + ".tmp")
            temporary.write_text(content, encoding="utf-8")
            temporary.replace(path)
        print(f"Screened {len(results)}/{len(clips)} clips: high={counts['high']}, medium={counts['medium']}, low={counts['low']}. Machine flags are not confirmed errors.")
        print(args.report_output)
        print(args.html_output)
    except (OSError, ValueError, KeyError, TypeError) as error:
        parser.exit(1, f"Speech comparison failed: {error}\n")


if __name__ == "__main__":
    main()
