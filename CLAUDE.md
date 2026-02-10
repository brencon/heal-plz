# Project Instructions for Claude Code

> This file is automatically loaded into context when Claude Code starts.
> It serves as the primary interface for providing Claude with project-specific knowledge.

## Project Overview

<!--
Describe your project here. Include:
- What the project does
- Core technologies and frameworks
- Target audience/users
-->

heal-plz is a Self-healing coding platform with enterprise response management and resolution.

## Architecture

<!--
Describe the high-level architecture:
- System components
- Data flow
- Key design decisions
-->

```
[Add architecture diagram or description here]
```

## Directory Structure

```
├── .claude/              # Claude Code configuration
│   ├── commands/         # Custom slash commands
│   ├── settings.json     # Project-level settings (version controlled)
│   └── settings.local.json # Local settings (gitignored)
├── .github/
│   └── workflows/        # GitHub Actions (including Claude code review)
├── docs/                 # Project documentation
│   └── references/       # External references and research
├── src/                  # Source code
│   └── [module]/CLAUDE.md  # Optional: module-specific instructions
├── tests/                # Test files
└── CLAUDE.md            # This file - Claude's primary instructions
```

> **Note**: CLAUDE.md files are hierarchical. You can place them in subdirectories
> for module-specific instructions. The most specific (most nested) file takes
> priority when Claude is working in that directory.

## Development Commands

<!--
Document the essential commands Claude needs to know.
These are the commands Claude will use frequently.
-->

### Build & Run
```bash
# Build the project
[BUILD_COMMAND]

# Run the project
[RUN_COMMAND]

# Run in development mode
[DEV_COMMAND]
```

### Testing
```bash
# Run all tests
[TEST_COMMAND]

# Run tests with coverage
[COVERAGE_COMMAND]

# Run specific test file
[SPECIFIC_TEST_COMMAND]
```

### Linting & Formatting
```bash
# Lint the codebase
[LINT_COMMAND]

# Format code
[FORMAT_COMMAND]

# Type checking
[TYPE_CHECK_COMMAND]
```

## Code Style & Conventions

<!--
Define your coding standards. Be specific - Claude follows these closely.
-->

### General Principles
- Write clear, self-documenting code
- Prefer explicit over implicit
- Keep functions small and focused
- Follow the single responsibility principle

### Naming Conventions
- **Files**: `kebab-case.ts` or `PascalCase.tsx` for components
- **Functions**: `camelCase`
- **Classes/Types**: `PascalCase`
- **Constants**: `SCREAMING_SNAKE_CASE`
- **Private members**: Prefix with `_` or use `#` for true private

### Code Organization
- Group imports: external, internal, relative
- Export from index files for cleaner imports
- Keep related code close together

### Comments Policy
- Do NOT add comments that describe "what" the code does
- Only add comments for "why" when the reasoning isn't obvious
- Use JSDoc/TSDoc for public APIs only
- Prefer self-documenting code over comments

## Testing Requirements

<!--
Define testing expectations for new code.
-->

- All new features must include tests
- Aim for [X]% code coverage on new code
- Test file location: `tests/` or `__tests__/` adjacent to source
- Naming convention: `*.test.ts` or `*.spec.ts`

### Test Structure
```typescript
describe('[Feature/Module]', () => {
  describe('[method/function]', () => {
    it('should [expected behavior]', () => {
      // Arrange
      // Act
      // Assert
    });
  });
});
```

## Git Workflow

### Commit Messages
Follow conventional commits:
```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

Types: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`

### Branch Naming
- Feature: `feature/[ticket-id]-brief-description`
- Bugfix: `fix/[ticket-id]-brief-description`
- Hotfix: `hotfix/[ticket-id]-brief-description`

## Important Patterns

<!--
Document patterns that are specific to this project.
Include examples when helpful.
-->

### Error Handling
```typescript
// Example pattern for this project
[ADD_ERROR_HANDLING_PATTERN]
```

