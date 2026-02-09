# Claude Code Project Template

A comprehensive, best-practice template for AI-assisted software development with Claude Code.

## Quick Start

1. **Use this template** - Click "Use this template" on GitHub, or:
   ```bash
   git clone https://github.com/brencon/claude-code-project-template.git my-project
   cd my-project
   rm -rf .git && git init
   ```

2. **Run the initialization script** (optional but recommended):
   ```bash
   # Linux/macOS
   ./init-project.sh

   # Windows PowerShell
   .\init-project.ps1
   ```
   This will guide you through selecting a tech stack template, configuring your project name, and optionally setting up the LLM Council.

3. **Or manually customize CLAUDE.md** - Update project overview, commands, and conventions. See [examples/](examples/) for tech stack templates.

4. **Start Claude Code**
   ```bash
   claude
   ```

**New to this template?** See the comprehensive [Getting Started Guide](docs/GETTING_STARTED.md) for:
- Choosing between template, fork, or clone approaches
- Step-by-step customization checklist
- How to sync upstream updates when the template improves

## Template Structure

```
├── .claude/
│   ├── commands/              # Custom slash commands
│   │   ├── brainstorm.md     # /brainstorm - Explore options first
│   │   ├── plan.md           # /plan - Plan before implementing
│   │   ├── debug.md          # /debug - Investigate issues
│   │   ├── review.md         # /review - Code review checklist
│   │   ├── test.md           # /test - Generate tests
│   │   ├── refactor.md       # /refactor - Safe refactoring
│   │   ├── commit.md         # /commit - Structured commits
│   │   ├── health.md         # /health - Project health check
│   │   └── agent-plan.md     # /agent-plan - Design agentic workflows
│   ├── settings.json          # Project settings (version controlled)
│   ├── settings.example.json  # Example settings with hooks
│   └── settings.local.json    # Local settings (gitignored)
├── .github/
│   └── workflows/
│       └── claude-code-review.yaml.example  # Auto PR review setup
├── docs/
│   ├── architecture/          # System design documentation
│   ├── decisions/             # Architecture Decision Records
│   ├── references/            # External references and research
│   ├── AGENTIC_GUIDE.md       # Building agentic AI solutions
│   ├── AGENT_SDK_QUICKSTART.md # Claude Agent SDK quickstart
│   ├── BEST_PRACTICES.md      # Claude Code best practices guide
│   ├── UI_DESIGN_GUIDE.md     # UI/design skill and techniques
│   ├── SKILLS_GUIDE.md        # Building skills and digital employees
│   └── LLM_COUNCIL_GUIDE.md   # Multi-model advisory board
├── scripts/
│   ├── llm-council/           # LLM Council (optional)
│   └── agent-examples/        # Agentic solution examples
├── examples/                  # Example CLAUDE.md for different tech stacks
│   ├── typescript-react/      # React + TypeScript frontend
│   ├── python-fastapi/        # Python + FastAPI backend
│   ├── node-express/          # Node.js + Express backend
│   └── agentic-claude-md/     # CLAUDE.md optimized for agents
├── init-project.sh            # Setup script (Linux/macOS)
├── init-project.ps1           # Setup script (Windows)
├── CLAUDE.md                  # Primary instructions for Claude
├── .env.example               # Environment variable template
├── .gitignore                 # Comprehensive gitignore
└── README.md                  # This file
```

## Included Slash Commands

| Command | Purpose |
|---------|---------|
| `/brainstorm [idea]` | Explore options before committing to an approach |
| `/plan [feature]` | Create implementation plan before coding |
| `/debug [issue]` | Systematic issue investigation |
| `/review [file/path]` | Code review with checklist |
| `/test [target]` | Generate comprehensive tests |
| `/refactor [target]` | Safe, test-verified refactoring |
| `/commit` | Create well-structured commits |
| `/health` | Check project setup and configuration |
| `/agent-plan [task]` | Design agentic workflows |
| `/council [question]` | Consult LLM Council for decisions (optional) |
| `/council-config` | Check LLM Council configuration |

## Customization Guide

### CLAUDE.md
The heart of your Claude Code configuration. Customize these sections:

- **Project Overview**: What your project does
- **Development Commands**: Build, test, lint, run commands
- **Code Style**: Your specific conventions
- **Architecture**: System structure and patterns
- **Important Patterns**: Project-specific patterns with examples

### Adding Custom Commands
Create `.claude/commands/[name].md`:

