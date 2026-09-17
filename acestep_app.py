#!/usr/bin/env python3
"""
ACE-Step for Mac - a front-end for ACE-Step 1.5 on Apple Silicon, using MLX.

Words in, a song out, plus covers of audio you already have. Everything the
model can actually be told - caption, lyrics, duration, tempo, key, time
signature, seed - is on one page, in plain English, with the trade-offs written
beside each control instead of hidden in a wiki.

This is an UNOFFICIAL front-end. It is not made by the ACE-Step team.

It does not reimplement the model. It imports ACE-Step's own handlers and calls
its own generate_music, so it stays correct when that project moves. That is
also why it has to run inside ACE-Step's virtual environment, which is what the
launcher beside it does for you.

Requires: an Apple Silicon Mac (M1 or later), ACE-Step 1.5 installed.
Install:  see INSTALL.md - it assumes you have never opened Terminal.
Run:      double-click launch_acestep.command
Port:     7873 by default; override with ACESTEP_PORT.

Environment variables it reads, all optional:
    ACESTEP_PORT              the port to serve on            (7873)
    ACESTEP_REPO              where ACE-Step 1.5 is           (~/AceStep/ACE-Step-1.5)
    ACESTEP_CHECKPOINTS_DIR   where the weights go            (~/AceStep/checkpoints)
    ACESTEP_DEMUCS_PYTHON     python of a Demucs install      (~/AceStep/demucs-venv/bin/python)
    ACESTEP_LM_BACKEND        set to mlx by the launcher

Licence: MIT. See LICENSE.
"""

import inspect
import os
import random
import re
import shutil
import subprocess
import sys
import threading
import time
from dataclasses import fields
from pathlib import Path

import gradio as gr

VERSION = "1.6"
MODEL_FAMILY = "ACE-Step 1.5"
MAX_TRACKS = 100

SCRIPT_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = SCRIPT_DIR / "outputs"
OUTPUT_DIR.mkdir(exist_ok=True)
PORT = int(os.environ.get("ACESTEP_PORT", 7873))

REPO_DIR = Path(os.environ.get("ACESTEP_REPO",
                               Path.home() / "AceStep" / "ACE-Step-1.5")).expanduser()
CKPT_DIR = Path(os.environ.get("ACESTEP_CHECKPOINTS_DIR",
                               Path.home() / "AceStep" / "checkpoints")).expanduser()


# --------------------------------------------------------------- vocabulary --

DIT_MODELS = {
    "Turbo - fastest, 8 steps (start here)": "acestep-v15-turbo",
    "SFT - slower, better finish": "acestep-v15-sft",
    "Base - slowest, takes a CFG scale": "acestep-v15-base",
}
DEFAULT_DIT = "Turbo - fastest, 8 steps (start here)"

LM_MODELS = {
    "0.6B - light, safe on any Mac": "acestep-5Hz-lm-0.6B",
    "1.7B - better captions, fine on 64 GB": "acestep-5Hz-lm-1.7B",
    "4B - known to run out of memory on macOS": "acestep-5Hz-lm-4B",
}
DEFAULT_LM = "1.7B - better captions, fine on 64 GB"

TIME_SIGNATURES = {
    "Auto - let the model decide": "",
    "4 - four beats to the bar": "4",
    "3 - three, waltz": "3",
    "6 - six-eight, lilting": "6",
    "2 - two, march or polka": "2",
}

KEYS = ["Auto - let the model decide"] + [
    f"{root} {mode}"
    for root in ["C", "C#", "Db", "D", "Eb", "E", "F", "F#", "Gb", "G", "Ab", "A", "Bb", "B"]
    for mode in ["Major", "Minor"]
]

LANGUAGES = {
    "Auto - detect from the lyrics": "unknown",
    "English": "en", "French": "fr", "Spanish": "es",
    "German": "de", "Italian": "it", "Japanese": "ja", "Chinese": "zh",
}

FORMATS = ["wav", "flac", "mp3", "opus", "aac"]

MAKE, COVER = "Make music from words", "Cover audio I already have"
JOB_MODES = [MAKE, COVER]

# --- the obedience controls -------------------------------------------------
#
# These are two different things, and knowing which is which is the difference
# between a model that surprises you and one that ignores you.
#
#   use_cot_caption  rewrites YOUR CAPTION. The language model takes what you
#                    wrote and produces its own, longer, more "producerly"
#                    version, and that is what the audio model actually sees.
#   thinking         lets the language model REASON FIRST, at length, before
#                    deciding anything - tempo, key, duration, arrangement.
#
# Off, your words go through nearly untouched and the model obeys. On, it
# elaborates - which is where the freshness comes from, and the disobedience.

AS_TYPED = "As typed - the model may not touch my words"
REWRITTEN = "Let the model rewrite it - fresher, less obedient"
BOTH = "Both - render each track twice, one of each"
CAPTION_MODES = [AS_TYPED, REWRITTEN, BOTH]

BARE_METADATA_NOTE = (
    "**Nothing is telling this model a tempo, a key or a time signature.** With caption "
    "handling on 'As typed' the language model is switched off - and the language model is "
    "the ONLY thing that fills those in when they are left on Auto. Read in their code: "
    "`cot_bpm` is only ever set inside the reasoning path.\n\nSo the audio model is inferring "
    "everything from your words alone, which is why 'As typed' can come out chaotic - and "
    "why it gets worse with a `{a|b}` prompt, where each track's wording is assembled fresh. "
    "**Set the tempo, the key and the time signature yourself below** and it settles down."
)

CAPTION_MODE_INFO = (
    "ACE-Step's language model normally rewrites your caption into its own, longer version "
    "before a note is rendered, and decides tempo, key and duration for itself. That is "
    "where the freshness comes from - and why it seems to ignore you. 'Both' renders each "
    "track twice on the same seed, so you hear exactly what the rewriting bought or cost."
)

CAPTION_INFO = (
    "What the music is: genre, instruments, mood, production. Up to 512 characters, so a "
    "paragraph, not an essay. There is no chord input on this model - the key, tempo and "
    "time signature below are the only structural controls it takes."
)

LYRICS_INFO = (
    "Section tags in square brackets, as in [Verse 1], [Chorus], [Bridge]. Leave it empty "
    "and tick Instrumental for music with no voice."
)

STEPS_INFO = (
    "How many denoising passes. **Measured on an M4 Pro: on Turbo this changes "
    "nothing at all.** Same seed at 8, 16 and 24 steps produced three byte-identical files, "
    "while taking 43, 47 and 56 seconds - so the extra work is done and thrown away. The "
    "slider is therefore switched off on Turbo. Base and SFT do use it: 32 to 64 there."
)

SHIFT_INFO = (
    "Moves where in the schedule the model spends its effort. The repo recommends 3.0 for "
    "Turbo and 1.0 otherwise. Leave it alone until everything else is settled."
)

CFG_INFO = (
    "How hard the render follows your caption. Base model only - Turbo and SFT force it "
    "back to 1.0 and ignore this."
)

LM_INFO = (
    "These two matter only when the model is allowed to rewrite. On 'As typed' it is "
    "bypassed and they do nothing at all."
)

LM_TEMP_INFO = (
    "Low: obvious, expected choices. High: odd tempos, unusual keys, stranger rewrites. "
    "Ships at 0.85."
)

LM_CFG_INFO = (
    "How hard it is held **to your words**, rather than to the negative prompt below. "
    "Higher clings tighter. Ships at 2.0."
)

