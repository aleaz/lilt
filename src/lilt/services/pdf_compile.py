"""Service-only PDF compilation via pdflatex / bibtex / biber.

Kept separate from TM build orchestration so ``PipelineService`` does not own
the TeX toolchain beside translation concerns.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from collections.abc import Callable

from lilt.exceptions import BuildError
from lilt.services.workspace_context import WorkspaceContext


class PdfCompileService:
    """Compile a ``.tex`` main file under the workspace sandbox."""

    def __init__(self, ctx: WorkspaceContext) -> None:
        self.ctx = ctx

    def compile_pdf(self, main_file: str, output_dir: str) -> None:
        """Compile ``main_file`` with pdflatex/bib tools (service-only helper)."""
        abs_output_dir = self.ctx.resolve_under_workspace(output_dir)
        abs_main = self.ctx.resolve_under_workspace(main_file)
        env = self._build_latex_env()
        base_name = os.path.splitext(os.path.basename(abs_main))[0]

        def run_pdflatex() -> str:
            return self._run_pdflatex(abs_output_dir, abs_main, env)

        output = run_pdflatex()
        if self._detect_and_run_bibliography(abs_output_dir, base_name, env):
            output = run_pdflatex()
        self._rerun_until_stable(output, run_pdflatex)

    def _build_latex_env(self) -> dict[str, str]:
        env = os.environ.copy()
        sep = os.pathsep
        workspace = os.path.abspath(self.ctx.workspace_dir)
        for tex_bin in ("/Library/TeX/texbin",):
            if os.path.isdir(tex_bin):
                path = env.get("PATH", "")
                if tex_bin not in path.split(sep):
                    env["PATH"] = f"{tex_bin}{sep}{path}"
        for var in ("TEXINPUTS", "BIBINPUTS", "BSTINPUTS"):
            existing = env.get(var, "")
            env[var] = f".{sep}{workspace}{sep}{existing}{sep}"
        return env

    def _resolve_tex_tool(self, name: str, env: dict[str, str]) -> str:
        path = env.get("PATH", os.environ.get("PATH", ""))
        found = shutil.which(name, path=path)
        return found if found else name

    def _run_pdflatex(
        self, abs_output_dir: str, abs_main: str, env: dict[str, str]
    ) -> str:
        pdflatex = self._resolve_tex_tool("pdflatex", env)
        try:
            res = subprocess.run(
                [pdflatex, "-interaction=nonstopmode", os.path.basename(abs_main)],
                cwd=abs_output_dir,
                env=env,
                check=True,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            return res.stdout
        except subprocess.CalledProcessError as e:
            raise BuildError(f"pdflatex failed:\n{e.output}") from e
        except FileNotFoundError as exc:
            raise BuildError(
                "pdflatex not found. Please install TeX Live or MiKTeX."
            ) from exc

    def _run_bib_tool(
        self, tool: str, base_name: str, abs_output_dir: str, env: dict[str, str]
    ) -> None:
        resolved = self._resolve_tex_tool(tool, env)
        try:
            subprocess.run(
                [resolved, base_name],
                cwd=abs_output_dir,
                env=env,
                check=True,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
        except subprocess.CalledProcessError as e:
            raise BuildError(f"{tool} failed:\n{e.output}") from e
        except FileNotFoundError as exc:
            raise BuildError(f"{tool} not found.") from exc

    def _detect_and_run_bibliography(
        self, abs_output_dir: str, base_name: str, env: dict[str, str]
    ) -> bool:
        aux_file = os.path.join(abs_output_dir, f"{base_name}.aux")
        bcf_file = os.path.join(abs_output_dir, f"{base_name}.bcf")
        if os.path.exists(bcf_file):
            self._run_bib_tool("biber", base_name, abs_output_dir, env)
            return True
        if os.path.exists(aux_file):
            with open(aux_file, encoding="utf-8", errors="ignore") as f:
                content = f.read()
                if "\\bibdata" in content or "\\bibstyle" in content:
                    self._run_bib_tool("bibtex", base_name, abs_output_dir, env)
                    return True
        return False

    def _rerun_until_stable(
        self, output: str, run_pdflatex: Callable[[], str], max_reruns: int = 2
    ) -> str:
        reruns = 0
        stability_markers = (
            "Rerun to get cross-references right",
            "Rerun to get citations correct",
            "Rerun to get pages right",
            "Rerun to get index right",
        )
        while reruns < max_reruns and any(
            marker in output for marker in stability_markers
        ):
            output = run_pdflatex()
            reruns += 1
        return output
