# VoiceClaw 🎙️

**Real-time voice interface for OpenClaw/Clawdbot** — Enable continuous speech-to-speech conversations with your AI agent while maintaining full session continuity with other channels.

> Talk to your agent naturally. Same brain, same memory, same context as when you text it through Telegram or WhatsApp.

## Why VoiceClaw?

OpenClaw has 80,000+ GitHub stars, but there's no proper real-time voice interface with gateway integration. Voice notes work but they're asynchronous — you can't have a natural back-and-forth conversation.

VoiceClaw bridges that gap:
- **Real-time bidirectional audio** — Talk naturally, interrupt mid-speech
- **Same brain** — Routes through OpenClaw gateway, not direct to LLM
- **Session continuity** — Conversations share context with Telegram/WhatsApp/other channels
- **Tool support** — Agent can make tool calls during conversation
- **Low latency** — Target sub-1 second response time

## Architecture

```
[Browser/Vocalis Frontend]
        ↓ WebSocket (audio)
[Vocalis Backend (FastAPI)]
        ↓ OpenAI-format HTTP/WS
[VoiceClaw Proxy] ← This project
        ↓ OpenClaw Gateway Protocol
[OpenClaw Gateway]
        ↓
[Claude/LLM + Tools + Session]
```

VoiceClaw is a translation layer that makes OpenClaw's gateway speak OpenAI-compatible API, allowing integration with voice frontend projects like [Vocalis](https://github.com/Lex-au/Vocalis).

## Status

🚧 **Early Development** — Currently in Phase 1 (Research)

- [ ] Phase 1: Research OpenClaw gateway protocol
- [ ] Phase 2: Architecture design
- [ ] Phase 3: Implementation
- [ ] Phase 4: Documentation & packaging
- [ ] Phase 5: Release & community

## Getting Started

Documentation coming soon. Star/watch this repo to stay updated.

## Contributing

This is an open-source project. Contributions welcome once we have a stable foundation.

## Related Projects

- [OpenClaw/Clawdbot](https://github.com/clawdbot/clawdbot) — The AI agent platform this integrates with
- [Vocalis](https://github.com/Lex-au/Vocalis) — Voice interface we're building on (React + FastAPI + Faster Whisper)

## License

MIT

---

*Built by Carl Jean-Louis with Atlas*