LM_PAIR_HINT = (
    "**Worth trying: both high.** Wild, but still anchored to what you wrote. Adventurous "
    "high with fidelity low is where it stops listening to you altogether."
)

LM_NEG_INFO = (
    "What the model is pushed away from. ACE-Step's own default is the literal string "
    "'NO USER INPUT', which is its way of saying 'anything but a blank prompt'. Put a real "
    "description here and caption fidelity will push away from that instead."
)

TEMPO_INFO = (
    "Leave both at 0 and the model chooses. Put a number in the first box alone and every "
    "track gets exactly that tempo. Put numbers in BOTH and each track draws a tempo at "
    "random between them - 50 and 65 for something slow that is never quite the same twice. "
    "The tempo actually drawn is written into that track's .txt."
)

BATCH_INFO = (
    "Variants made in one pass, sharing the expensive language-model step - so four "
    "variants cost far less than four tracks. It MULTIPLIES with the number of tracks: "
    "5 tracks at batch 4 is 20 files."
)

COVER_INFO = (
    "How far from your original it goes. Low keeps the structure and re-dresses it; high "
    "keeps little more than the outline."
)

DURATION_INFO = (
    "10 to 600 - the model's ceiling is ten minutes. 120 is a good default: a whole piece, "
    "and it renders in a minute or two on an M4 Pro."
)

LIVE_INFO = (
    "**Every control on this page is re-read at the start of every track.** Change the "
    "tempo, the key, the caption, even the model, twenty minutes into a fifty-track run - "
    "the change lands on the next track. Nothing needs stopping. Only the number of tracks "
    "is fixed once you press Generate."
)


# ------------------------------------------------------------- prompt modes --

_WILDCARD_RE = re.compile(r"\{([^{}]+)\}")
_SEQUENTIAL_RE = re.compile(r"(?m)^\s*-{3,}\s*$")


def resolve_dynamic(text):
    def pick(match):
        options = [o.strip() for o in match.group(1).split("|") if o.strip()]
        return random.choice(options) if options else match.group(0)
    return _WILDCARD_RE.sub(pick, text or "")


def split_sequential(text):
    blocks = [b.strip() for b in _SEQUENTIAL_RE.split(text or "") if b.strip()]
    return blocks or [text or ""]


def detect_prompt_mode(text):
    """Sequential wins over dynamic: a sequential prompt may well have braces
    inside each of its versions."""
    if _SEQUENTIAL_RE.search(text or ""):
        return "Sequential"
    if _WILDCARD_RE.search(text or ""):
        return "Dynamic"
    return "Fixed"


def prompt_mode_note(label, text):
    mode = detect_prompt_mode(text)
    if mode == "Sequential":
        n = len(split_sequential(text))
        extra = (" Braces inside each version are still resolved."
                 if _WILDCARD_RE.search(text or "") else "")
        return (f"\N{CLOCKWISE RIGHTWARDS AND LEFTWARDS OPEN CIRCLE ARROWS} "
                f"**{label}: sequential** - {n} version{'s' if n != 1 else ''}, one per "
                f"track, in order. **The number of tracks is a separate setting**, further "
                f"down: set it to {n} for one render of each. Fewer, and the versions past "
                f"that are never used; more, and it starts again from the top.{extra}")
    if mode == "Dynamic":
        n = len(_WILDCARD_RE.findall(text or ""))
        return (f"\N{GAME DIE} **{label}: dynamic** - {n} `{{a|b}}` "
                f"choice{'s' if n != 1 else ''}, drawn fresh for every track.")
    return f"\N{PAGE FACING UP} **{label}: fixed** - used exactly as typed for every track."


def seq_button(text):
    """Visible only for a sequential prompt, and it says the number it will set."""
    if detect_prompt_mode(text) != "Sequential":
        return gr.update(visible=False)
    n = min(MAX_TRACKS, len(split_sequential(text)))
    return gr.update(visible=True, value=f"Set the number of tracks to {n}")


def resolve_prompt(text, track_index):
    if detect_prompt_mode(text) == "Sequential":
        blocks = split_sequential(text)
        return resolve_dynamic(blocks[track_index % len(blocks)])
    return resolve_dynamic(text)


PROMPT_HELP = (
    "The prompt tells us how to treat it - there is nothing to choose.\n\n"
    "\N{PAGE FACING UP} Plain text is used exactly as typed, for every track.\n\n"
    "\N{GAME DIE} `{bright|dark}` picks one at random, fresh for every track.\n\n"
    "\N{CLOCKWISE RIGHTWARDS AND LEFTWARDS OPEN CIRCLE ARROWS} Complete versions separated "
    "by a line of three dashes or more are used one per track, in order. The number of "
    "tracks stays your choice - a button appears to line the two up."
)


# ------------------------------------------------------------ live settings --
#
# Gradio hands a function its inputs once, when the button is pressed. For a
# fifty-track run that is the wrong moment: by track twelve you have heard
# eleven and you know what you want changed. So every control also writes its
# value here as you move it, and each track reads from here rather than from
# the arguments it was launched with.

LIVE = {}


def seed_live(values):
    """Press-time values become the starting point, so an untouched control
    behaves exactly as before."""
    LIVE.clear()
    LIVE.update(values)


def now(name, fallback=None):
    return LIVE.get(name, fallback)


def bind_live(mapping):
    """Wire every control to keep LIVE current. Called once, at build time."""
    for name, component in mapping.items():
        component.change(lambda v, n=name: LIVE.__setitem__(n, v), inputs=component)


# -------------------------------------------------------------------- stop --

class StopRequest:
    """ACE-Step runs inside this process, not as a subprocess, so a render that
    has started cannot be killed without killing the app. This stops the batch
    at the end of the track in flight - which, at a minute or two a track, is
    soon enough to be useful and honest enough to say on the button."""

    def __init__(self):
        self.event = threading.Event()

    def clear(self):
        self.event.clear()

    def is_set(self):
        return self.event.is_set()

    def request(self):
        self.event.set()
        return "Stopping - the batch ends when the track in flight finishes."


STOP = StopRequest()


# ------------------------------------------------------------------ engine --

ENGINE = {"dit": None, "llm": None, "dit_name": None, "llm_name": None}


def import_acestep():
    """Import ACE-Step, or explain in one paragraph why it could not be."""
    if str(REPO_DIR) not in sys.path:
        sys.path.insert(0, str(REPO_DIR))
    try:
        from acestep.handler import AceStepHandler
        from acestep.llm_inference import LLMHandler
        from acestep.inference import GenerationParams, GenerationConfig, generate_music
    except Exception as exc:
        raise RuntimeError(
            f"Could not import ACE-Step from {REPO_DIR}.\n"
            f"  {type(exc).__name__}: {exc}\n\n"
            "This app has to run inside ACE-Step's own virtual environment - that is what "
            "launch_acestep.command does. Press 'Check the installation' below for a full "
            "report."
        ) from exc
    return AceStepHandler, LLMHandler, GenerationParams, GenerationConfig, generate_music


def only_known(cls, values):
    """Send a dataclass only the fields it actually has.

    ACE-Step is moving quickly and its parameter names will drift. Filtering
    here means a renamed field costs you that one control, visibly, instead of
    a TypeError that kills the render."""
    known = {f.name for f in fields(cls)}
    kept = {k: v for k, v in values.items() if k in known}
    return kept, sorted(set(values) - known)


def call_with_known(fn, values):
    """The same, for a function's keyword arguments."""
    try:
        allowed = set(inspect.signature(fn).parameters)
    except (TypeError, ValueError):
        return fn(**values), []
    kept = {k: v for k, v in values.items() if k in allowed}
    return fn(**kept), sorted(set(values) - allowed)


