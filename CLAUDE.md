# Claude God Code - System Instructions

## Identity & Mission

**Claude God Code** is an elite autonomous multi-agent coding framework engineered for **zero-bug production** and **high-performance architecture**. The system orchestrates AI agents to autonomously plan, build, validate, and integrate software with surgical precision.

**Core Principles:**
- Zero tolerance for production bugs
- Performance-first architecture decisions
- Minimal human intervention required
- Self-healing and self-validating systems

---

## Agentic Workflow Loop

### Phase Execution Model

```
┌─────────────────────────────────────────────────────────────────┐
│                    CLAUDE GOD CODE WORKFLOW                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  [1] DISCOVERY ──► Analyze project DNA (deterministic)         │
│         │                                                       │
│         ▼                                                       │
│  [2] REQUIREMENTS ──► Gather specs via agent dialogue          │
│         │                                                       │
│         ▼                                                       │
│  [3] CONTEXT ──► Map relevant files & dependencies             │
│         │                                                       │
│         ▼                                                       │
│  [4] SPECIFICATION ──► Generate implementation spec            │
│         │                                                       │
│         ▼                                                       │
│  [5] PLANNING ──► Break into phases → chunks → subtasks        │
│         │                                                       │
│         ▼                                                       │
│  [6] VALIDATION ──► Contract verification (deterministic)      │
│         │                                                       │
│         ▼                                                       │
│  [7] BUILD ──► Autonomous implementation in isolated worktree  │
│         │                                                       │
│         ▼                                                       │
│  [8] QA LOOP ──► Self-validating review cycle (max 50 iter)    │
│         │                                                       │
│         ▼                                                       │
│  [9] MERGE ──► AI-powered conflict resolution & integration    │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Execution Rules

1. **Isolation First**: Every spec gets its own git worktree and branch
2. **Atomic Progress**: Commit after each subtask completion
3. **Self-Correction**: QA loop runs until approval or human escalation
4. **Memory Persistence**: Learnings stored in knowledge graph for future sessions

---

## TypeScript Standards

### Naming Conventions

| Element | Convention | Example |
|---------|------------|---------|
| Files | kebab-case | `task-runner.ts` |
| Classes | PascalCase | `TaskRunner` |
| Interfaces | PascalCase with I prefix (optional) | `ITaskRunner` or `TaskRunner` |
| Types | PascalCase | `TaskConfig` |
| Functions | camelCase | `runTask()` |
| Constants | SCREAMING_SNAKE_CASE | `MAX_RETRIES` |
| Private members | _prefixed camelCase | `_internalState` |
| Boolean vars | is/has/should prefix | `isRunning`, `hasError` |

### Code Structure Rules

```typescript
// Imports: grouped and ordered
import { external } from 'external-package';     // 1. External packages

import { internal } from '@/core/internal';       // 2. Internal aliases
import { shared } from '@shared/utils';           // 3. Shared modules

import { local } from './local-module';           // 4. Local imports
import type { LocalType } from './types';         // 5. Type imports last

// Interface/Type definitions at top of file
interface TaskConfig {
  readonly id: string;
  name: string;
  timeout?: number;
}

// Class implementation
export class TaskRunner {
  private readonly _config: TaskConfig;

  constructor(config: TaskConfig) {
    this._config = config;
  }

  async run(): Promise<TaskResult> {
    // Implementation
  }
}
```

### Error Handling Pattern

```typescript
// Custom error types for domain-specific errors
class TaskExecutionError extends Error {
  constructor(
    message: string,
    public readonly taskId: string,
    public readonly cause?: Error
  ) {
    super(message);
    this.name = 'TaskExecutionError';
  }
}

// Result pattern for operations that can fail
type Result<T, E = Error> =
  | { success: true; data: T }
  | { success: false; error: E };

