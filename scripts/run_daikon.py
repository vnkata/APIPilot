"""Run Daikon jar without Docker and verify invariants output."""

from __future__ import annotations

import argparse
import logging
import os
from pathlib import Path
import shutil
import subprocess
import sys
import urllib.request


LOGGER = logging.getLogger("run_daikon")


def configure_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )


def warn_if_venv_missing() -> None:
    in_venv = sys.prefix != getattr(sys, "base_prefix", sys.prefix)
    if not in_venv:
        LOGGER.warning(
            "No active virtualenv detected. Recommended to activate `.venv` (Windows) "
            "or `.venv-linux` (Linux/WSL/macOS) before running."
        )


def run_java_daikon(jar: Path, decls: Path, dtrace: Path, cwd: Path) -> str:
    if not jar.exists():
        raise FileNotFoundError(f"Jar file not found: {jar}")
    if not decls.exists():
        raise FileNotFoundError(f"Decls file not found: {decls}")
    if not dtrace.exists():
        raise FileNotFoundError(f"Dtrace file not found: {dtrace}")

    command = ["java", "-jar", str(jar), str(decls), str(dtrace)]
    LOGGER.info("Running (cwd=%s): %s", cwd, " ".join(command))
    result = subprocess.run(
        command,
        cwd=str(cwd),
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        check=False,
    )
    if result.returncode == 0:
        return result.stdout

    # Compatibility fallback for modified Daikon builds that reference JavaFX Pair.
    if "javafx/util/Pair" in (result.stderr or ""):
        LOGGER.warning("Detected missing JavaFX Pair. Retrying with javafx-base on classpath...")
        javafx_jar = ensure_javafx_base_jar(repo_root=cwd)
        cp_sep = ";" if os.name == "nt" else ":"
        cp = f"{jar}{cp_sep}{javafx_jar}"
        fallback_cmd = ["java", "-cp", cp, "daikon.Daikon", str(decls), str(dtrace)]
        LOGGER.info("Running fallback: %s", " ".join(fallback_cmd))
        fallback_result = subprocess.run(
            fallback_cmd,
            cwd=str(cwd),
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=True,
            check=False,
        )
        if fallback_result.returncode == 0:
            return fallback_result.stdout
        raise RuntimeError(
            "Daikon fallback execution failed.\n"
            f"Exit code: {fallback_result.returncode}\n"
            f"Stdout: {fallback_result.stdout[-2000:] if fallback_result.stdout else ''}\n"
            f"Stderr: {fallback_result.stderr[-2000:] if fallback_result.stderr else ''}"
        )

    raise RuntimeError(
        "Daikon execution failed.\n"
        f"Exit code: {result.returncode}\n"
        f"Stdout: {result.stdout[-2000:] if result.stdout else ''}\n"
        f"Stderr: {result.stderr[-2000:] if result.stderr else ''}"
    )


def ensure_javafx_base_jar(repo_root: Path) -> Path:
    cache_dir = repo_root / ".cache" / "tooling" / "javafx"
    cache_dir.mkdir(parents=True, exist_ok=True)

    if sys.platform.startswith("win"):
        classifier = "win"
    elif sys.platform == "darwin":
        classifier = "mac"
    else:
        classifier = "linux"

    version = "21.0.2"
    jar_name = f"javafx-base-{version}-{classifier}.jar"
    jar_path = cache_dir / jar_name
    if jar_path.exists():
        return jar_path

    url = f"https://repo1.maven.org/maven2/org/openjfx/javafx-base/{version}/{jar_name}"
    LOGGER.info("Downloading JavaFX runtime dependency: %s", url)
    with urllib.request.urlopen(url) as response:
        data = response.read()
    if not data:
        raise RuntimeError(f"Downloaded empty JavaFX jar from {url}")
    jar_path.write_bytes(data)
    LOGGER.info("Saved JavaFX jar: %s", jar_path)
    return jar_path


def ensure_oracle_generation_config(repo_root: Path) -> None:
    """Ensure Daikon custom config exists at runtime expected path.

    Some modified Daikon builds expect `utils/config_oracleGeneration.txt`
    relative to current working directory.
    """
    utils_dir = repo_root / "utils"
    target = utils_dir / "config_oracleGeneration.txt"
    if target.exists():
        return

    source = (
        repo_root
        / "extensions"
        / "daikon"
        / "java"
        / "daikon"
        / "config"
        / "config_oracleGeneration.txt"
    )
    if not source.exists():
        LOGGER.warning(
            "Missing optional Daikon config source: %s. "
            "If runtime fails with config_oracleGeneration, provide this file manually.",
            source,
        )
        return

    utils_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)
    LOGGER.info("Prepared runtime config: %s", target)


