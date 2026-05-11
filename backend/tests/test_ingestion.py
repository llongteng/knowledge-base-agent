import unittest

from app.services.chunker import chunk_segments
from app.services.document_parser import parse_bytes


class IngestionTests(unittest.TestCase):
    def test_markdown_keeps_heading_path_in_chunks(self):
        segments = parse_bytes(
            filename="policy.md",
            content=b"# Refunds\n\n## Enterprise\nRefunds after 7 days require manual review.",
            content_type="text/markdown",
        )

        chunks = chunk_segments(segments, chunk_size=80, overlap=10)

        self.assertEqual(chunks[0].title_path, "Refunds > Enterprise")
        self.assertIn("manual review", chunks[0].content)
        self.assertEqual(chunks[0].paragraph_index, 1)

    def test_csv_rows_become_traceable_row_chunks(self):
        segments = parse_bytes(
            filename="plans.csv",
            content="plan,refund_window\nEnterprise,14 days\nPersonal,7 days\n".encode(),
            content_type="text/csv",
        )

        self.assertEqual(len(segments), 2)
        self.assertIn("plan: Enterprise", segments[0].content)
        self.assertEqual(segments[0].row_number, 2)
        self.assertEqual(segments[1].row_number, 3)


if __name__ == "__main__":
    unittest.main()
