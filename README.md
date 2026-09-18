# 📍 Thikana: five words for any square metre on Earth

## What we built

Imagine the whole Earth covered in graph paper where every square is 1 metre wide. Thikana gives every square a name made of five words, like `flavor.man.strong.treat.travel`. Tell someone the five words and they can find your exact square. No app, no account, no company in the middle. The recipe is open, so anybody can make their own decoder.

When you share a spot, the message has three lines:

```
flavor.man.strong.treat.travel          <- say it, write it, remember it
27.17501,78.04213                    <- every map app on Earth already understands this
https://dtensor.github.io/thikana/#flavor.man.strong.treat.travel   <- tap to open
```

If our web page vanished tomorrow, line 2 still works. The page is ONE file (`index.html`, about 140 KB) with the word list inside it. Save it on a phone and it works with no internet. The words after `#` never leave your device.

## How I use it manually

- `python3.11 thikana.py 27.17501,78.04213` prints the three-line message plus a 16-digit number form (for feature phones and reading over a call).
- `python3.11 thikana.py flavor.man.strong.treat.travel` gives back the coordinates. A wrong or misheard word is refused (exit 2), not silently sent to the wrong place.
- `python3.11 thikana.py 4218 3006 1804 2133` does the same from the digits (last digit is a check digit).
- `python3.11 thikana.py build` rebuilds `index.html` from `page.template.html` + `wordlist_en.txt`.
- Open `index.html` in any browser: type words / coordinates / digits, or press "Use my location", then "Share this".

## What runs automatically

Nothing. There is no server, no daemon, no database. That is the point.

| Command | What It Does | When I Use It |
|---|---|---|
| `thikana.py <lat,lon>` | Makes the words, digits and share message | Sharing a spot |
| `thikana.py <five.words>` | Words back to coordinates, checksum verified | Someone sent me words |
| `thikana.py <16 digits>` | Digits back to coordinates | SMS / voice call |
| `thikana.py build` | Bakes the word list into `index.html` | After changing the word list or page |
| `pytest test_thikana.py` | 17 tests, 100k random round trips | After any codec change |

## One real example

A delivery rider cannot find a farmhouse gate. The owner opens the saved page, presses "Use my location", then "Share this" into WhatsApp. The rider taps the link, presses "Google Maps", and drives to the gate. Later the owner reads the five words over a phone call to a plumber; the plumber mistypes one word and the page says "a word is wrong or misheard" instead of sending him to another village.

## Honest limits

- The grid is 1 m, but phone GPS is usually only good to 3-5 m. For true 1 m, read coordinates off a map and type them in.
- The word list is the standard BIP39 English list (2,048 common words, globally neutral, the same one crypto wallets use; every word is unique in its first 4 letters). A test pins its SHA-256, so it cannot change by accident; changing it on purpose changes every word code. The 16-digit form does not depend on the word list and is already stable.
- Voice test (Mac robot voice → whisper "base", 80 spoken codes): 63 decode straight away (homophones like serial→cereal, tied→tide, I'll→aisle are accepted automatically, the checksum still has to pass), 8 more come back as a "did you mean" suggestion, 9 are refused outright, and **0 went silently to a wrong place**. Suggestions are never auto-accepted: with 4 check bits roughly 1 wrong swap in 16 also passes, so the listener confirms with the sender. The page carries the small sound-alike table (61 KB); the CLI also falls back to the big one (`aliases_full_en.txt`, 893 KB). Rebuild both with `make_aliases.py` (needs CMUdict in `~/nltk_data`).
- **Hindi (DRAFT):** the same square also has five Hindi words (`डोर पुल शिखर समीक्षक समिति` is the Taj Mahal example). Word number 731 in English and word number 731 in Hindi mean the same thing to the machine, so either language decodes to the same spot. Spelling slips that sound the same are forgiven (ि/ी, ु/ू, ं vs half-nasal, nukta). The list was machine-picked (subtitle word frequencies, then an AI pass to throw out names, English loanwords, verb forms and unpleasant words) and has NOT been reviewed by a person yet, so it may still change; the English words and the digits will not. The share link always carries the English words, because Devanagari inside a link often breaks in chat apps.
- The first two words name an area of roughly 18 x 36 km; neighbours share them.
- The format: 25 bits latitude + 26 bits longitude, interleaved, + CRC-4, cut into five 11-bit words. Only the first 4 letters of each word matter.
- what3words and Mappls eLoc are secret recipes, so nobody can compute them offline. DIGIPIN is open but not added yet (needs checking against India Post's official code).

*Grown-up note: MIT licensed. The word list is the BIP-0039 English list (MIT); the sound-alike tables are derived from the CMU Pronouncing Dictionary. Anyone may copy, mirror or reimplement this.*
