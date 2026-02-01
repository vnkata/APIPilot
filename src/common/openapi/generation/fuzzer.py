"""
Schemathesis integration for API fuzzing

This module provides wrappers around Schemathesis for automated
API testing and fuzzing.
"""

from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any

import schemathesis
import schemathesis.openapi
from schemathesis import Case

from common.logger.utils.helpers import get_logger

logger = get_logger(__name__)


class SchemaFuzzer:
    """
    API fuzzing using Schemathesis

    Features:
    - Property-based testing strategies
    - Automatic test case generation
    - Integration with pytest
    - Coverage of edge cases
    """

    def __init__(
        self,
        spec_path: str | Path,
        base_url: str | None = None,
    ) -> None:
        """
        Initialize schema fuzzer

        Args:
            spec_path: Path or URL to OpenAPI spec
            base_url: Base URL for API (overrides spec servers) - DEPRECATED: Not used in current Schemathesis
        """
        self.spec_path = str(spec_path)
        self.base_url = base_url

        # Load schema with schemathesis
        self.schema = schemathesis.openapi.from_path(self.spec_path)

        logger.info(f"Initialized Schemathesis fuzzer for spec: {self.spec_path}")

    @classmethod
    def from_dict(
        cls,
        spec_dict: dict[str, Any],
        base_url: str | None = None,
    ) -> "SchemaFuzzer":
        """
        Create fuzzer from spec dict

        Args:
            spec_dict: OpenAPI spec as dictionary
            base_url: Base URL for API - DEPRECATED: Not used in current Schemathesis

        Returns:
            SchemaFuzzer instance
        """
        schema = schemathesis.openapi.from_dict(spec_dict)

        fuzzer = cls.__new__(cls)
        fuzzer.spec_path = "<in-memory>"
        fuzzer.base_url = base_url
        fuzzer.schema = schema

        logger.info("Initialized Schemathesis fuzzer from dict")

        return fuzzer

    def generate_cases(
        self,
        endpoint: str | None = None,
        method: str | None = None,
        count: int = 10,
    ) -> Iterator[Case]:
        """
        Generate test cases for endpoints

        Args:
            endpoint: Specific endpoint path (e.g., "/users/{id}")
            method: Specific HTTP method (e.g., "GET")
            count: Number of cases to generate per endpoint

        Yields:
            Schemathesis Case objects

        Example:
            ```python
            fuzzer = SchemaFuzzer("openapi.yaml")
            for case in fuzzer.generate_cases(endpoint="/users", method="POST"):
                print(f"Path: {case.path}, Body: {case.body}")
            ```
        """
        logger.debug(
            f"Generating {count} test cases for "
            f"endpoint={endpoint or 'all'}, method={method or 'all'}"
        )

        # Generate test cases
        generated = 0

        # Get operations based on filters
        if endpoint and method:
            # Specific endpoint and method
            try:
                path_item = self.schema[endpoint]
                operation = path_item.get(method.upper())
                if operation:
                    strategy = operation.as_strategy()
                    for i in range(count):
                        try:
                            case = strategy.example()
                            generated += 1
                            yield case
                        except Exception as e:
                            logger.warning(
                                f"Failed to generate case {i + 1} for "
                                f"{method.upper()} {endpoint}: {e}"
                            )
                            continue
                else:
                    logger.warning(f"Operation not found: {method.upper()} {endpoint}")
            except (KeyError, AttributeError) as e:
                logger.warning(f"Operation not found: {method.upper()} {endpoint}: {e}")
        else:
            # Iterate over all or filtered operations
            for path in self.schema:
                path_item = self.schema[path]
                for method_name, operation in path_item.items():
                    # Apply filters
                    if endpoint and path != endpoint:
                        continue
                    if method and method_name.upper() != method.upper():
                        continue

                    # Generate cases for this operation
                    strategy = operation.as_strategy()
                    for i in range(count):
                        try:
                            case = strategy.example()
                            generated += 1
                            yield case
                        except Exception as e:
                            logger.warning(
                                f"Failed to generate case {i + 1} for "
                                f"{method_name.upper()} {path}: {e}"
                            )
                            continue

        logger.debug(f"Generated {generated} test cases")

    def generate_test_cases(
        self,
        endpoint: str | None = None,
        method: str | None = None,
        count: int = 10,
    ) -> list[dict[str, Any]]:
        """
        Generate test cases as list of dicts (convenience wrapper around generate_cases)

        Args:
            endpoint: Specific endpoint path (e.g., "/users/{id}")
            method: Specific HTTP method (e.g., "GET")
            count: Number of cases to generate per endpoint

        Returns:
            List of test case dictionaries with path, method, query, headers, body

        Example:
            ```python
            fuzzer = SchemaFuzzer("openapi.yaml")
            cases = fuzzer.generate_test_cases(endpoint="/users", method="POST", count=5)
            for case in cases:
                print(f"Path: {case['path']}, Body: {case['body']}")
            ```
        """
        test_cases = []

        try:
            for case in self.generate_cases(
                endpoint=endpoint, method=method, count=count
            ):
                # Convert Schemathesis Case to dict
                test_case = {
                    "path": case.path,
                    "method": case.method,
                    "query": dict(case.query) if case.query else {},
                    "headers": dict(case.headers) if case.headers else {},
                    "body": case.body,
                }
                test_cases.append(test_case)

                # Limit to requested count
                if len(test_cases) >= count:
                    break
        except Exception as e:
            logger.warning(f"Error generating test cases: {e}")

        return test_cases

    def create_pytest_strategy(
        self,
        endpoint: str | None = None,
        method: str | None = None,
    ) -> Any:
        """
        Create Hypothesis strategy for pytest parametrization

        Args:
            endpoint: Specific endpoint path
            method: Specific HTTP method

        Returns:
            Schemathesis strategy for use with @given decorator

        Example:
            ```python
            fuzzer = SchemaFuzzer("openapi.yaml")
            schema = fuzzer.schema

            @schema.parametrize()
            def test_api(case):
                response = case.call()
                case.validate_response(response)
            ```
        """
        if endpoint and method:
            return self.schema[endpoint][method.lower()]
        elif endpoint:
            return self.schema[endpoint]
        else:
            return self.schema

    def fuzz_endpoint(
        self,
        endpoint: str,
        method: str,
        test_func: Callable[[Case], None],
        count: int = 10,
    ) -> dict[str, Any]:
        """
        Fuzz a specific endpoint with generated test cases

        Args:
            endpoint: API endpoint path
            method: HTTP method
            test_func: Function that accepts Case and tests it
            count: Number of test cases to run

        Returns:
            Summary dict with passed/failed counts and errors

        Example:
            ```python
            def test_case(case: Case):
                response = case.call()
                assert response.status_code < 500

            fuzzer = SchemaFuzzer("openapi.yaml")
            results = fuzzer.fuzz_endpoint("/users", "GET", test_case, count=20)
            print(f"Passed: {results['passed']}, Failed: {results['failed']}")
            ```
        """
        logger.info(f"Fuzzing {method} {endpoint} with {count} cases")

        passed = 0
        failed = 0
        errors = []

        for i, case in enumerate(self.generate_cases(endpoint, method, count)):
            try:
                test_func(case)
                passed += 1
            except Exception as e:
                failed += 1
                errors.append(
                    {
                        "case_num": i + 1,
                        "error": str(e),
                        "path": case.path,
                        "method": case.method,
                    }
                )
                logger.warning(f"Fuzz test {i + 1} failed: {e}")

        results = {
            "endpoint": endpoint,
            "method": method,
            "total": passed + failed,
            "passed": passed,
            "failed": failed,
            "errors": errors,
        }

        logger.info(
            f"Fuzzing complete: {passed} passed, {failed} failed out of {passed + failed}"
        )

        return results


__all__ = ["SchemaFuzzer"]
