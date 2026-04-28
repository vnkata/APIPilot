"""Build a functional-equivalent daikon_modified.jar without Docker.

This script:
1) Validates local toolchain (Python, Java, make, optional gradle).
2) Bootstraps dependencies required by extensions/daikon/java/lib.
3) Builds `daikon.jar` from `extensions/daikon` using native shell first (with timeout).
4) Falls back to WSL on Windows if native build fails or times out.
5) In WSL: preflight apt (sudo -n or sudo -S with optional password), prefer JDK 17 for make,
   normalize CRLF on .jpp/scripts, retry with cpp-12 if needed.
6) Copies output to repository root as `daikon_modified.jar`.
"""

from __future__ import annotations

import argparse
import logging
import os
from pathlib import Path
import platform
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import urllib.request
import zipfile


LOGGER = logging.getLogger("build_daikon")

DEFAULT_NATIVE_TIMEOUT_SECONDS = 600

def configure_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )


def is_windows() -> bool:
    return os.name == "nt"


def check_python_version() -> None:
    if sys.version_info < (3, 11):
        raise RuntimeError(
            f"Python 3.11+ is required. Current: {platform.python_version()}"
        )


def warn_if_venv_missing() -> None:
    in_venv = sys.prefix != getattr(sys, "base_prefix", sys.prefix)
    if in_venv:
        LOGGER.info("Python virtual environment detected: %s", sys.prefix)
        return
    if is_windows():
        LOGGER.warning(
            "No active venv detected. Recommended:\n"
            "  .\\.venv\\Scripts\\Activate.ps1"
        )
    else:
        LOGGER.warning(
            "No active venv detected. Recommended:\n"
            "  source .venv-linux/bin/activate"
        )