def normalize_lines(text: str) -> set[str]:
    def canonicalize(value: str) -> str:
        return (
            value.replace("\ufffd", "’")
            .replace("’", "'")
            .replace("`", "'")
            .replace("\\'", "'")
            .rstrip()
        )

    return {
        canonicalize(line)
        for line in text.splitlines()
        if line.strip()
    }


def line_count(text: str) -> int:
    return len(text.splitlines())


def verify_output(
    new_text: str,
    baseline_text: str,
    verify_mode: str,
) -> tuple[bool, str]:
    new_count = line_count(new_text)
    old_count = line_count(baseline_text)
    count_ok = new_count == old_count

    if verify_mode == "line_count_only":
        ok = count_ok
        msg = (
            f"Line count check: new={new_count}, baseline={old_count}, "
            f"status={'PASS' if ok else 'FAIL'}"
        )
        return ok, msg

    if verify_mode == "strict_exact":
        exact_ok = new_text == baseline_text
        ok = count_ok and exact_ok
        msg = (
            f"Strict check: line_count={'PASS' if count_ok else 'FAIL'} "
            f"(new={new_count}, baseline={old_count}), "
            f"exact_match={'PASS' if exact_ok else 'FAIL'}"
        )
        return ok, msg

    # normalized_set (default)
    new_set = normalize_lines(new_text)
    old_set = normalize_lines(baseline_text)
    set_ok = new_set == old_set
    missing = sorted(old_set - new_set)[:5]
    added = sorted(new_set - old_set)[:5]
    ok = count_ok and set_ok
    msg = (
        f"Normalized-set check: line_count={'PASS' if count_ok else 'FAIL'} "
        f"(new={new_count}, baseline={old_count}), "
        f"set_match={'PASS' if set_ok else 'FAIL'} "
        f"(missing={len(old_set - new_set)}, added={len(new_set - old_set)})."
    )
    if missing or added:
        msg += f"\nSample missing lines: {missing}\nSample added lines: {added}"
    return ok, msg


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Daikon jar and optionally verify output.")
    parser.add_argument(
        "--jar",
        type=Path,
        default=Path("daikon_modified.jar"),
        help="Path to daikon jar file (default: daikon_modified.jar)",
    )
    parser.add_argument("--decls", type=Path, required=True, help="Path to *.decls file")
    parser.add_argument("--dtrace", type=Path, required=True, help="Path to *.dtrace file")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("invariants.csv"),
        help="Output invariants file path",
    )
    parser.add_argument(
        "--baseline",
        type=Path,
        default=None,
        help="Optional baseline invariants file for verification",
    )
    parser.add_argument(
        "--verify-mode",
        choices=["line_count_only", "normalized_set", "strict_exact"],
        default="normalized_set",
        help="Verification mode when --baseline is provided",
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=None,
        help="Repository root (for utils/config and working directory). "
        "Default: parent of scripts/",
    )
    parser.add_argument("--verbose", action="store_true", help="Enable debug logging")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    configure_logging(args.verbose)
    warn_if_venv_missing()

    repo_root = (args.repo_root or Path(__file__).resolve().parents[1]).resolve()
    ensure_oracle_generation_config(repo_root=repo_root)

    stdout = run_java_daikon(
        jar=args.jar.resolve(),
        decls=args.decls.resolve(),
        dtrace=args.dtrace.resolve(),
        cwd=repo_root,
    )

    output_path = args.output.resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(stdout, encoding="utf-8", newline="\n")
    LOGGER.info("Wrote output: %s (%d lines)", output_path, line_count(stdout))

    if args.baseline:
        baseline_path = args.baseline.resolve()
        if not baseline_path.exists():
            raise FileNotFoundError(f"Baseline file not found: {baseline_path}")
        baseline_text = baseline_path.read_text(encoding="utf-8")
        ok, report = verify_output(stdout, baseline_text, args.verify_mode)
        if ok:
            LOGGER.info("Verification passed.\n%s", report)
            return 0
        LOGGER.error("Verification failed.\n%s", report)
        return 2

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
