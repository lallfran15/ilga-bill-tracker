from scrape_committee import extract_schedule_text, has_schedule_changed, validate_schedule_text


# --- Sample HTML fragments mimicking ILGA committee pages ---

HEARING_HTML = """
<div id="scheduled">
  <div>
    <table>
      <tbody>
        <tr>
          <td>3/24/2026 2:00 PM</td>
          <td>Room 114</td>
        </tr>
      </tbody>
    </table>
  </div>
</div>
"""

NO_HEARING_HTML = """
<div id="scheduled">
  <div>
    <table>
      <tbody>
        <tr>
          <td>No Hearings Scheduled</td>
        </tr>
      </tbody>
    </table>
  </div>
</div>
"""

SENATE_HTML = """
<div id="scheduled">
  <div>
    <table>
      <tbody>
        <tr>
          <td><p>3/25/2026 10:00 AM</p></td>
        </tr>
      </tbody>
    </table>
  </div>
</div>
"""

EMPTY_PAGE_HTML = """
<div id="main-content">
  <p>Welcome to the committee page.</p>
</div>
"""


# --- Tests for extract_schedule_text ---

class TestExtractScheduleText:
    def test_primary_selector_matches(self):
        selectors = [
            "#scheduled > div > table > tbody > tr > td:nth-child(1)",
            "#scheduled td",
        ]
        result = extract_schedule_text(HEARING_HTML, selectors)
        assert result == "3/24/2026 2:00 PM"

    def test_fallback_selector_matches(self):
        # Use a broken primary selector so it falls through to the fallback
        selectors = [
            "#nonexistent > div > table",
            "#scheduled td",
        ]
        result = extract_schedule_text(HEARING_HTML, selectors)
        assert result == "3/24/2026 2:00 PM"

    def test_senate_paragraph_selector(self):
        selectors = [
            "#scheduled > div > table > tbody > tr > td > p",
            "#scheduled td",
        ]
        result = extract_schedule_text(SENATE_HTML, selectors)
        assert result == "3/25/2026 10:00 AM"

    def test_no_selector_matches(self):
        selectors = [
            "#nonexistent > div",
            "#also-nonexistent td",
        ]
        result = extract_schedule_text(EMPTY_PAGE_HTML, selectors)
        assert result is None

    def test_no_hearings_scheduled(self):
        selectors = ["#scheduled td"]
        result = extract_schedule_text(NO_HEARING_HTML, selectors)
        assert "No Hearings Scheduled" in result


# --- Tests for has_schedule_changed ---

class TestHasScheduleChanged:
    def test_identical_text(self):
        assert not has_schedule_changed("3/24/2026 2:00 PM", "3/24/2026 2:00 PM")

    def test_trailing_whitespace_ignored(self):
        assert not has_schedule_changed("3/24/2026 2:00 PM\n", "3/24/2026 2:00 PM")

    def test_leading_whitespace_ignored(self):
        assert not has_schedule_changed("  3/24/2026 2:00 PM", "3/24/2026 2:00 PM  ")

    def test_actual_content_change(self):
        assert has_schedule_changed("3/25/2026 10:00 AM", "3/24/2026 2:00 PM")

    def test_empty_old_text(self):
        assert has_schedule_changed("3/24/2026 2:00 PM", "")

    def test_both_empty(self):
        assert not has_schedule_changed("", "")


# --- Tests for validate_schedule_text ---

class TestValidateScheduleText:
    def test_valid_date_text(self):
        assert validate_schedule_text("3/24/2026 2:00 PM", "Test Committee")

    def test_no_hearings_text(self):
        assert validate_schedule_text("No Hearings Scheduled", "Test Committee")

    def test_empty_text_invalid(self):
        assert not validate_schedule_text("", "Test Committee")

    def test_whitespace_only_invalid(self):
        assert not validate_schedule_text("   ", "Test Committee")

    def test_none_invalid(self):
        assert not validate_schedule_text(None, "Test Committee")

    def test_very_long_text_invalid(self):
        long_text = "x" * 6000
        assert not validate_schedule_text(long_text, "Test Committee")