def load_engine(dit_label, lm_label, use_mlx_dit, log, need_llm=True):
    """Bring the two handlers up, reusing them if the choice has not changed.

    Both initialisers return (status_message, ok) - ACE-Step reports a failure
    by handing back False, not by raising. Ignoring that is how you get a
    confusing crash three steps later instead of the real reason."""
    AceStepHandler, LLMHandler, *_ = import_acestep()
    dit_name, lm_name = DIT_MODELS[dit_label], LM_MODELS[lm_label]
    want = (dit_name, bool(use_mlx_dit))

    if ENGINE["dit"] is None or ENGINE["dit_name"] != want:
        log(f"Loading the audio model ({dit_name}"
            f"{', on MLX' if use_mlx_dit else ', on MPS'}) - the first time, this downloads "
            f"several gigabytes into {CKPT_DIR}.")
        dit = AceStepHandler()
        result, dropped = call_with_known(dit.initialize_service, {
            "project_root": str(REPO_DIR),
            "config_path": dit_name,
            "device": "mps",
            "use_mlx_dit": bool(use_mlx_dit),
            "quantization": None,          # macOS: ACE-Step itself leaves this off
        })
        if dropped:
            log(f"Note: this build does not take {', '.join(dropped)} - carrying on.")
        status, ok = result if isinstance(result, tuple) else (str(result), True)
        if not ok:
            raise RuntimeError(f"ACE-Step could not start the audio model:\n{status}")
        ENGINE["dit"], ENGINE["dit_name"] = dit, want

    if ENGINE["llm"] is None or ENGINE["llm_name"] != lm_name:
        log(f"Loading the language model ({lm_name}) on the MLX backend.")
        llm = LLMHandler()
        result, _ = call_with_known(llm.initialize, {
            "checkpoint_dir": str(CKPT_DIR),
            "lm_model_path": lm_name,
            "backend": "mlx",
            "device": "mps",
        })
        status, ok = result if isinstance(result, tuple) else (str(result), True)
        if not ok:
            # Found the hard way: the language model is only needed when it is
            # allowed to think or rewrite. With caption handling on "As typed"
            # the render works perfectly without it - so refusing to start here
            # would block a job that has no use for the thing that failed.
            if need_llm:
                raise RuntimeError(
                    f"ACE-Step could not start the language model:\n{status}\n\n"
                    "That model may not be downloaded yet - try another size, or set "
                    "Caption handling to 'As typed', which does not need it at all. "
                    "If it mentions memory, drop to 0.6B.")
            log(f"The language model did not start ({str(status).strip()[:120]}) - carrying "
                f"on without it, which 'As typed' does not need.")
            ENGINE["llm"], ENGINE["llm_name"] = llm, None
            return ENGINE["dit"], ENGINE["llm"]
        ENGINE["llm"], ENGINE["llm_name"] = llm, lm_name

    return ENGINE["dit"], ENGINE["llm"]


# ------------------------------------------------------------------- files --

def safe_name(text):
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", (text or "").strip())
    return cleaned.strip("_.")[:60]


def write_sidecar(path, lines, caption, lyrics):
    """Every track carries its own settings beside
    it, so anything you liked is reproducible six months later."""
    body = [f"AceStep {VERSION} - {MODEL_FAMILY}",
            f"Generated: {time.strftime('%Y%m%d-%H%M%S')}"] + list(lines)
    body += ["", "--- Caption (as sent to the model) ---", caption,
             "", "--- Lyrics (as sent to the model) ---", lyrics or "[instrumental]"]
    Path(path).write_text("\n".join(body), encoding="utf-8")


# macOS label indices, as AppleScript numbers them.
FINDER = {"none": 0, "orange": 1, "red": 2, "yellow": 3,
          "blue": 4, "purple": 5, "green": 6, "grey": 7}


def set_finder_label(path, colour):
    """Colour ONE file. Only the .wav gets a colour: a folder where every single
    item is blue tells you nothing, which is what 1.2 did. Green for a track
    rendered from your words as typed, yellow for one the model rewrote - so a
    Finder window sorted by colour is a window sorted by obedience."""
    index = FINDER.get(colour, 0)
    try:
        subprocess.run(["osascript", "-e",
                        f'tell application "Finder" to set label index of '
                        f'(POSIX file "{path}" as alias) to {index}'],
                       capture_output=True, timeout=10)
    except Exception:
        pass


def convert_audio(src, want_mp3, want_flac):
    """Optional MP3/FLAC beside the rendered file."""
    saved, warning = [], None
    if not (want_mp3 or want_flac):
        return saved, None
    if shutil.which("ffmpeg") is None:
        return saved, ("ffmpeg not found - install it once with 'brew install ffmpeg' to "
                       "get MP3 and FLAC copies.")
    src = Path(src)
    jobs = []
    if want_mp3 and src.suffix.lower() != ".mp3":
        jobs.append((src.with_suffix(".mp3"), ["-codec:a", "libmp3lame", "-q:a", "2"]))
    if want_flac and src.suffix.lower() != ".flac":
        jobs.append((src.with_suffix(".flac"), []))
    for target, opts in jobs:
        subprocess.run(["ffmpeg", "-y", "-i", str(src)] + opts + [str(target)],
                       capture_output=True, text=True)
        if target.exists():
            saved.append(target)
        else:
            warning = f"{target.suffix[1:].upper()} export failed."
    return saved, warning


# ------------------------------------------------------------------ stems --
#
# Demucs has nothing to do with ACE-Step: it is a separate model that takes a
# finished .wav and pulls it apart into drums, bass, vocals and everything
# else. That is why this works on any file you already have, and why it lives
# in its own virtual environment - it brings its own torch, and ACE-Step's is
# pinned. Nothing here can break a working install.

DEMUCS_PY = Path(os.environ.get(
    "ACESTEP_DEMUCS_PYTHON",
    Path.home() / "AceStep" / "demucs-venv" / "bin" / "python")).expanduser()

STEMS_INFO = (
    "Splits the finished track into drums, bass, vocals and everything else - four .wav "
    "files you can drag into GarageBand as separate parts. This model gives you no score, "
    "but it can give you stems. They go in a folder of their own beside the track, so a "
    "night's work does not turn into five times as many loose files."
)


def demucs_available():
    return DEMUCS_PY.exists()


def separate_stems(wav_path, log=lambda m: None):
    """Four stems in <track>_stems/, or a plain reason why not."""
    wav_path = Path(wav_path)
    if not demucs_available():
        return None, ("Stem separation needs Demucs, which is not installed. It lives in its "
                      "own environment at ~/AceStep/demucs-venv.")
    if not wav_path.exists():
        return None, f"{wav_path.name} is not there any more."
    dest = wav_path.with_name(wav_path.stem + "_stems")
    scratch = wav_path.parent / f".demucs_tmp_{wav_path.stem}"
    for device in ("mps", "cpu"):
        r = subprocess.run(
            [str(DEMUCS_PY), "-m", "demucs", "-n", "htdemucs", "-d", device,
             "-o", str(scratch), str(wav_path)],
            capture_output=True, text=True)
        produced = sorted(scratch.glob("htdemucs/*/*.wav"))
        if produced:
            dest.mkdir(exist_ok=True)
            for f in produced:
                f.replace(dest / f.name)
            shutil.rmtree(scratch, ignore_errors=True)
            if device == "cpu":
                log("  (Demucs fell back to the CPU - slower, same result.)")
            return dest, None
        shutil.rmtree(scratch, ignore_errors=True)
        if device == "mps":
            log("  Demucs could not use the GPU, retrying on the CPU...")
    return None, f"Stem separation failed: {(r.stderr or r.stdout).strip()[-300:]}"


