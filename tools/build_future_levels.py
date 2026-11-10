#!/usr/bin/env python3
import argparse
import asyncio
import html
import json
import shutil
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SEED_PATH = ROOT / "tools/future-levels-seed.json"
LANGUAGES = ("en", "ur", "id", "tr", "fr")
VOICE = "ar-SA-HamedNeural"
LESSON_ITEMS = 8
REVIEW_ITEMS = 5
BATCH_SIZE = 12

QUIZ_PROMPT = {
    "en": "Listen to the Arabic audio, then choose the matching text.",
    "ur": "عربی آڈیو سنیں، پھر اس سے ملتا ہوا متن منتخب کریں۔",
    "id": "Dengarkan audio bahasa Arab, lalu pilih teks yang cocok.",
    "tr": "Arapça sesi dinleyin ve eşleşen metni seçin.",
    "fr": "Écoutez l’audio arabe, puis choisissez le texte correspondant.",
}
TRANSLATION_OVERRIDES = {
    "fr": {
        "I eat breakfast at seven o'clock.": (
            "Je prends le petit-déjeuner à sept heures."
        ),
        "I work from morning until noon.": "Je travaille du matin jusqu'à midi.",
        "Reviewing time and routine": "Révision de l'heure et de la routine",
    }
}
INSTRUCTION = (
    "Listen to each item, repeat it aloud, then use the review items to "
    "recall earlier lessons."
)
OBJECTIVE_TEMPLATE = "Practice useful Arabic words and short phrases about {}."


