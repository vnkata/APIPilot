"""Unit tests for the Daikon invariant extractor."""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from api_testing.constraint.dynamic_constraints.decls_exit import DeclsExit
from api_testing.constraint.dynamic_constraints.dtrace.enter_array import (
    generate_dtrace_enter_value_of_array,
)
from api_testing.constraint.dynamic_constraints.invariant_extractor import (
    EXPECTED_INVARIANTS_HEADER,
    InvariantExtractor,
)
from api_testing.constraint.dynamic_constraints.invariant_reader import InvariantReader
from api_testing.constraint.dynamic_constraints.test_case import cast_value
from api_testing.constraint.dynamic_constraint_miner import DynamicConstraintMiner


def _create_daikon_input_files(
    base_dir: Path,
    *,
    create_runtime_config: bool = True,
) -> tuple[Path, Path, Path]:
    cache_dir = base_dir / "cache"
    cache_dir.mkdir(parents=True, exist_ok=True)

    decls_path = cache_dir / "test_cases.decls"
    dtrace_path = cache_dir / "test_cases.dtrace"
    jar_path = base_dir / "tools" / "daikon" / "daikon_modified.jar"
    jar_path.parent.mkdir(parents=True, exist_ok=True)

    decls_path.write_text("decl-version 2.0\nvar-comparability implicit\n", encoding="utf-8")
    dtrace_path.write_text("decl-version 2.0\nvar-comparability implicit\n", encoding="utf-8")
    jar_path.write_text("placeholder", encoding="utf-8")
    if create_runtime_config:
        runtime_config = base_dir / "utils" / "config_oracleGeneration.txt"
        runtime_config.parent.mkdir(parents=True, exist_ok=True)
        runtime_config.write_text("config", encoding="utf-8")

    return decls_path, dtrace_path, jar_path


