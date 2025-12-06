import pytest
from unittest.mock import patch

@pytest.mark.asyncio
async def test_parser_agent():
    mock_response = '{"title": "Test", "body": "Body text", "publication_date": "2025-12-05", "source_url": "https://test.com"}'
    with patch('agents.request.call_llm', return_value=mock_response):
        from agents.parser_agent import run
        result = await run("Dummy news text")
        assert result["title"] == "Test"
        assert "body" in result
