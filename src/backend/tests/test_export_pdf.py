"""Tests for PDF export with chart generation."""

import pytest
from datetime import datetime
from modules.export import ExportModule


class TestGenerateChartImage:
    """Tests for ExportModule.generate_chart_image."""

    def setup_method(self):
        self.export = ExportModule()

    def test_returns_png_bytes(self):
        data_points = [
            {"collected_at": datetime(2024, 1, 1), "value": 95.0},
            {"collected_at": datetime(2024, 6, 1), "value": 102.0},
            {"collected_at": datetime(2024, 12, 1), "value": 98.0},
        ]
        result = self.export.generate_chart_image(
            analyte="glucose",
            data_points=data_points,
            unit="mg/dL",
            ref_low=70.0,
            ref_high=100.0,
        )
        assert isinstance(result, bytes)
        assert result[:8] == b'\x89PNG\r\n\x1a\n'  # PNG magic bytes

    def test_empty_data_returns_empty_bytes(self):
        result = self.export.generate_chart_image(
            analyte="glucose",
            data_points=[],
            unit="mg/dL",
        )
        assert result == b''

    def test_single_point_returns_png(self):
        data_points = [
            {"collected_at": datetime(2024, 1, 1), "value": 95.0},
        ]
        result = self.export.generate_chart_image(
            analyte="glucose",
            data_points=data_points,
            unit="mg/dL",
        )
        assert isinstance(result, bytes)
        assert len(result) > 0

    def test_abnormal_points_highlighted(self):
        data_points = [
            {"collected_at": datetime(2024, 1, 1), "value": 95.0, "is_abnormal": False},
            {"collected_at": datetime(2024, 6, 1), "value": 130.0, "is_abnormal": True},
        ]
        result = self.export.generate_chart_image(
            analyte="glucose",
            data_points=data_points,
            unit="mg/dL",
            ref_low=70.0,
            ref_high=100.0,
        )
        assert isinstance(result, bytes)
        assert len(result) > 100  # Non-trivial image


class TestRenderHtmlWithCharts:
    """Tests for ExportModule.render_html_summary with chart_images."""

    def setup_method(self):
        self.export = ExportModule()

    def test_charts_embedded_as_base64(self):
        summary_data = {
            "key_findings": ["Glucose: 130 mg/dL (H)"],
            "sections": [{"title": "Overview", "content": "Test"}],
            "questions": [],
        }
        # Minimal 1x1 red PNG
        chart_images = {"glucose": b'\x89PNG\r\n\x1a\n' + b'\x00' * 50}
        result = self.export.render_html_summary(
            summary_data, chart_images=chart_images
        )
        assert "data:image/png;base64," in result
        assert "glucose" in result.lower()

    def test_no_charts_produces_standard_html(self):
        summary_data = {
            "key_findings": [],
            "sections": [{"title": "Overview", "content": "Test"}],
            "questions": [],
        }
        result = self.export.render_html_summary(summary_data, chart_images={})
        assert "data:image/png;base64," not in result
