"""
LLM Client Usage Examples

This file demonstrates the new unified API for LLM operations.
Run with: python -m common.llm.examples
"""

import asyncio
from typing import Literal

from dotenv import load_dotenv
from pydantic import BaseModel, Field

from common.logger.utils.helpers import get_logger

logger = get_logger(__name__)
load_dotenv()


# =============================================================================
# Example 1: Basic Ask - Plain Text Response
# =============================================================================
async def example_basic_ask():
    """Simple text response using unified ask() API."""
    from common.llm import ask

    logger.info("=== Example 1: Basic Ask - Plain Text ===")

    # Simple question
    answer = await ask("What is the capital of France?")
    logger.info("Answer", answer=answer)

    # With system prompt
    answer = await ask(
        "Explain quantum computing",
        system="You are a physics professor. Be concise.",
        temperature=0.5,
    )
    logger.info("Explanation:", answer=answer)


# =============================================================================
# Example 2: Structured Output with Pydantic Models
# =============================================================================
class Person(BaseModel):
    """Person information model."""

    name: str = Field(description="Person's full name")
    age: int = Field(description="Person's age in years")
    occupation: str = Field(default="unknown", description="Person's job")


async def example_structured_output():
    """Extract structured data using Pydantic models."""
    from common.llm import INSTRUCTOR_AVAILABLE, ask

    logger.info("=== Example 2: Structured Output ===")

    if not INSTRUCTOR_AVAILABLE:
        logger.warning("Instructor not available. Install with: pip install instructor")
        return

    # Extract person information
    person = await ask(
        "Extract: Dr. Jane Smith is a 42-year-old neurologist.",
        response_model=Person,
    )
    logger.info(
        "Extracted",
        person=person,
    )

    # Multiple extractions
    class Product(BaseModel):
        name: str
        price: float
        category: str

    product = await ask(
        "The iPhone 15 Pro costs $999 and is a smartphone",
        response_model=Product,
        system="Extract product details accurately",
    )
    logger.info("Extracted product", product=product)


# =============================================================================
# Example 3: Streaming Response
# =============================================================================
async def example_streaming():
    """Stream response token by token."""
    from common.llm import ask_stream

    logger.info("=== Example 3: Streaming Response ===")
    logger.info("Streaming story: ")

    full_content = ""
    async for chunk in ask_stream(
        "Tell me a very short story about a robot (2 sentences max)",
        temperature=0.8,
    ):
        print(chunk.delta, end="", flush=True)
        full_content = chunk.content

    print()  # Newline after streaming
    logger.info(f"Stream complete. Total length: {len(full_content)} chars")


# =============================================================================
# Example 4: Batch Processing
# =============================================================================
async def example_batch_processing():
    """Process multiple prompts concurrently."""
    from common.llm import ask_batch

    logger.info("=== Example 4: Batch Processing ===")

    # Batch text responses
    prompts = [
        "What is 2+2?",
        "What is the speed of light?",
        "What is the capital of Japan?",
    ]

    results = await ask_batch(prompts, temperature=0.3)

    for i, result in enumerate(results):
        if isinstance(result, Exception):
            logger.error(f"Prompt {i} failed: {result}")
        else:
            logger.info(f"Q{i + 1}: {prompts[i][:30]}... → {result[:50]}...")

    # Batch structured responses
    class Sentiment(BaseModel):
        label: str = Field(description="positive, negative, or neutral")
        score: float = Field(ge=0.0, le=1.0, description="confidence score")

    texts = [
        "I absolutely love this product!",
        "This is terrible, worst purchase ever.",
        "It's okay, nothing special.",
    ]

    sentiments = await ask_batch(
        texts,
        response_model=Sentiment,
        system="Classify sentiment accurately",
        temperature=0.2,
    )

    logger.info("Sentiment analysis results:")
    for text, sentiment in zip(texts, sentiments, strict=False):
        if isinstance(sentiment, Exception):
            logger.error(f"Failed: {sentiment}")
        else:
            logger.info(
                f"  '{text[:30]}...' → {sentiment.label} ({sentiment.score:.2f})"
            )


async def example_batch_processing_versus_sequential():
    """Compare batch processing vs sequential calls."""
    import time

    from common.llm import ask, ask_batch

    logger.info("=== Example 4b: Batch vs Sequential ===")

    prompts = [
        "What is the capital of Germany?",
        "What is the capital of Italy?",
        "What is the capital of Canada?",
        "What is the capital of Australia?",
        "What is the capital of Brazil?",
    ]

    # Sequential
    start_seq = time.time()
    results_seq = []
    for prompt in prompts:
        answer = await ask(prompt)
        results_seq.append(answer)
    time_seq = time.time() - start_seq
    logger.info(f"Sequential took {time_seq:.2f}s")

    # Batch
    start_batch = time.time()
    results_batch = await ask_batch(prompts)
    time_batch = time.time() - start_batch
    logger.info(f"Batch took {time_batch:.2f}s")

    # Log results
    for i, (seq, batch) in enumerate(zip(results_seq, results_batch, strict=False)):
        logger.info(f"Q{i + 1}: Seq='{seq}' | Batch='{batch}'")