class TestInvariantExtractor:
    def test_extract_invariants_writes_normalized_csv(self, tmp_path: Path):
        decls_path, dtrace_path, jar_path = _create_daikon_input_files(tmp_path)
        extractor = InvariantExtractor(
            cache_dir=decls_path.parent,
            repo_root=tmp_path,
            jar_path=jar_path,
        )
        output_path = decls_path.parent / "result" / "invariants.csv"
        stdout = (
            f"{EXPECTED_INVARIANTS_HEADER}\r\n"
            "ppt:::EXIT;size(x) == 1;demo.Invariant;(x);pm.expect(x).to.eql(1)\r\n"
        )

        with patch(
            "api_testing.constraint.dynamic_constraints.invariant_extractor.subprocess.run",
            return_value=subprocess.CompletedProcess([], 0, stdout, ""),
        ):
            written_path = extractor.extract_invariants(output_path=output_path)

        assert written_path == output_path
        assert written_path.read_text(encoding="utf-8") == stdout.replace("\r\n", "\n")
        assert "\r" not in written_path.read_text(encoding="utf-8")

    def test_extract_invariants_rejects_invalid_header(self, tmp_path: Path):
        decls_path, dtrace_path, jar_path = _create_daikon_input_files(tmp_path)
        extractor = InvariantExtractor(
            cache_dir=decls_path.parent,
            repo_root=tmp_path,
            jar_path=jar_path,
        )

        with patch(
            "api_testing.constraint.dynamic_constraints.invariant_extractor.subprocess.run",
            return_value=subprocess.CompletedProcess([], 0, "unexpected_header\nrow\n", ""),
        ):
            with pytest.raises(RuntimeError, match="Unexpected Daikon output header"):
                extractor.extract_invariants()

    def test_extract_invariants_discards_warning_preamble_before_header(self, tmp_path: Path):
        decls_path, dtrace_path, jar_path = _create_daikon_input_files(tmp_path)
        extractor = InvariantExtractor(
            cache_dir=decls_path.parent,
            repo_root=tmp_path,
            jar_path=jar_path,
        )
        stdout = (
            "Warning: unquoted string value at file.dtrace line 10: 0\n"
            f"{EXPECTED_INVARIANTS_HEADER}\n"
            "ppt:::EXIT;size(x) == 1;demo.Invariant;(x);pm.expect(x).to.eql(1)\n"
        )

        with patch(
            "api_testing.constraint.dynamic_constraints.invariant_extractor.subprocess.run",
            return_value=subprocess.CompletedProcess([], 0, stdout, ""),
        ):
            written_path = extractor.extract_invariants()

        written_lines = written_path.read_text(encoding="utf-8").splitlines()
        assert written_lines[0] == EXPECTED_INVARIANTS_HEADER
        assert all(not line.startswith("Warning:") for line in written_lines)

    def test_extract_invariants_raises_for_missing_inputs(self, tmp_path: Path):
        jar_path = tmp_path / "tools" / "daikon" / "daikon_modified.jar"
        jar_path.parent.mkdir(parents=True, exist_ok=True)
        jar_path.write_text("placeholder", encoding="utf-8")
        runtime_config = tmp_path / "utils" / "config_oracleGeneration.txt"
        runtime_config.parent.mkdir(parents=True, exist_ok=True)
        runtime_config.write_text("config", encoding="utf-8")
        extractor = InvariantExtractor(cache_dir=tmp_path / "cache", repo_root=tmp_path, jar_path=jar_path)

        with pytest.raises(FileNotFoundError, match="decls file not found"):
            extractor.extract_invariants()

    def test_extract_invariants_uses_javafx_fallback_when_needed(self, tmp_path: Path):
        decls_path, dtrace_path, jar_path = _create_daikon_input_files(tmp_path)
        extractor = InvariantExtractor(
            cache_dir=decls_path.parent,
            repo_root=tmp_path,
            jar_path=jar_path,
        )
        javafx_jar = tmp_path / ".cache" / "tooling" / "javafx" / "javafx-base.jar"
        javafx_jar.parent.mkdir(parents=True, exist_ok=True)
        javafx_jar.write_text("placeholder", encoding="utf-8")

        initial_failure = subprocess.CompletedProcess(
            [],
            1,
            "",
            "Exception in thread \"main\" java.lang.NoClassDefFoundError: javafx/util/Pair",
        )
        fallback_success = subprocess.CompletedProcess(
            [],
            0,
            f"{EXPECTED_INVARIANTS_HEADER}\nrow\n",
            "",
        )

        with patch(
            "api_testing.constraint.dynamic_constraints.invariant_extractor.subprocess.run",
            side_effect=[initial_failure, fallback_success],
        ) as run_mock:
            with patch.object(extractor, "_ensure_javafx_base_jar", return_value=javafx_jar):
                output_path = extractor.extract_invariants()

        assert output_path.exists()
        assert run_mock.call_count == 2
        fallback_command = run_mock.call_args_list[1].args[0]
        assert fallback_command[0] == "java"
        assert fallback_command[1] == "-cp"
        assert str(javafx_jar) in fallback_command[2]
        assert fallback_command[3] == "daikon.Daikon"

    def test_extract_invariants_prepares_runtime_config(self, tmp_path: Path):
        decls_path, dtrace_path, jar_path = _create_daikon_input_files(
            tmp_path,
            create_runtime_config=False,
        )
        source_config = (
            tmp_path
            / "extensions"
            / "daikon"
            / "java"
            / "daikon"
            / "config"
            / "config_oracleGeneration.txt"
        )
        source_config.parent.mkdir(parents=True, exist_ok=True)
        source_config.write_text("config", encoding="utf-8")

        extractor = InvariantExtractor(
            cache_dir=decls_path.parent,
            repo_root=tmp_path,
            jar_path=jar_path,
        )

        with patch(
            "api_testing.constraint.dynamic_constraints.invariant_extractor.subprocess.run",
            return_value=subprocess.CompletedProcess([], 0, f"{EXPECTED_INVARIANTS_HEADER}\nrow\n", ""),
        ):
            extractor.extract_invariants()

        target_config = tmp_path / "utils" / "config_oracleGeneration.txt"
        assert target_config.exists()
        assert target_config.read_text(encoding="utf-8") == "config"

    @pytest.mark.skipif(
        os.getenv("RUN_DAIKON_INTEGRATION") != "1",
        reason="Set RUN_DAIKON_INTEGRATION=1 to run the Daikon integration test.",
    )
    def test_extract_invariants_with_real_daikon_when_fixtures_exist(self):
        repo_root = Path(__file__).resolve().parents[1]
        cache_dir = repo_root / ".cache" / "Canada Holidays API_3"
        decls_path = cache_dir / "test_cases.decls"
        dtrace_path = cache_dir / "test_cases.dtrace"
        jar_path = repo_root / "tools" / "daikon" / "daikon_modified.jar"

        if not shutil.which("java"):
            pytest.skip("Java runtime is not available on PATH.")
        if not (decls_path.exists() and dtrace_path.exists() and jar_path.exists()):
            pytest.skip("Daikon integration fixtures are not available.")

        extractor = InvariantExtractor(cache_dir=cache_dir, repo_root=repo_root, jar_path=jar_path)
        output_path = cache_dir / "invariants.integration.csv"

        written_path = extractor.extract_invariants(
            decls_path=decls_path,
            dtrace_path=dtrace_path,
            output_path=output_path,
        )

        first_line = written_path.read_text(encoding="utf-8").splitlines()[0]
        assert first_line == EXPECTED_INVARIANTS_HEADER