def run_command(
    command: list[str],
    cwd: Path | None = None,
    check: bool = True,
    capture_output: bool = True,
    timeout: float | None = None,
) -> subprocess.CompletedProcess[str]:
    LOGGER.debug("Running command: %s (cwd=%s, timeout=%s)", command, cwd, timeout)
    try:
        result = subprocess.run(
            command,
            cwd=str(cwd) if cwd else None,
            text=True,
            capture_output=capture_output,
            check=False,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(
            f"Command timed out after {timeout}s: {' '.join(command)}"
        ) from exc
    if check and result.returncode != 0:
        raise RuntimeError(
            "Command failed.\n"
            f"  Command: {' '.join(command)}\n"
            f"  Exit code: {result.returncode}\n"
            f"  Stdout: {result.stdout[-4000:] if result.stdout else ''}\n"
            f"  Stderr: {result.stderr[-4000:] if result.stderr else ''}"
        )
    return result


def tool_exists(cmd: str) -> bool:
    return shutil.which(cmd) is not None


def require_tools_for_native() -> None:
    for cmd in ("java", "javac"):
        if not tool_exists(cmd):
            raise RuntimeError(
                f"Required tool '{cmd}' not found in PATH. "
                "Please install JDK and ensure PATH is configured."
            )


def require_make_for_platform() -> None:
    if tool_exists("make"):
        return
    if is_windows():
        raise RuntimeError(
            "Native build requires 'make' in PATH on Windows.\n"
            "You can install via MSYS2/Chocolatey, or rely on WSL fallback."
        )
    raise RuntimeError("Required tool 'make' not found in PATH.")


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def download_file(url: str, dest: Path) -> None:
    if dest.exists():
        LOGGER.debug("Dependency already exists: %s", dest.name)
        return
    LOGGER.info("Downloading: %s", url)
    ensure_dir(dest.parent)
    with urllib.request.urlopen(url) as response:
        data = response.read()
    if not data:
        raise RuntimeError(f"Downloaded empty file from {url}")
    dest.write_bytes(data)
    LOGGER.info("Saved: %s", dest)


def extract_zip_members(zip_path: Path, members: dict[str, Path]) -> None:
    with zipfile.ZipFile(zip_path) as zf:
        names = set(zf.namelist())
        for source_member, target_path in members.items():
            if source_member not in names:
                raise RuntimeError(
                    f"Missing zip member '{source_member}' in {zip_path.name}"
                )
            ensure_dir(target_path.parent)
            with zf.open(source_member) as src, target_path.open("wb") as dst:
                dst.write(src.read())


def bootstrap_daikon_libs(repo_root: Path, daikon_dir: Path) -> None:
    lib_dir = daikon_dir / "java" / "lib"
    checker_dir = lib_dir / "checker-framework"
    require_javadoc_dir = lib_dir / "require-javadoc"
    error_prone_dir = lib_dir / "error-prone"

    ensure_dir(lib_dir)
    ensure_dir(checker_dir)
    ensure_dir(require_javadoc_dir)
    ensure_dir(error_prone_dir)

    maven_downloads: dict[str, str] = {
        "bcel-6.8.1.jar": "https://repo.maven.apache.org/maven2/org/checkerframework/annotatedlib/bcel/6.8.1/bcel-6.8.1.jar",
        "bcel-util-1.2.3.jar": "https://repo.maven.apache.org/maven2/org/plumelib/bcel-util/1.2.3/bcel-util-1.2.3.jar",
        "hashmap-util-0.0.1.jar": "https://repo.maven.apache.org/maven2/org/plumelib/hashmap-util/0.0.1/hashmap-util-0.0.1.jar",
        "options-1.0.6.jar": "https://repo.maven.apache.org/maven2/org/plumelib/options/1.0.6/options-1.0.6.jar",
        "plume-util-1.12.3.jar": "https://repo.maven.apache.org/maven2/org/plumelib/plume-util/1.12.3/plume-util-1.12.3.jar",
        "reflection-util-1.1.5.jar": "https://repo.maven.apache.org/maven2/org/plumelib/reflection-util/1.1.5/reflection-util-1.1.5.jar",
        "java-getopt-1.0.14.0.1.jar": "https://repo.maven.apache.org/maven2/org/checkerframework/annotatedlib/java-getopt/1.0.14.0.1/java-getopt-1.0.14.0.1.jar",
    }
    for filename, url in maven_downloads.items():
        download_file(url, lib_dir / filename)

    commons_exec_jar = lib_dir / "commons-exec-1.4.0.jar"
    if not commons_exec_jar.exists():
        with tempfile.TemporaryDirectory() as td:
            zip_path = Path(td) / "commons-exec-1.4.0-bin.zip"
            download_file(
                "https://dlcdn.apache.org/commons/exec/binaries/commons-exec-1.4.0-bin.zip",
                zip_path,
            )
            extract_zip_members(
                zip_path,
                {"commons-exec-1.4.0/commons-exec-1.4.0.jar": commons_exec_jar},
            )

    commons_lang_jar = lib_dir / "commons-lang3-3.19.0.jar"
    if not commons_lang_jar.exists():
        with tempfile.TemporaryDirectory() as td:
            zip_path = Path(td) / "commons-lang3-3.19.0-bin.zip"
            download_file(
                "https://dlcdn.apache.org/commons/lang/binaries/commons-lang3-3.19.0-bin.zip",
                zip_path,
            )
            extract_zip_members(
                zip_path,
                {"commons-lang3-3.19.0/commons-lang3-3.19.0.jar": commons_lang_jar},
            )

    checker_qual = lib_dir / "checker-qual.jar"
    checker_jar = checker_dir / "checker.jar"
    javac_jar = checker_dir / "javac.jar"
    if not (checker_qual.exists() and checker_jar.exists() and javac_jar.exists()):
        with tempfile.TemporaryDirectory() as td:
            zip_path = Path(td) / "checker-framework-3.52.0.zip"
            download_file(
                "https://github.com/typetools/checker-framework/releases/download/checker-framework-3.52.0/checker-framework-3.52.0.zip",
                zip_path,
            )
            extract_zip_members(
                zip_path,
                {
                    "checker-framework-3.52.0/checker/dist/checker.jar": checker_jar,
                    "checker-framework-3.52.0/checker/dist/javac.jar": javac_jar,
                    "checker-framework-3.52.0/checker/dist/checker-qual.jar": checker_qual,
                },
            )

    download_file(
        "https://repo1.maven.org/maven2/com/google/errorprone/error_prone_core/2.46.0/error_prone_core-2.46.0-with-dependencies.jar",
        error_prone_dir / "error_prone_core-2.46.0-with-dependencies.jar",
    )
    download_file(
        "https://repo1.maven.org/maven2/io/github/eisop/dataflow-errorprone/3.49.3-eisop1/dataflow-errorprone-3.49.3-eisop1.jar",
        error_prone_dir / "dataflow-errorprone-3.49.3-eisop1.jar",
    )

    download_file(
        "https://github.com/plume-lib/require-javadoc/releases/download/v2.0.0/require-javadoc-2.0.0-all.jar",
        require_javadoc_dir / "require-javadoc-2.0.0-all.jar",
    )

    download_file(
        "https://repo1.maven.org/maven2/org/json/json/20240303/json-20240303.jar",
        lib_dir / "json-20240303.jar",
    )

    daikon_plumelib = lib_dir / "daikon-plumelib.jar"
    if not daikon_plumelib.exists():
        if not tool_exists("gradle"):
            raise RuntimeError(
                "Missing 'gradle' command required to build daikon-plumelib.jar.\n"
                "Install Gradle or provide java/lib/daikon-plumelib.jar manually."
            )
        LOGGER.info("Building daikon-plumelib.jar via Gradle shadowJar...")
        run_command(["gradle", "shadowJar"], cwd=lib_dir)
        produced_jar = lib_dir / "build" / "libs" / "daikon-plumelib.jar"
        if not produced_jar.exists():
            raise RuntimeError("Gradle completed but daikon-plumelib.jar was not produced.")
        shutil.copy2(produced_jar, daikon_plumelib)
        LOGGER.info("Created %s", daikon_plumelib)

    expected_optional = [
        "junit-4.13.2-Daikon.jar",
        "hamcrest-core-1.3-Daikon.jar",
        "junit-platform-console-standalone-1.9.0-Daikon.jar",
    ]
    missing_optional = [name for name in expected_optional if not (lib_dir / name).exists()]
    if missing_optional:
        LOGGER.warning(
            "Optional Daikon test jars are missing: %s\n"
            "If packaging fails with jar extraction errors, provide these jars in java/lib.",
            ", ".join(missing_optional),
        )


def windows_to_wsl_path(path: Path) -> str:
    win_style = str(path).replace("\\", "/")
    result = run_command(["wsl", "wslpath", "-a", win_style], check=True)
    return result.stdout.strip()


def wsl_bash(script: str, check: bool = False) -> subprocess.CompletedProcess[str]:
    """Run a bash script inside default WSL distro.

    Uses ``bash -s`` with stdin so ``wsl.exe`` does not strip ``$variables`` from ``-lc`` strings
    (see Microsoft WSL argument parsing). Normalizes CRLF so scripts work when ``build_daikon.py``
    has Windows line endings.
    """
    # Source file may be CRLF; triple-quoted strings then contain \r. splitlines() strips all variants.
    script = "\n".join(script.splitlines()) + "\n"
    LOGGER.debug("Running wsl bash -s (script length=%s)", len(script))
    # Use bytes for stdin: on Windows, text=True can turn \n into \r\n and break bash.
    result = subprocess.run(
        ["wsl", "bash", "-s"],
        input=script.encode("utf-8"),
        capture_output=True,
        check=False,
        cwd=None,
    )
    out = result.stdout.decode("utf-8", errors="replace") if result.stdout else ""
    err = result.stderr.decode("utf-8", errors="replace") if result.stderr else ""
    wrapped = subprocess.CompletedProcess(
        args=["wsl", "bash", "-s"],
        returncode=result.returncode,
        stdout=out,
        stderr=err,
    )
    if check and wrapped.returncode != 0:
        raise RuntimeError(
            "WSL bash script failed.\n"
            f"  Exit code: {wrapped.returncode}\n"
            f"  Stdout: {wrapped.stdout[-4000:] if wrapped.stdout else ''}\n"
            f"  Stderr: {wrapped.stderr[-4000:] if wrapped.stderr else ''}"
        )
    return wrapped


APT_INSTALL_PACKAGES = (
    "build-essential perl cpp gcc g++ make openjdk-17-jdk-headless"
)


def _wsl_sudo_bash_c(inner: str, sudo_password: str | None) -> str:
    """Run a bash -c script under sudo. Uses sudo -n when password is absent; else sudo -S."""
    inner = inner.strip()
    quoted = shlex.quote(inner)
    if sudo_password:
        return (
            f"set -euo pipefail\n"
            f"printf '%s\\n' {shlex.quote(sudo_password)} | "
            f"sudo -S env DEBIAN_FRONTEND=noninteractive bash -c {quoted}\n"
        )
    return (
        f"set -euo pipefail\n"
        f"sudo -n env DEBIAN_FRONTEND=noninteractive bash -c {quoted}\n"
    )


def wsl_preflight_apt(allow_apt: bool, sudo_password: str | None) -> None:
    """Ensure WSL has toolchain; optionally run non-interactive apt."""
    check_script = r"""
missing=""
for cmd in perl make cpp gcc g++ java javac; do
  command -v "$cmd" >/dev/null 2>&1 || missing="$missing $cmd"
done
if [ -n "$missing" ]; then
  echo "WSL_MISSING:${missing}"
  exit 2
fi
echo "WSL_OK"
exit 0
"""
    result = wsl_bash(check_script, check=False)
    out = (result.stdout or "") + (result.stderr or "")
    if result.returncode == 0 and "WSL_OK" in out:
        LOGGER.info("WSL toolchain check passed.")
        return

    m = re.search(r"WSL_MISSING:(.+)", out, re.DOTALL)
    if m:
        LOGGER.warning("WSL missing tools:%s", m.group(1).strip())
    else:
        LOGGER.warning(
            "WSL preflight check inconclusive (rc=%s). Output:\n%s",
            result.returncode,
            out[:2000] or "(empty)",
        )
    manual = (
        "In WSL, run:\n"
        "  sudo apt-get update && sudo apt-get install -y "
        "build-essential perl cpp gcc g++ make openjdk-17-jdk-headless\n"
    )
    if not allow_apt:
        LOGGER.error("Auto apt disabled. %s", manual)
        raise RuntimeError("WSL toolchain incomplete. " + manual)

    LOGGER.info(
        "Attempting apt install (%s)...",
        "sudo -S with provided password" if sudo_password else "sudo -n",
    )
    apt_inner = f"apt-get update -qq && apt-get install -y {APT_INSTALL_PACKAGES}"
    apt_result = wsl_bash(_wsl_sudo_bash_c(apt_inner, sudo_password), check=False)
    if apt_result.returncode != 0:
        LOGGER.error(
            "apt install failed (need passwordless sudo or run manually).\n%s\napt stderr: %s",
            manual,
            apt_result.stderr[-1500:] if apt_result.stderr else "",
        )
        raise RuntimeError("WSL apt install failed. " + manual)

    result2 = wsl_bash(check_script, check=False)
    if result2.returncode != 0:
        raise RuntimeError("WSL still missing tools after apt. " + manual)


def wsl_log_tool_versions(java_exports: str = "") -> None:
    """Log toolchain versions; optional java_exports prepends JAVA_HOME (JDK 17) to the shell."""
    je = (java_exports.strip() + "\n") if java_exports.strip() else ""
    script = je + r"""
set -e
echo "=== WSL toolchain ==="
command -v javac && javac -version 2>&1 | head -1 || true
command -v java && java --version 2>&1 | head -1 || true
command -v cpp && cpp --version | head -1 || true
command -v gcc && gcc --version | head -1 || true
command -v perl && perl -v | head -2 || true
"""
    r = wsl_bash(script, check=False)
    LOGGER.info("%s", (r.stdout or r.stderr or "").strip())


def wsl_normalize_crlf(wsl_daikon: str) -> None:
    """Strip CR from scripts and Java preprocessor sources (critical for cpp line continuations)."""
    script = f"""
set -euo pipefail
cd '{wsl_daikon}'
# Executable / Perl scripts under scripts/
if [ -d scripts ]; then
  find scripts -type f -print0 | xargs -0 -r sed -i 's/\\r$//'
fi
# All .jpp templates (Quant.java.jpp, QuantBody.java.jpp, etc.)
if [ -d java ]; then
  find java -name '*.jpp' -print0 | xargs -0 -r sed -i 's/\\r$//'
  find java -name '*.java.jpp' -print0 | xargs -0 -r sed -i 's/\\r$//'
fi
echo "CRLF normalization done"
"""
    wsl_bash(script, check=True)


def wsl_install_cpp12(sudo_password: str | None) -> bool:
    """Install gcc-12 for a compatible cpp; return True if cpp-12 is available after."""
    inner = "apt-get install -y gcc-12 g++-12"
    r = wsl_bash(_wsl_sudo_bash_c(inner, sudo_password), check=False)
    if r.returncode != 0:
        return False
    r2 = wsl_bash("test -x /usr/bin/cpp-12", check=False)
    return r2.returncode == 0


def wsl_ensure_java17_home(sudo_password: str | None) -> str:
    """Ensure OpenJDK 17 is installed in WSL; return JAVA_HOME path, or '' if unavailable."""
    script = r"""
set -euo pipefail
for d in /usr/lib/jvm/java-17-openjdk-*; do
  if [ -x "$d/bin/javac" ]; then
    echo "$d"
    exit 0
  fi
done
echo ""
exit 0
"""
    r = wsl_bash(script, check=False)
    lines = [ln.strip() for ln in (r.stdout or "").splitlines() if ln.strip()]
    path = lines[-1] if lines else ""
    if path:
        LOGGER.info("Using JDK 17 for WSL build: %s", path)
        return path

    LOGGER.info("JDK 17 not found in WSL; installing openjdk-17-jdk-headless...")
    inner = "apt-get update -qq && apt-get install -y openjdk-17-jdk-headless"
    r2 = wsl_bash(_wsl_sudo_bash_c(inner, sudo_password), check=False)
    if r2.returncode != 0:
        LOGGER.error(
            "Could not install openjdk-17-jdk-headless. stderr tail: %s",
            (r2.stderr or "")[-800:],
        )
        return ""

    r3 = wsl_bash(script, check=False)
    lines3 = [ln.strip() for ln in (r3.stdout or "").splitlines() if ln.strip()]
    path3 = lines3[-1] if lines3 else ""
    if path3:
        LOGGER.info("Installed JDK 17 at: %s", path3)
    return path3


def wsl_java17_path_exports(java17_home: str) -> str:
    """Bash snippet to put JDK 17 on PATH for make/javac (avoids JDK 21 -Werror on deprecations)."""
    if not java17_home:
        return ""
    return f"""
export JAVA_HOME='{java17_home}'
export PATH="$JAVA_HOME/bin:$PATH"
"""


def wsl_cpp12_path_prefix(wsl_repo: str) -> str:
    """Create a directory with `cpp` -> cpp-12 and return WSL PATH prefix."""
    script = f"""
set -euo pipefail
BIN="{wsl_repo}/.cache/tooling/wsl-bin"
mkdir -p "$BIN"
rm -f "$BIN/cpp"
if [ -x /usr/bin/cpp-12 ]; then
  ln -sf /usr/bin/cpp-12 "$BIN/cpp"
  echo "$BIN"
else
  echo ""
fi
"""
    r = wsl_bash(script.strip(), check=False)
    lines = [ln.strip() for ln in (r.stdout or "").splitlines() if ln.strip()]
    return lines[-1] if lines else ""


def looks_like_java_cpp_failure(log: str) -> bool:
    """True only for preprocessor/cpp failures, not javac -Werror on generated .java files."""
    if not log:
        return False
    # Makefile echoes `java-cpp` in every recipe; do not match that alone (false positives).
    if "missing binary operator" in log or "JAVACPP_" in log:
        return True
    if "cpp -ffreestanding" in log:
        return True
    if "java-cpp: cpp" in log or "Actual command that failed:" in log:
        return True
    # Preprocessor source errors look like path/to/File.java.jpp:42:
    if re.search(r"\.(java\.)?jpp:\d+:", log):
        return True
    return False


def wsl_make_daikon_jar(
    wsl_daikon: str,
    path_prefix: str,
    java_exports: str,
) -> subprocess.CompletedProcess[str]:
    """Run make daikon.jar in WSL with optional PATH prefix for cpp wrapper and JDK 17."""
    je = (java_exports.strip() + "\n") if java_exports.strip() else ""
    pp = ""
    if path_prefix:
        pp = f'export PATH="{path_prefix}:$PATH"\n'
    # WSL: extensions/daikon/java/Makefile omits -Werror for JDK 17+ compatibility (see that file).
    script = f"""
set -euo pipefail
{je}{pp}cd '{wsl_daikon}'
make daikon.jar
"""
    return wsl_bash(script, check=False)


def copy_jar_to_root(repo_root: Path, daikon_dir: Path) -> Path:
    jar_path = daikon_dir / "daikon.jar"
    if not jar_path.exists():
        raise RuntimeError("extensions/daikon/daikon.jar not found after build.")
    output_jar = repo_root / "daikon_modified.jar"
    shutil.copy2(jar_path, output_jar)
    return output_jar


def build_daikon_native(
    daikon_dir: Path,
    repo_root: Path,
    timeout_seconds: float | None,
) -> Path:
    require_make_for_platform()
    run_command(
        ["make", "daikon.jar"],
        cwd=daikon_dir,
        timeout=timeout_seconds,
    )
    return copy_jar_to_root(repo_root, daikon_dir)


def wsl_copy_jar_to_windows_tree(wsl_src_daikon: str, wsl_dest_daikon: str) -> None:
    """After building in a WSL-only workdir, copy daikon.jar back to the repo on /mnt/."""
    script = f"""
set -euo pipefail
if [ ! -f '{wsl_src_daikon}/daikon.jar' ]; then
  echo "No daikon.jar at {wsl_src_daikon}" >&2
  exit 1
fi
cp -f '{wsl_src_daikon}/daikon.jar' '{wsl_dest_daikon}/daikon.jar'
echo "Copied daikon.jar to Windows tree"
"""
    wsl_bash(script.strip(), check=True)


def build_daikon_wsl(
    repo_root: Path,
    daikon_dir: Path,
    allow_wsl_apt: bool,
    wsl_workdir: str | None,
    wsl_sudo_password: str | None,
) -> Path:
    if not tool_exists("wsl"):
        raise RuntimeError("WSL fallback requested but 'wsl' command is unavailable.")

    wsl_repo = windows_to_wsl_path(repo_root)
    wsl_daikon = windows_to_wsl_path(daikon_dir)
    wsl_daikon_orig = wsl_daikon

    wsl_preflight_apt(allow_apt=allow_wsl_apt, sudo_password=wsl_sudo_password)
    java17 = wsl_ensure_java17_home(sudo_password=wsl_sudo_password)
    java_exports = wsl_java17_path_exports(java17)
    if not java17:
        LOGGER.warning(
            "JDK 17 not available in WSL; build may fail under JDK 21+ due to -Werror. "
            "Install openjdk-17-jdk-headless or pass --wsl-sudo-password / "
            "DAIKON_WSL_SUDO_PASSWORD for automated apt."
        )
    wsl_log_tool_versions(java_exports=java_exports)

    if wsl_workdir:
        wd_in = wsl_workdir.strip()
        script = f"""
set -euo pipefail
SRC='{wsl_daikon}'
WORKDIR=$(eval echo "{wd_in}")
DST="$WORKDIR/daikon-build"
rm -rf "$DST"
mkdir -p "$DST"
cp -a "$SRC/." "$DST/"
echo "$DST"
"""
        r = wsl_bash(script, check=True)
        lines = [ln.strip() for ln in (r.stdout or "").splitlines() if ln.strip()]
        wsl_daikon = lines[-1] if lines else ""
        if not wsl_daikon:
            raise RuntimeError("WSL workdir copy failed (empty path).")
        LOGGER.info("Using WSL workdir build path: %s", wsl_daikon)

    wsl_normalize_crlf(wsl_daikon)

    def run_make(path_prefix: str) -> subprocess.CompletedProcess[str]:
        return wsl_make_daikon_jar(
            wsl_daikon,
            path_prefix=path_prefix,
            java_exports=java_exports,
        )

    result = run_make("")
    log = (result.stdout or "") + (result.stderr or "")

    if result.returncode == 0:
        if wsl_workdir:
            wsl_copy_jar_to_windows_tree(wsl_daikon, wsl_daikon_orig)
        LOGGER.info("WSL repository path: %s", wsl_repo)
        return copy_jar_to_root(repo_root, daikon_dir)

    LOGGER.warning("First WSL make failed (exit %s)", result.returncode)
    LOGGER.debug("make output tail: %s", log[-3000:])

    if looks_like_java_cpp_failure(log):
        LOGGER.info("Detected java-cpp/cpp failure pattern; trying gcc-12 cpp...")
        if wsl_install_cpp12(sudo_password=wsl_sudo_password):
            prefix = wsl_cpp12_path_prefix(wsl_repo)
            if prefix:
                LOGGER.info("Using cpp wrapper PATH prefix: %s", prefix)
                result2 = run_make(prefix)
                log2 = (result2.stdout or "") + (result2.stderr or "")
                if result2.returncode == 0:
                    if wsl_workdir:
                        wsl_copy_jar_to_windows_tree(wsl_daikon, wsl_daikon_orig)
                    return copy_jar_to_root(repo_root, daikon_dir)
                LOGGER.error("Second WSL make failed:\n%s", log2[-4000:])
            else:
                LOGGER.error("cpp-12 not found after install attempt.")
        else:
            LOGGER.error(
                "Could not install gcc-12 via apt. Install manually in WSL:\n"
                "  sudo apt-get install -y gcc-12 g++-12"
            )

    raise RuntimeError(
        "WSL build failed after CRLF normalization, JDK 17 preference, and cpp retry.\n"
        "If building on /mnt/d, try: python scripts/build_daikon.py --force-wsl "
        "--wsl-workdir ~/daikon-wsl-build\n"
        "Ensure JDK 17 is used for javac (see log). For apt without NOPASSWD sudo, pass "
        "--wsl-sudo-password or set DAIKON_WSL_SUDO_PASSWORD.\n"
        f"Last log tail:\n{log[-4000:]}"
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build daikon_modified.jar from extensions/daikon")
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="Repository root path",
    )
    parser.add_argument(
        "--force-wsl",
        action="store_true",
        help="Force building in WSL (Windows only)",
    )
    parser.add_argument(
        "--skip-bootstrap",
        action="store_true",
        help="Skip dependency bootstrap and use existing java/lib artifacts",
    )
    parser.add_argument(
        "--timeout-seconds",
        type=float,
        default=DEFAULT_NATIVE_TIMEOUT_SECONDS,
        help=f"Timeout for native Windows make (default {DEFAULT_NATIVE_TIMEOUT_SECONDS}s); 0 disables",
    )
    parser.add_argument(
        "--no-wsl-apt",
        action="store_true",
        help="Do not run apt in WSL via sudo; only print manual install if tools missing",
    )
    pw_env = os.environ.get("DAIKON_WSL_SUDO_PASSWORD")
    parser.add_argument(
        "--wsl-sudo-password",
        default=pw_env,
        metavar="PASSWORD",
        help="WSL sudo password for apt when sudo -n is not allowed (also env DAIKON_WSL_SUDO_PASSWORD)",
    )
    parser.add_argument(
        "--wsl-workdir",
        type=str,
        default=None,
        metavar="WSL_PATH",
        help="Optional WSL path (e.g. ~/build) to copy daikon sources and build on Linux fs",
    )
    parser.add_argument("--verbose", action="store_true", help="Enable debug logging")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    configure_logging(verbose=args.verbose)

    repo_root = args.repo_root.resolve()
    daikon_dir = repo_root / "extensions" / "daikon"
    if not daikon_dir.exists():
        raise RuntimeError(f"Daikon source directory not found: {daikon_dir}")

    check_python_version()
    warn_if_venv_missing()
    require_tools_for_native()

    if not args.skip_bootstrap:
        LOGGER.info("Bootstrapping Daikon dependencies...")
        bootstrap_daikon_libs(repo_root=repo_root, daikon_dir=daikon_dir)

    timeout = None if args.timeout_seconds == 0 else args.timeout_seconds
    allow_apt = not args.no_wsl_apt
    wsl_pw = (args.wsl_sudo_password or "").strip() or None

    LOGGER.info("Building daikon jar from source...")
    if args.force_wsl:
        if not is_windows():
            raise RuntimeError("--force-wsl is only valid on Windows hosts.")
        jar_output = build_daikon_wsl(
            repo_root=repo_root,
            daikon_dir=daikon_dir,
            allow_wsl_apt=allow_apt,
            wsl_workdir=args.wsl_workdir,
            wsl_sudo_password=wsl_pw,
        )
        LOGGER.info("Built jar: %s", jar_output)
        return 0

    try:
        jar_output = build_daikon_native(
            daikon_dir=daikon_dir,
            repo_root=repo_root,
            timeout_seconds=timeout,
        )
        LOGGER.info("Built jar: %s", jar_output)
        return 0
    except Exception as native_error:
        if not is_windows():
            raise
        LOGGER.warning("Native build failed on Windows: %s", native_error)
        LOGGER.info("Attempting WSL fallback build...")
        jar_output = build_daikon_wsl(
            repo_root=repo_root,
            daikon_dir=daikon_dir,
            allow_wsl_apt=allow_apt,
            wsl_workdir=args.wsl_workdir,
            wsl_sudo_password=wsl_pw,
        )
        LOGGER.info("Built jar via WSL fallback: %s", jar_output)
        return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        LOGGER.error("Build failed: %s", exc)
        LOGGER.error(
            "Next steps:\n"
            "- Ensure JDK (java+javac), make, and gradle are installed.\n"
            "- On Windows WSL: prefer JDK 17 for Daikon (script sets JAVA_HOME when possible); "
            "use --wsl-sudo-password if apt needs a password.\n"
            "- For cpp errors on Quant.java.jpp: try --wsl-workdir ~/daikon-build or install gcc-12.\n"
            "- Re-run with --verbose for detailed diagnostics."
        )
        raise SystemExit(1)