def read_json(path):
    with path.open(encoding="utf-8") as file:
        return json.load(file)


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def translate_batch(texts, language):
    query = urllib.parse.urlencode(
        {
            "client": "gtx",
            "sl": "en",
            "tl": language,
            "dt": "t",
            "q": "\n".join(texts),
        }
    )
    request = urllib.request.Request(
        f"https://translate.googleapis.com/translate_a/single?{query}",
        headers={"User-Agent": "Noor-Arabic-Course-Content/1.0"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        payload = json.loads(response.read())
    segments = payload[0]
    translated = "".join(segment[0] for segment in segments if segment)
    rows = translated.splitlines()
    if len(rows) != len(texts):
        raise ValueError(
            f"Translation batch mismatch for {language}: "
            f"expected {len(texts)}, got {len(rows)}."
        )
    return rows


def translate_strings(strings):
    strings = list(dict.fromkeys(strings))
    result = {"en": {text: text for text in strings}}
    for language in LANGUAGES[1:]:
        translations = {}
        for start in range(0, len(strings), BATCH_SIZE):
            batch = strings[start : start + BATCH_SIZE]
            for attempt in range(4):
                try:
                    rows = translate_batch(batch, language)
                    break
                except Exception:
                    if attempt == 3:
                        raise
                    time.sleep(2**attempt)
            translations.update(zip(batch, rows, strict=True))
        result[language] = translations
    for language, overrides in TRANSLATION_OVERRIDES.items():
        result[language].update(
            {source: translated for source, translated in overrides.items()
             if source in result[language]}
        )
    return result


def localize(text, translations):
    return {language: translations[language][text] for language in LANGUAGES}


def previous_review_items(level_id, lesson_index, previous_items):
    candidates = previous_items[-REVIEW_ITEMS:]
    if len(candidates) < REVIEW_ITEMS:
        raise ValueError(
            f"Not enough review items before {level_id} lesson {lesson_index + 1}."
        )
    items = []
    for index, source in enumerate(candidates, 1):
        item = {
            "id": f"{level_id}-{lesson_index + 1:02d}-review-{index}",
            "type": source["type"],
            "arabic": source["arabic"],
            "transliteration": source["transliteration"],
            "audioText": source["audioText"],
            "meaning": source["meaning"],
        }
        if source.get("audio"):
            item["audio"] = source["audio"]
        items.append(item)
    return items


def build():
    seed = read_json(SEED_PATH)
    if seed.get("schemaVersion") != 1 or seed.get("translationLanguages") != list(
        LANGUAGES
    ):
        raise ValueError("Future-level seed has an unsupported schema.")

    phrases = []
    for level in seed["levels"]:
        phrases.append(level["title"])
        if len(level["lessons"]) != 10:
            raise ValueError(f"{level['id']} must contain ten lessons.")
        for lesson in level["lessons"]:
            if len(lesson["items"]) != 3:
                raise ValueError(
                    f"{level['id']} lesson {lesson['title']} needs three new items."
                )
            for item in lesson["items"]:
                if len(item) != 5:
                    raise ValueError(f"Invalid seed item: {item}")
                phrases.append(item[4])
            objective = OBJECTIVE_TEMPLATE.format(lesson["title"])
            lesson["_objective"] = objective
            phrases.extend([lesson["title"], objective])
    phrases.extend([INSTRUCTION, QUIZ_PROMPT["en"]])
    translations = translate_strings(phrases)

    manifest_path = ROOT / "manifest.json"
    manifest = read_json(manifest_path)
    existing_ids = {level["id"] for level in manifest["levels"]}
    new_levels = []
    generated = {}
    for level in seed["levels"]:
        if level["id"] in existing_ids:
            raise ValueError(f"Level {level['id']} is already in the manifest.")
        lesson_path = f"arabic/{level['id']}.json"
        quiz_path = f"arabic/{level['id']}-quizzes.json"
        level_entry = {
            "id": level["id"],
            "order": level["order"],
            "title": localize(level["title"], translations),
            "quizFile": quiz_path,
            "lessonFiles": [lesson_path],
        }
        new_levels.append(level_entry)
        generated[level["id"]] = {"lessons": [], "items": []}

    old_words = read_json(ROOT / "arabic/words-and-sentences.json")
    previous_items = old_words["lessons"][-1]["items"]
    previous_items = [
        item
        for item in previous_items
        if item.get("audio") and item["audio"].get("path")
    ]

    for level, level_entry in zip(seed["levels"], new_levels, strict=True):
        lesson_file = {
            "schemaVersion": 1,
            "courseId": "arabic",
            "levelId": level["id"],
            "unitId": level["id"],
            "translationLanguages": list(LANGUAGES),
            "lessons": [],
        }
        quiz_file = {
            "schemaVersion": 1,
            "courseId": "arabic",
            "levelId": level["id"],
            "questionType": "listen_and_choose",
            "prompts": QUIZ_PROMPT,
            "lessons": [],
        }
        for lesson_index, lesson in enumerate(level["lessons"]):
            lesson_id = f"{level['id']}-{lesson_index + 1:02d}"
            items = previous_review_items(level["id"], lesson_index, previous_items)
            new_items = []
            for slug, item_type, arabic, romanization, meaning_en in lesson["items"]:
                item_id = f"{lesson_id}-{slug}"
                item = {
                    "id": item_id,
                    "type": item_type,
                    "arabic": arabic,
                    "transliteration": romanization.strip(),
                    "audioText": arabic,
                    "meaning": localize(meaning_en, translations),
                }
                items.append(item)
                new_items.append(item)
            if len(items) != LESSON_ITEMS:
                raise ValueError(f"{lesson_id} does not have eight practice items.")
            lesson_entry = {
                "id": lesson_id,
                "order": lesson_index + 1,
                "title": localize(lesson["title"], translations),
                "objective": localize(lesson["_objective"], translations),
                "instruction": localize(INSTRUCTION, translations),
                "items": items,
            }
            lesson_file["lessons"].append(lesson_entry)
            quiz_file["lessons"].append(
                {"lessonId": lesson_id, "questionCount": 4}
            )
            generated[level["id"]]["lessons"].append(lesson_entry)
            generated[level["id"]]["items"].extend(new_items)
            previous_items = items

        write_json(ROOT / level_entry["lessonFiles"][0], lesson_file)
        write_json(ROOT / level_entry["quizFile"], quiz_file)

    manifest["levels"].extend(new_levels)
    write_json(manifest_path, manifest)
    build_review_page(generated)
    validate(generated)
    print(
        f"Built {len(new_levels)} levels, "
        f"{sum(len(level['lessons']) for level in generated.values())} lessons, "
        f"{sum(len(level['items']) for level in generated.values())} new audio texts."
    )


def validate(generated=None):
    manifest = read_json(ROOT / "manifest.json")
    levels = manifest["levels"]
    if [level["order"] for level in levels] != list(range(1, len(levels) + 1)):
        raise ValueError("Manifest level order must be contiguous.")
    level_ids = [level["id"] for level in levels]
    if len(level_ids) != len(set(level_ids)):
        raise ValueError("Manifest contains duplicate level IDs.")
    all_ids = set()
    for level in levels:
        if level["order"] < 3:
            continue
        lessons_path = ROOT / level["lessonFiles"][0]
        quiz_path = ROOT / level["quizFile"]
        lessons_data = read_json(lessons_path)
        quiz_data = read_json(quiz_path)
        lessons = lessons_data["lessons"]
        quizzes = quiz_data["lessons"]
        if len(lessons) != 10 or len(quizzes) != 10:
            raise ValueError(f"Level {level['id']} must have ten lessons.")
        if set(quiz_data["prompts"]) != set(LANGUAGES):
            raise ValueError(f"Level {level['id']} has incomplete quiz prompts.")
        if [lesson["order"] for lesson in lessons] != list(range(1, 11)):
            raise ValueError(f"Level {level['id']} lesson order is invalid.")
        for lesson, quiz in zip(lessons, quizzes, strict=True):
            if lesson["id"] != quiz["lessonId"]:
                raise ValueError(f"Quiz mapping mismatch in {lesson['id']}.")
            if lesson["id"] in all_ids:
                raise ValueError(f"Duplicate ID: {lesson['id']}.")
            all_ids.add(lesson["id"])
            if len(lesson["items"]) != LESSON_ITEMS or quiz["questionCount"] != 4:
                raise ValueError(f"Practice or quiz count is invalid in {lesson['id']}.")
            for item in lesson["items"]:
                if item["id"] in all_ids:
                    raise ValueError(f"Duplicate ID: {item['id']}.")
                all_ids.add(item["id"])
                if not item.get("arabic") or item.get("audioText") != item["arabic"]:
                    raise ValueError(f"Arabic audio text mismatch in {item['id']}.")
                if set(item["meaning"]) != set(LANGUAGES):
                    raise ValueError(f"Missing localized meaning in {item['id']}.")
                if any(not value.strip() for value in item["meaning"].values()):
                    raise ValueError(f"Empty localized meaning in {item['id']}.")
                if generated is None:
                    audio = item.get("audio")
                    if not isinstance(audio, dict) or not audio.get("path"):
                        raise ValueError(f"Missing audio mapping in {item['id']}.")
                    audio_path = ROOT / audio["path"]
                    if not audio_path.is_file() or audio_path.stat().st_size == 0:
                        raise ValueError(
                            f"Missing audio file for {item['id']}: {audio['path']}."
                        )
    if generated is not None:
        expected = 0
        audio_texts = []
        for level in generated.values():
            expected += len(level["items"])
            audio_texts.extend(item["audioText"] for item in level["items"])
            if any("audio" in item for item in level["items"]):
                raise ValueError("New draft audio must remain unmapped in lesson JSON.")
        if expected != 240:
            raise ValueError(f"Expected 240 new audio texts, got {expected}.")
        if len(set(audio_texts)) != expected:
            raise ValueError("Draft levels contain duplicate new audio texts.")


def map_approved_audio():
    manifest = read_json(ROOT / "manifest.json")
    levels = [level for level in manifest["levels"] if level["order"] >= 3]
    audio_by_text = {}
    audio_moves = []
    for level in levels:
        lesson_file = read_json(ROOT / level["lessonFiles"][0])
        for lesson in lesson_file["lessons"]:
            for item in lesson["items"]:
                if "-review-" in item["id"]:
                    continue
                draft_path = Path("audio/draft-next-levels") / level["id"] / (
                    f"{item['id']}.mp3"
                )
                final_path = Path("audio") / level["id"] / f"{item['id']}.mp3"
                current_path = Path(item.get("audio", {}).get("path", ""))
                if current_path.parts[:2] == ("audio", level["id"]):
                    source_path = current_path
                else:
                    source_path = draft_path
                source_file = ROOT / source_path
                final_file = ROOT / final_path
                if (
                    not source_file.is_file()
                    or source_file.stat().st_size == 0
                ) and (
                    not final_file.is_file()
                    or final_file.stat().st_size == 0
                ):
                    raise FileNotFoundError(
                        f"Approved audio is missing for {item['id']}: "
                        f"{draft_path.as_posix()}."
                    )
                if source_file.is_file() and source_path != final_path:
                    audio_moves.append((source_file, final_file))
                audio_by_text[item["audioText"]] = final_path.as_posix()

    for source_file, final_file in audio_moves:
        final_file.parent.mkdir(parents=True, exist_ok=True)
        if final_file.exists():
            if final_file.stat().st_size == 0:
                raise ValueError(f"Final audio file is empty: {final_file}.")
            source_file.unlink()
        else:
            source_file.rename(final_file)

    mapped_count = 0
    reused_count = 0
    for level in levels:
        lesson_path = ROOT / level["lessonFiles"][0]
        lesson_file = read_json(lesson_path)
        for lesson in lesson_file["lessons"]:
            for item in lesson["items"]:
                if "-review-" in item["id"]:
                    existing_audio = item.get("audio")
                    existing_path = (
                        ROOT / existing_audio["path"]
                        if isinstance(existing_audio, dict)
                        and existing_audio.get("path")
                        else None
                    )
                    if (
                        existing_path is not None
                        and existing_path.is_file()
                        and existing_path.stat().st_size
                    ):
                        continue
                    relative_path = audio_by_text.get(item["audioText"])
                    if relative_path is None:
                        raise ValueError(
                            f"No approved audio found for review item {item['id']}."
                        )
                    item["audio"] = {
                        "path": relative_path,
                        "format": "mp3",
                        "provider": "edge-tts",
                        "voice": VOICE,
                        "volumeBoostDb": 2,
                    }
                    reused_count += 1
                    continue
                relative_path = (
                    Path("audio") / level["id"] / f"{item['id']}.mp3"
                )
                item["audio"] = {
                    "path": relative_path.as_posix(),
                    "format": "mp3",
                    "provider": "edge-tts",
                    "voice": VOICE,
                    "volumeBoostDb": 2,
                }
                mapped_count += 1
        write_json(lesson_path, lesson_file)

    if mapped_count != 240:
        raise ValueError(f"Expected to map 240 new clips, mapped {mapped_count}.")
    validate()
    review_items = {}
    for level in levels:
        lesson_file = read_json(ROOT / level["lessonFiles"][0])
        review_items[level["id"]] = {
            "items": [
                item
                for lesson in lesson_file["lessons"]
                for item in lesson["items"]
                if "-review-" not in item["id"]
            ]
        }
    build_review_page(review_items, approved=True)
    print(
        f"Mapped {mapped_count} new approved clips and reused audio for "
        f"{reused_count} review items."
    )


def build_review_page(generated, approved=False):
    cards_by_level = {}
    for level_id, level in generated.items():
        cards_by_level[level_id] = []
        for item in level["items"]:
            audio_directory = level_id if approved else f"draft-next-levels/{level_id}"
            path = f"{audio_directory}/{item['id']}.mp3"
            cards_by_level[level_id].append(
                f"""
                <article class="item" data-search="{html.escape(
                    item['arabic'] + ' ' + item['transliteration'] + ' ' +
                    item['meaning']['en'], quote=True
                )}">
                  <div class="arabic" lang="ar" dir="rtl">{html.escape(item['arabic'])}</div>
                  <div class="transliteration">{html.escape(item['transliteration'])}</div>
                  <div class="meaning">{html.escape(item['meaning']['en'])}</div>
                  <audio controls preload="none" src="{path}"></audio>
                  <small>{html.escape(level_id)} · {html.escape(item['id'])}</small>
                </article>
                """
            )
    page = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Noor · {"Approved" if approved else "Draft"} Arabic Levels 3–10 Audio</title>
<style>
body{{font:16px system-ui,sans-serif;max-width:980px;margin:auto;padding:20px;background:#f4f2ec;color:#202720}}
h1{{color:#173e30}} section{{margin:36px 0}} .grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:12px}}
.item{{background:#fff;border:1px solid #d5ded6;border-radius:14px;padding:14px}}
.arabic{{font-size:28px;line-height:1.8;text-align:center}} .transliteration{{text-align:center;color:#50655a}}
.meaning{{margin:8px 0;text-align:center}} audio{{width:100%;margin:8px 0}} small{{color:#637269}}
input{{box-sizing:border-box;width:100%;padding:12px;border:1px solid #aebcaf;border-radius:10px;font-size:16px}}
</style>
</head>
<body>
<h1>{"Approved" if approved else "Draft"} Arabic course audio · Levels 3–10</h1>
<p>{"All 240 new clips have been reviewed and mapped into the lesson JSON for the next integration step." if approved else "Preview only. These generated clips are not mapped into lesson JSON yet. Please check each pronunciation before approving it for the app."}</p>
<label>Filter by Arabic, transliteration, or meaning
<input id="filter" type="search" placeholder="Search audio items"></label>
{''.join(
    f'<section><h2>Level {index + 3}: {html.escape(level_id.replace("-", " ").title())}</h2>'
    f'<div class="grid">{"".join(cards_by_level[level_id])}</div></section>'
    for index, level_id in enumerate(generated)
)}
<script>
const input=document.querySelector('#filter');
input.addEventListener('input',()=>{{
  const query=input.value.trim().toLowerCase();
  document.querySelectorAll('.item').forEach(card=>{{
    card.hidden=!card.dataset.search.toLowerCase().includes(query);
  }});
}});
</script>
</body>
</html>
"""
    page = "\n".join(line.rstrip() for line in page.splitlines()) + "\n"
    review_path = ROOT / "audio/review-next-levels.html"
    review_path.parent.mkdir(parents=True, exist_ok=True)
    review_path.write_text(page, encoding="utf-8")


async def generate_audio():
    try:
        import edge_tts
    except ImportError as error:
        raise RuntimeError(
            "Install edge-tts 7.3.1 in the active Python environment first."
        ) from error

    validate()
    semaphore = asyncio.Semaphore(3)
    jobs = []
    for level in read_json(ROOT / "manifest.json")["levels"]:
        if level["order"] < 3:
            continue
        lessons_data = read_json(ROOT / level["lessonFiles"][0])
        for lesson in lessons_data["lessons"]:
            for item in lesson["items"]:
                if item.get("audio") or "-review-" in item["id"]:
                    continue
                output = ROOT / "audio/draft-next-levels" / level["id"] / (
                    f"{item['id']}.mp3"
                )
                jobs.append((item["audioText"], output))

    unique_jobs = {}
    for text, output in jobs:
        unique_jobs.setdefault(text, []).append(output)
    if len(unique_jobs) != 240:
        raise ValueError(
            f"Expected 240 unique new recordings; found {len(unique_jobs)}."
        )
    if shutil.which("ffmpeg") is None:
        raise RuntimeError("ffmpeg is required to process the draft MP3 files.")

    failures = []
    pending_jobs = {}
    for text, outputs in unique_jobs.items():
        existing = next(
            (path for path in outputs if path.is_file() and path.stat().st_size),
            None,
        )
        if existing is None:
            pending_jobs[text] = outputs
            continue
        for duplicate in outputs:
            if duplicate != existing and not duplicate.is_file():
                duplicate.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(existing, duplicate)

    async def record(text, outputs):
        async with semaphore:
            output = outputs[0]
            output.parent.mkdir(parents=True, exist_ok=True)
            if output.is_file() and output.stat().st_size:
                for duplicate in outputs[1:]:
                    duplicate.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(output, duplicate)
                return
            raw = output.with_name(output.stem + ".raw.mp3")
            for attempt in range(4):
                try:
                    await edge_tts.Communicate(text, VOICE).save(str(raw))
                    process = await asyncio.create_subprocess_exec(
                        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
                        "-i", str(raw), "-af",
                        "volume=2dB,alimiter=limit=0.95", "-ar", "44100",
                        "-ac", "1", "-b:a", "128k", str(output),
                        stdout=asyncio.subprocess.DEVNULL,
                        stderr=asyncio.subprocess.PIPE,
                    )
                    _, stderr = await process.communicate()
                    if process.returncode:
                        raise RuntimeError(stderr.decode(errors="replace"))
                    raw.unlink(missing_ok=True)
                    if output.stat().st_size == 0:
                        raise RuntimeError("TTS produced an empty MP3.")
                    for duplicate in outputs[1:]:
                        duplicate.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(output, duplicate)
                    return
                except Exception as error:
                    raw.unlink(missing_ok=True)
                    if attempt == 3:
                        failures.append((output, str(error)))
                    else:
                        await asyncio.sleep(2**attempt)

    tasks = [
        asyncio.create_task(record(text, outputs))
        for text, outputs in pending_jobs.items()
    ]
    for completed, task in enumerate(asyncio.as_completed(tasks), 1):
        await task
        if completed % 20 == 0 or completed == len(tasks):
            print(f"Generated {completed}/{len(tasks)} draft clips.", flush=True)
    if failures:
        details = "\n".join(f"{path}: {error}" for path, error in failures)
        raise RuntimeError(f"{len(failures)} audio clips failed:\n{details}")

    missing = [
        path
        for outputs in unique_jobs.values()
        for path in outputs
        if not path.is_file() or path.stat().st_size == 0
    ]
    if missing:
        raise RuntimeError(f"{len(missing)} draft audio files are missing or empty.")
    print(
        f"Draft audio ready: {len(unique_jobs)} unique Edge TTS clips "
        f"using {VOICE}; {len(tasks)} generated in this run."
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "command",
        choices=("build", "audio", "map-audio", "validate"),
    )
    command = parser.parse_args().command
    if command == "build":
        build()
    elif command == "audio":
        asyncio.run(generate_audio())
    elif command == "map-audio":
        map_approved_audio()
    else:
        validate()
        print("Future-level JSON, audio mappings, and audio files are valid.")


if __name__ == "__main__":
    main()
