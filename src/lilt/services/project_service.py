"""Project workspace initialization, configuration, and static analysis."""

import os

import yaml

from lilt.exceptions import ProjectNotInitializedError
from lilt.parser.analyzer import AnalysisReport, ProjectAnalyzer
from lilt.services.workspace_context import WorkspaceContext
from lilt.utils.yaml_loader import load_yaml_config

DEFAULT_CONFIG = {
    "project": {
        "source_lang": "English",
        "target_lang": "Spanish",
        "domain_context": "",
    },
    "llm": {
        "provider": "openai",
        "model": "local-model",
        "base_url": "http://localhost:1234/v1",
        "max_tokens": 4096,
        "model_context_limit": 8192,
        "cost_profile": "balanced",
    },
    "tm": {
        "durability": "strict",
    },
    "review": {
        "queue_statuses": ["refined", "reviewed"],
    },
    "parser": {
        "custom_macros": [],
        "block_transparent_macros": [
            "section",
            "namespace",
            "subsection",
            "subsubsection",
            "paragraph",
            "title",
            "author",
            "date",
            "thanks",
            "item",
            "part",
            "abstract",
        ],
    },
}


INIT_ADVANCED_COMMENTS = """
# --- Advanced configuration (uncomment / extend as needed) ---
# project:
#   domain_context_max_tokens: 512
#   injections: []
# llm:
#   # Leave draft_model / critique_model / refine_model empty to fall back to model
#   draft_model: ""
#   critique_model: ""
#   refine_model: ""
#   temperature: 0.3
#   reflection_temperature: 0.0
#   reflection_enabled: true
#   output_token_mode: shared_budget
#   reasoning_reserve: 0
#   tokenizer_fudge: 1.1
#   chat_template_overhead: 48
#   timeout: 600.0
#   draft_empty_retries: 1
#   context_window: 3
#   translation_mode: workflow
#   token_price_per_million: 5.0
#   prompt_dir: null
#   retry:
#     max_attempts: 3
#     min_wait_seconds: 2
#     max_wait_seconds: 60
#   stages:
#     draft:
#       model: local-model
#     critique:
#       provider: openai
#       model: gpt-4o
#     refine:
#       model: gpt-4o-mini
# parser:
#   identity:
#     similarity_threshold: 0.85
#   protected_terms: []
#   opaque_environments: []
#   block_transparent_macros:
#     - section
#     - subsection
#     - abstract
"""


class ProjectService:
    """Manages the configuration and initialization of LILT workspaces."""

    def __init__(
        self,
        workspace_dir: str,
        workspace_ctx: WorkspaceContext | None = None,
    ):
        self.ctx = workspace_ctx or WorkspaceContext.from_workspace(workspace_dir)
        self.workspace_dir = self.ctx.workspace_dir
        self.lilt_dir = self.ctx.lilt_dir
        self.config_path = self.ctx.config_path

    def initialize_workspace(self) -> tuple[str, bool]:
        """Initialize a new LILT workspace and create the default configuration file.

        Returns:
            Tuple of (config path, whether a git repository was detected).
        """
        os.makedirs(self.lilt_dir, exist_ok=True)
        if not os.path.exists(self.config_path):
            with open(self.config_path, "w", encoding="utf-8") as f:
                yaml.dump(DEFAULT_CONFIG, f, default_flow_style=False, sort_keys=False)
                f.write(INIT_ADVANCED_COMMENTS)

        # Create .env template
        env_path = os.path.join(self.lilt_dir, ".env")
        if not os.path.exists(env_path):
            with open(env_path, "w", encoding="utf-8") as f:
                f.write("# LLM API Keys (Loaded automatically)\n")
                f.write("# OPENAI_API_KEY=sk-...\n")

        # Create .gitignore for lilt directory
        gitignore_path = os.path.join(self.lilt_dir, ".gitignore")
        if not os.path.exists(gitignore_path):
            with open(gitignore_path, "w", encoding="utf-8") as f:
                f.write("tm/\n")
                f.write("*.db\n")
                f.write("*.db-journal\n")
                f.write(".env\n")
                f.write("lilt.log\n")

        git_dir = os.path.join(self.workspace_dir, ".git")
        return self.config_path, os.path.isdir(git_dir)

    def configure_project(
        self,
        path_to_scan: str,
        include_macros: bool = True,
        include_aliases: bool = False,
    ) -> tuple[int, int]:
        """Scan the project and register discovered parser configuration.

        Returns:
            Tuple of (new_macros_count, new_aliases_count).
        """
        if not os.path.exists(self.config_path):
            raise ProjectNotInitializedError(self.workspace_dir)

        analyzer = ProjectAnalyzer(config_path=self.config_path)
        report = analyzer.analyze_directory(path_to_scan)

        data = load_yaml_config(self.config_path)

        if "parser" not in data:
            data["parser"] = {}

        new_macros = 0
        if include_macros and report.unknown_macros:
            if "custom_macros" not in data["parser"]:
                data["parser"]["custom_macros"] = []
            known_names = {m.get("name") for m in data["parser"]["custom_macros"]}
            for name in report.unknown_macros:
                if name not in known_names:
                    data["parser"]["custom_macros"].append(
                        {
                            "name": name,
                            "args": report.unknown_macros_with_args.get(name, 0),
                            "translatable": False,
                        }
                    )
                    new_macros += 1

        new_aliases = 0
        if include_aliases and report.environment_aliases:
            if "environment_aliases" not in data["parser"]:
                data["parser"]["environment_aliases"] = {}
            for alias, spec in report.environment_aliases.items():
                if alias not in data["parser"]["environment_aliases"]:
                    data["parser"]["environment_aliases"][alias] = spec
                    new_aliases += 1

        if new_macros > 0 or new_aliases > 0:
            with open(self.config_path, "w", encoding="utf-8") as f:
                yaml.dump(data, f, default_flow_style=False, sort_keys=False)

        return new_macros, new_aliases

    def configure_macros(self, path_to_scan: str) -> int:
        """Scan the project for unknown macros and register them in the configuration."""
        new_macros, _ = self.configure_project(
            path_to_scan, include_macros=True, include_aliases=False
        )
        return new_macros

    def analyze(self, path_to_scan: str) -> AnalysisReport:
        """Run the ProjectAnalyzer on *path_to_scan* and return the full AnalysisReport.

        This is a read-only, dry-run operation — it never modifies lilt.yaml.
        If the project has not been initialized the analyzer still runs, but it
        cannot cross-reference against already-configured macros.
        """
        config_path = (
            self.config_path if os.path.exists(self.config_path) else "lilt.yaml"
        )
        analyzer = ProjectAnalyzer(config_path=config_path)
        report: AnalysisReport = analyzer.analyze_directory(path_to_scan)
        return report
