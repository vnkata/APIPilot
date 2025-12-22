"""Command-line interface for OpenAPI operations

Provides CLI commands for:
- Validating OpenAPI specs
- Converting Swagger → OpenAPI
- Generating mock data
- Fuzzing APIs
"""

import json
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from common.openapi import OpenAPIClient
from common.openapi.generation.fuzzer import Fuzzer

app = typer.Typer(
    name="openapi",
    help="OpenAPI specification tools",
    add_completion=False,
)
console = Console()


@app.command()
def validate(
    spec_path: Path = typer.Argument(
        ..., help="Path to OpenAPI specification", exists=True
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose output"),
):
    """
    Validate OpenAPI specification

    Checks:
    - Spec format (OpenAPI 3.x / Swagger 2.0)
    - Schema validity
    - $ref resolution
    - Endpoint structure
    """
    try:
        console.print(f"[blue]Validating:[/blue] {spec_path}")

        # Load spec
        client = OpenAPIClient.from_file(spec_path)

        # Basic validation
        console.print("✓ Spec loaded successfully")
        console.print(f"  Format: OpenAPI {client.spec.openapi}")
        console.print(f"  Title: {client.spec.info.title}")
        console.print(f"  Version: {client.spec.info.version}")

        # Check endpoints
        endpoints = client.get_endpoints()
        console.print(f"  Endpoints: {len(endpoints)}")

        if verbose:
            table = Table(title="Endpoints")
            table.add_column("Method", style="cyan")
            table.add_column("Path", style="green")
            table.add_column("Operation ID", style="yellow")

            for endpoint in endpoints:
                table.add_row(
                    endpoint.method.upper(),
                    endpoint.path,
                    endpoint.operation_id or "-",
                )

            console.print(table)

        # Check schemas
        schemas = client.validator.list_schemas()
        console.print(f"  Schemas: {len(schemas)}")

        if verbose and schemas:
            console.print("\n[bold]Schemas:[/bold]")
            for schema in schemas[:10]:  # Show first 10
                console.print(f"  - {schema}")

        console.print("\n[green]✓ Validation passed![/green]")

    except Exception as e:
        console.print(f"[red]✗ Validation failed:[/red] {e}")
        raise typer.Exit(code=1)


@app.command()
def convert(
    input_path: Path = typer.Argument(
        ..., help="Path to Swagger 2.0 specification", exists=True
    ),
    output_path: Optional[Path] = typer.Option(
        None, "--output", "-o", help="Output path (default: stdout)"
    ),
):
    """
    Convert Swagger 2.0 → OpenAPI 3.x

    Automatically detects spec format and converts if needed.
    """
    try:
        console.print(f"[blue]Converting:[/blue] {input_path}")

        # Load spec (automatically converts)
        client = OpenAPIClient.from_file(input_path)

        console.print(f"✓ Converted to OpenAPI {client.spec.openapi}")

        # Output
        if output_path:
            # Write to file
            with open(output_path, "w") as f:
                json.dump(client.spec_dict, f, indent=2)
            console.print(f"✓ Written to: {output_path}")
        else:
            # Print to stdout
            console.print("\n[bold]Converted spec:[/bold]")
            console.print(json.dumps(client.spec_dict, indent=2))

    except Exception as e:
        console.print(f"[red]✗ Conversion failed:[/red] {e}")
        raise typer.Exit(code=1)


@app.command()
def mock(
    spec_path: Path = typer.Argument(
        ..., help="Path to OpenAPI specification", exists=True
    ),
    endpoint: Optional[str] = typer.Option(
        None, "--endpoint", "-e", help="Endpoint path (e.g., /users)"
    ),
    method: str = typer.Option("GET", "--method", "-m", help="HTTP method"),
    count: int = typer.Option(1, "--count", "-c", help="Number of mock items"),
    output: Optional[Path] = typer.Option(
        None, "--output", "-o", help="Output file (default: stdout)"
    ),
):
    """
    Generate mock data from OpenAPI spec

    Examples:
        openapi mock spec.json --endpoint /users --count 5
        openapi mock spec.json --endpoint /users/{id} --method POST
    """
    try:
        console.print(f"[blue]Generating mock data:[/blue] {spec_path}")

        # Load spec
        client = OpenAPIClient.from_file(spec_path)

        # Generate mock data
        if endpoint:
            # Single endpoint
            mock_data = client.generate_mock_response(endpoint, method, "200", count)
            result = {f"{method.upper()} {endpoint}": mock_data}
        else:
            # All endpoints
            result = client.mock_generator.generate_mock_server_data()

        console.print(f"✓ Generated mock data")

        # Output
        if output:
            with open(output, "w") as f:
                json.dump(result, f, indent=2, default=str)
            console.print(f"✓ Written to: {output}")
        else:
            console.print("\n[bold]Mock data:[/bold]")
            console.print(json.dumps(result, indent=2, default=str))

    except Exception as e:
        console.print(f"[red]✗ Mock generation failed:[/red] {e}")
        raise typer.Exit(code=1)


@app.command()
def fuzz(
    spec_path: Path = typer.Argument(
        ..., help="Path to OpenAPI specification", exists=True
    ),
    endpoint: Optional[str] = typer.Option(
        None, "--endpoint", "-e", help="Endpoint path (e.g., /users)"
    ),
    method: str = typer.Option("GET", "--method", "-m", help="HTTP method"),
    count: int = typer.Option(10, "--count", "-c", help="Number of test cases"),
):
    """
    Generate fuzzing test cases

    Creates property-based test cases for API endpoints.
    """
    try:
        console.print(f"[blue]Generating fuzz test cases:[/blue] {spec_path}")

        # Load spec
        client = OpenAPIClient.from_file(spec_path)
        fuzzer = Fuzzer(client.spec)

        # Generate test cases
        if endpoint:
            test_cases = fuzzer.generate_test_cases(endpoint, method, count)

            console.print(
                f"✓ Generated {len(test_cases)} test cases for {method.upper()} {endpoint}"
            )

            # Display test cases
            for i, case in enumerate(test_cases[:10], 1):  # Show first 10
                console.print(f"\n[bold]Test Case {i}:[/bold]")
                console.print(json.dumps(case, indent=2, default=str))

        else:
            # Fuzz all endpoints
            endpoints = client.get_endpoints()
            console.print(f"✓ Fuzzing {len(endpoints)} endpoints...")

            for ep in endpoints[:5]:  # Show first 5
                test_cases = fuzzer.generate_test_cases(ep.path, ep.method, 3)
                console.print(
                    f"\n[bold]{ep.method.upper()} {ep.path}:[/bold] {len(test_cases)} cases"
                )

    except Exception as e:
        console.print(f"[red]✗ Fuzzing failed:[/red] {e}")
        raise typer.Exit(code=1)


@app.command()
def info(
    spec_path: Path = typer.Argument(
        ..., help="Path to OpenAPI specification", exists=True
    ),
):
    """
    Display spec information

    Shows:
    - Metadata (title, version, description)
    - Endpoints summary
    - Schemas summary
    - Servers
    """
    try:
        # Load spec
        client = OpenAPIClient.from_file(spec_path)

        # Metadata
        console.print("[bold]OpenAPI Specification[/bold]\n")

        table = Table(show_header=False, box=None)
        table.add_column("Key", style="cyan")
        table.add_column("Value", style="white")

        table.add_row("Format", f"OpenAPI {client.spec.openapi}")
        table.add_row("Title", client.spec.info.title)
        table.add_row("Version", client.spec.info.version)

        if client.spec.info.description:
            desc = client.spec.info.description[:100] + "..."
            table.add_row("Description", desc)

        console.print(table)

        # Endpoints
        endpoints = client.get_endpoints()
        methods = {}
        for ep in endpoints:
            method = ep.method.upper()
            methods[method] = methods.get(method, 0) + 1

        console.print(f"\n[bold]Endpoints:[/bold] {len(endpoints)} total")
        for method, count in sorted(methods.items()):
            console.print(f"  {method}: {count}")

        # Schemas
        schemas = client.validator.list_schemas()
        console.print(f"\n[bold]Schemas:[/bold] {len(schemas)}")

        # Servers
        servers = client.introspector.get_servers()
        if servers:
            console.print(f"\n[bold]Servers:[/bold]")
            for server in servers[:3]:
                console.print(f"  - {server}")

    except Exception as e:
        console.print(f"[red]✗ Error:[/red] {e}")
        raise typer.Exit(code=1)


def main():
    """Entry point for CLI"""
    app()


if __name__ == "__main__":
    main()
