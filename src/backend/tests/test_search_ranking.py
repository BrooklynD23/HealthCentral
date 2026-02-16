"""Tests for search module ranking logic."""

import pytest
from datetime import datetime
from modules.search import (
    reciprocal_rank_fusion,
    SearchResult,
    SearchModule,
    _snippet_to_plain_text,
)


class TestReciprocalRankFusion:
    def test_single_list(self):
        results = [
            SearchResult(id="a", type="observation", title="Glucose", score=1.0),
            SearchResult(id="b", type="observation", title="HbA1c", score=0.8),
        ]
        fused = reciprocal_rank_fusion([results], k=60)
        assert fused[0].id == "a"
        assert fused[1].id == "b"

    def test_two_lists_merge(self):
        list1 = [
            SearchResult(id="a", type="observation", title="Glucose", score=1.0),
            SearchResult(id="b", type="observation", title="HbA1c", score=0.8),
        ]
        list2 = [
            SearchResult(id="b", type="observation", title="HbA1c", score=1.0),
            SearchResult(id="c", type="chunk", title="Doc chunk", score=0.5),
        ]
        fused = reciprocal_rank_fusion([list1, list2], k=60)
        # "b" appears in both lists, should be ranked higher
        ids = [r.id for r in fused]
        assert ids.index("b") < ids.index("c")

    def test_empty_lists(self):
        fused = reciprocal_rank_fusion([], k=60)
        assert fused == []

    def test_score_is_rrf_sum(self):
        list1 = [SearchResult(id="a", type="observation", title="X", score=1.0)]
        list2 = [SearchResult(id="a", type="observation", title="X", score=1.0)]
        fused = reciprocal_rank_fusion([list1, list2], k=60)
        # rank 1 in both => 1/(60+1) + 1/(60+1) = 2/61
        expected = 2.0 / 61.0
        assert abs(fused[0].score - expected) < 0.001

    def test_deduplication_by_id(self):
        list1 = [SearchResult(id="a", type="observation", title="X", score=1.0)]
        list2 = [SearchResult(id="a", type="observation", title="X", score=0.9)]
        fused = reciprocal_rank_fusion([list1, list2], k=60)
        assert len(fused) == 1


class _FakeSqlResult:
    def __init__(self, rows):
        self._rows = rows

    def fetchall(self):
        return self._rows


class _FakeProfileDb:
    def __init__(self):
        self._calls = 0

    async def execute(self, _sql, _params):
        self._calls += 1
        if self._calls == 1:
            return _FakeSqlResult([
                type(
                    "Row",
                    (),
                    {
                        "id": "obs-1",
                        "analyte_canonical": "Glucose",
                        "value": 95.0,
                        "unit": "mg/dL",
                        "collected_at": datetime(2024, 1, 15),
                        "is_abnormal": False,
                        "snip": "<b>Glucose</b> <script>alert(1)</script> match",
                    },
                )()
            ])

        return _FakeSqlResult([
            type(
                "Row",
                (),
                {
                    "id": "chunk-1",
                    "doc_id": "doc-1",
                    "text": "<i>Document body</i>",
                    "page_number": 1,
                    "snip": "showing <b>chunk</b> text",
                },
            )()
        ])


class TestSearchSnippetSecurity:
    def test_snippet_helper_removes_html_tags(self):
        text = _snippet_to_plain_text("<b>Glucose</b> &amp; <script>bad()</script>")
        assert text == "Glucose & bad()"

    @pytest.mark.asyncio
    async def test_search_fulltext_returns_plain_text_snippets(self):
        search = SearchModule()
        profile_db = _FakeProfileDb()

        results = await search.search_fulltext(
            query="glucose",
            profile_db=profile_db,
            profile_id="profile-1",
            limit=5,
        )

        assert len(results) == 2
        assert "<" not in results[0].snippet and ">" not in results[0].snippet
        assert "<" not in results[1].snippet and ">" not in results[1].snippet
        assert "Glucose" in results[0].snippet
        assert "chunk" in results[1].snippet
