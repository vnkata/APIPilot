"""Mock data generator for API responses

Generates realistic mock responses based on OpenAPI spec for:
- Frontend development without backend
- Contract testing
- CI/CD pipelines
- API documentation examples
"""

from typing import Any

from common.logger import get_logger
from common.openapi.generation.test_generator import TestDataGenerator

logger = get_logger(__name__)


class MockGenerator:
    """Generate mock API responses from OpenAPI spec"""

    def __init__(self, spec):
        """
        Initialize mock generator

        Args:
            spec: OpenAPI specification object
        """
        self.spec = spec
        self.test_generator = TestDataGenerator(spec)
        logger.debug("MockGenerator initialized")

    def generate_response(
        self,
        path: str,
        method: str,
        status_code: str = "200",
        count: int = 1,
    ) -> Any:
        """
        Generate mock response for endpoint

        Args:
            path: API endpoint path (e.g., "/users/{id}")
            method: HTTP method (GET, POST, etc.)
            status_code: Response status code (default: "200")
            count: Number of items for array responses (default: 1)

        Returns:
            Mock response data matching schema

        Example:
            >>> generator = MockGenerator(spec)
            >>> mock = generator.generate_response("/users", "GET")
            >>> print(mock)
            [{"id": 1, "name": "John Doe", ...}]
        """
        logger.debug(
            f"Generating mock response: {method.upper()} {path} ({status_code})"
        )

        try:
            # Generate response using TestDataGenerator
            responses = []
            for _ in range(count):
                response = self.test_generator.generate_response_body(
                    path, method, status_code
                )
                responses.append(response)

            # Return single item if count=1, else array
            result = responses[0] if count == 1 else responses

            logger.debug(f"Generated mock response with {count} items")
            return result

        except Exception as e:
            logger.error(f"Failed to generate mock response: {e}")
            raise

    def generate_request(self, path: str, method: str) -> dict[str, Any]:
        """
        Generate mock request body

        Args:
            path: API endpoint path
            method: HTTP method

        Returns:
            Mock request body matching schema

        Example:
            >>> generator = MockGenerator(spec)
            >>> mock = generator.generate_request("/users", "POST")
            >>> print(mock)
            {"name": "Alice", "email": "alice@example.com"}
        """
        logger.debug(f"Generating mock request: {method.upper()} {path}")

        try:
            body = self.test_generator.generate_request_body(path, method)
            logger.debug("Generated mock request body")
            return body

        except Exception as e:
            logger.error(f"Failed to generate mock request: {e}")
            raise

    def generate_parameters(self, path: str, method: str) -> dict[str, Any]:
        """
        Generate mock parameters (query, path, header)

        Args:
            path: API endpoint path
            method: HTTP method

        Returns:
            Dict with 'query', 'path', 'header' keys

        Example:
            >>> generator = MockGenerator(spec)
            >>> params = generator.generate_parameters("/users/{id}", "GET")
            >>> print(params)
            {"path": {"id": 123}, "query": {"filter": "active"}}
        """
        logger.debug(f"Generating mock parameters: {method.upper()} {path}")

        try:
            params = self.test_generator.generate_parameters(path, method)
            logger.debug(f"Generated parameters: {list(params.keys())}")
            return params

        except Exception as e:
            logger.error(f"Failed to generate mock parameters: {e}")
            raise

    def generate_error_response(
        self, path: str, method: str, status_code: str
    ) -> dict[str, Any]:
        """
        Generate mock error response

        Args:
            path: API endpoint path
            method: HTTP method
            status_code: Error status code (e.g., "400", "404", "500")

        Returns:
            Mock error response

        Example:
            >>> generator = MockGenerator(spec)
            >>> error = generator.generate_error_response("/users", "GET", "404")
            >>> print(error)
            {"error": "Not Found", "message": "User not found"}
        """
        logger.debug(
            f"Generating error response: {method.upper()} {path} ({status_code})"
        )

        try:
            # Try to generate from spec
            response = self.test_generator.generate_response_body(
                path, method, status_code
            )

            if response:
                return response

            # Fallback: Generate generic error
            error_messages = {
                "400": "Bad Request",
                "401": "Unauthorized",
                "403": "Forbidden",
                "404": "Not Found",
                "500": "Internal Server Error",
            }

            return {
                "error": error_messages.get(status_code, "Error"),
                "message": f"An error occurred: {status_code}",
                "status": int(status_code),
            }

        except Exception as e:
            logger.error(f"Failed to generate error response: {e}")
            raise

    def generate_batch_responses(
        self,
        path: str,
        method: str,
        status_code: str = "200",
        batch_size: int = 10,
    ) -> list[Any]:
        """
        Generate batch of mock responses

        Args:
            path: API endpoint path
            method: HTTP method
            status_code: Response status code
            batch_size: Number of responses to generate

        Returns:
            List of mock responses

        Example:
            >>> generator = MockGenerator(spec)
            >>> batch = generator.generate_batch_responses("/users", "GET", batch_size=5)
            >>> print(len(batch))
            5
        """
        logger.debug(
            f"Generating batch of {batch_size} responses: {method.upper()} {path}"
        )

        try:
            return self.generate_response(path, method, status_code, count=batch_size)

        except Exception as e:
            logger.error(f"Failed to generate batch responses: {e}")
            raise

    def generate_all_responses_for_endpoint(
        self, path: str, method: str
    ) -> dict[str, Any]:
        """
        Generate all possible responses for endpoint (all status codes)

        Args:
            path: API endpoint path
            method: HTTP method

        Returns:
            Dict mapping status codes to mock responses

        Example:
            >>> generator = MockGenerator(spec)
            >>> responses = generator.generate_all_responses_for_endpoint("/users", "GET")
            >>> print(responses.keys())
            dict_keys(['200', '404', '500'])
        """
        logger.debug(f"Generating all responses: {method.upper()} {path}")

        # Get operation from spec
        path_item = self.spec.paths.get(path)
        if not path_item:
            logger.error(f"Path not found: {path}")
            raise ValueError(f"Path not found: {path}")

        operation = getattr(path_item, method.lower(), None)
        if not operation:
            logger.error(f"Method not found: {method.upper()} {path}")
            raise ValueError(f"Method not found: {method}")

        # Generate response for each status code
        responses = {}

        if operation.responses:
            for status_code in operation.responses.keys():
                try:
                    response = self.generate_response(path, method, status_code)
                    responses[status_code] = response
                except Exception as e:
                    logger.warning(
                        f"Could not generate response for {status_code}: {e}"
                    )

        logger.debug(f"Generated {len(responses)} responses")
        return responses

    def generate_mock_server_data(
        self, include_errors: bool = False
    ) -> dict[str, dict[str, Any]]:
        """
        Generate complete mock data for all endpoints

        Args:
            include_errors: Include error responses (default: False)

        Returns:
            Dict mapping endpoints to mock responses

        Example:
            >>> generator = MockGenerator(spec)
            >>> data = generator.generate_mock_server_data()
            >>> print(data.keys())
            dict_keys(['GET /users', 'POST /users', ...])
        """
        logger.debug("Generating complete mock server data")

        mock_data = {}

        if not self.spec.paths:
            logger.warning("No paths in spec")
            return mock_data

        for path, path_item in self.spec.paths.items():
            for method in ["get", "post", "put", "patch", "delete"]:
                operation = getattr(path_item, method, None)

                if operation:
                    key = f"{method.upper()} {path}"

                    try:
                        # Generate success response
                        mock_data[key] = {
                            "200": self.generate_response(path, method, "200")
                        }

                        # Include errors if requested
                        if include_errors and operation.responses:
                            for status_code in operation.responses.keys():
                                if status_code != "200":
                                    try:
                                        error_response = self.generate_response(
                                            path, method, status_code
                                        )
                                        mock_data[key][status_code] = error_response
                                    except Exception:
                                        pass

                    except Exception as e:
                        logger.warning(f"Could not generate mock for {key}: {e}")

        logger.debug(f"Generated mock data for {len(mock_data)} endpoints")
        return mock_data
