# Arabic learning content

This is the standalone content repository for Noor's Arabic course. The app
loads versioned lesson, quiz, and audio files referenced by the manifest.

- `manifest.json` describes the Arabic course and the Basic lesson sequence.
- `arabic/basic-quizzes.json` configures the listening quiz for each Basic
  lesson; answer choices are built from the reviewed lesson items.
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

Every `audioText` is Arabic script with vowel marks where useful. Each item
links to a local MP3 through its `audio.path`; paths are relative to this
repository root. The current clips use Edge TTS `ar-SA-HamedNeural` with a
small 2 dB volume boost and a limiter; isolated short-vowel drills use 6 dB.
The isolated ḍamma drill uses loudness normalization at -16 LUFS. The content
is Modern Standard Arabic (MSA). The Basic lesson text and all 71 audio clips
have been reviewed before publishing.
# arabic-learning-content
# arabic-learning-content
