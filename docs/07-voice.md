# Voice

## Voice mode (talk with Claude)

Full two-way spoken conversation. Available on all plans, on mobile (iOS/Android), desktop and web. Non-English support is in beta — set your voice language in settings (it's separate from display language).

- **Hands-free** (default): Claude listens continuously and replies at natural pauses. Interrupt by just talking.
- **Push-to-talk**: better in noisy rooms or with several voices around.
- Several voices and speaking paces to choose from.
- Claude can **use connected tools in voice mode** — calendar, Gmail, Docs, Slack — so "what's my next meeting and email them I'm running late" works by voice.
- Voice mode works in any conversation in the new Claude experience, including ones where Claude is mid-task. In Claude Code and the Cowork surface, dictation is available but voice mode isn't.
- Fable isn't offered in voice mode at the moment.
- Enterprise owners can disable it via Support.
- Docs: https://support.claude.com/en/articles/11101966

## Dictation (talk *to* Claude, read the reply)

The mic icon transcribes your speech into the message box. Available everywhere including Claude Code. Great for long rambling briefs you'd never type.

## Voice-overs, narration, audio content

Claude doesn't synthesise audio files natively. What works:

1. **Script with Claude, generate elsewhere.** Ask for the script with timing cues, pronunciation hints and SSML-style pauses; feed it to a TTS/voice tool. Media-generation connectors in the directory can create speech, cloned voices, dubbing and music directly from the chat — Claude orchestrates the calls.
2. **Prompt for TTS-friendly text**: *"This will be read aloud by a TTS engine: no ellipses, spell out numbers and abbreviations, short sentences, no markdown."*
3. **Explainer videos**: script + storyboard in Claude, visuals from a Design/Motion artifact or a video connector, narration from a voice connector. Ask Claude to keep the three in sync.
4. **Transcribe & summarise**: attach an audio or video file; Claude reads it in its sandbox and can produce transcripts, chapters, show notes, quotes.
5. **Localisation**: translate a script and ask for a version that keeps the same timing.

## Lesser-known

- Voice mode's tool use means it can *do* things, not just chat: "add milk and eggs to my groceries list" creates one reminder per item on mobile.
- Ask Claude to draft the message you'll say — "give me a 30-second version I can say in the meeting" — then read it in voice mode to hear pacing.
- On a flaky connection, voice degrades first; switch to dictation.