### State Management
```typescript
// Example pattern for this project
[ADD_STATE_MANAGEMENT_PATTERN]
```

## External Integrations

<!--
Document APIs, services, and external dependencies.
Include links to documentation.
-->

| Integration | Purpose | Docs |
|-------------|---------|------|
| [SERVICE] | [PURPOSE] | [LINK] |

## Environment Variables

<!--
List required environment variables.
DO NOT include actual values - reference .env.example
-->

| Variable | Description | Required |
|----------|-------------|----------|
| `[VAR_NAME]` | [Description] | Yes/No |

See `.env.example` for all required variables.

## Common Tasks

<!--
Quick reference for tasks Claude will perform frequently.
-->

### Adding a New Feature
1. Create feature branch
2. Implement with tests
3. Run lint and type checks
4. Create PR with description

### Debugging
- Check logs at: `[LOG_LOCATION]`
- Use debugger: `[DEBUG_INSTRUCTIONS]`

### Deployment
- Staging: `[STAGING_DEPLOY_COMMAND]`
- Production: `[PRODUCTION_DEPLOY_COMMAND]`

## Known Issues & Gotchas

<!--
Document things that might trip up Claude or new developers.
-->

- [GOTCHA_1]: [Explanation and workaround]
- [GOTCHA_2]: [Explanation and workaround]

## Additional Context Files

<!--
Reference other documentation that Claude should read when relevant.
Use @ syntax to include files dynamically.

Example references (uncomment and modify as needed):
- For API documentation, see: @docs/api.md
- For database schema, see: @docs/schema.md
- For component library, see: @docs/components.md
-->

<!-- Add your project-specific documentation references here -->

---

## Rules for Claude

<!--
These rules improve Claude's performance significantly.
Based on extensive real-world usage patterns.
-->

### Core Principles

1. **Think first, code second**: Before any task, slow down. Read relevant files in the codebase. Build a mental model. Create a to-do list for yourself.

2. **Explain before changing**: Stop and explain your reasoning before making each change. This helps both of us understand the approach.

3. **Keep changes minimal**: Make every task and code change as simple as possible. Only touch the files and code necessary to complete the task.

4. **No lazy shortcuts**: Do not take shortcuts. Do not be lazy. If context is getting long, stay focused - don't hallucinate or skip steps.

5. **Fix root causes**: No temporary fixes or band-aids. Every fix should address the root cause of the problem.

6. **Simplicity over cleverness**: Don't overthink. Don't over-engineer. Don't write more code than necessary. Simple, readable code wins.

### Before Making Changes
1. Search the codebase to understand existing patterns
2. Check for similar implementations to follow
3. Propose a plan for significant changes
4. Ask clarifying questions when requirements are ambiguous

### When Writing Code
- Follow existing patterns in the codebase
- Run tests after changes
- Run linter and type checker
- Keep changes focused and atomic

### When Stuck
- Use `git log` to understand code evolution
- Search for similar patterns in the codebase
- Check docs/ for additional context
- Ask for clarification rather than guessing

---

## LLM Council (Optional)

This template includes an optional **LLM Council** feature - an "agentic advisory board" that consults multiple AI models for decision-making.

### When to Use the Council
- **Architecture decisions**: REST vs GraphQL, microservices vs monolith
- **Technology choices**: Database selection, caching strategies
- **Plan evaluation**: Review implementation plans before executing
- **Tie-breaking**: When multiple valid approaches exist

### How to Invoke

**Slash command**:
```
/council Should we use PostgreSQL or MongoDB for this use case?
```

**Natural language**:
```
I'm torn between these approaches. Can you consult the council?
```

**Check configuration**:
```
/council-config
```

### Setup Required

1. Set API keys in `.env` (at least 2 providers):
   - `ANTHROPIC_API_KEY`
   - `OPENAI_API_KEY`
   - `GOOGLE_AI_API_KEY`
   - `XAI_API_KEY`

