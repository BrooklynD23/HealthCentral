"""Tests for search module ranking logic."""

import pytest
from modules.search import reciprocal_rank_fusion, SearchResult


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
