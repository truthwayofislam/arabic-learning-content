# Arabic learning content

This directory is a standalone local content repository intended for a
separate public GitHub repository. It is not wired into the Noor app yet.

- `manifest.json` describes the Arabic course and the Basic lesson sequence.
- `arabic/basic-alphabet.json` contains the 28 letters, their joining forms,
  and a fully vocalized example word for each letter.
- `arabic/basic-reading.json` teaches short vowels and the other foundational
  reading patterns that follow the alphabet.

Each lesson has a stable `id`, `order`, and localized `title`, `objective`, and
`instruction`. Lessons contain ordered `items` with a stable `id`, Arabic
`arabic` text, Latin `transliteration`, and Arabic `audioText`. A word's
localized `meaning` is keyed by language code. Letter items also include their
positional `forms`, whether they `connectsToNext`, and an example word. Sound
charts keep the Arabic mark and letter list separate so the app can render
individual combinations.

Learner-facing explanations and word meanings are provided in the app's
non-Arabic languages: English (`en`), Urdu (`ur`), Indonesian (`id`), Turkish
(`tr`), and French (`fr`). Arabic is the learning language, so it is not offered
as its own translation language. Transliteration uses a consistent learner
friendly scholarly style (`ā`, `ī`, `ū`, `ḥ`, `ṣ`, `ḍ`, `ṭ`, `ẓ`, `ʿ`, and
`ʾ`).

Every `audioText` is Arabic script with vowel marks where useful. Audio assets
have not been generated yet; `audio` is deliberately `null` until the later
audio-generation step. Stable item IDs can be used to assign audio filenames
without changing lesson order. The content is Modern Standard Arabic (MSA).
Review translations and pronunciation with a qualified Arabic educator before
publishing lessons to learners.
# arabic-learning-content
# arabic-learning-content