2. Install dependencies:
   ```bash
   pip install -r scripts/llm-council/requirements.txt
   ```

3. Optionally customize `scripts/llm-council/config.yaml`

### Council Modes
- `quick`: Fast responses only (cheapest)
- `full`: Complete deliberation with peer review (most thorough)
- `vote`: Focus on ranking options

See `docs/LLM_COUNCIL_GUIDE.md` for detailed documentation.

---

## Agentic Solutions (Optional)

This template supports building **agentic AI solutions**—systems that autonomously complete complex tasks across multiple sessions.

### Agentic Patterns

| Pattern | Use Case | Documentation |
|---------|----------|---------------|
| **Sub-Agents** | Delegate complex subtasks | Built-in (Task tool) |
| **Skills** | Automated workflows | `docs/SKILLS_GUIDE.md` |
| **LLM Council** | Multi-model decisions | `docs/LLM_COUNCIL_GUIDE.md` |
| **Long-Running Agents** | Multi-session tasks | `docs/AGENTIC_GUIDE.md` |
| **Agent SDK** | Programmatic agents | `docs/AGENT_SDK_QUICKSTART.md` |

### When to Use Agentic Patterns

- **Multi-step tasks** spanning hours or days
- **Complex decisions** benefiting from multiple perspectives
- **Automated workflows** requiring consistency
- **Production systems** needing programmatic control

### Quick Start

1. Read `docs/AGENTIC_GUIDE.md` for pattern overview
2. Use `/agent-plan` to design your workflow
3. See `scripts/agent-examples/` for working code
4. Check `examples/agentic-claude-md/` for optimized templates

### Key Concepts

- **State Management**: Use files (`progress.txt`, `feature_list.json`) + git commits
- **Security**: Allowlist commands, sandbox filesystem, validate with hooks
- **Session Continuity**: Resume via session IDs, checkpoint with git
- **Error Recovery**: Always run tests first, rollback on failure

See `docs/AGENTIC_GUIDE.md` for comprehensive documentation.

---

## PDF Reference Parser (Optional)

This template includes a **PDF Semantic Decomposition Tool** that transforms large PDF documents into organized markdown knowledge bases that Claude Code can easily reference.

### When to Use

- Large specification documents (API specs, technical manuals)
- Research papers or whitepapers
- Any PDF too large for Claude Code to read directly
- Documents you want to version control as markdown

### How to Invoke

**Slash command**:
```
/parse-pdf docs/references/api-spec.pdf
```

**Direct CLI**:
```bash
python scripts/pdf-parser/parse_pdf.py document.pdf
```

**With options**:
```bash
python scripts/pdf-parser/parse_pdf.py document.pdf --output docs/references/custom-name
```

### Setup Required

1. Set API key in `.env`:
   - `ANTHROPIC_API_KEY` (preferred)
   - `OPENAI_API_KEY` (fallback)

2. Install dependencies:
   ```bash
   pip install -r scripts/pdf-parser/requirements.txt
   ```

### How It Works

The tool processes PDFs in three phases:

1. **Chunk Extraction**: Splits PDF into ~2000 token chunks, extracts images/tables
2. **Semantic Analysis**: LLM reads chunks sequentially, proposes folder/file organization
3. **Content Organization**: LLM writes organized markdown with proper formatting and images

### Output Structure

```
docs/references/api-spec/
├── _index.md                    # Overview and navigation
├── 01-introduction/
│   ├── overview.md
│   └── images/
├── 02-authentication/
│   ├── oauth2-flow.md
│   └── images/
└── ...
```

### Referencing Parsed Content

After parsing, reference the content in this file:
```markdown
## Additional Context Files

- For API specification, see: @docs/references/api-spec/_index.md
```

See `scripts/pdf-parser/config.example.yaml` for configuration options.
