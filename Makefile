# CortexHub Examples - single project
# Run examples for each supported agentic framework

.PHONY: help sync use-local-sdk use-published-sdk langgraph crewai openai-agents claude-agents run-all clean

help:
	@echo "CortexHub Examples (single project)"
	@echo ""
	@echo "Setup:"
	@echo "  make sync            Install all dependencies (run first)"
	@echo "  make use-local-sdk   Switch cortexhub to local editable SDK"
	@echo "  make use-published-sdk Switch cortexhub back to PyPI"
	@echo ""
	@echo "Run examples:"
	@echo "  make langgraph       Run LangGraph Customer Support Agent"
	@echo "  make simple-refund   Run Simple Refund Approval"
	@echo "  make crewai          Run CrewAI Financial Operations Team"
	@echo "  make openai-agents   Run OpenAI Agents Research Assistant"
	@echo "  make claude-agents   Run Claude Agent SDK DevOps Assistant"
	@echo "  make run-all         Run all examples sequentially"
	@echo ""
	@echo "Maintenance:"
	@echo "  make clean           Remove virtual environments and lock files"
	@echo ""

# Sync single project environment
sync:
	@echo "Installing example dependencies..."
	uv sync

use-local-sdk:
	@echo "Switching cortexhub to local editable SDK..."
	uv pip install -e ../sdks/python --reinstall

use-published-sdk:
	@echo "Switching cortexhub to published SDK..."
	uv pip install "cortexhub[all]>=0.1.7" --reinstall

simple-refund: sync
	@echo "Running Simple Refund Approval..."
	uv run python langgraph/simple_refund_approval.py

langgraph: sync
	@echo "Running LangGraph Customer Support Agent..."
	uv run python langgraph/main.py

crewai: sync
	@echo "Running CrewAI Financial Operations Team..."
	uv run python crewai/main.py

openai-agents: sync
	@echo "Running OpenAI Agents Research Assistant..."
	uv run python openai-agents/main.py

claude-agents: sync
	@echo "Running Claude Agent SDK DevOps Assistant..."
	uv run python claude-agents/main.py

# Run all examples
run-all: langgraph crewai openai-agents claude-agents
	@echo ""
	@echo "All examples completed!"
	@echo "Check your CortexHub dashboard to see the activity."

# Clean up
clean:
	rm -rf .venv uv.lock
	@echo "Cleaned all virtual environments and lock files"