```markdown
# Command Title

Description of what this command does.

$ARGUMENTS will contain any text passed to the command.

## Instructions
1. Step one
2. Step two
```

Use with: `/name your arguments here`

### Permission Configuration
Edit `.claude/settings.json` to pre-approve safe operations:

```json
{
  "permissions": {
    "allow": [
      "Bash(npm test:*)",
      "Bash(npm run lint:*)"
    ]
  }
}
```

See `.claude/settings.example.json` for comprehensive examples including hooks.

### Hooks Configuration
Add hooks to run commands before/after Claude's tool use:

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Edit",
        "hooks": [{ "type": "command", "command": "npx prettier --write $CLAUDE_FILE_PATH" }]
      }
    ]
  }
}
```

### GitHub PR Review
1. Run `/install-github-app` in Claude Code
2. Rename `.github/workflows/claude-code-review.yaml.example` to `.yaml`
3. Customize the review prompt for your needs

## Best Practices

See [docs/BEST_PRACTICES.md](docs/BEST_PRACTICES.md) for comprehensive guidance on:

- CLAUDE.md configuration
- Permission management
- Workflow optimization
- Advanced techniques
- Anti-patterns to avoid

See [docs/UI_DESIGN_GUIDE.md](docs/UI_DESIGN_GUIDE.md) for:

- Front-end design skill installation
- Design reference sources (Dribbble, V0.dev, Pinterest)
- The "black, white, and one color" rule
- Creating design systems
- Avoiding generic AI aesthetics

See [docs/SKILLS_GUIDE.md](docs/SKILLS_GUIDE.md) for:

- Building specialized "digital employees"
- Skills vs Projects vs Sub-Agents
- Creating deterministic workflows with scripts
- The context rot problem and how skills solve it

See [docs/LLM_COUNCIL_GUIDE.md](docs/LLM_COUNCIL_GUIDE.md) for:

- Multi-model advisory board for decisions
- BYOK (Bring Your Own Keys) configuration
- Three-stage deliberation process
- Cost optimization strategies
- Based on [karpathy/llm-council](https://github.com/karpathy/llm-council)

## Agentic Solutions

This template supports building **agentic AI solutions**—systems that autonomously complete complex tasks.

### Agentic Patterns

| Pattern | Use Case | Documentation |
|---------|----------|---------------|
| **Sub-Agents** | Delegate complex subtasks | Built-in (Task tool) |
| **Skills** | Automated workflows | [SKILLS_GUIDE.md](docs/SKILLS_GUIDE.md) |
| **LLM Council** | Multi-model decisions | [LLM_COUNCIL_GUIDE.md](docs/LLM_COUNCIL_GUIDE.md) |
| **Long-Running Agents** | Multi-session tasks | [AGENTIC_GUIDE.md](docs/AGENTIC_GUIDE.md) |
| **Agent SDK** | Programmatic agents | [AGENT_SDK_QUICKSTART.md](docs/AGENT_SDK_QUICKSTART.md) |

### Quick Start

1. Read [docs/AGENTIC_GUIDE.md](docs/AGENTIC_GUIDE.md) for pattern overview
2. Use `/agent-plan` to design your workflow
3. See [scripts/agent-examples/](scripts/agent-examples/) for working code
4. Check [examples/agentic-claude-md/](examples/agentic-claude-md/) for optimized templates

### Resources

- [Anthropic's Research on Long-Running Agents](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents)
- [Claude Agent SDK Documentation](https://docs.anthropic.com/en/docs/claude-code/sdk)
- [Autonomous Coding Quickstart](https://github.com/anthropics/claude-quickstarts/tree/main/autonomous-coding)

## Philosophy

This template embodies key principles:

1. **Keep It Simple**: Claude Code works out of the box. Don't over-engineer.
2. **Brainstorm → Plan → Execute**: Think before coding, get options, then implement.
3. **Test-Driven**: Verify behavior with tests.
4. **Minimal Changes**: Only touch what needs to change. Simple > clever.
5. **Claude as Partner**: Treat Claude as a creative collaborator, not just a code generator.

## Sources

This template synthesizes best practices from:
- Anthropic official documentation and talks
- Claude Code team recommendations
- Community patterns and field experience

## Contributing

Contributions welcome! Please:
1. Follow the existing patterns
2. Update documentation
3. Test with Claude Code
4. Submit a PR with clear description

## License

MIT License - see [LICENSE](LICENSE) for details.

---

*Built for the AI-assisted development era.*