# =============================================================================
# Example 5: Conversation with History
# =============================================================================
async def example_conversation_history():
    """Multi-turn conversation using history parameter."""
    from common.llm import ask

    logger.info("=== Example 5: Conversation with History ===")

    # Start conversation
    history = []

    response1 = await ask(
        "My name is Alice and I love Python programming",
        history=history,
    )
    logger.info(f"Assistant: {response1}")

    # Add to history
    history.append(
        {"role": "user", "content": "My name is Alice and I love Python programming"}
    )
    history.append({"role": "assistant", "content": response1})

    # Continue conversation
    response2 = await ask(
        "What's my name and what do I love?",
        history=history,
    )
    logger.info(f"Assistant (remembers): {response2}")

    # One more turn
    history.append({"role": "user", "content": "What's my name and what do I love?"})
    history.append({"role": "assistant", "content": response2})

    response3 = await ask(
        "Suggest a Python project for me",
        history=history,
        temperature=0.7,
    )
    logger.info(f"Assistant (contextual): {response3}")


# =============================================================================
# Example 6: Global Configuration
# =============================================================================
async def example_global_config():
    """Use global default configuration."""
    from common.llm import LLMConfig, ask, set_default_config

    logger.info("=== Example 6: Global Configuration ===")

    # Set global config
    set_default_config(
        LLMConfig(
            model="gpt-4o-mini",
            enable_cache=True,
            cache_ttl=300,
            default_temperature=0.3,
        )
    )

    # Now all ask() calls use this config by default
    answer1 = await ask("What is 5+5?")
    logger.info(f"Using global config: {answer1}")

    # Can still override specific parameters
    answer2 = await ask(
        "Write a creative tagline",
        temperature=0.9,  # Override global temperature
    )
    logger.info(f"With override: {answer2}")


# =============================================================================
# Example 7: Advanced - Classification Task
# =============================================================================
async def example_classification():
    """Classification using structured outputs."""
    from common.llm import ask

    logger.info("=== Example 7: Classification Task ===")

    class EmailClassification(BaseModel):
        category: Literal["spam", "important", "promotional", "personal"]
        confidence: float = Field(ge=0.0, le=1.0)
        reason: str = Field(description="Brief explanation")

    email = """
    Subject: URGENT: You've won $1,000,000!
    Click here now to claim your prize! Limited time offer!
    """

    result = await ask(
        f"Classify this email:\n{email}",
        response_model=EmailClassification,
        system="You are an email spam filter. Analyze carefully.",
        temperature=0.2,
    )

    logger.info(f"Category: {result.category}")
    logger.info(f"Confidence: {result.confidence:.2%}")
    logger.info(f"Reason: {result.reason}")


# =============================================================================
# Example 8: Advanced - Data Extraction
# =============================================================================
async def example_data_extraction():
    """Extract complex structured data."""
    from common.llm import ask

    logger.info("=== Example 8: Data Extraction ===")

    class Event(BaseModel):
        name: str
        date: str
        location: str
        attendees: int

    class EventList(BaseModel):
        events: list[Event]

    text = """
    Upcoming tech events:
    1. PyCon 2024 in Pittsburgh from May 15-23 with 2500 attendees
    2. Django Con in Durham, NC on October 6-11 expecting 800 people
    3. JS Conf in Austin, Texas - June 7-9, around 1200 participants
    """

    result = await ask(
        f"Extract all events:\n{text}",
        response_model=EventList,
        system="Extract event information accurately. Use ISO date format where possible.",
    )

    logger.info(f"Extracted {len(result.events)} events:")
    for event in result.events:
        logger.info(
            f"  • {event.name} | {event.date} | {event.location} | {event.attendees} people"
        )


# =============================================================================
# Example 9: Error Handling in Batch
# =============================================================================
async def example_error_handling():
    """Handle errors gracefully in batch processing."""
    from common.llm import ask_batch

    logger.info("=== Example 9: Error Handling ===")

    # Mix of valid and potentially problematic prompts
    prompts = [
        "What is 2+2?",
        "What is the capital of France?",
        "Translate 'hello' to Spanish",
    ]

    results = await ask_batch(
        prompts,
        temperature=0.3,
        max_tokens=50,
    )

    successes = 0
    failures = 0

    for i, (_prompt, result) in enumerate(zip(prompts, results, strict=False)):
        if isinstance(result, Exception):
            logger.error(f"Request {i + 1} failed: {result}")
            failures += 1
        else:
            logger.info(f"Request {i + 1} succeeded: {result[:50]}...")
            successes += 1

    logger.info(f"Summary: {successes} successes, {failures} failures")


