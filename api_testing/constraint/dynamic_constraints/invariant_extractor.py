from __future__ import annotations

import os
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path
from typing import Final

from api_testing.utils.log import getLogger


EXPECTED_INVARIANTS_HEADER: Final[str] = (
    "pptname;invariant;invariantType;variables;postmanAssertion;dslExpression"
)
JAVA_FX_VERSION: Final[str] = "21.0.2"
MAX_ERROR_OUTPUT_CHARS: Final[int] = 2_000


class InvariantExtractor:
    """Run Daikon on generated instrumentation files and persist the resulting invariants CSV."""

    def __init__(
        self,
        cache_dir: str | Path,
        jar_path: str | Path | None = None,
        repo_root: str | Path | None = None,
        java_executable: str | Path | None = None,
    ) -> None:
        self.cache_dir = Path(cache_dir)
        self.repo_root = Path(repo_root).resolve() if repo_root else Path(__file__).resolve().parents[3]
        self.jar_path = (
            Path(jar_path).resolve()
            if jar_path
            else (self.repo_root / "tools" / "daikon" / "daikon.jar").resolve()
        )
        self.java_executable = str(java_executable) if java_executable is not None else None
        self._resolved_java_executable: str | None = None
        self.logger = getLogger(__name__)

    def extract_invariants(
        self,
        decls_path: str | Path | None = None,
        dtrace_path: str | Path | None = None,
        output_path: str | Path | None = None,
    ) -> Path:
        """Generate the invariants CSV from Daikon input files."""
        resolved_decls = Path(decls_path) if decls_path else self.cache_dir / "test_cases.decls"
        resolved_dtrace = Path(dtrace_path) if dtrace_path else self.cache_dir / "test_cases.dtrace"
        resolved_output = Path(output_path) if output_path else self.cache_dir / "invariants.csv"

        self._validate_required_files(
            {
                "Daikon jar": self.jar_path,
                "decls file": resolved_decls,
                "dtrace file": resolved_dtrace,
            }
        )
        self._ensure_runtime_config()

        raw_output = self._run_daikon(
            decls_path=resolved_decls.resolve(),
            dtrace_path=resolved_dtrace.resolve(),
        )
        normalized_output = self._extract_csv_payload(self._normalize_output(raw_output))

        resolved_output.parent.mkdir(parents=True, exist_ok=True)
        with resolved_output.open("w", encoding="utf-8", newline="\n") as output_file:
            output_file.write(normalized_output)

        self.logger.info("Wrote invariants to %s", resolved_output)
        return resolved_output

    def _validate_required_files(self, files: dict[str, Path]) -> None:
        for label, path in files.items():
            if not path.exists():
                raise FileNotFoundError(f"{label} not found: {path}")

    def _ensure_runtime_config(self) -> None:
        """Ensure the modified Daikon runtime config exists at the expected runtime path."""
        target = self.repo_root / "utils" / "config_oracleGeneration.txt"
        if target.exists():
            return

        source = (
            self.repo_root
            / "extensions"
            / "daikon"
            / "java"
            / "daikon"
            / "config"
            / "config_oracleGeneration.txt"
        )
        if not source.exists():
            raise FileNotFoundError(
                "Daikon runtime config source not found: "
                f"{source}. Expected to copy it to {target}."
            )

        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        self.logger.info("Prepared Daikon runtime config at %s", target)

    def _run_daikon(self, decls_path: Path, dtrace_path: Path) -> str:
        java_executable = self._resolve_java_executable()
        command = [java_executable, "-cp", str(self.jar_path), "daikon.Daikon", str(decls_path), str(dtrace_path)]
        print("Running Daikon with command:", " ".join(command))
        result = self._run_process(command)
        if result.returncode == 0:
            return result.stdout

        stderr = result.stderr or ""
        if "javafx/util/Pair" in stderr:
            self.logger.warning(
                "Detected missing JavaFX Pair dependency. Retrying with javafx-base on the classpath."
            )
            return self._run_daikon_with_javafx(decls_path=decls_path, dtrace_path=dtrace_path)

        raise RuntimeError(self._build_failure_message("Daikon execution failed", result))

    def _run_daikon_with_javafx(self, decls_path: Path, dtrace_path: Path) -> str:
        javafx_jar = self._ensure_javafx_base_jar()
        classpath_separator = ";" if os.name == "nt" else ":"
        classpath = f"{self.jar_path}{classpath_separator}{javafx_jar}"
        command = [
            self._resolve_java_executable(),
            "-cp",
            classpath,
            "daikon.Daikon",
            str(decls_path),
            str(dtrace_path),
        ]
        print("Running Daikon with command:", " ".join(command))

        result = self._run_process(command)
        if result.returncode == 0:
            return result.stdout

        raise RuntimeError(self._build_failure_message("Daikon fallback execution failed", result))

    def _resolve_java_executable(self) -> str:
        if self._resolved_java_executable is not None:
            return self._resolved_java_executable

        tried_candidates: list[str] = []

        if self.java_executable is not None:
            resolved = self._resolve_configured_java(self.java_executable, tried_candidates)
            self._resolved_java_executable = resolved
            return resolved

        java_on_path = shutil.which("java")
        tried_candidates.append("PATH:java")
        if java_on_path:
            self._resolved_java_executable = java_on_path
            return java_on_path

        java_home = os.getenv("JAVA_HOME")
        if java_home:
            binary_name = "java.exe" if os.name == "nt" else "java"
            java_home_candidate = Path(java_home) / "bin" / binary_name
            tried_candidates.append(str(java_home_candidate))
            if java_home_candidate.exists():
                self._resolved_java_executable = str(java_home_candidate.resolve())
                return self._resolved_java_executable

        raise RuntimeError(self._build_java_runtime_error(tried_candidates))

    def _resolve_configured_java(
        self,
        configured_java: str,
        tried_candidates: list[str],
    ) -> str:
        configured_text = configured_java.strip()
        if not configured_text:
            raise RuntimeError(self._build_java_runtime_error(tried_candidates, configured_java))

        configured_path = Path(configured_text)
        if configured_path.exists():
            return str(configured_path.resolve())

        tried_candidates.append(configured_text)
        java_on_path = shutil.which(configured_text)
        if java_on_path:
            return java_on_path

        raise RuntimeError(self._build_java_runtime_error(tried_candidates, configured_java))

    def _run_process(self, command: list[str]) -> subprocess.CompletedProcess[str]:
        self.logger.info("Running Daikon command (cwd=%s): %s", self.repo_root, " ".join(command))
        return subprocess.run(
            command,
            cwd=str(self.repo_root),
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=True,
            check=False,
        )

    def _ensure_javafx_base_jar(self) -> Path:
        cache_dir = self.repo_root / ".cache" / "tooling" / "javafx"
        cache_dir.mkdir(parents=True, exist_ok=True)

        if sys.platform.startswith("win"):
            classifier = "win"
        elif sys.platform == "darwin":
            classifier = "mac"
        else:
            classifier = "linux"

        jar_name = f"javafx-base-{JAVA_FX_VERSION}-{classifier}.jar"
        jar_path = cache_dir / jar_name
        if jar_path.exists():
            return jar_path

        url = (
            "https://repo1.maven.org/maven2/org/openjfx/javafx-base/"
            f"{JAVA_FX_VERSION}/{jar_name}"
        )
        self.logger.info("Downloading JavaFX runtime dependency from %s", url)
        with urllib.request.urlopen(url) as response:
            data = response.read()

        if not data:
            raise RuntimeError(f"Downloaded empty JavaFX jar from {url}")

        jar_path.write_bytes(data)
        self.logger.info("Saved JavaFX dependency to %s", jar_path)
        return jar_path

    def _extract_csv_payload(self, content: str) -> str:
        lines = content.splitlines()
        for index, line in enumerate(lines):
            if line.strip() != EXPECTED_INVARIANTS_HEADER:
                continue

            if index > 0:
                preamble = [candidate for candidate in lines[:index] if candidate.strip()]
                if preamble:
                    self.logger.warning(
                        "Daikon produced %d preamble line(s) before the CSV header. "
                        "They will be discarded. First preamble line: %s",
                        len(preamble),
                        preamble[0],
                    )
            return "\n".join(lines[index:]) + "\n"

        first_non_empty_line = next((line.strip() for line in lines if line.strip()), None)
        if first_non_empty_line is None:
            raise RuntimeError("Daikon produced empty output; expected a CSV header line.")

        raise RuntimeError(
            "Unexpected Daikon output header. "
            f"Expected '{EXPECTED_INVARIANTS_HEADER}' but got '{first_non_empty_line}'."
        )

    @staticmethod
    def _normalize_output(content: str) -> str:
        return content.replace("\r\n", "\n").replace("\r", "\n")

    @staticmethod
    def _build_failure_message(
        prefix: str,
        result: subprocess.CompletedProcess[str],
    ) -> str:
        stdout_tail = (result.stdout or "")[-MAX_ERROR_OUTPUT_CHARS:]
        stderr_tail = (result.stderr or "")[-MAX_ERROR_OUTPUT_CHARS:]
        return (
            f"{prefix}.\n"
            f"Exit code: {result.returncode}\n"
            f"Stdout: {stdout_tail}\n"
            f"Stderr: {stderr_tail}"
        )

    @staticmethod
    def _build_java_runtime_error(
        tried_candidates: list[str],
        configured_java: str | None = None,
    ) -> str:
        java_home = os.getenv("JAVA_HOME")
        configured_text = configured_java or "<not provided>"
        tried = ", ".join(tried_candidates) if tried_candidates else "<none>"
        return (
            "Java runtime not found for Daikon execution. "
            f"Configured java_executable={configured_text}. "
            f"Current JAVA_HOME={java_home!r}. "
            f"Tried: {tried}. "
            "Ensure `java` is available on PATH or that JAVA_HOME points to a valid JDK/JRE."
        )