// Usage
async function executeTask(id: string): Promise<Result<TaskOutput>> {
  try {
    const output = await runTask(id);
    return { success: true, data: output };
  } catch (error) {
    return { success: false, error: new TaskExecutionError('Failed', id, error) };
  }
}
```

---

## Python Standards

### Naming Conventions

| Element | Convention | Example |
|---------|------------|---------|
| Files | snake_case | `task_runner.py` |
| Classes | PascalCase | `TaskRunner` |
| Functions | snake_case | `run_task()` |
| Constants | SCREAMING_SNAKE_CASE | `MAX_RETRIES` |
| Private | _prefixed | `_internal_method()` |
| Module-private | __prefixed | `__module_only()` |

### Code Structure

```python
"""Module docstring: Brief description of module purpose."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .types import TaskConfig

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class TaskResult:
    """Immutable result of task execution."""

    task_id: str
    success: bool
    output: str | None = None
    error: str | None = None


class TaskRunner:
    """Orchestrates task execution with retry logic."""

    def __init__(self, config: TaskConfig) -> None:
        self._config = config
        self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    async def run(self) -> TaskResult:
        """Execute the configured task."""
        # Implementation
```

---

## Architecture Patterns

### Layered Architecture

```
┌─────────────────────────────────────────┐
│           PRESENTATION LAYER            │
│    (Electron UI / CLI Interface)        │
├─────────────────────────────────────────┤
│           APPLICATION LAYER             │
│    (Orchestration / Use Cases)          │
├─────────────────────────────────────────┤
│            DOMAIN LAYER                 │
│    (Business Logic / Agents)            │
├─────────────────────────────────────────┤
│         INFRASTRUCTURE LAYER            │
│    (Git / Memory / Integrations)        │
└─────────────────────────────────────────┘
```

### Module Organization

```
apps/
├── backend/
│   ├── core/           # Foundation (client, auth, workspace)
│   ├── agents/         # Agent implementations
│   ├── spec/           # Spec lifecycle
│   ├── qa/             # Quality assurance
│   ├── memory/         # Knowledge persistence
│   ├── integrations/   # External services
│   └── cli/            # Command interface
│
└── frontend/
    ├── src/main/       # Electron main process
    ├── src/renderer/   # React UI
    └── src/shared/     # Shared utilities
```

---

## Concurrency Model

### Git Worktree Isolation

```
.claude-god-code/worktrees/specs/
├── spec-001/           # Isolated worktree
│   └── branch: claude-god-code/spec-001
├── spec-002/
│   └── branch: claude-god-code/spec-002
└── spec-003/
    └── branch: claude-god-code/spec-003
```

**Rules:**
- 1:1:1 mapping: spec → worktree → branch
- No cross-worktree file access
- Merge only through orchestrator
- Automatic cleanup on spec completion

### Parallel Execution

- Up to 12 concurrent agent terminals
- Independent Claude Code CLI connections per agent
- Rate limit monitoring with automatic throttling
- Session state isolation

---

## Memory System

### Three-Layer Memory Architecture

```
┌────────────────────────────────────────┐
│     LAYER 3: KNOWLEDGE GRAPH           │
│   (Graphiti/LadybugDB - Long-term)     │
├────────────────────────────────────────┤
│     LAYER 2: SESSION MEMORY            │
│   (File-based - Per-session)           │
├────────────────────────────────────────┤
│     LAYER 1: CONTEXT CACHE             │
│   (In-memory - Active session)         │
└────────────────────────────────────────┘
```

### Episode Types

| Type | Purpose |
|------|---------|
| `SESSION_INSIGHT` | Learnings from build sessions |
| `CODEBASE_DISCOVERY` | Project structure findings |
| `PATTERN` | Reusable code patterns |
| `GOTCHA` | Known issues and workarounds |
| `TASK_OUTCOME` | Build success/failure data |
| `QA_RESULT` | Quality assessment findings |

---

## Quality Assurance Loop

### Self-Validating Cycle

```
       ┌──────────────┐
       │    BUILD     │
       └──────┬───────┘
              │
              ▼
       ┌──────────────┐
       │  QA REVIEW   │◄─────────────┐
       └──────┬───────┘              │
              │                      │
         ┌────┴────┐                 │
         │         │                 │
    APPROVED    REJECTED             │
         │         │                 │
         ▼         ▼                 │
    ┌────────┐ ┌──────────┐          │
    │ MERGE  │ │  FIXER   │──────────┘
    └────────┘ └──────────┘
```

**Rules:**
- Maximum 50 QA iterations
- Recurring issue detection (3+ same issue → human escalation)
- Issue similarity threshold: 0.85
- Automatic rollback on critical failures

---

## Security Model

### Zero-Trust Architecture

1. **Command Allowlisting**: Stack-aware command validation
2. **Filesystem Sandboxing**: Operations limited to project scope
3. **Credential Isolation**: Platform-native secure storage
4. **Audit Logging**: All agent actions logged with correlation IDs

### Allowed Commands by Stack

| Stack | Permitted Commands |
|-------|-------------------|
| Node.js | npm, npx, yarn, pnpm, node |
| Python | python, pip, uv, pytest |
| .NET | dotnet, nuget |
| Rust | cargo, rustc |
| Go | go |
| General | git, gh, curl (limited) |

---

## Logging Standards

### Structured JSON Format

```json
{
  "timestamp": "2025-01-15T10:30:00Z",
  "level": "INFO",
  "correlation_id": "spec-001-build-abc123",
  "component": "qa.reviewer",
  "message": "QA review completed",
  "context": {
    "spec_id": "001",
    "iteration": 3,
    "result": "approved"
  }
}
```

### Log Levels

| Level | Usage |
|-------|-------|
| `ERROR` | Failures requiring attention |
| `WARN` | Recoverable issues |
| `INFO` | Key workflow events |
| `DEBUG` | Detailed execution data |
| `TRACE` | Verbose diagnostic info |

---

## Commit Standards

### Message Format

```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

### Types

| Type | Description |
|------|-------------|
| `feat` | New feature |
| `fix` | Bug fix |
| `refactor` | Code restructuring |
| `perf` | Performance improvement |
| `test` | Test addition/modification |
| `docs` | Documentation only |
| `chore` | Build/tooling changes |

### Examples

```
feat(agents): implement enhanced error recovery in coder agent

- Add circuit breaker pattern for external API calls
- Implement exponential backoff with jitter
- Add health check endpoint for agent status

Closes #123
```

---

## Performance Guidelines

### Startup Optimization

- Lazy import heavy dependencies
- Pre-warm tool caches
- Parallel initialization where possible
- Dependency graph analysis for optimal load order

### Runtime Optimization

- Connection pooling for API clients
- Batch operations where applicable
- Stream large file operations
- Cache frequently accessed data

### Memory Management

- Limit concurrent worktrees based on available RAM
- Cleanup completed worktrees promptly
- Use generators for large datasets
- Implement LRU caches with size limits

---

## Error Recovery

### Circuit Breaker Pattern

```
CLOSED ──[failure]──► OPEN ──[timeout]──► HALF-OPEN
   ▲                                          │
   └─────────[success]────────────────────────┘
```

**Thresholds:**
- Open after: 5 consecutive failures
- Half-open timeout: 30 seconds
- Close after: 3 consecutive successes

### Retry Strategy

```
Attempt 1: Immediate
Attempt 2: 2 seconds delay
Attempt 3: 4 seconds delay
Attempt 4: 8 seconds delay (max)
```

**Retryable Errors:**
- Network timeouts
- 5xx HTTP responses
- Rate limit (429)

**Non-Retryable:**
- 401 Unauthorized
- 403 Forbidden
- 404 Not Found
- 400 Bad Request

---

## Agent Communication Protocol

### Agent Autonomy Levels

| Level | Description | Human Intervention |
|-------|-------------|-------------------|
| 1 | Full autonomy | None required |
| 2 | Guided | Checkpoints only |
| 3 | Supervised | Per-phase approval |
| 4 | Manual | Per-action approval |

### Pause/Resume Protocol

- Create `PAUSE` file in worktree root to pause agent
- Agent completes current subtask then stops
- Remove `PAUSE` file to resume on next run
- `ABORT` file triggers immediate stop with state save

---

## Development Workflow

### Local Development

```bash
# Install dependencies
npm run install:all

# Start development mode
npm run dev

# Run tests
npm test
npm run test:backend
npm run test:e2e

# Build for production
npm run build
npm run package
```

### Spec Operations

```bash
# Create new spec
python spec_runner.py --interactive

# Run build
python run.py --spec <spec-id>

# QA validation
python run.py --spec <spec-id> --qa

# Merge to main
python run.py --spec <spec-id> --merge
```

---

## Skills System

### Overview

The Skills System provides modular, domain-specific protocols that enhance agent capabilities. Skills are automatically discovered and applied based on task context.

### Architecture

```
apps/backend/skills/
├── __init__.py          # Skills module exports
├── loader.py            # SkillLoader and SkillRegistry
└── frontend_design/     # Professional Frontend Design skill
    ├── __init__.py
    ├── SKILL.md         # Skill definition and standards
    ├── EXAMPLES.md      # Before/After code examples
    └── PROMPT.md        # System prompt injection
```

### Active Skills

#### Professional Frontend Design (`frontend_design`)

**Applicability**: Automatically applied to frontend tasks

**Detection Triggers**:
- Task keywords: `frontend`, `ui`, `component`, `react`, `vue`, `css`, `tailwind`, `button`, `form`, `modal`, `responsive`, `design`
- File extensions: `.tsx`, `.jsx`, `.vue`, `.svelte`, `.css`, `.scss`, `.html`

**Standards Enforced**:
1. **Aesthetic Excellence**: Typography, color systems, motion, spatial composition
2. **Accessibility (A11Y)**: WCAG AA compliance, keyboard navigation, screen reader support, focus management
3. **Tailwind Best Practices**: Utility organization, responsive prefixes, design tokens
4. **Responsive Design**: Mobile-first approach, touch targets, breakpoint strategy
5. **Performance**: Core Web Vitals targets (LCP < 2.5s, FID < 100ms, CLS < 0.1)

**Integration**:
```python
from skills import SkillRegistry

# Automatic discovery
registry = SkillRegistry()
skills = registry.get_applicable_skills(task_description, file_paths)

# Manual loading
skill = registry.get_skill("frontend_design")
prompt = skill.get_full_prompt()
```

### Agent Integration

Agents automatically load applicable skills via `BaseAgent`:

```python
class CoderAgent(BaseAgent):
    async def run(self):
        # Skills are auto-loaded based on task
        self.load_applicable_skills(task_description, file_paths)

        # Get combined prompt for all loaded skills
        skills_prompt = self.get_skills_prompt()
```

### Spec Pipeline Integration

During the **Specification Writing** phase, the pipeline:
1. Discovers applicable skills based on task description and file context
2. Records skills in `skills.json` within the spec directory
3. Includes skill information in the generated `spec.md`

---

*Claude God Code - Autonomous Excellence*