class TestInvariantReader:
    def test_read_invariants_returns_structured_records(self, tmp_path: Path):
        invariants_path = tmp_path / "invariants.csv"
        invariants_path.write_text(
            EXPECTED_INVARIANTS_HEADER + "\n"
            "ppt:::EXIT;size(x) == 1;demo.Invariant;(x);pm.expect(x).to.eql(1)\n",
            encoding="utf-8",
        )
        reader = InvariantReader()

        records = reader.read_invariants(invariants_path)

        assert len(records) == 1
        assert records[0].pptname == "ppt:::EXIT"
        assert records[0].invariant == "size(x) == 1"
        assert records[0].invariant_type == "demo.Invariant"


class TestDynamicConstraintSupport:
    @pytest.mark.parametrize(
        ("raw_value", "expected"),
        [
            ("yes", True),
            ("no", False),
            ("{'val': False}", False),
            ("{'value': 7}", 7),
            ("['root']", "root"),
            ("3.25", 3.25),
        ],
    )
    def test_cast_value_normalizes_wrapped_literals(self, raw_value, expected):
        assert cast_value(raw_value) == expected

    def test_generate_dtrace_enter_value_of_array_accepts_python_list(self):
        test_case = SimpleNamespace(get_test_case_id=lambda: "tc-1")

        value = generate_dtrace_enter_value_of_array(
            test_case,
            ["alice", "bob"],
            "string[]",
            "input.members[..]",
        )

        assert value == '["alice" "bob"]'

    def test_generate_dtrace_skips_non_json_response_body(self):
        class FakeDeclsExit:
            is_nested_array = False
            name_suffix = ""

            @staticmethod
            def get_exit_name() -> str:
                return "demo()"

            @staticmethod
            def generate_single_dtrace_enter_and_exit(*args, **kwargs) -> str:
                raise AssertionError("Non-JSON responses should be skipped before dtrace generation.")

            @staticmethod
            def generate_single_dtrace_enter_and_exit_array(*args, **kwargs) -> str:
                raise AssertionError("Non-JSON responses should be skipped before dtrace generation.")

        test_case = SimpleNamespace(
            response_body="<html>Sign in</html>",
            test_case_id="tc-1",
        )

        assert DeclsExit.generate_dtrace(FakeDeclsExit(), test_case, None) == ""


class TestDynamicConstraintMiner:
    def test_extract_invariants_requires_generated_inputs(self, tmp_path: Path):
        spec_parser = type("SpecParser", (), {"operations": {}})()
        miner = DynamicConstraintMiner(spec_parser=spec_parser, cache_dir=tmp_path)

        with pytest.raises(FileNotFoundError, match="Call extract_decls_classes\\(\\) and extract_dtraces\\(\\) first"):
            miner.extract_invariants()

    def test_mine_dynamic_constraints_returns_artifact_paths(self, tmp_path: Path):
        spec_parser = type("SpecParser", (), {"operations": {}})()
        miner = DynamicConstraintMiner(spec_parser=spec_parser, cache_dir=tmp_path)
        expected_paths = {
            "decls_path": tmp_path / "test_cases.decls",
            "dtrace_path": tmp_path / "test_cases.dtrace",
            "invariants_path": tmp_path / "invariants.csv",
        }

        with patch.object(miner, "extract_decls_classes") as extract_decls_mock:
            with patch.object(miner, "extract_dtraces") as extract_dtraces_mock:
                with patch.object(
                    miner,
                    "extract_invariants",
                    return_value=expected_paths["invariants_path"],
                ) as extract_invariants_mock:
                    result = miner.mine_dynamic_constraints()

        extract_decls_mock.assert_called_once_with()
        extract_dtraces_mock.assert_called_once_with()
        extract_invariants_mock.assert_called_once_with()
        assert result == expected_paths
