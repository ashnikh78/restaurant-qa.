import pytest
from src.pipeline import RAGPipeline
from src.config import AppConfig

@pytest.fixture
def pipeline():
    config = AppConfig(
        data_dir="data",
        chroma_persist_dir="chroma_db_test",
        llm_model="deepseek-llm:7b",
        embed_model="all-MiniLM-L6-v2"
    )
    return RAGPipeline(config)

def test_answer_query(pipeline):
    query = "What kind of food does Eleven Madison Park serve?"
    answer, sources = pipeline.answer_query(query)
    assert isinstance(answer, str)
    assert isinstance(sources, str)
    assert len(answer) > 0
    assert "No answer found" not in answer

def test_empty_query(pipeline):
    answer, sources = pipeline.answer_query("")
    assert answer == "Please enter a question."
    assert sources == ""