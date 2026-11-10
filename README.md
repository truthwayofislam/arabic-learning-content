# Arabic learning content

This is the standalone content repository for Noor's Arabic course. The app
loads versioned lesson, quiz, and audio files referenced by the manifest.

- `manifest.json` describes the Arabic course levels and their lesson sequences.
- `arabic/basic-quizzes.json` configures the listening quiz for each Basic
  lesson; answer choices are built from the reviewed lesson items.
- `arabic/words-and-sentences.json` contains the next 12-lesson level with 89
  practice items, covering common words, simple descriptions, possession,
  locations, questions, and short verbal sentences.
- `arabic/words-quizzes.json` configures an audio-to-text matching quiz for
  each lesson in that level.
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

Every `audioText` is Arabic script with vowel marks where useful. Reviewed
Basic items link to local MP3 files through `audio.path`; paths are relative
to this repository root. The current Basic clips use Edge TTS
`ar-SA-HamedNeural` with a small 2 dB volume boost and a limiter; isolated
short-vowel drills use 6 dB. The isolated ḍamma drill uses loudness
normalization at -16 LUFS. The content is Modern Standard Arabic (MSA). The
Basic lesson text and all 71 Basic audio clips have been reviewed before
publishing.

The Words & Simple Sentences lessons, translations, quizzes, and 89 Edge TTS
clips (`ar-SA-HamedNeural`, +2 dB) have been reviewed. The content is mapped in
the manifest but still needs app integration before learners can access the
new level.
# arabic-learning-content
# arabic-learning-content
