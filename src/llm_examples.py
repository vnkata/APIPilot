"""
LLM Examples with Log Level Testing and Langfuse Integration

Tests various log level configurations for LLM helper functions
and demonstrates Langfuse observability integration.
"""

from common.llm import LLMClient, ask, ask_stream, ask_batch, LLMConfig
from common.logger import get_logger, LogLevel
from dotenv import load_dotenv
import asyncio

load_dotenv()

logger = get_logger(__name__)


async def test_default_log_level():
    """Test 1: Default behavior (no log_level specified) - should use INFO."""
    print("\n" + "=" * 70)
    print("Test 1: Default log level (INFO)")
    print("=" * 70)
    logger.info("Starting test with default log level")

    # This should use INFO level (default)
    result = await ask("What is 2+2? Give a simple one-word answer.")
    print(f"Result: {result}")

    logger.info("Test 1 completed")


async def test_function_param_debug():
    """Test 2: Function parameter log_level=DEBUG - should show debug logs."""
    print("\n" + "=" * 70)
    print("Test 2: Function parameter log_level=DEBUG")
    print("=" * 70)
    logger.info("Starting test with DEBUG log level via function parameter")

    # This should show debug logs
    result = await ask(
        "What is 3+3? Give a simple one-word answer.", log_level=LogLevel.DEBUG
    )
    print(f"Result: {result}")

    logger.info("Test 2 completed (debug logs should be visible above)")


async def test_function_param_warning():
    """Test 3: Function parameter log_level=WARNING - should hide info/debug logs."""
    print("\n" + "=" * 70)
    print("Test 3: Function parameter log_level=WARNING")
    print("=" * 70)
    logger.info("This info log should be visible before the call")

    # This should hide info/debug logs (only warnings/errors visible)
    result = await ask(
        "What is 4+4? Give a simple one-word answer.", log_level=LogLevel.WARNING
    )
    print(f"Result: {result}")
    logger.info("This info log should be visible after the call")

    print("Note: Info/debug logs during the LLM call should be suppressed")


async def test_config_log_level():
    """Test 4: LLMConfig.log_level - should use config level."""
    print("\n" + "=" * 70)
    print("Test 4: LLMConfig.log_level=DEBUG")
    print("=" * 70)
    logger.info("Starting test with DEBUG log level via config")

    # Create config with DEBUG log level
    config = LLMConfig(log_level=LogLevel.DEBUG)
    result = await ask("What is 5+5? Give a simple one-word answer.", config=config)
    print(f"Result: {result}")

    logger.info("Test 4 completed (debug logs from config should be visible)")


async def test_function_param_overrides_config():
    """Test 5: Function parameter overrides config - function param takes priority."""
    print("\n" + "=" * 70)
    print("Test 5: Function parameter overrides config")
    print("=" * 70)
    logger.info(
        "Starting test: function param (WARNING) should override config (DEBUG)"
    )

    # Config says DEBUG, but function param says WARNING - WARNING should win
    config = LLMConfig(log_level=LogLevel.DEBUG)
    result = await ask(
        "What is 6+6? Give a simple one-word answer.",
        config=config,
        log_level=LogLevel.WARNING,  # This should override config
    )
    print(f"Result: {result}")

    logger.info("Test 5 completed (should use WARNING, suppressing info/debug)")


async def test_ask_batch_log_level():
    """Test 6: ask_batch with log_level - should apply to batch operations."""
    print("\n" + "=" * 70)
    print("Test 6: ask_batch with log_level=DEBUG")
    print("=" * 70)
    logger.info("Starting batch test with DEBUG log level")

    prompts = [
        "What is 1+1? Answer in one word.",
        "What is 2+2? Answer in one word.",
        "What is 3+3? Answer in one word.",
    ]

    results = await ask_batch(prompts, log_level=LogLevel.DEBUG)

    print("Batch results:")
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            print(f"  Prompt {i+1}: Error - {result}")
        else:
            print(f"  Prompt {i+1}: {result}")

    logger.info("Test 6 completed")