# --------------------------------------------------------- restoring a track --

_SIDE = {
    "seed": r"^Seed:\s*(-?\d+)",
    "duration": r"^Duration asked \(s\):\s*(\d+)",
    "bpm": r"^BPM asked:\s*(\d+)",
    "batch_size": r"^Batch size:\s*(\d+)",
    "steps": r"^Inference steps:\s*(\d+)",
    "shift": r"^Inference steps:.*?shift\s*([\d.]+)",
    "instrumental": r"^Instrumental:\s*(\w+)",
    "dit": r"^Audio model:\s*(\S+)",
    "lm": r"^Language model:\s*(\S+)",
    "handling": r"^Caption handling:\s*(.+?)\s*\[",
    "key": r"^Key asked:\s*(.+)$",
    "timesig": r"^Time signature asked:\s*(.+)$",
    "cover": r"^Cover strength:\s*([\d.]+)",
}


def read_sidecar(text):
    """Pull a track's settings back out of the .txt written beside it."""
    info = {}
    for key, pat in _SIDE.items():
        m = re.search(pat, text, re.MULTILINE)
        if m:
            info[key] = m.group(1).strip()
    for tag, field in (("Caption", "caption"), ("Lyrics", "lyrics")):
        m = re.search(rf"---\s*{tag}.*?---\s*\n(.*?)(?:\n\n---|\Z)", text, re.DOTALL)
        if m:
            info[field] = m.group(1).strip()
    return info


def progress_html(text, fraction, done=False, segments=0):
    """One tick per render, so a batch reads as boxes filling up."""
    pct = max(0.0, min(1.0, float(fraction))) * 100
    colour = "#22c55e" if done else "#0ea5e9"
    ticks = ""
    if segments and 1 < int(segments) <= 60:
        step = 100.0 / int(segments)
        ticks = (f'<div style="position:absolute;inset:0;background:'
                 f'repeating-linear-gradient(to right,transparent 0,'
                 f'transparent calc({step}% - 1px),rgba(0,0,0,.28) calc({step}% - 1px),'
                 f'rgba(0,0,0,.28) {step}%)"></div>')
    return (f'<div style="font-size:0.95em;margin-bottom:6px">{text or "Not running."}</div>'
            f'<div style="position:relative;background:#e5e7eb;border-radius:999px;'
            f'height:14px;overflow:hidden">'
            f'<div style="width:{pct:.1f}%;height:100%;background:{colour};'
            f'transition:width .4s"></div>{ticks}</div>')


IDLE = progress_html("Not running.", 0.0)


def clock(seconds):
    seconds = max(0, int(seconds))
    h, m = seconds // 3600, (seconds % 3600) // 60
    return f"{h} h {m:02d}" if h else (f"{m} min" if m else f"{seconds} s")


def draw_tempo(low, high, rng):
    """One tempo for one track. A range is drawn fresh per track; a single value
    is used as given; nothing means the model decides."""
    try:
        low = int(low or 0)
        high = int(high or 0)
    except (TypeError, ValueError):
        return None
    if low <= 0 and high <= 0:
        return None
    if low <= 0:
        low = high
    if high <= 0 or high == low:
        return max(30, min(300, low))
    if high < low:
        low, high = high, low
    return max(30, min(300, rng.randint(low, high)))


def tempo_note(low, high):
    drawn = draw_tempo(low, high, random.Random(0))
    if drawn is None:
        return "*Tempo: the model decides, track by track.*"
    try:
        lo, hi = int(low or 0), int(high or 0)
    except (TypeError, ValueError):
        return "*Tempo: the model decides.*"
    if hi > 0 and lo > 0 and hi != lo:
        a, b = min(lo, hi), max(lo, hi)
        return f"*Tempo: drawn at random between **{a}** and **{b}** BPM, fresh for every track.*"
    return f"*Tempo: fixed at **{drawn}** BPM for every track.*"


def total_renders(tracks, batch, caption_mode):
    return max(1, int(tracks)) * max(1, int(batch)) * (2 if caption_mode == BOTH else 1)


def estimate(tracks, batch, caption_mode, duration, dit_label, steps):
    """Every render costs a fixed amount before a single second of audio is
    made - the language-model pass, loading, decoding - and only then a cost
    proportional to the length. The first version of this ignored the fixed
    part, so eighty 30-second tracks were quoted at 14 minutes and took 40.

    Fitted to measurements on an M4 Pro: 30 s of audio on Turbo at batch 4
    comes out at about 30 seconds per file."""
    n = total_renders(tracks, batch, caption_mode)
    dur = float(duration) if duration and float(duration) > 0 else 120.0
    turbo = DIT_MODELS[dit_label] == "acestep-v15-turbo"
    per = 28.0 + dur * (0.20 if turbo else 0.90)
    if turbo:
        per *= max(0.6, float(steps) / 8.0)
    if int(batch) > 1:
        per *= 0.9                       # the LM step is paid once for the batch
    total = n * per
    return (f"This run will render **{n} file{'s' if n != 1 else ''}** - roughly "
            f"{clock(total)}. This is a guess from the settings; once the run starts, "
            f"the estimate in the progress bar is measured and far better.")


# ------------------------------------------------------------- diagnostics --

def check_installation():
    """Everything this app needs, checked in one click - so you can diagnose a
    bad install yourself instead of reading a stack trace."""
    lines = [f"**Looking for ACE-Step in** `{REPO_DIR}`",
             f"**Checkpoints directory** `{CKPT_DIR}`", ""]
    ok = True

    if REPO_DIR.is_dir():
        lines.append("- The repo folder exists.")
        if (REPO_DIR / "acestep").is_dir():
            lines.append("- It contains the `acestep` package.")
        else:
            ok = False
            lines.append("- **But there is no `acestep` folder inside it.**")
        venv = REPO_DIR / ".venv" / "bin" / "python3"
        lines.append(f"- Its virtual environment: "
                     f"{'found' if venv.exists() else '**missing - run `uv sync` there**'}")
    else:
        ok = False
        lines.append("- **The repo folder does not exist.** Read INSTALLATION.md.")

    if CKPT_DIR.is_dir():
        size = sum(f.stat().st_size for f in CKPT_DIR.rglob("*") if f.is_file())
        lines.append(f"- Checkpoints: {size / 1e9:.1f} GB downloaded so far.")
    else:
        lines.append("- Checkpoints: nothing yet. The first render fetches them.")

    lines.append(f"- Python running this app: `{sys.executable}` ({sys.version.split()[0]})")
    lines.append(f"- `ACESTEP_LM_BACKEND` = `{os.environ.get('ACESTEP_LM_BACKEND', '(not set)')}`"
                 " (should be `mlx`)")
    lines.append(f"- ffmpeg, for MP3 and FLAC copies: "
                 f"{'found' if shutil.which('ffmpeg') else '**missing** (brew install ffmpeg)'}")

    try:
        import mlx.core  # noqa: F401
        lines.append("- MLX: installed.")
    except Exception:
        ok = False
        lines.append("- **MLX is not installed** in this environment.")

    try:
        import_acestep()
        lines.append("- **ACE-Step imports cleanly. You are ready to render.**")
    except RuntimeError as exc:
        ok = False
        lines.append(f"- Import failed:\n\n```\n{exc}\n```")

    lines.insert(0, "### \N{WHITE HEAVY CHECK MARK} Everything is in place\n" if ok else "### \N{WARNING SIGN} Something is missing\n")
    return "\n".join(lines)


