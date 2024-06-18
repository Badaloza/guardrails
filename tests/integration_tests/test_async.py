from unittest.mock import patch
import openai
import pytest

from guardrails.guard import Guard
from guardrails.prompt.prompt import Prompt
from guardrails.utils import docs_utils
from tests.integration_tests.test_assets.fixtures import (  # noqa
    fixture_llm_output,
    fixture_rail_spec,
    fixture_validated_output,
)

from .mock_llm_outputs import MockAsyncOpenAICallable, entity_extraction


# FIXME: None of these tests were ever updated to work with OpenAI 1.x
#   making them useless once we drop support for 0.x


@pytest.mark.asyncio
@pytest.mark.parametrize("multiprocessing_validators", (True, False))
@pytest.mark.skip(reason="Only for OpenAI v0")
async def test_entity_extraction_with_reask(mocker, multiprocessing_validators: bool):
    """Test that the entity extraction works with re-asking."""
    mocker.patch(
        "guardrails.llm_providers.AsyncOpenAICallable",
        new=MockAsyncOpenAICallable,
    )
    mocker.patch(
        "guardrails.validators.Validator.run_in_separate_process",
        new=multiprocessing_validators,
    )

    content = docs_utils.read_pdf("docs/examples/data/chase_card_agreement.pdf")
    guard = Guard.from_rail_string(entity_extraction.RAIL_SPEC_WITH_REASK)

    with patch(
        "guardrails.run.async_runner.preprocess_prompt"
    ) as mock_preprocess_prompt:
        final_output = await guard(
            llm_api=openai.Completion.acreate,
            prompt_params={"document": content[:6000]},
            num_reasks=1,
        )

        # Check that the preprocess_prompt method was called.
        mock_preprocess_prompt.assert_called()

    # Assertions are made on the guard state object.
    assert final_output.validation_passed is True
    assert final_output.validated_output == entity_extraction.VALIDATED_OUTPUT_REASK_2

    guard_history = guard.history
    call = guard_history.first

    # Check that the guard was only called once and
    # has the correct number of re-asks.
    assert guard_history.length == 1
    assert call.iterations.length == 2

    # For orginal prompt and output
    first = call.iterations.first
    assert first.inputs.prompt == Prompt(entity_extraction.COMPILED_PROMPT)
    # Same as above
    assert call.compiled_prompt == entity_extraction.COMPILED_PROMPT
    assert first.prompt_tokens_consumed == 123
    assert first.completion_tokens_consumed == 1234
    assert first.raw_output == entity_extraction.LLM_OUTPUT
    assert first.validation_response == entity_extraction.VALIDATED_OUTPUT_REASK_1

    # For re-asked prompt and output
    final = call.iterations.last
    assert final.inputs.prompt == Prompt(entity_extraction.COMPILED_PROMPT_REASK)
    # Same as above
    assert call.reask_prompts.last == entity_extraction.COMPILED_PROMPT_REASK
    assert final.raw_output == entity_extraction.LLM_OUTPUT_REASK
    assert call.guarded_output == entity_extraction.VALIDATED_OUTPUT_REASK_2


@pytest.mark.asyncio
@pytest.mark.skip(reason="Only for OpenAI v0")
async def test_entity_extraction_with_noop(mocker):
    mocker.patch(
        "guardrails.llm_providers.AsyncOpenAICallable",
        new=MockAsyncOpenAICallable,
    )
    content = docs_utils.read_pdf("docs/examples/data/chase_card_agreement.pdf")
    guard = Guard.from_rail_string(entity_extraction.RAIL_SPEC_WITH_NOOP)
    final_output = await guard(
        llm_api=openai.Completion.acreate,
        prompt_params={"document": content[:6000]},
        num_reasks=1,
    )

    # Assertions are made on the guard state object.

    # Old assertion which is wrong
    # This should not pass validation and therefore will not have a validated output
    # assert final_output.validated_output == entity_extraction.VALIDATED_OUTPUT_NOOP

    assert final_output.validation_passed is False
    assert final_output.validated_output is not None
    assert final_output.validated_output["fees"]
    assert final_output.validated_output["interest_rates"]

    call = guard.history.first

    # Check that the guard was called once
    # and did not have to reask
    assert guard.history.length == 1
    assert call.iterations.length == 1

    # For orginal prompt and output
    assert call.compiled_prompt == entity_extraction.COMPILED_PROMPT
    assert call.raw_outputs.last == entity_extraction.LLM_OUTPUT
    assert call.validation_response == entity_extraction.VALIDATED_OUTPUT_NOOP


@pytest.mark.asyncio
@pytest.mark.skip(reason="Only for OpenAI v0")
async def test_entity_extraction_with_noop_pydantic(mocker):
    mocker.patch(
        "guardrails.llm_providers.AsyncOpenAICallable",
        new=MockAsyncOpenAICallable,
    )
    content = docs_utils.read_pdf("docs/examples/data/chase_card_agreement.pdf")
    guard = Guard.from_pydantic(
        entity_extraction.PYDANTIC_RAIL_WITH_NOOP, entity_extraction.PYDANTIC_PROMPT
    )
    final_output = await guard(
        llm_api=openai.Completion.acreate,
        prompt_params={"document": content[:6000]},
        num_reasks=1,
    )

    # Assertions are made on the guard state object.
    assert final_output.validation_passed is False
    assert final_output.validated_output is not None
    assert final_output.validated_output["fees"]
    assert final_output.validated_output["interest_rates"]

    call = guard.history.first

    # Check that the guard was called once
    # and did not have toreask
    assert guard.history.length == 1
    assert call.iterations.length == 1

    # For orginal prompt and output
    assert call.compiled_prompt == entity_extraction.COMPILED_PROMPT
    assert call.raw_outputs.last == entity_extraction.LLM_OUTPUT
    assert call.validation_response == entity_extraction.VALIDATED_OUTPUT_NOOP