async def test_ask_stream_log_level():
    """Test 7: ask_stream with log_level - should apply to streaming."""
    print("\n" + "=" * 70)
    print("Test 7: ask_stream with log_level=DEBUG")
    print("=" * 70)
    logger.info("Starting stream test with DEBUG log level")

    print("Streaming response (should see debug logs):")
    async for chunk in ask_stream(
        "Count from 1 to 5. Say only the numbers.", log_level=LogLevel.DEBUG
    ):
        print(chunk.delta, end="", flush=True)
    print()  # Newline after stream

    logger.info("Test 7 completed")


async def test_all_scenarios():
    """Run all test scenarios."""
    print("\n" + "#" * 70)
    print("# LLM Log Level Control Tests")
    print("#" * 70)

    try:
        await test_default_log_level()
        await test_function_param_debug()
        await test_function_param_warning()
        await test_config_log_level()
        await test_function_param_overrides_config()
        await test_ask_batch_log_level()
        await test_ask_stream_log_level()

        print("\n" + "=" * 70)
        print("All tests completed successfully!")
        print("=" * 70)
        print("\nCheck the log files to verify log levels:")
        print("- logs/common_llm_helpers.log (should show different verbosity levels)")
        print("- Console output above shows log messages at different levels")

    except Exception as e:
        logger.error(f"Test failed with error: {e}", exc_info=True)
        raise


async def test_langfuse_integration():
    """
    Test Langfuse integration with LLM calls.

    This demonstrates how to configure and use Langfuse for observability.
    Langfuse captures full LLM call details: prompts, responses, token usage, and metadata.

    Setup:
        1. Install Langfuse: pip install langfuse
        2. Start Langfuse (self-hosted): docker-compose up (if using self-hosted)
           OR use cloud.langfuse.com
        3. Set environment variables:
           - LANGFUSE_PUBLIC_KEY: Your Langfuse public key
           - LANGFUSE_SECRET_KEY: Your Langfuse secret key
           - LANGFUSE_HOST: Langfuse host URL (defaults to http://localhost:3000 if not set)

    Verification:
        1. Run this test
        2. Check Langfuse UI (default: http://localhost:3000 for self-hosted)
        3. Verify traces appear with:
           - Input messages (prompts)
           - Output responses
           - Token usage (prompt_tokens, completion_tokens, total_tokens)
           - Model name
           - Metadata (provider, request_id, temperature, etc.)
    """
    print("\n" + "=" * 70)
    print("Langfuse Integration Test")
    print("=" * 70)

    print("\n1. Testing chat() with Langfuse tracing...")
    async with LLMClient() as client:
        response = await client.chat(
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "What is 2+2? Answer in one word."},
            ]
        )
        print(f"   Response: {response.content}")
        print(f"   Tokens used: {response.usage.total_tokens}")

    print("\n2. Testing stream() with Langfuse tracing...")
    async with LLMClient() as client:
        accumulated = ""
        async for chunk in client.stream(
            messages=[
                {"role": "user", "content": "Count from 1 to 5. Say only numbers."}
            ]
        ):
            print(chunk.delta, end="", flush=True)
            accumulated = chunk.content
        print()
        print(f"   Full response: {accumulated}")

    print("\n3. Testing helper functions with Langfuse...")
    # Create a config for helper functions
    config_for_helpers = LLMConfig()

    result = await ask(
        "What is the capital of France? Answer in one word.",
        config=config_for_helpers,
    )
    print(f"   Response: {result}")

    print("\n[OK] Langfuse integration test completed!")
    print("\n[INFO] Next steps:")
    print("   1. Open Langfuse UI:")
    print("   2. Navigate to 'Traces' or 'Generations' section")
    print("   3. Verify you see:")
    print("      - Input messages (prompts)")
    print("      - Output responses")
    print("      - Token usage statistics")
    print("      - Model information")
    print("      - Metadata (request_id, provider, temperature, etc.)")


async def test_all_scenarios_with_langfuse():
    """Run all log level tests plus Langfuse integration test."""
    try:
        # await test_all_scenarios()
        print("\n" + "=" * 70)
        await test_langfuse_integration()
    except Exception as e:
        logger.error(f"Test failed with error: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    # Run all tests (log level + Langfuse)
    # To run only log level tests, use: asyncio.run(test_all_scenarios())
    # To run only Langfuse test, use: asyncio.run(test_langfuse_integration())
    asyncio.run(test_all_scenarios_with_langfuse())