# ------------------------------------------------------------------ render --

def generate(job_mode, dit_label, lm_label, use_mlx_dit, caption, lyrics, instrumental,
             language_label, caption_mode, duration, bpm, bpm_max, key_label, timesig_label,
             src_audio, cover_strength,
             lm_temperature, lm_cfg, lm_top_p, lm_negative,
             steps, shift, cfg, seed, vary_seed, num_tracks, batch_size,
             batch_name, audio_format, save_mp3, save_flac, save_stems):
    STOP.clear()
    seed_live(locals())
    log, files = [], []
    last_audio, bar = None, IDLE
    started = time.time()
    ffmpeg_warned = {"done": False}
    done_count = [0]

    def out():
        return last_audio, "\n".join(files), "\n".join(log[-200:]), bar

    def say(msg):
        log.append(msg)

    n = max(1, min(MAX_TRACKS, int(num_tracks)))    # fixed once we start
    total = total_renders(n, now("batch_size", 1), now("caption_mode", AS_TYPED))

    def tick(label):
        nonlocal bar
        elapsed = time.time() - started
        frac = done_count[0] / total if total else 0
        parts = [f"**Render {min(done_count[0] + 1, total)} of {total}**", label,
                 f"{clock(elapsed)} elapsed"]
        if done_count[0]:
            left = elapsed / frac - elapsed
            end = time.localtime(time.time() + left)
            parts += [f"about {clock(left)} left",
                      f"finishing around **{time.strftime('%H:%M', end)}**"]
        bar = progress_html("  -  ".join(parts), frac, segments=total)

    if now("job_mode") == COVER and not src_audio:
        say("Cover mode needs an audio file - drop one in, or switch back to making music.")
        yield out(); return
    if not (caption or "").strip() and now("job_mode") == MAKE:
        say("A caption is required - describe the music you want.")
        yield out(); return

    tick("loading the model")
    yield out()

    try:
        _, _, GenerationParams, GenerationConfig, generate_music = import_acestep()
        dit, llm = load_engine(now("dit_label"), now("lm_label"), now("use_mlx_dit"),
                               say, need_llm=now("caption_mode") != AS_TYPED)
    except Exception as exc:
        say(str(exc)); bar = IDLE
        yield out(); return

    say(f"Saving to: {OUTPUT_DIR}")
    say(estimate(n, now("batch_size", 1), now("caption_mode"), now("duration"),
                 now("dit_label"), now("steps")).replace("**", ""))
    say("")
    yield out()

    for i in range(n):
        if STOP.is_set():
            bar = progress_html(f"Stopped after {done_count[0]} of {total}.",
                                done_count[0] / total, segments=total)
            say(f"Stopped after {done_count[0]}/{total} render(s).")
            yield out(); return

        # ---- everything is re-read HERE, once per track ---------------------
        mode = now("job_mode")
        dit_label_l, lm_label_l = now("dit_label"), now("lm_label")
        cap_mode = now("caption_mode")
        inst = bool(now("instrumental"))
        duration_l = now("duration")
        bpm_l = draw_tempo(now("bpm"), now("bpm_max"),
                           random.Random(int(now("seed", -1)) * 31 + i))
        key_l, timesig_l = now("key_label"), now("timesig_label")
        steps_l, shift_l, cfg_l = now("steps"), now("shift"), now("cfg")
        batch_l = max(1, min(8, int(now("batch_size", 1) or 1)))
        fmt_l = now("audio_format")
        mp3_l, flac_l = now("save_mp3"), now("save_flac")

        try:
            dit, llm = load_engine(dit_label_l, lm_label_l, now("use_mlx_dit"), say,
                                   need_llm=cap_mode != AS_TYPED)
        except Exception as exc:
            say(str(exc)); yield out(); return

        track_caption = resolve_prompt(now("caption", ""), i)
        track_lyrics = "" if inst else resolve_prompt(now("lyrics", ""), i)
        base_seed = (random.randint(0, 2**31 - 1) if int(now("seed", -1)) < 0
                     else (int(now("seed")) + i if now("vary_seed") else int(now("seed"))))

        variants = [(AS_TYPED, False), (REWRITTEN, True)] if cap_mode == BOTH else \
                   [(cap_mode, cap_mode == REWRITTEN)]

        for variant_label, let_it_rewrite in variants:
            if STOP.is_set():
                break
            # 1.2 only wrote this into the filename in "Both" mode, so a folder
            # of single-mode runs could not be told apart at a glance. It is
            # always written now - the .txt always said it, the name never did.
            tag = "rewritten" if let_it_rewrite else "as-typed"
            tick(f"track {i + 1}/{n} - {tag}")
            say(f"=== Track {i + 1}/{n} - seed {base_seed} - caption {tag} ===")
            yield out()

            turbo = DIT_MODELS[dit_label_l] != "acestep-v15-base"
            wanted = {
                "task_type": "cover" if mode == COVER else "text2music",
                "caption": track_caption.strip()[:512],
                "lyrics": track_lyrics.strip()[:4096],
                "instrumental": inst,
                "vocal_language": LANGUAGES[now("language_label")],
                "duration": float(duration_l) if duration_l and float(duration_l) > 0 else -1.0,
                "bpm": bpm_l,
                "keyscale": "" if str(key_l).startswith("Auto") else key_l,
                "timesignature": TIME_SIGNATURES[timesig_l],
                "inference_steps": int(steps_l),
                "guidance_scale": float(cfg_l) if not turbo else 1.0,
                "shift": float(shift_l),
                "seed": int(base_seed),
                "infer_method": "ode",
                # the obedience pair - see CAPTION_MODE_INFO above
                "thinking": bool(let_it_rewrite),
                "use_cot_caption": bool(let_it_rewrite),
                "use_cot_metas": bool(let_it_rewrite),
            }
            if let_it_rewrite:
                # Only meaningful when the language model is actually in play.
                wanted.update({
                    "lm_temperature": float(now("lm_temperature", 0.85)),
                    "lm_cfg_scale": float(now("lm_cfg", 2.0)),
                    "lm_top_p": float(now("lm_top_p", 0.9)),
                    "lm_negative_prompt": (now("lm_negative") or "NO USER INPUT"),
                })
            if mode == COVER:
                path = src_audio if isinstance(src_audio, str) else getattr(src_audio, "name", None)
                wanted["src_audio"] = path
                wanted["audio_cover_strength"] = float(now("cover_strength", 0.7))

            params_kw, dropped = only_known(GenerationParams, wanted)
            if dropped and done_count[0] == 0:
                say(f"Note: this build of ACE-Step does not have these settings, so they "
                    f"were not sent: {', '.join(dropped)}. Everything else applies.")

            config_kw, _ = only_known(GenerationConfig, {
                "batch_size": batch_l,
                "use_random_seed": False,
                "seeds": [int(base_seed) + j for j in range(batch_l)],
                "audio_format": fmt_l,
            })

            try:
                result = generate_music(dit, llm, GenerationParams(**params_kw),
                                        GenerationConfig(**config_kw), save_dir=str(OUTPUT_DIR))
            except Exception as exc:
                say(f"Track {i + 1} failed: {type(exc).__name__}: {exc}")
                say("If that mentions memory: try the 0.6B language model, the Turbo audio "
                    "model, a smaller batch size, or a shorter duration.")
                yield out(); return

            done_count[0] += 1
            if not getattr(result, "success", True):
                say(f"Track {i + 1} failed: {getattr(result, 'error', 'unknown error')}")
                yield out(); return

            produced = getattr(result, "audios", []) or []
            if not produced:
                say(f"Track {i + 1} produced no audio. {getattr(result, 'status_message', '')}")
                yield out(); continue

            stamp = time.strftime("%Y%m%d-%H%M%S")
            stem = safe_name(now("batch_name"))
            stem = ((f"{stem}_" if stem else "") +
                    f"acestep_{stamp}_track{i + 1}of{n}_seed{base_seed}" +
                    f"_{tag}" +
                    ("_cover" if mode == COVER else ""))

            for k, audio in enumerate(produced):
                src = Path(audio.get("path", ""))
                if not src.exists():
                    continue
                suffix = f"_v{k + 1}" if len(produced) > 1 else ""
                dest = OUTPUT_DIR / f"{stem}{suffix}{src.suffix}"
                if src.resolve() != dest.resolve():
                    src.replace(dest)
                txt = dest.with_suffix(".txt")
                meta = getattr(result, "extra_outputs", {}) or {}
                write_sidecar(txt, caption=track_caption, lyrics=track_lyrics, lines=[
                    f"Job: {mode}",
                    f"Audio model: {DIT_MODELS[dit_label_l]} "
                    f"({'MLX' if now('use_mlx_dit') else 'MPS'})",
                    f"Language model: {LM_MODELS[lm_label_l]} (MLX backend)",
                    f"Caption handling: {variant_label}"
                    f"  [thinking={let_it_rewrite}, use_cot_caption={let_it_rewrite}]",
                    f"Seed: {base_seed}" + (f" (+{k} in batch)" if k else ""),
                    f"Batch size: {batch_l}",
                    f"Duration asked (s): "
                    f"{int(duration_l) if duration_l and float(duration_l) > 0 else 'auto'}",
                    f"BPM asked: {bpm_l if bpm_l else 'auto (model decides)'}"
                    + (f"  [drawn from {now('bpm')}-{now('bpm_max')}]"
                       if now("bpm_max") and int(now("bpm_max") or 0) > 0 else ""),
                    f"Key asked: {'auto' if str(key_l).startswith('Auto') else key_l}",
                    f"Time signature asked: {TIME_SIGNATURES[timesig_l] or 'auto'}",
                    f"Inference steps: {int(steps_l)}, shift {float(shift_l)}, "
                    f"CFG {float(cfg_l) if not turbo else '1.0 (forced by this model)'}",
                    f"Instrumental: {inst}",
                    f"Cover strength: {now('cover_strength')}" if mode == COVER else
                    "Cover strength: n/a",
                    f"Batch name: {safe_name(now('batch_name')) or '(none)'}",
                    (f"Language-model settings: temperature {now('lm_temperature')}, "
                     f"caption fidelity {now('lm_cfg')}, top_p {now('lm_top_p')}, "
                     f"negative {now('lm_negative')!r}" if let_it_rewrite else
                     "Language-model settings: not used (caption as typed)"),
                    f"What the model decided for itself: {meta.get('lm_metadata', '(none)')}",
                ])
                extra, warn = convert_audio(dest, mp3_l, flac_l)
                if warn and not ffmpeg_warned["done"]:
                    ffmpeg_warned["done"] = True
                    say(warn)
                if dest.suffix.lower() == ".wav":
                    set_finder_label(dest, "yellow" if let_it_rewrite else "green")
                    if now("save_stems"):
                        folder, why = separate_stems(dest, say)
                        if folder:
                            say(f"  stems: {folder.name}/ (drums, bass, vocals, other)")
                        elif why:
                            say(f"  {why}")
                for q in extra:
                    files.append(str(q))
                files.append(str(dest))
                last_audio = str(dest)
                say(f"Saved: {dest.name}")

            say("")
            tick(f"track {i + 1}/{n}")
            yield out()

    bar = progress_html(f"**Done** - {len(files)} file(s) in {clock(time.time() - started)}.",
                        1.0, done=True, segments=total)
    say(f"Done - {len(files)} file(s) in {OUTPUT_DIR}")
    yield out()


