"""CLI entry point for FreeSpec compiler.

Supports a two-pass compilation architecture:
- Pass 1 (headers): Generate interface files independently
- Pass 2 (impl): Generate implementations using all headers as context
- Tests: Generate test skeletons from headers or implementations
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

import click

from freespec.config import ConfigError, FreeSpecConfig, find_config, load_config
from freespec.generator.compiler import CompileError, IndependentCompiler
from freespec.generator.cpp_runner import CppRunnerError, CppTestRunner
from freespec.generator.headers import HeaderGenerationError, HeaderGenerator, load_headers
from freespec.generator.impl import ImplementationError, ImplementationGenerator
from freespec.generator.runner import PytestRunner, RunnerError
from freespec.generator.stubs import GenerationError
from freespec.generator.tests import SkeletonGenError, SkeletonTestGenerator
from freespec.llm.claude_code import ClaudeCodeClient
from freespec.parser.dependency import DependencyResolver
from freespec.parser.spec_parser import ParseError, SpecParser
from freespec.verifier.imports import ImportVerifier


def setup_logging(verbose: bool) -> None:
    """Configure logging based on verbosity.

    Args:
        verbose: Whether to enable debug logging.
    """
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(message)s",
    )


@click.group()
@click.version_option()
def main() -> None:
    """FreeSpec compiler - generate code stubs from .spec files."""
    pass


@main.command()
@click.option(
    "-c",
    "--config",
    "config_path",
    type=click.Path(exists=True, path_type=Path),
    help="Path to freespec.yaml (auto-detected if not specified)",
)
@click.option(
    "-v",
    "--verbose",
    is_flag=True,
    help="Enable verbose output",
)
def headers(config_path: Path | None, verbose: bool) -> None:
    """Generate header/interface files (Pass 1).

    Headers are generated independently without dependency ordering.
    Each header defines the public API with NotImplementedError implementations.
    """
    setup_logging(verbose)

    try:
        # Load configuration
        click.echo("Loading configuration...")
        if config_path is None:
            config_path = find_config()
        config = load_config(config_path)
        click.echo(f"  Project: {config.name} v{config.version}")

        # Parse spec files
        click.echo("\nParsing spec files...")
        parser = SpecParser()
        specs = []
        for pattern in config.specs:
            parsed = parser.parse_glob(pattern, config.root_path)
            specs.extend(parsed)

        if not specs:
            click.echo("  No spec files found!", err=True)
            sys.exit(1)

        click.echo(f"  Found {len(specs)} spec files")

        # Validate dependencies (warn only, don't fail on cycles)
        resolver = DependencyResolver()
        _, missing_deps = resolver.get_all_specs(specs, validate=True)

        if missing_deps:
            click.echo("  Warning: Missing dependencies:", err=True)
            for error in missing_deps:
                click.echo(f"    - {error.spec_id} references @{error.missing}", err=True)

        # Check for cycles (informational)
        cycles = resolver.find_cycles(specs)
        if cycles:
            click.echo(f"  Note: {len(cycles)} circular @mention(s) (allowed in two-pass)")

        # Check Claude Code availability
        client = ClaudeCodeClient(working_dir=config.root_path)
        if not client.check_available():
            click.echo("  Error: Claude Code CLI not available", err=True)
            sys.exit(1)

        # Generate headers
        click.echo("\nGenerating headers (Pass 1)...")
        generator = HeaderGenerator(client=client)
        context = generator.generate_all_headers(specs, config)

        click.echo(f"  Generated {len(context.generated_files)} header files")
        click.echo(f"\nHeaders written to: {config.get_output_path('headers')}")

    except ConfigError as e:
        click.echo(f"Configuration error: {e}", err=True)
        sys.exit(1)
    except ParseError as e:
        click.echo(f"Parse error: {e}", err=True)
        sys.exit(1)
    except HeaderGenerationError as e:
        click.echo(f"Header generation error: {e}", err=True)
        sys.exit(1)


@main.command()
@click.option(
    "-c",
    "--config",
    "config_path",
    type=click.Path(exists=True, path_type=Path),
    help="Path to freespec.yaml (auto-detected if not specified)",
)
@click.option(
    "--no-verify",
    is_flag=True,
    help="Skip import verification",
)
@click.option(
    "-v",
    "--verbose",
    is_flag=True,
    help="Enable verbose output",
)
def impl(config_path: Path | None, no_verify: bool, verbose: bool) -> None:
    """Generate implementation files (Pass 2).

    Requires headers to be generated first. Uses all headers as context
    so circular @mentions are supported.
    """
    setup_logging(verbose)

    try:
        # Load configuration
        click.echo("Loading configuration...")
        if config_path is None:
            config_path = find_config()
        config = load_config(config_path)
        click.echo(f"  Project: {config.name} v{config.version}")

        # Load existing headers
        click.echo("\nLoading headers...")
        all_headers = load_headers(config)
        if not all_headers:
            click.echo("  Error: No headers found. Run 'freespec headers' first.", err=True)
            sys.exit(1)
        click.echo(f"  Loaded {len(all_headers)} headers")

        # Parse spec files
        click.echo("\nParsing spec files...")
        parser = SpecParser()
        specs = []
        for pattern in config.specs:
            parsed = parser.parse_glob(pattern, config.root_path)
            specs.extend(parsed)

        if not specs:
            click.echo("  No spec files found!", err=True)
            sys.exit(1)

        click.echo(f"  Found {len(specs)} spec files")

        # Check Claude Code availability
        client = ClaudeCodeClient(working_dir=config.root_path)
        if not client.check_available():
            click.echo("  Error: Claude Code CLI not available", err=True)
            sys.exit(1)

        # Generate implementations
        click.echo("\nGenerating implementations (Pass 2)...")
        generator = ImplementationGenerator(client=client)
        context = generator.generate_all_impls(specs, config, all_headers)

        click.echo(f"  Generated {len(context.generated_files)} implementation files")

        # Verify imports
        if not no_verify:
            click.echo("\nVerifying imports...")
            verifier = ImportVerifier()
            impl_paths = [f.path for f in context.generated_files]
            result = verifier.verify_cross_imports(impl_paths, config.get_output_path("impl"))

            if result.success:
                click.echo("  All imports verified successfully")
            else:
                click.echo("  Import verification failed:", err=True)
                for error in result.errors:
                    line_info = f":{error.line}" if error.line else ""
                    click.echo(f"    - {error.file_path}{line_info}: {error.error}", err=True)
                sys.exit(1)

        click.echo(f"\nImplementations written to: {config.get_output_path('impl')}")

    except ConfigError as e:
        click.echo(f"Configuration error: {e}", err=True)
        sys.exit(1)
    except ParseError as e:
        click.echo(f"Parse error: {e}", err=True)
        sys.exit(1)
    except ImplementationError as e:
        click.echo(f"Implementation error: {e}", err=True)
        sys.exit(1)


@main.command()
@click.option(
    "-c",
    "--config",
    "config_path",
    type=click.Path(exists=True, path_type=Path),
    help="Path to freespec.yaml (auto-detected if not specified)",
)
@click.option(
    "--from-headers",
    is_flag=True,
    help="Generate tests from headers instead of implementations (TDD workflow)",
)
@click.option(
    "-v",
    "--verbose",
    is_flag=True,
    help="Enable verbose output",
)
def tests(config_path: Path | None, from_headers: bool, verbose: bool) -> None:
    """Generate test skeleton files.

    By default, generates tests from implementation files.
    Use --from-headers for TDD workflow (tests before implementation).
    """
    setup_logging(verbose)

    try:
        # Load configuration
        click.echo("Loading configuration...")
        if config_path is None:
            config_path = find_config()
        config = load_config(config_path)
        click.echo(f"  Project: {config.name} v{config.version}")

        # Load source code (headers or implementations)
        if from_headers:
            click.echo("\nLoading headers for test generation...")
            source_code = load_headers(config)
            if not source_code:
                click.echo("  Error: No headers found. Run 'freespec headers' first.", err=True)
                sys.exit(1)
            click.echo(f"  Loaded {len(source_code)} headers")
        else:
            click.echo("\nLoading implementations for test generation...")
            source_code = _load_implementations(config)
            if not source_code:
                click.echo("  Error: No implementations. Run 'freespec impl' first.", err=True)
                sys.exit(1)
            click.echo(f"  Loaded {len(source_code)} implementations")

        # Parse spec files
        click.echo("\nParsing spec files...")
        parser = SpecParser()
        specs = []
        for pattern in config.specs:
            parsed = parser.parse_glob(pattern, config.root_path)
            specs.extend(parsed)

        if not specs:
            click.echo("  No spec files found!", err=True)
            sys.exit(1)

        click.echo(f"  Found {len(specs)} spec files")

        # Check Claude Code availability
        client = ClaudeCodeClient(working_dir=config.root_path)
        if not client.check_available():
            click.echo("  Error: Claude Code CLI not available", err=True)
            sys.exit(1)

        # Generate tests
        click.echo("\nGenerating test skeletons...")
        generator = SkeletonTestGenerator(client=client)
        context = generator.generate_all_tests(specs, config, source_code)

        click.echo(f"  Generated {len(context.generated_files)} test files")
        click.echo(f"\nTests written to: {config.get_output_path('tests')}")

    except ConfigError as e:
        click.echo(f"Configuration error: {e}", err=True)
        sys.exit(1)
    except ParseError as e:
        click.echo(f"Parse error: {e}", err=True)
        sys.exit(1)
    except SkeletonGenError as e:
        click.echo(f"Test generation error: {e}", err=True)
        sys.exit(1)


def _load_implementations(config: FreeSpecConfig) -> dict[str, str]:
    """Load all existing implementation files.

    Args:
        config: Project configuration.

    Returns:
        Map of spec_id to implementation content.
    """
    impls: dict[str, str] = {}

    # Load from impl directory
    impl_dir = config.get_output_path("impl")
    if impl_dir.exists():
        for py_file in impl_dir.rglob("*.py"):
            if py_file.name == "__init__.py":
                continue
            relative = py_file.relative_to(impl_dir)
            category = relative.parent.name if relative.parent.name else ""
            name = py_file.stem
            if category:
                spec_id = f"{category}/{name}"
            else:
                spec_id = name
            impls[spec_id] = py_file.read_text()

    # Load from api directory
    api_dir = config.get_output_path("api")
    if api_dir.exists():
        for py_file in api_dir.rglob("*.py"):
            if py_file.name == "__init__.py":
                continue
            spec_id = f"api/{py_file.stem}"
            impls[spec_id] = py_file.read_text()

    return impls


@main.command()
@click.option(
    "-c",
    "--config",
    "config_path",
    type=click.Path(exists=True, path_type=Path),
    help="Path to freespec.yaml (auto-detected if not specified)",
)
@click.option(
    "--fail-fast",
    is_flag=True,
    help="Stop on first module failure",
)
@click.option(
    "-v",
    "--verbose",
    is_flag=True,
    help="Enable verbose output",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Parse and validate specs without generating code",
)
@click.option(
    "--skip-headers",
    is_flag=True,
    help="Skip header generation, use existing headers",
)
@click.option(
    "--file",
    "spec_file",
    type=click.Path(exists=True, path_type=Path),
    help="Compile only this specific .spec file",
)
@click.option(
    "--log-dir",
    "log_dir",
    type=click.Path(path_type=Path),
    help="Directory to save detailed compilation logs",
)
def compile(
    config_path: Path | None,
    fail_fast: bool,
    verbose: bool,
    dry_run: bool,
    skip_headers: bool,
    spec_file: Path | None,
    log_dir: Path | None,
) -> None:
    """Compile .spec files using independent compilation (gcc model).

    Each file compiles independently:
    - Pass 1: Generate all headers (interfaces)
    - Pass 2: For each file:
        - Generate impl + tests together (impl sees only @mentioned headers)
        - Run tests with pytest
        - Retry with error feedback on failure

    Files "compile" successfully only when their tests pass.
    """
    setup_logging(verbose)

    try:
        # Stage 0: Load configuration
        click.echo("Loading configuration...")
        if config_path is None:
            config_path = find_config()
        config = load_config(config_path)
        click.echo(f"  Project: {config.name} v{config.version}")
        click.echo(f"  Language: {config.language}")

        # Stage 1: Parse spec files
        click.echo("\nStage 1: Parsing spec files...")
        parser = SpecParser()
        specs = []
        for pattern in config.specs:
            parsed = parser.parse_glob(pattern, config.root_path)
            specs.extend(parsed)
            click.echo(f"  Found {len(parsed)} specs matching '{pattern}'")

        if not specs:
            click.echo("  No spec files found!", err=True)
            sys.exit(1)

        click.echo(f"  Total: {len(specs)} spec files")

        # Filter to single file if --file specified
        if spec_file:
            spec_file = spec_file.resolve()
            matching = [s for s in specs if s.path.resolve() == spec_file]
            if not matching:
                click.echo(f"  Error: {spec_file} not found in configured specs", err=True)
                sys.exit(1)
            click.echo(f"  Filtering to single file: {spec_file.name}")
            compile_specs = matching
        else:
            compile_specs = specs

        # Validate dependencies (allow cycles)
        click.echo("\nValidating dependencies...")
        resolver = DependencyResolver()
        _, missing_deps = resolver.get_all_specs(specs, validate=True)

        if missing_deps:
            click.echo("  Warning: Missing dependencies found:", err=True)
            for error in missing_deps:
                click.echo(f"    - {error.spec_id} references @{error.missing}", err=True)

        # Check for cycles (informational only)
        cycles = resolver.find_cycles(specs)
        if cycles:
            click.echo(f"  Note: {len(cycles)} circular @mention(s) (allowed)")

        if dry_run:
            click.echo("\n[Dry run] Skipping code generation")
            click.echo("Validation passed!")
            return

        # Check Claude Code availability
        # Use default log dir if not specified
        if log_dir is None:
            log_dir = config.root_path / "logs" / "compile"
        click.echo(f"\nLogs will be saved to: {log_dir}")

        client = ClaudeCodeClient(working_dir=config.root_path, log_dir=log_dir)
        if not client.check_available():
            click.echo("  Error: Claude Code CLI not available", err=True)
            click.echo("  Please ensure 'claude' is installed and in PATH", err=True)
            sys.exit(1)

        # Check test runner availability based on language
        lang = config.language.lower()
        if lang == "python":
            click.echo("\nChecking pytest availability...")
            runner = PytestRunner(working_dir=config.root_path)
            try:
                runner.check_available()
                click.echo("  pytest is available")
            except RunnerError as e:
                click.echo(f"  Error: {e}", err=True)
                sys.exit(1)
        elif lang in ("cpp", "c++"):
            click.echo("\nChecking C++ compiler availability...")
            cpp_runner = CppTestRunner(working_dir=config.root_path)
            try:
                cpp_runner.check_available()
                click.echo("  C++ compiler is available")
            except CppRunnerError as e:
                click.echo(f"  Error: {e}", err=True)
                sys.exit(1)

        # Stage 2: Generate or load headers (Pass 1)
        if skip_headers:
            click.echo("\nStage 2: Loading existing headers...")
            all_headers = load_headers(config)
            if not all_headers:
                click.echo("  Error: No headers found. Run without --skip-headers first.", err=True)
                sys.exit(1)
            click.echo(f"  Loaded {len(all_headers)} existing headers")
        else:
            click.echo("\nStage 2: Generating headers (Pass 1)...")
            header_generator = HeaderGenerator(client=client)
            header_context = header_generator.generate_all_headers(specs, config)
            all_headers = header_context.headers
            click.echo(f"  Generated {len(header_context.generated_files)} header files")

        # Stage 3: Independent compilation (Pass 2)
        click.echo("\nStage 3: Independent compilation...")
        click.echo(f"  Compiling {len(compile_specs)} spec(s)...")
        compiler = IndependentCompiler(client=client)
        compile_context = compiler.compile_all(
            specs=compile_specs,
            config=config,
            all_headers=all_headers,
            fail_fast=fail_fast,
        )

        # Report results
        click.echo("\nCompilation Results:")
        for result in compile_context.results:
            status = "[PASS]" if result.success else "[FAIL]"
            duration = f"({result.duration_seconds:.1f}s)" if result.duration_seconds else ""
            click.echo(f"  {status} {result.spec_id} {duration}")
            if result.log_file:
                click.echo(f"       Log: {result.log_file}")

        # Summary
        passed = len(compile_context.passed)
        failed = len(compile_context.failed)
        total = passed + failed
        click.echo(f"\nSummary: {passed}/{total} modules compiled successfully")

        if compile_context.failed:
            click.echo("\nFailed modules:", err=True)
            for result in compile_context.failed:
                click.echo(f"  - {result.spec_id}", err=True)
                if result.error and verbose:
                    # Truncate long errors
                    error_preview = result.error[:500]
                    if len(result.error) > 500:
                        error_preview += "..."
                    click.echo(f"    Error: {error_preview}", err=True)
            sys.exit(1)

        click.echo("\nCompilation complete!")
        click.echo("Output written to:")
        click.echo(f"  Headers: {config.get_output_path('headers')}")
        click.echo(f"  Implementations: {config.get_output_path('impl')}")
        click.echo(f"  Tests: {config.get_output_path('tests')}")
        click.echo(f"  Logs: {log_dir}")

    except ConfigError as e:
        click.echo(f"Configuration error: {e}", err=True)
        sys.exit(1)
    except ParseError as e:
        click.echo(f"Parse error: {e}", err=True)
        sys.exit(1)
    except HeaderGenerationError as e:
        click.echo(f"Header generation error: {e}", err=True)
        sys.exit(1)
    except CompileError as e:
        click.echo(f"Compilation error: {e}", err=True)
        sys.exit(1)
    except GenerationError as e:
        click.echo(f"Generation error: {e}", err=True)
        sys.exit(1)
    except RunnerError as e:
        click.echo(f"Test runner error: {e}", err=True)
        sys.exit(1)
    except CppRunnerError as e:
        click.echo(f"C++ runner error: {e}", err=True)
        sys.exit(1)


@main.command()
@click.option(
    "-c",
    "--config",
    "config_path",
    type=click.Path(exists=True, path_type=Path),
    help="Path to freespec.yaml",
)
def validate(config_path: Path | None) -> None:
    """Validate spec files without generating code.

    Checks syntax and missing dependencies. Circular @mentions are allowed
    since two-pass compilation supports them.
    """
    setup_logging(verbose=False)

    try:
        # Load configuration
        if config_path is None:
            config_path = find_config()
        config = load_config(config_path)
        click.echo(f"Project: {config.name} v{config.version}")

        # Parse spec files
        parser = SpecParser()
        specs = []
        for pattern in config.specs:
            specs.extend(parser.parse_glob(pattern, config.root_path))

        click.echo(f"Parsed {len(specs)} spec files")

        # Validate dependencies (allow cycles)
        resolver = DependencyResolver()
        _, missing_deps = resolver.get_all_specs(specs, validate=True)

        if missing_deps:
            click.echo("\nMissing dependencies:", err=True)
            for error in missing_deps:
                click.echo(f"  - {error.spec_id} references @{error.missing}", err=True)
            sys.exit(1)

        # Report cycles (informational)
        cycles = resolver.find_cycles(specs)
        if cycles:
            click.echo(f"\nNote: {len(cycles)} circular @mention(s) (allowed in two-pass)")

        click.echo("All specs valid!")

    except ConfigError as e:
        click.echo(f"Configuration error: {e}", err=True)
        sys.exit(1)
    except ParseError as e:
        click.echo(f"Parse error: {e}", err=True)
        sys.exit(1)


@main.command()
@click.argument("spec_path", type=click.Path(exists=True, path_type=Path))
def show(spec_path: Path) -> None:
    """Show parsed content of a spec file.

    Useful for debugging spec parsing.
    """
    try:
        parser = SpecParser()
        spec = parser.parse_file(spec_path)

        click.echo(f"Spec: {spec.spec_id}")
        click.echo(f"Path: {spec.path}")
        click.echo(f"Category: {spec.category}")
        click.echo(f"Name: {spec.name}")

        click.echo(f"\nDependencies (@mentions): {spec.mentions or 'none'}")

        click.echo(f"\nDescription:\n{spec.description.content[:500]}...")

        click.echo(f"\nExports ({len(spec.exports.items)} items):")
        for item in spec.exports.items[:5]:
            click.echo(f"  - {item}")
        if len(spec.exports.items) > 5:
            click.echo(f"  ... and {len(spec.exports.items) - 5} more")

        click.echo(f"\nTests ({len(spec.tests.items)} items):")
        for item in spec.tests.items[:5]:
            click.echo(f"  - {item}")
        if len(spec.tests.items) > 5:
            click.echo(f"  ... and {len(spec.tests.items) - 5} more")

    except ParseError as e:
        click.echo(f"Parse error: {e}", err=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
