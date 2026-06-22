# Day 11 Lab Guide
## eComBot v8 — Voice Interface

---

### Module alignment
This session adds a real-time voice pipeline: microphone → faster-whisper STT → Orchestrator → Piper TTS → speaker. The multi-agent routing from Day 09 must work identically whether the input arrives as text or speech. A mic button is added to the Chainlit UI with live transcription.

---

### Starting state
- eComBot v7 is working with the Chainlit UI, streaming, and rich components.
- Orchestrator routes correctly between Support and Sales agents.
- No voice pipeline exists yet.

### Target state
- `src/voice/pipeline.py` implements the mic → STT → agent → TTS loop.
- faster-whisper transcribes audio in real time.
- Piper TTS reads the agent's reply back.
- Chainlit UI has a mic button that activates voice input with live transcription display.
- At least 2 languages tested (English + Hindi or French).
- Round-trip latency measured.

### New dependencies

```
faster-whisper
piper-tts
sounddevice
numpy
```

Add to `requirements.txt` and install. Note: Piper requires downloading a voice model file separately.

### Repository addition

```text
ecombot/
└── src/
    └── voice/
        ├── __init__.py
        └── pipeline.py
```

---

## Task 1 — STT with faster-whisper

Create `src/voice/pipeline.py` with a function to transcribe an audio buffer:

```python
from faster_whisper import WhisperModel

_model = None

def get_stt_model(model_size: str = "small"):
    global _model
    if _model is None:
        _model = WhisperModel(model_size, device="cpu", compute_type="int8")
    return _model

def transcribe(audio_path: str, language: str = None) -> str:
    """Transcribe an audio file. Returns the transcript text."""
    model = get_stt_model()
    segments, info = model.transcribe(audio_path, language=language)
    text = " ".join(s.text for s in segments).strip()
    return text
```

Download the `small` model on first run (faster-whisper handles this automatically).

**Checkpoint:** `transcribe("test.wav")` returns readable English text from a short audio clip.

---

## Task 2 — TTS with Piper

Add TTS to `src/voice/pipeline.py`:

```python
import subprocess
import tempfile
import os

PIPER_MODEL = os.getenv("PIPER_MODEL", "en_US-lessac-medium.onnx")
PIPER_PATH  = os.getenv("PIPER_PATH",  "piper")  # or full path to piper binary

def speak(text: str, output_path: str = None) -> str:
    """Convert text to speech using Piper. Returns path to the output WAV file."""
    if output_path is None:
        output_path = tempfile.mktemp(suffix=".wav")
    subprocess.run(
        [PIPER_PATH, "--model", PIPER_MODEL, "--output_file", output_path],
        input=text.encode(),
        check=True,
    )
    return output_path
```

Add to `.env`:
```
PIPER_MODEL=en_US-lessac-medium.onnx
PIPER_PATH=piper
```

Download the Piper binary and voice model from the Piper releases page and place them in your project root or add to PATH.

**Checkpoint:** `speak("Hello, how can I help you?")` creates a playable WAV file.

---

## Task 3 — Microphone capture

Add a function to capture audio from the microphone:

```python
import sounddevice as sd
import numpy as np
import tempfile
import scipy.io.wavfile as wav

SAMPLE_RATE = 16000

def record_audio(duration_seconds: int = 5) -> str:
    """Record from microphone for given duration. Returns path to WAV file."""
    print(f"Recording for {duration_seconds}s...")
    audio = sd.rec(
        int(duration_seconds * SAMPLE_RATE),
        samplerate=SAMPLE_RATE,
        channels=1,
        dtype="int16",
    )
    sd.wait()
    path = tempfile.mktemp(suffix=".wav")
    wav.write(path, SAMPLE_RATE, audio)
    return path
```

**Checkpoint:** `record_audio(3)` captures 3 seconds and saves a WAV file that plays back correctly.

---

## Task 4 — Full voice loop

Add the end-to-end pipeline function:

```python
import time

async def voice_turn(agent_runner, session_id: str, language: str = "en") -> dict:
    """One full voice turn: record → STT → agent → TTS. Returns timing and transcript."""
    t0 = time.time()

    audio_path = record_audio(duration_seconds=5)
    transcript = transcribe(audio_path, language=language)
    print(f"STT: {transcript}")

    t_stt = time.time()

    from google.genai.types import Content, Part
    response_text = ""
    async for event in agent_runner.run_async(
        user_id="voice_user",
        session_id=session_id,
        new_message=Content(role="user", parts=[Part(text=transcript)]),
    ):
        if event.is_final_response() and event.content and event.content.parts:
            response_text = event.content.parts[0].text or ""

    t_agent = time.time()

    output_wav = speak(response_text)

    t_tts = time.time()

    # Play the output
    import sounddevice as sd
    import scipy.io.wavfile as wav_io
    rate, data = wav_io.read(output_wav)
    sd.play(data, rate)
    sd.wait()

    return {
        "transcript":    transcript,
        "response":      response_text,
        "stt_ms":        int((t_stt - t0) * 1000),
        "agent_ms":      int((t_agent - t_stt) * 1000),
        "tts_ms":        int((t_tts - t_agent) * 1000),
        "total_ms":      int((t_tts - t0) * 1000),
    }
```

**Checkpoint:** Running one voice turn end-to-end produces a spoken reply. Timing dict shows round-trip latency.

---

## Task 5 — Mic button in Chainlit UI

Add a voice input button to `src/ui/app.py`. Chainlit supports audio input via `cl.Audio`:

```python
@cl.on_audio_chunk
async def on_audio_chunk(chunk: cl.InputAudioChunk):
    # Accumulate audio chunks
    audio_buffer = cl.user_session.get("audio_buffer", b"")
    audio_buffer += chunk.data
    cl.user_session.set("audio_buffer", audio_buffer)

@cl.on_audio_end
async def on_audio_end(elements):
    import tempfile
    audio_buffer = cl.user_session.get("audio_buffer", b"")
    cl.user_session.set("audio_buffer", b"")

    # Save to temp WAV
    wav_path = tempfile.mktemp(suffix=".wav")
    with open(wav_path, "wb") as f:
        f.write(audio_buffer)

    # Transcribe
    from src.voice.pipeline import transcribe
    transcript = transcribe(wav_path)

    # Show transcript
    await cl.Message(content=f"[Voice input]: {transcript}").send()

    # Run through agent (same as text path)
    await on_message(cl.Message(content=transcript))
```

**Checkpoint:** Clicking the mic button in Chainlit, speaking, and releasing triggers the full agent flow and displays the transcript.

---

## Task 6 — Multi-language test

Test the pipeline with at least two languages:

**English:**
- Say: `"Where is my order ORD-001?"`
- Expected: Agent calls tool; reads status back in English.

**Hindi:**
- Set `language="hi"` in `transcribe()`.
- Say: `"मेरा ऑर्डर कहाँ है?"` (Where is my order?)
- Expected: STT transcribes Hindi; agent responds.

Record latency for both:

| Language | STT (ms) | Agent (ms) | TTS (ms) | Total (ms) |
|----------|----------|------------|----------|------------|
| English  |          |            |          |            |
| Hindi    |          |            |          |            |

**Checkpoint:** Both languages produce a coherent agent response. Total latency under 10 seconds for a 5-second clip on CPU.

---

## Task 7 — Interruption handling

Test what happens when the recording is stopped early (< 1 second of audio):
- `transcribe()` should return an empty string or a short snippet.
- The agent should ask the customer to repeat: `"I didn't catch that. Could you please repeat?"`
- No exception should reach the user.

Add a guard in `on_audio_end`:

```python
if not transcript or len(transcript.strip()) < 3:
    await cl.Message(content="I didn't catch that. Could you please try again?").send()
    return
```

**Checkpoint:** 0-second recording returns a polite retry message, not an error.

---

## Verification checklist
- [ ] `src/voice/pipeline.py` implements `transcribe()`, `speak()`, and `record_audio()`.
- [ ] End-to-end voice turn works: mic → STT → agent → TTS → speaker.
- [ ] Chainlit mic button captures audio and routes through the agent.
- [ ] Transcript displayed in Chainlit alongside the agent reply.
- [ ] English voice input tested and working.
- [ ] Second language (Hindi or French) tested and working.
- [ ] Round-trip latency measured and recorded.
- [ ] Short/empty audio handled gracefully with retry message.
