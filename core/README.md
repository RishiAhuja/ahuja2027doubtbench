# Core Code

Reusable code shared across experiments.

Current modules:

- `models.py`: low-budget provider/model registry
- `prompts.py`: prompt registry and forbidden capability terms
- `llm_client.py`: minimal OpenAI, Anthropic, Groq, and xAI HTTP clients
- `audit.py`: EXP-01 audit and prompt-polishing logic
- `json_utils.py`: JSON/JSONL helpers