CSS = """
.resizable textarea { resize: vertical !important; min-height: 8em; }
.runbar { border: 2px solid #0ea5e9; border-radius: 10px; padding: 12px; }
.live { border: 2px solid #22c55e; border-radius: 10px; padding: 10px; }
"""


def labelled(title, info, factory, text_scale=2, control_scale=3):
    """Explanation on the left, control on the right - the same block the
    same shape every time, so the files read the same way."""
    with gr.Row(equal_height=True):
        with gr.Column(scale=text_scale, min_width=0):
            gr.Markdown(f"**{title}**  \n{info}")
        with gr.Column(scale=control_scale, min_width=0):
            component = factory()
    return component


with gr.Blocks(title="ACE-Step for Mac") as demo:
    gr.Markdown(
        f"## ACE-Step for Mac {VERSION}\n"
        f"Words in, a song out - or a cover of audio you already have. Straight generation "
        f"only: this model takes no chords, no melody and no MIDI.\n\n"
        f"Model: **{MODEL_FAMILY}** - Apple Silicon build, language model on MLX. Tracks "
        f"are saved to `{OUTPUT_DIR}` and marked **blue** in the Finder."
    )

    with gr.Group(elem_classes=["runbar"]):
        progress_bar = gr.HTML(IDLE)
        with gr.Row():
            generate_btn = gr.Button("Generate", variant="primary", scale=3)
            stop_btn = gr.Button("Stop after this track", variant="stop", scale=1)
        estimate_out = gr.Markdown(estimate(1, 1, AS_TYPED, 120, DEFAULT_DIT, 8))
        status_out = gr.Textbox(label="Status", lines=1, interactive=False, show_label=False)

    with gr.Group(elem_classes=["live"]):
        gr.Markdown(LIVE_INFO)

    job_mode = gr.Radio(JOB_MODES, value=MAKE, label="What are we doing?", show_label=False)

    with gr.Accordion("Bring back the settings of a track you liked", open=False):
        gr.Markdown("Drop the **.txt** written beside any track and every control on this "
                    "page goes back to what made it. The caption restored is the one that "
                    "was actually sent - so a `{a|b}` prompt comes back already resolved, "
                    "which is what reproduces that exact track.")
        restore_file = gr.File(label="Drop a track's .txt", file_types=[".txt"])
        restore_note = gr.Markdown()

    with gr.Row():
        with gr.Column():
            with gr.Group(visible=False) as cover_group:
                gr.Markdown("### \N{MUSICAL NOTE} The audio to cover")
                src_audio = gr.Audio(label="Drop a track", type="filepath")
                cover_strength = labelled(
                    "How far from the original", COVER_INFO,
                    lambda: gr.Slider(0.0, 1.0, value=0.7, step=0.05, label="Cover strength",
                                      show_label=False))
                gr.Markdown("*The caption below still applies: it says what to turn the "
                            "track into.*")

            gr.Markdown("### \N{PENCIL} What to make")
            gr.Markdown(PROMPT_HELP)   # NOT italic: it is four paragraphs now,
                                       # and a blank line closes an italic run,
                                       # which printed the asterisks as text.
            caption = gr.Textbox(label="Caption", lines=5, elem_classes=["resizable"],
                                 placeholder="Dream pop, warm analog synths, brushed drums, "
                                             "female vocal, hazy and unhurried",
                                 info=CAPTION_INFO)
            caption_note = gr.Markdown(prompt_mode_note("Caption", ""))
            seq_btn = gr.Button("Set the number of tracks", size="sm", visible=False)
            caption_mode = gr.Radio(CAPTION_MODES, value=AS_TYPED, label="Caption handling")
            gr.Markdown(f"*{CAPTION_MODE_INFO}*")

            with gr.Group(visible=False) as lm_group:
                gr.Markdown("#### \N{SPARKLES} How it rewrites")
                gr.Markdown(f"*{LM_INFO}*")
                lm_temperature = labelled(
                    "Adventurousness", LM_TEMP_INFO,
                    lambda: gr.Slider(0.0, 2.0, value=0.85, step=0.05,
                                      label="lm_temperature", show_label=False))
                lm_cfg = labelled(
                    "Caption fidelity", LM_CFG_INFO,
                    lambda: gr.Slider(1.0, 3.0, value=2.0, step=0.1,
                                      label="lm_cfg_scale", show_label=False))
                gr.Markdown(LM_PAIR_HINT)
                with gr.Accordion("Further language-model settings", open=False):
                    lm_top_p = labelled(
                        "Nucleus sampling (top_p)",
                        "How much of the probability mass it may draw from. 0.9 is the "
                        "default; lower narrows it to the safest words.",
                        lambda: gr.Slider(0.1, 1.0, value=0.9, step=0.05,
                                          label="lm_top_p", show_label=False))
                    lm_negative = gr.Textbox(value="NO USER INPUT", lines=2,
                                             label="Negative prompt",
                                             elem_classes=["resizable"], info=LM_NEG_INFO)

            instrumental = gr.Checkbox(value=True, label="Instrumental - no voice at all")
            lyrics = gr.Textbox(label="Lyrics", lines=6, elem_classes=["resizable"],
                                visible=False, placeholder="[Verse 1]\n...\n[Chorus]\n...",
                                info=LYRICS_INFO)
            lyrics_note = gr.Markdown(prompt_mode_note("Lyrics", ""), visible=False)
            language = gr.Dropdown(list(LANGUAGES), value="Auto - detect from the lyrics",
                                   label="Sung language", visible=False)

            gr.Markdown("### \N{TRIANGULAR RULER} Shape")
            gr.Markdown("*The only structural controls this model takes. Every one can be "
                        "left on Auto, and the model will choose.*")
            with gr.Row():
                duration = gr.Number(value=120, precision=0, minimum=0, maximum=600,
                                     label="Duration in seconds (0 = auto)", scale=1,
                                     info=DURATION_INFO)
                bpm = gr.Number(value=0, precision=0, minimum=0, maximum=300,
                                label="Tempo, or lowest (0 = auto)", scale=1)
                bpm_max = gr.Number(value=0, precision=0, minimum=0, maximum=300,
                                    label="...highest (0 = fixed)", scale=1)
            tempo_readout = gr.Markdown(tempo_note(0, 0))
            bare_note = gr.Markdown("")
            gr.Markdown(f"*{TEMPO_INFO}*")
            with gr.Row():
                key = gr.Dropdown(KEYS, value=KEYS[0], label="Key", scale=2)
                timesig = gr.Dropdown(list(TIME_SIGNATURES), value=list(TIME_SIGNATURES)[0],
                                      label="Time signature", scale=2)

        with gr.Column():
            gr.Markdown("### \N{CONTROL KNOBS} How to render it")
            dit_label = gr.Dropdown(list(DIT_MODELS), value=DEFAULT_DIT, label="Audio model")
            lm_label = gr.Dropdown(list(LM_MODELS), value=DEFAULT_LM,
                                   label="Language model (writes the metadata)")
            use_mlx_dit = gr.Checkbox(
                value=True, label="Run the audio model on MLX as well as the language model")
            gr.Markdown(
                "*Leave this on. Measured on an M4 Pro, same seed and settings: MLX "
                "gave 97 waveform discontinuities and 3.3% of its energy above 12 kHz; the "
                "PyTorch MPS path gave **3062** discontinuities and 0.27% - thirty times "
                "rougher and far duller. Untick it only if a render actually fails.*")
            steps = labelled("Inference steps", STEPS_INFO,
                             lambda: gr.Slider(1, 20, value=8, step=1,
                                               label="Steps (ignored by Turbo)",
                                               interactive=False, show_label=False))
            shift = labelled("Schedule shift", SHIFT_INFO,
                             lambda: gr.Slider(1.0, 5.0, value=3.0, step=0.1, label="Shift",
                                               show_label=False))
            cfg = labelled("Caption strength", CFG_INFO,
                           lambda: gr.Slider(1.0, 15.0, value=7.0, step=0.5, label="CFG",
                                             show_label=False))
            seed = labelled("Seed",
                            "-1 gives every track a new one. Type a number to reproduce a "
                            "track you liked - every track writes its seed into its .txt.",
                            lambda: gr.Number(value=-1, precision=0, label="Seed",
                                              show_label=False))
            vary_seed = gr.Checkbox(value=True,
                                    label="Add 1 to the seed for each extra track "
                                          "(ignored while the seed is -1)")

            gr.Markdown("### \N{INPUT SYMBOL FOR NUMBERS} How many")
            num_tracks = gr.Slider(1, MAX_TRACKS, value=1, step=1, label="Number of tracks")
            batch_size = labelled("Batch size", BATCH_INFO,
                                  lambda: gr.Slider(1, 8, value=1, step=1, label="Batch size",
                                                    show_label=False))
            batch_name = gr.Textbox(value="", label="Batch name",
                                    placeholder="e.g. dream-pop-night-1",
                                    info="Your own name, at the front of every filename.")
            audio_format = gr.Dropdown(FORMATS, value="wav", label="File format")
            with gr.Row():
                save_mp3 = gr.Checkbox(label="Also save MP3")
                save_flac = gr.Checkbox(label="Also save FLAC")
            save_stems = gr.Checkbox(
                value=False, interactive=demucs_available(),
                label="Also split into stems (drums, bass, vocals, other)"
                      + ("" if demucs_available() else " - Demucs not installed"))
            gr.Markdown(f"*{STEMS_INFO}*")

    gr.Markdown("### \N{SPEAKER WITH THREE SOUND WAVES} Results")
    audio_out = gr.Audio(label="Latest track", type="filepath")
    files_out = gr.Textbox(label="Files saved this run", lines=4)
    log_out = gr.Textbox(label="Log", lines=14, max_lines=40)

    with gr.Accordion("Split a track you already have into stems", open=False):
        gr.Markdown("Demucs works on any finished .wav, whenever you like - including every "
                    "track you made before today. The four parts land in a folder beside it.")
        with gr.Row():
            stem_file = gr.File(label="Drop a .wav", file_types=[".wav", ".flac", ".mp3"])
            stem_btn = gr.Button("Split it", variant="primary")
        stem_out = gr.Markdown()

    with gr.Accordion("Is it installed properly?", open=False):
        gr.Markdown("Press this before your first render, or whenever something fails. It "
                    "checks every piece and says which one is missing, so you do not have "
                    "to read a stack trace.")
        check_btn = gr.Button("Check the installation")
        check_out = gr.Markdown()

    # ------------------------------------------------------------------ wiring

    ALL_INPUTS = [job_mode, dit_label, lm_label, use_mlx_dit, caption, lyrics, instrumental,
                  language, caption_mode, duration, bpm, bpm_max, key, timesig,
                  src_audio, cover_strength,
                  lm_temperature, lm_cfg, lm_top_p, lm_negative,
                  steps, shift, cfg, seed, vary_seed, num_tracks, batch_size,
                  batch_name, audio_format, save_mp3, save_flac, save_stems]

    # The names here must match generate()'s parameter names, because seed_live()
    # seeds LIVE from locals() and each track reads it back by name.
    bind_live({
        "job_mode": job_mode, "dit_label": dit_label, "lm_label": lm_label,
        "use_mlx_dit": use_mlx_dit, "caption": caption, "lyrics": lyrics,
        "instrumental": instrumental, "language_label": language,
        "caption_mode": caption_mode, "duration": duration, "bpm": bpm, "bpm_max": bpm_max,
        "key_label": key, "timesig_label": timesig, "cover_strength": cover_strength,
        "steps": steps, "shift": shift, "cfg": cfg, "seed": seed,
        "vary_seed": vary_seed, "batch_size": batch_size, "batch_name": batch_name,
        "audio_format": audio_format, "save_mp3": save_mp3, "save_flac": save_flac,
        "lm_temperature": lm_temperature, "lm_cfg": lm_cfg, "lm_top_p": lm_top_p,
        "lm_negative": lm_negative,
    })

    # The language-model panel is only shown when the language model is used.
    caption_mode.change(lambda m: gr.update(visible=m != AS_TYPED),
                        inputs=caption_mode, outputs=lm_group)

    def show_cover(mode):
        return gr.update(visible=mode == COVER), gr.update(
            label="Number of covers" if mode == COVER else "Number of tracks")

    job_mode.change(show_cover, inputs=job_mode, outputs=[cover_group, num_tracks])

    def toggle_lyrics(inst):
        return (gr.update(visible=not inst),) * 3

    instrumental.change(toggle_lyrics, inputs=instrumental,
                        outputs=[lyrics, lyrics_note, language])
    def bare_metadata(mode, bpm_v, bpm_hi, key_v, ts_v):
        """Warn only when it actually applies: the LM off AND everything on Auto."""
        lm_off = mode in (AS_TYPED, BOTH)
        nothing_set = (not (bpm_v and int(bpm_v) > 0)
                       and not (bpm_hi and int(bpm_hi) > 0)
                       and str(key_v).startswith("Auto")
                       and not TIME_SIGNATURES.get(ts_v))
        return BARE_METADATA_NOTE if (lm_off and nothing_set) else ""

    _bare_inputs = [caption_mode, bpm, bpm_max, key, timesig]
    for _c in _bare_inputs:
        _c.change(bare_metadata, inputs=_bare_inputs, outputs=bare_note)

    caption.change(lambda v: prompt_mode_note("Caption", v),
                   inputs=caption, outputs=caption_note)
    caption.change(seq_button, inputs=caption, outputs=seq_btn)
    seq_btn.click(lambda v: min(MAX_TRACKS, len(split_sequential(v))),
                  inputs=caption, outputs=num_tracks)
    lyrics.change(lambda v: prompt_mode_note("Lyrics", v), inputs=lyrics, outputs=lyrics_note)

    def steps_for(dit):
        # Turbo ignores inference_steps entirely - proven by three byte-identical
        # renders at 8, 16 and 24. A slider that does nothing is worse than no
        # slider, so it is greyed out rather than left there to be believed in.
        turbo = DIT_MODELS[dit] == "acestep-v15-turbo"
        return (gr.update(maximum=20 if turbo else 200, value=8 if turbo else 48,
                          interactive=not turbo,
                          label="Steps (ignored by Turbo)" if turbo else "Steps"),
                gr.update(value=3.0 if turbo else 1.0),
                gr.update(interactive=DIT_MODELS[dit] == "acestep-v15-base"))

    dit_label.change(steps_for, inputs=dit_label, outputs=[steps, shift, cfg])
    for ctrl in (bpm, bpm_max):
        ctrl.change(tempo_note, inputs=[bpm, bpm_max], outputs=tempo_readout)

    est_inputs = [num_tracks, batch_size, caption_mode, duration, dit_label, steps]
    for ctrl in est_inputs:
        ctrl.change(estimate, inputs=est_inputs, outputs=estimate_out)

    def do_stems(f):
        if not f:
            return "*Drop a file first.*"
        path = f if isinstance(f, str) else getattr(f, "name", None)
        folder, why = separate_stems(path)
        if folder:
            names = ", ".join(sorted(q.stem for q in folder.glob("*.wav")))
            return f"**Done.** `{folder.name}/` - {names}"
        return f"*{why}*"

    stem_btn.click(do_stems, inputs=stem_file, outputs=stem_out)

    RESTORE_TARGETS = [caption, lyrics, instrumental, caption_mode, duration, bpm, bpm_max,
                       key, timesig, seed, dit_label, lm_label, steps, shift, cfg,
                       batch_size, cover_strength, restore_note]

    def restore(f):
        blank = [gr.update()] * (len(RESTORE_TARGETS) - 1)
        if not f:
            return (*blank, "")
        path = f if isinstance(f, str) else getattr(f, "name", None)
        try:
            info = read_sidecar(Path(path).read_text(encoding="utf-8"))
        except Exception as exc:
            return (*blank, f"*Could not read that file: {exc}*")
        if not info:
            return (*blank, "*That does not look like one of this app's .txt files.*")

        def pick(mapping, value, contains=True):
            """Match a stored short name back to its full menu label."""
            if not value:
                return gr.update()
            for label, short in mapping.items():
                if short == value or (contains and value in label):
                    return gr.update(value=label)
            return gr.update()

        def num(key, cast=int, default=gr.update()):
            try:
                return gr.update(value=cast(info[key]))
            except (KeyError, ValueError, TypeError):
                return default

        handling = info.get("handling", "")
        mode = (REWRITTEN if "rewrite" in handling.lower() else
                AS_TYPED if handling else gr.update())
        key_value = info.get("key", "")
        timesig_value = info.get("timesig", "")
        restored = []
        return (
            gr.update(value=info.get("caption", "")) if "caption" in info else gr.update(),
            gr.update(value=info.get("lyrics", "")) if "lyrics" in info else gr.update(),
            gr.update(value=info.get("instrumental", "") == "True"),
            gr.update(value=mode) if isinstance(mode, str) else mode,
            num("duration"),
            num("bpm", default=gr.update(value=0)),   # "auto" in the file -> 0 here
            gr.update(value=0),                      # a .txt records one tempo, not a range
            gr.update(value=key_value) if key_value in KEYS else gr.update(value=KEYS[0]),
            next((gr.update(value=lab) for lab, v in TIME_SIGNATURES.items()
                  if v == timesig_value), gr.update(value=list(TIME_SIGNATURES)[0])),
            num("seed"),
            pick(DIT_MODELS, info.get("dit")),
            pick(LM_MODELS, info.get("lm")),
            num("steps"),
            num("shift", float),
            gr.update(),                             # CFG is reported as forced on turbo
            num("batch_size"),
            num("cover", float),
            f"**Restored from `{Path(path).name}`** - seed {info.get('seed', '?')}, "
            f"{info.get('duration', '?')} s, {info.get('handling', 'unknown handling')}. "
            f"The tempo range is cleared: a .txt records the tempo that was drawn, not the "
            f"range it came from.",
        )

    restore_file.change(restore, inputs=restore_file, outputs=RESTORE_TARGETS)

    check_btn.click(check_installation, outputs=check_out)
    generate_btn.click(generate, inputs=ALL_INPUTS,
                       outputs=[audio_out, files_out, log_out, progress_bar])
    stop_btn.click(STOP.request, inputs=None, outputs=status_out)

if __name__ == "__main__":
    demo.launch(server_port=PORT, css=CSS)
