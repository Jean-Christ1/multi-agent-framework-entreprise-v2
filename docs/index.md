# 🤖 JAF - Jems AI Framework

Welcome to the official documentation for the **Jems AI Framework (JAF)**. JAF is an enterprise-grade, Actor-based orchestration framework designed to enable complex automation workflows from a single, robust runtime.

---

## 🚀 Overview
JAF provides the core infrastructure needed to build, manage, and scale multi-agent systems. By leveraging an event-driven architecture and structured State Machines, it ensures seamless communication and predictable behavior across all automation layers.

## ⚙️ Execution Modes
JAF is uniquely designed to handle three distinct types of workflows:

1. **Agentic Flow**: A single orchestrator utilizing multiple deterministic tools for focused tasks.
2. **Multi-Agent Flow**: Complex orchestration where tasks are delegated to specialized agent actors.
3. **Traditional Automation**: Purely deterministic, BPMN-like workflows that operate without an LLM.

## 📂 Quick Navigation
* **[Getting Started](GETTING_STARTED.md)**: Installation guide and your first "Hello World" actor.
* **[Architecture](ARCHITECTURE.md)**: Deep dive into the Orchestrator, Event Bus, and Actor Model.
* **[API Reference](API_REFERENCE.md)**: Technical documentation auto-generated from the source code.

## 🛠 Key Features
* **Vendor Independence**: Flexible integration with different LLM providers and engines.
* **Event-Driven Design**: Real-time updates and decoupled communication via a central Event Bus.
* **Reliability & Persistence**: Crash recovery and state management powered by PostgreSQL.
* **Hybrid Nature**: Seamlessly blend neuro-symbolic AI with traditional rule-based logic.

---