@pytest.mark.asyncio
@pytest.mark.skip(reason="Only for OpenAI v0")
async def test_entity_extraction_with_filter(mocker):
    """Test that the entity extraction works with re-asking."""
    mocker.patch(
        "guardrails.llm_providers.AsyncOpenAICallable",
        new=MockAsyncOpenAICallable,
    )

    content = docs_utils.read_pdf("docs/examples/data/chase_card_agreement.pdf")
    guard = Guard.from_rail_string(entity_extraction.RAIL_SPEC_WITH_FILTER)
    final_output = await guard(
        llm_api=openai.Completion.acreate,
        prompt_params={"document": content[:6000]},
        num_reasks=1,
    )

    # Assertions are made on the guard state object.
    assert final_output.validation_passed is False
    assert final_output.validated_output is None

    call = guard.history.first

    # Check that the guard state object has the correct number of re-asks.
    assert guard.history.length == 1
    assert call.iterations.length == 1

    # For orginal prompt and output
    assert call.compiled_prompt == entity_extraction.COMPILED_PROMPT
    assert call.raw_outputs.last == entity_extraction.LLM_OUTPUT
    assert call.validation_response == entity_extraction.VALIDATED_OUTPUT_FILTER
    assert call.guarded_output is None
    assert call.status == "fail"


@pytest.mark.asyncio
@pytest.mark.skip(reason="Only for OpenAI v0")
async def test_entity_extraction_with_fix(mocker):
    """Test that the entity extraction works with re-asking."""
    mocker.patch(
        "guardrails.llm_providers.AsyncOpenAICallable",
        new=MockAsyncOpenAICallable,
    )

    content = docs_utils.read_pdf("docs/examples/data/chase_card_agreement.pdf")
    guard = Guard.from_rail_string(entity_extraction.RAIL_SPEC_WITH_FIX)
    final_output = await guard(
        llm_api=openai.Completion.acreate,
        prompt_params={"document": content[:6000]},
        num_reasks=1,
    )

    # Assertions are made on the guard state object.
    assert final_output.validation_passed is True
    assert final_output.validated_output == entity_extraction.VALIDATED_OUTPUT_FIX

    call = guard.history.first

    # Check that the guard state object has the correct number of re-asks.
    assert guard.history.length == 1

    # For orginal prompt and output
    assert call.compiled_prompt == entity_extraction.COMPILED_PROMPT
    assert call.raw_outputs.last == entity_extraction.LLM_OUTPUT
    assert call.guarded_output == entity_extraction.VALIDATED_OUTPUT_FIX


@pytest.mark.asyncio
@pytest.mark.skip(reason="Only for OpenAI v0")
async def test_entity_extraction_with_refrain(mocker):
    """Test that the entity extraction works with re-asking."""
    mocker.patch(
        "guardrails.llm_providers.AsyncOpenAICallable",
        new=MockAsyncOpenAICallable,
    )

    content = docs_utils.read_pdf("docs/examples/data/chase_card_agreement.pdf")
    guard = Guard.from_rail_string(entity_extraction.RAIL_SPEC_WITH_REFRAIN)
    final_output = await guard(
        llm_api=openai.Completion.acreate,
        prompt_params={"document": content[:6000]},
        num_reasks=1,
    )
    # Assertions are made on the guard state object.

    assert final_output.validation_passed is False
    assert final_output.validated_output == entity_extraction.VALIDATED_OUTPUT_REFRAIN

    call = guard.history.first

    # Check that the guard state object has the correct number of re-asks.
    assert guard.history.length == 1

    # For orginal prompt and output
    assert call.compiled_prompt == entity_extraction.COMPILED_PROMPT
    assert call.raw_outputs.last == entity_extraction.LLM_OUTPUT
    assert call.guarded_output == entity_extraction.VALIDATED_OUTPUT_REFRAIN


@pytest.mark.asyncio
@pytest.mark.skip(reason="Only for OpenAI v0")
async def test_rail_spec_output_parse(rail_spec, llm_output, validated_output):
    """Test that the rail_spec fixture is working."""
    guard = Guard.from_rail_string(rail_spec)
    output = await guard.parse(
        llm_output,
        llm_api=openai.Completion.acreate,
    )
    assert output.validated_output == validated_output


@pytest.fixture
def string_rail_spec():
    return """
<rail version="0.1">
<output
  type="string"
  validators="two-words"
  on-fail-two-words="fix"
/>
<prompt>
Hi please make me a string
</prompt>
</rail>
"""


@pytest.fixture
def string_llm_output():
    return "string output yes"


@pytest.fixture
def validated_string_output():
    return "string output"
