# Installing this, step by step

**This guide assumes you have never opened Terminal in your life.** Every
command is written out in full. After each one you press Return and you wait
until the prompt comes back before typing the next. If you have installed
developer tools before, skip to [the short version](#the-short-version) at the
bottom.

Total time: about an hour, of which fifty minutes is downloading while you do
something else.

---

## 🍏 Before you start: does your Mac qualify?

**It must be an Apple Silicon Mac.** M1, M2, M3, M4, any of them, including the
Pro / Max / Ultra variants. An older Intel Mac cannot run this at all — MLX is
Apple's own framework and it only exists on Apple's own chips.

To check: **Apple menu ( ) → About This Mac**. You are looking for a line
that says **Chip: Apple M-something**. If it says *Processor: Intel*, stop
here.

**Memory.** 16 GB works. 24 GB or more is comfortable. On 16 GB, choose the
0.6B language model and keep tracks short — the app explains where.

**Disk space.** You need about **25 GB free**, and you want more than that
spare, because a disk that fills up in the middle of a 10 GB download gives you
a corrupted download rather than an error message.

To check: **Apple menu → About This Mac → More Info → Storage**.

**macOS.** Sonoma (14) or later is the safe answer.

---

## 0️⃣ Opening Terminal, and what it is

Terminal is an app that comes with every Mac. It lets you type instructions
instead of clicking them. It looks alarming and it is not.

Press **Command-Space**, type `terminal`, press **Return**.

A window opens with a line of text ending in `%` or `$`. That is the prompt: it
means "ready, type something".

**How to use this guide:** copy one block of text, click in the Terminal window,
paste with **Command-V**, press **Return**. Then wait. Some steps take fifteen
minutes and show nothing while they work. A step is finished when the `%`
prompt comes back on its own.

Two things worth knowing before you are surprised by them:

- **When you type a password, nothing appears.** No dots, no stars, nothing at
  all. That is deliberate. Type it and press Return.
- **You can always close the window and start again.** Nothing here can damage
  your Mac.

---

## 1️⃣ Apple's developer tools

The `git` command, which downloads code, is not on a fresh Mac until you ask
for it. Type this:

```
xcode-select --install
```

**What happens:** either a window appears offering to install "command line
developer tools" — click **Install**, agree, wait a few minutes — or Terminal
answers `command line tools are already installed`, which is equally fine.

---

## 2️⃣ uv, which manages Python for you

ACE-Step uses a tool called **uv** to build its own private Python environment.
That word "private" is the point: nothing here touches the Python your Mac
already has, and uninstalling later means deleting one folder.

```
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**Then close the Terminal window completely and open a new one** (Command-Q,
then Command-Space, `terminal`, Return). This is not optional — the new command
only becomes visible to a freshly opened window.

Check it worked:

```
uv --version
```

You should see something like `uv 0.12.14`. The exact number does not matter.

If instead you see `command not found: uv`, the most likely reason is that you
did not open a *new* window. Try that first.

---

## 3️⃣ Downloading ACE-Step itself

This is the model's own project, not mine. Three commands:

```
mkdir -p ~/AceStep
```

```
cd ~/AceStep
```

```
git clone https://github.com/ace-step/ACE-Step-1.5.git
```

**What happens:** a few minutes of progress percentages. The `~` means your
home folder, so this creates **AceStep** inside it, with **ACE-Step-1.5**
inside that. You can see it in Finder: **Go menu → Home**.

---

## 4️⃣ Building the environment

```
cd ~/AceStep/ACE-Step-1.5
```

```
uv sync
```

**This is the long one: ten to twenty-five minutes.** It downloads PyTorch,
MLX, Gradio and about two hundred other pieces, and builds a private Python
3.12 inside a hidden folder called `.venv`.

It prints a great deal. Lines saying *Building*, *Downloading*, *Resolving* are
normal. The step has finished when the prompt comes back and the last line
starts with `Installed` or `Audited`.

**If it fails**, the useful information is in the *last* few lines, not the
first. The commonest cause is a dropped connection: run `uv sync` again, it
picks up where it left off.

---

## 5️⃣ Downloading this front-end

Two ways. Pick one.

**The simple way, no Terminal:** at the top of this project's GitHub page,
click the green **Code** button, then **Download ZIP**. Double-click the
downloaded ZIP to unpack it. Drag the resulting folder wherever you like —
Documents, Desktop, an external drive. It does not matter where; the launcher
works out its own location.

**The Terminal way**, which makes updating easier later:

```
cd ~/AceStep
```

```
git clone https://github.com/Quick-Eyed-Sky/acestep-mac-mlx.git
```

---

## 6️⃣ Letting the launcher launch

**If you used the ZIP, this step is required.** A ZIP file forgets which files
are allowed to run, so the launcher arrives inert and double-clicking it opens
it in a text editor instead of starting anything.

Type `chmod +x ` — **including the space at the end** — then drag
`launch_acestep.command` from the Finder window into the Terminal window. macOS
fills in its location for you. Then press Return.

The whole line ends up looking something like:

```
chmod +x /Users/yourname/Documents/acestep-mac-mlx/launch_acestep.command
```

Nothing is printed. That means it worked.

---

## 7️⃣ The first launch, and Apple's warning

Double-click **launch_acestep.command**.

**The first time, macOS will refuse**, with a message about an unidentified
developer. This is expected and it happens to every downloaded script that is
not signed with a paid Apple developer certificate. To get past it:

**Right-click** (or Control-click) **launch_acestep.command → Open**, then
**Open** again in the dialog that appears. You only ever do this once.

If the right-click route does not offer *Open*: go to **System Settings →
Privacy & Security**, scroll down, and there will be a line about
`launch_acestep.command` being blocked, with an **Open Anyway** button.

**What you should then see:** a Terminal window that fills with start-up
messages, and after a few seconds your browser opens at
`http://127.0.0.1:7873`.

That address is your own Mac talking to itself. Nothing is being sent anywhere.

---

## 8️⃣ The first render, which is slow, once

Type something in the caption box — `slow piano, rain, night` will do — and
click **Generate**.

**The first render downloads the model weights: ten to sixteen gigabytes.**
Nothing appears to happen for a long time. The Terminal window is where the
progress actually shows, which is why the launcher tells you to keep it open.

This happens once. The weights land in `~/AceStep/checkpoints` and are reused
afterwards. From then on a render takes a couple of minutes.

**If you want to know that things are healthy before committing to that**, the
app has a **Check the installation** button that reports what it can find and
what it cannot.

---

## ➕ Optional extras

Neither is required. The app works without both and says so where it matters.

### 🎚️ ffmpeg — for MP3 and FLAC copies

Without it you still get WAV, which is the real output. ffmpeg only makes the
extra copies.

It comes from **Homebrew**, a package manager for Mac. If you do not have
Homebrew:

```
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

It asks for your Mac password (remember: nothing appears as you type it) and
takes a few minutes. It also prints two or three commands at the end under a
heading like *Next steps* — **run those**, they are what makes `brew` visible.

Then:

```
brew install ffmpeg
```

### 🥁 Demucs — for splitting a finished track into stems

Drums, bass, vocals and everything else, as four separate files.

Demucs needs its own version of PyTorch, different from ACE-Step's. Installing
it alongside would break ACE-Step. So it gets a separate environment of its
own, which is what these two commands do:

```
uv venv ~/AceStep/demucs-venv --python 3.12
```

```
uv pip install --python ~/AceStep/demucs-venv/bin/python demucs torch torchaudio numpy soundfile
```

That is about 3 GB and five minutes. The app finds it automatically and the
stems checkbox stops being greyed out.

*(Tested with demucs 4.1.0, torch 2.14.0, torchaudio 2.11.0, numpy 2.5.3.)*

---

## 🆘 If something goes wrong

| What you see | What it means |
|---|---|
| `command not found: uv` | Step 2️⃣ did not finish, or you did not open a **new** Terminal window afterwards. |
| `Can't find ACE-Step's virtual environment` | Step 4️⃣ did not finish. Go back to `~/AceStep/ACE-Step-1.5` and run `uv sync` again, then read the **last** error line. |
| Double-clicking the launcher opens a text editor | Step 6️⃣. The executable bit was lost in the ZIP. |
| `unidentified developer` | Step 7️⃣. Right-click → Open. |
| An out-of-memory error during a render | Set the language model to **0.6B**, the audio model to **Turbo**, and shorten the duration. |
| `Abort trap: 6` | A known clash between MLX and PyTorch-MPS on some machines. Run it again. If it happens every time, untick **Run the audio model on MLX as well** — slower, but it works. |
| Anything else | Click **Check the installation** and paste its report into an issue. It contains everything needed to answer you. |

---

## 💾 Installing somewhere other than the internal disk

Everything above puts ACE-Step in your home folder. To put it on an external
drive instead, set two environment variables before launching:

```
export ACESTEP_REPO="/Volumes/YourDrive/AceStep/ACE-Step-1.5"
export ACESTEP_CHECKPOINTS_DIR="/Volumes/YourDrive/AceStep/checkpoints"
```

**One warning from experience: the drive must be formatted APFS or Mac OS
Extended (HFS+).** A Python environment does not work on exFAT, which is what
most drives are formatted as when you buy them.

And check the free space honestly first. An external drive that is 99% full is
worse than an internal disk that is 20% full, however large it is.

---

## 🗑️ Removing all of this

Delete the folder `~/AceStep` and the folder you unzipped this into. That is
everything: no system files are touched, nothing is installed globally except
`uv` itself, which lives in `~/.local/bin` and can be deleted too.

---

## ⚡ The short version

For people who already have `git`, `uv` and a Terminal habit:

```
mkdir -p ~/AceStep && cd ~/AceStep
git clone https://github.com/ace-step/ACE-Step-1.5.git
cd ACE-Step-1.5 && uv sync
cd ~/AceStep && git clone https://github.com/Quick-Eyed-Sky/acestep-mac-mlx.git
chmod +x acestep-mac-mlx/launch_acestep.command
open acestep-mac-mlx/launch_acestep.command
```

Optional:

```
brew install ffmpeg
uv venv ~/AceStep/demucs-venv --python 3.12
uv pip install --python ~/AceStep/demucs-venv/bin/python demucs torch torchaudio numpy soundfile
```

The launcher honours `ACESTEP_REPO`, `ACESTEP_CHECKPOINTS_DIR`, `ACESTEP_PORT`
and `ACESTEP_DEMUCS_PYTHON`, so nothing has to live where this guide puts it.