# =============================================================================
# Example 10: Different Models and Providers
# =============================================================================
async def example_providers():
    """Use different models and providers."""
    from common.llm import ask

    logger.info("=== Example 10: Providers & Models ===")

    # OpenAI GPT-4o-mini (default)
    answer1 = await ask("What is AI?", model="gpt-4o-mini")
    logger.info(f"GPT-4o-mini: {answer1[:80]}...")

    # Can use custom config for advanced scenarios
    # ollama_config = ModelPresets.ollama_llama3()
    # answer2 = await ask("What is AI?", config=ollama_config)
    # logger.info(f"Ollama: {answer2[:80]}...")

    logger.info("Provider configuration examples available in ModelPresets")


# =============================================================================
# Example 11: Caching Demonstration
# =============================================================================
async def example_caching():
    """Demonstrate response caching."""
    import time

    from common.llm import ask

    logger.info("=== Example 11: Caching ===")

    question = "What is the speed of light in vacuum?"

    # First call - hits API
    start = time.time()
    answer1 = await ask(question, temperature=0, enable_cache=True)
    time1 = time.time() - start
    logger.info(f"First call: {time1:.3f}s")
    logger.info("Answer", answer=answer1)

    # Second call - hits cache (much faster)
    start = time.time()
    answer2 = await ask(question, temperature=0, enable_cache=True)
    time2 = time.time() - start
    logger.info(f"Second call (cached): {time2:.3f}s")
    logger.info("Answer", answer=answer2)
    logger.info(f"Speedup: {time1 / time2:.1f}x faster")

    # Third call - hits cache again
    start = time.time()
    answer3 = await ask(question, temperature=0, enable_cache=True)
    time3 = time.time() - start
    logger.info(f"Third call: {time3:.3f}s")
    logger.info("Answer", answer=answer3)
    logger.info(f"Speedup: {time1 / time3:.1f}x faster")


# =============================================================================
# Example 12: JSON Output (Structured)
# =============================================================================
async def example_json_output():
    """Get JSON with Pydantic model."""
    from common.llm import ask

    logger.info("=== Example 12: JSON Output ===")

    # Use Pydantic for type-safe JSON
    class ColorList(BaseModel):
        colors: list[str]
        count: int

    result = await ask(
        "List 5 rainbow colors",
        response_model=ColorList,
        system="Return colors as a structured list",
    )

    logger.info(f"Colors ({result.count}): {', '.join(result.colors)}")


# =============================================================================
# Example 13: Tool Calling (using LLMClient directly)
# =============================================================================
async def example_tool_calling():
    """Use tool/function calling with LLMClient."""
    from common.llm import LLMClient, LLMConfig, ToolDefinition

    logger.info("=== Example 13: Tool Calling ===")

    config = LLMConfig(model="gpt-4o-mini")

    tools = [
        ToolDefinition(
            name="get_weather",
            description="Get current weather for a city",
            parameters={
                "type": "object",
                "properties": {
                    "city": {"type": "string", "description": "City name"},
                    "unit": {"type": "string", "enum": ["celsius", "fahrenheit"]},
                },
                "required": ["city"],
            },
        ),
    ]

    async with LLMClient(config) as client:
        response = await client.chat(
            [{"role": "user", "content": "What's the weather in Tokyo?"}],
            tools=tools,
            tool_choice="auto",
        )

        if response.has_tool_calls:
            for tool_call in response.tool_calls:
                logger.info(f"Tool: {tool_call.name}")
                logger.info(f"Arguments: {tool_call.parse_arguments()}")
        else:
            logger.info(f"Response: {response.content}")


# =============================================================================
# Main
# =============================================================================
async def main():
    """Run all examples."""
    separator = "=" * 70
    logger.info(separator)
    logger.info("LLM Client Examples - New Unified API")
    logger.info(separator)

    try:
        # Real API examples (require OpenAI API key)
        # await example_basic_ask()
        await example_structured_output()
        # await example_streaming()
        # await example_batch_processing()
        # await example_batch_processing_versus_sequential()
        # await example_conversation_history()
        # await example_global_config()
        # await example_classification()
        # await example_data_extraction()
        # await example_error_handling()
        # await example_providers()
        # await example_caching()
        # await example_json_output()
        # await example_tool_calling()

    except Exception as e:
        logger.error(f"Example failed: {e}", exc_info=True)
        raise

    logger.info(separator)
    logger.info("✅ All examples completed successfully!")
    logger.info(separator)


if __name__ == "__main__":
    asyncio.run(main())
