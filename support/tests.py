from unittest import TestCase, mock
from support.rag import _sparse_retrieve, _reciprocal_rank_fusion, hybrid_retrieve
from support.models import DocumentChunk


class HybridRAGTests(TestCase):
    def test_sparse_retrieve_empty_query(self):
        """Empty query should return an empty list immediately without hitting DB."""
        results = _sparse_retrieve("", DocumentChunk.objects.none(), top_k=5)
        self.assertEqual(results, [])

    def test_sparse_retrieve_whitespace_query(self):
        """Whitespace query should return an empty list."""
        results = _sparse_retrieve("   ", DocumentChunk.objects.none(), top_k=5)
        self.assertEqual(results, [])

    def test_reciprocal_rank_fusion_order(self):
        """
        Verify RRF correctly merges dense and sparse results.
        An item appearing in both lists should float to the top.
        """
        chunk1 = mock.MagicMock(id=1)
        chunk2 = mock.MagicMock(id=2)
        chunk3 = mock.MagicMock(id=3)

        # chunk1 is rank 1 in dense and rank 1 in sparse
        dense_chunks = [chunk1, chunk2]
        sparse_chunks = [chunk1, chunk3]

        fused = _reciprocal_rank_fusion(dense_chunks, sparse_chunks, top_k=3, k=60)
        self.assertEqual(fused[0].id, 1)
        self.assertEqual(len(fused), 3)

    @mock.patch("support.rag.DocumentChunk.objects.select_related")
    def test_hybrid_retrieve_empty_database(self, mock_select_related):
        """hybrid_retrieve should return empty list gracefully when no documents exist."""
        mock_qs = mock.MagicMock()
        mock_qs.filter.return_value = mock_qs
        mock_qs.exists.return_value = False
        mock_select_related.return_value = mock_qs

        results = hybrid_retrieve("What is the refund policy?")
        self.assertEqual(results, [])
