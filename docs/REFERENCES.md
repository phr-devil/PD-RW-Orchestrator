# Reference implementations and reuse decisions

Reviewed official upstream documentation:

- [LangGraph](https://github.com/langchain-ai/langgraph): durable execution, state and human-in-the-loop patterns. **Borrow design concepts**, do not add a dependency before live orchestration needs it.
- [OpenAI Agents SDK](https://github.com/openai/openai-agents-python): handoffs, specialized agents and tracing patterns. **Borrow portable contracts**, no default model vendor lock.
- [CrewAI](https://github.com/crewAIInc/crewAI): capability-oriented collaboration and explicit process orchestration. Avoid duplicating its full runtime.
- [Microsoft AutoGen](https://github.com/microsoft/autogen): now archived (see repo README); not selected as a live dependency. Review successor separately if warranted.
- [AIDE](https://github.com/WecoAI/aideml), [AutoResearchClaw](https://github.com/aiming-lab/AutoResearchClaw), [R&D-Agent](https://github.com/microsoft/RD-Agent): external execution targets, not copied implementations.
- [PD-RW-Agent v1.0 RC](https://github.com/phr-devil/PD-RW-Agent/tree/rc/v1.0-integration): reuse original project recovery/science/case interfaces, never replace authoritative rules.
- [ACE](https://github.com/ace-agent/ace), [ExpeL](https://github.com/LeapLabTHU/ExpeL): experience distillation belongs in PD-RW-Experience, exposed here by an advisory provider.

References are architectural inspiration, not claims of adapter readiness or certified scientific efficacy. Respect each project's license before copying code; this repository does not vendor upstream code.
