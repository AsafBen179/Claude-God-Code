# Claude God Code

An elite autonomous multi-agent coding framework engineered for **zero-bug production** and **high-performance architecture**.

## Overview

Claude God Code orchestrates AI agents to autonomously plan, build, validate, and integrate software with surgical precision. The system leverages:

- **Isolated Execution**: Per-spec git worktrees for parallel, contamination-free development
- **Self-Validating QA**: Automated review loops with intelligent escalation
- **Persistent Memory**: Knowledge graph for cross-session learning
- **Multi-Provider Support**: Works with OpenAI, Anthropic, Google, and Ollama

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    CLAUDE GOD CODE WORKFLOW                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  DISCOVERY → REQUIREMENTS → CONTEXT → SPEC → PLANNING           │
│                                                                 │
│      ↓                                                          │
│                                                                 │
│  VALIDATION → BUILD → QA LOOP → MERGE                           │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## Project Structure

```
claude-god-code/
├── apps/
│   ├── backend/              # Python backend
│   │   ├── core/             # Foundation (client, auth, workspace)
│   │   ├── agents/           # Agent implementations
│   │   ├── spec/             # Spec lifecycle
│   │   ├── qa/               # Quality assurance
│   │   ├── memory/           # Knowledge persistence
│   │   ├── integrations/     # External services
│   │   ├── cli/              # Command interface
│   │   ├── prompts/          # System prompts
│   │   └── security/         # Security validation
│   │
│   └── frontend/             # Electron + React desktop app
│       ├── src/main/         # Electron main process
│       ├── src/renderer/     # React UI
│       └── src/shared/       # Shared utilities
│
├── docs/                     # Documentation
├── tests/                    # Test suite
├── scripts/                  # Build and utility scripts
├── CLAUDE.md                 # System instructions
└── README.md                 # This file
```

## Tech Stack

### Backend
- **Runtime**: Python 3.10+ (3.12+ for Graphiti)
- **AI SDK**: Claude Agent SDK
- **Memory**: Graphiti / LadybugDB
- **Package Manager**: uv (recommended)

### Frontend
- **Framework**: Electron 39 + React 19
- **Build Tool**: Vite 7
- **Language**: TypeScript 5.9
- **Styling**: Tailwind CSS v4
- **State**: Zustand
- **Terminal**: xterm.js

## Getting Started

### Prerequisites

- Node.js 18+
- Python 3.10+
- Git

### Installation

```bash
# Clone the repository
git clone https://github.com/AsafBen179/Claude-God-Code.git
cd Claude-God-Code

# Install dependencies
npm run install:all

# Start development mode
npm run dev
```

### Quick Start

```bash
# Create a new spec
python apps/backend/spec_runner.py --interactive

# Run autonomous build
python apps/backend/run.py --spec <spec-id>

# Run QA validation
python apps/backend/run.py --spec <spec-id> --qa

# Merge to main branch
python apps/backend/run.py --spec <spec-id> --merge
```

## Key Features

### Workspace Isolation
Each specification runs in an isolated git worktree, preventing cross-contamination between parallel tasks.

### Self-Validating QA Loop
Automatic code review with up to 50 iterations. Recurring issues (3+) escalate to human review.

### Memory Persistence
Three-layer memory system:
1. **Context Cache**: In-memory for active session
2. **Session Memory**: File-based per-session
3. **Knowledge Graph**: Long-term learning with Graphiti

### Security Model
- Zero-trust command execution
- Stack-aware allowlisting
- Platform-native credential storage
- Full audit logging

## Development

```bash
# Run tests
npm test
npm run test:backend
npm run test:e2e

# Build for production
npm run build

# Package for distribution
npm run package
```

## Contributing

See [CONTRIBUTING.md](docs/CONTRIBUTING.md) for guidelines.

## License

MIT License - See [LICENSE](LICENSE) for details.

---

*Claude God Code - Autonomous Excellence*
