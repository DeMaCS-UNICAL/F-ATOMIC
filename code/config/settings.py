import os
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

load_dotenv(os.path.join(BASE_DIR, ".env"))


class Settings:
    """
    Global configuration class.
    Handles environment variables and absolute path resolution.
    """

    # Project Root Path
    # Exposed for other scripts if they need to construct custom paths
    BASE_PATH = BASE_DIR

    # Pipeline & Concurrency
    WORKERS = int(os.getenv("BATCH_SIZE", 40))
    GEN_SEMAPHORE_LIMIT = int(os.getenv("GEN_SEMAPHORE", 28))
    JUDGE_SEMAPHORE_LIMIT = int(os.getenv("JUDGE_SEMAPHORE", 4))
    LLM_TIMEOUT_SECONDS = float(os.getenv("LLM_TIMEOUT_SECONDS", "120"))

    # Set to True to route ALL three judge slots through a single provider/model.
    # For testing the pipeline logic without spending credits on 3 different APIs.
    # When True, SINGLE_JUDGE_PROVIDER and SINGLE_JUDGE_MODEL are used for every judge call.
    USE_SINGLE_JUDGE_PROVIDER = os.getenv("USE_SINGLE_JUDGE_PROVIDER", "false").lower() == "true"

    # Provider and model to use when USE_SINGLE_JUDGE_PROVIDER is True.
    # Defaults to OpenRouter + the same model used for generation (Model A).
    SINGLE_JUDGE_PROVIDER = os.getenv("SINGLE_JUDGE_PROVIDER", "openrouter").strip().lower()
    SINGLE_JUDGE_MODEL = os.getenv("SINGLE_JUDGE_MODEL", os.getenv("OPENROUTER_MODEL_A", "deepseek/deepseek-v3.2"))

    # Optional explicit panel: configure all three provider/model pairs together.
    JUDGE_1_PROVIDER = os.getenv("JUDGE_1_PROVIDER", "").strip().lower()
    JUDGE_1_MODEL = os.getenv("JUDGE_1_MODEL", "").strip()
    JUDGE_2_PROVIDER = os.getenv("JUDGE_2_PROVIDER", "").strip().lower()
    JUDGE_2_MODEL = os.getenv("JUDGE_2_MODEL", "").strip()
    JUDGE_3_PROVIDER = os.getenv("JUDGE_3_PROVIDER", "").strip().lower()
    JUDGE_3_MODEL = os.getenv("JUDGE_3_MODEL", "").strip()

    # Optional limit for testing
    LIMIT = None

    # Database (Redis)
    REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))

    # File Paths (Resolved to Absolute Paths)
    # We join the BASE_DIR with the relative path defined in .env or defaults

    INPUT_FILE = os.path.join(BASE_DIR, os.getenv("INPUT_FILE", "data/atomic_dataset/v4_atomic_all_agg.csv"))

    OUTPUT_FILE = os.path.join(BASE_DIR, os.getenv("OUTPUT_FILE", "experiments/events/results/forensic_atomic_final.csv"))

    JUDGEMENT_FILE = os.path.join(BASE_DIR, os.getenv("JUDGEMENT_FILE", "experiments/events/results/tribunal_judgments_new.csv"))

    CONCEPTNET_CACHE = os.path.join(BASE_DIR, os.getenv("CONCEPTNET_CACHE", "data/objects/conceptnet_cache.json"))

    LOG_FILE = os.path.join(BASE_DIR, "logs", "pipeline.log")

    # Generation Models (OpenRouter)
    OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
    OPENROUTER_BASE_URL = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")

    # Models for generation
    GEN_MODEL_A = os.getenv("OPENROUTER_MODEL_A", "deepseek/deepseek-v3.2")

    # OpenAI (Direct)
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")
    OPENAI_REASONING_EFFORT = os.getenv("OPENAI_REASONING_EFFORT", "").strip() or None

    # Anthropic (Direct)
    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
    ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-latest")

    # Google Gemini (Direct via REST)
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-pro")
    GEMINI_THINKING_LEVEL = os.getenv("GEMINI_THINKING_LEVEL", "").strip() or None

    # Eden AI uses the OpenAI-compatible adapter
    EDENAI_API_KEY = os.getenv("EDENAI_API_KEY")
    EDENAI_BASE_URL = os.getenv("EDENAI_BASE_URL", "https://api.edenai.run/v3/llm")

    def judge_panel(self) -> list[tuple[str, str]]:
        pairs = [
            (self.JUDGE_1_PROVIDER, self.JUDGE_1_MODEL),
            (self.JUDGE_2_PROVIDER, self.JUDGE_2_MODEL),
            (self.JUDGE_3_PROVIDER, self.JUDGE_3_MODEL),
        ]
        if any(provider or model for provider, model in pairs):
            if self.USE_SINGLE_JUDGE_PROVIDER:
                raise ValueError("Explicit JUDGE_1..3 settings cannot be combined with single-provider mode.")
            if not all(provider and model for provider, model in pairs):
                raise ValueError("Configure all three JUDGE_1..3 provider/model pairs together.")
            return pairs
        if self.USE_SINGLE_JUDGE_PROVIDER:
            return [(self.SINGLE_JUDGE_PROVIDER, self.SINGLE_JUDGE_MODEL)] * 3
        return [
            ("openai", self.OPENAI_MODEL),
            ("anthropic", self.ANTHROPIC_MODEL),
            ("gemini", self.GEMINI_MODEL),
        ]


settings = Settings()
