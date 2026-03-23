import os
import tempfile

from fetch_bills import detect_changes, read_bill_list, load_old_data


SAMPLE_MASTER_LIST = {
    "session": {"session_id": 2345, "session_name": "104th General Assembly"},
    "0": {
        "number": "HB4068",
        "title": "SCH CD-ACCOMODATIONS-TIMELINE",
        "last_action": "Referred to Rules Committee",
        "last_action_date": "2026-03-18",
        "url": "https://legiscan.com/IL/bill/HB4068/2025"
    },
    "1": {
        "number": "HB1783",
        "title": "ST BD ED-LANGUAGE ASSESSMENT",
        "last_action": "House Committee Amendment No. 1",
        "last_action_date": "2026-03-17",
        "url": "https://legiscan.com/IL/bill/HB1783/2025"
    },
    "2": {
        "number": "SB9999",
        "title": "UNTRACKED BILL",
        "last_action": "Introduced",
        "last_action_date": "2026-03-10",
        "url": "https://legiscan.com/IL/bill/SB9999/2025"
    },
}

TRACKED_BILLS = {
    "HB4068": {"position": "core bill", "note": "waiting for hearing"},
    "HB1783": {"position": "core bill", "note": ""},
}


class TestDetectChanges:
    def test_no_changes(self):
        old_data = {
            "HB4068": "Referred to Rules Committee",
            "HB1783": "House Committee Amendment No. 1",
        }
        results, changes = detect_changes(SAMPLE_MASTER_LIST, TRACKED_BILLS, old_data)
        assert len(results) == 2
        assert len(changes) == 0

    def test_status_changed(self):
        old_data = {
            "HB4068": "Introduced",  # changed from old
            "HB1783": "House Committee Amendment No. 1",
        }
        results, changes = detect_changes(SAMPLE_MASTER_LIST, TRACKED_BILLS, old_data)
        assert len(changes) == 1
        assert changes[0]["bill"] == "HB4068"
        assert changes[0]["old"] == "Introduced"
        assert changes[0]["new"] == "Referred to Rules Committee"

    def test_new_bill_no_old_data(self):
        """A tracked bill appearing for the first time should not count as a 'change'."""
        old_data = {}
        results, changes = detect_changes(SAMPLE_MASTER_LIST, TRACKED_BILLS, old_data)
        assert len(results) == 2
        assert len(changes) == 0

    def test_untracked_bill_excluded(self):
        old_data = {}
        results, changes = detect_changes(SAMPLE_MASTER_LIST, TRACKED_BILLS, old_data)
        bill_numbers = [r["Bill Number"] for r in results]
        assert "SB9999" not in bill_numbers

    def test_tracked_bill_not_in_master_list(self):
        """If a tracked bill isn't in the API response, it shouldn't appear in results."""
        empty_master = {"session": {"session_id": 1}}
        results, changes = detect_changes(empty_master, TRACKED_BILLS, {})
        assert len(results) == 0
        assert len(changes) == 0

    def test_session_key_skipped(self):
        results, changes = detect_changes(SAMPLE_MASTER_LIST, TRACKED_BILLS, {})
        bill_numbers = [r["Bill Number"] for r in results]
        assert "session" not in bill_numbers

    def test_result_contains_expected_fields(self):
        results, _ = detect_changes(SAMPLE_MASTER_LIST, TRACKED_BILLS, {})
        for r in results:
            assert "Bill Number" in r
            assert "Position" in r
            assert "Title" in r
            assert "Last Action" in r
            assert "Action Date" in r
            assert "Notes" in r
            assert "LegiScan Link" in r


class TestReadBillList:
    def test_reads_bills_with_positions_and_notes(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("HB1234, core bill, some note\n")
            f.write("SB5678, oppose, another note\n")
            path = f.name
        try:
            bills = read_bill_list(path)
            assert len(bills) == 2
            assert bills["HB1234"]["position"] == "core bill"
            assert bills["HB1234"]["note"] == "some note"
            assert bills["SB5678"]["position"] == "oppose"
        finally:
            os.unlink(path)

    def test_missing_file_returns_empty(self):
        bills = read_bill_list("/nonexistent/path.txt")
        assert bills == {}

    def test_empty_file_returns_empty(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("")
            path = f.name
        try:
            bills = read_bill_list(path)
            assert bills == {}
        finally:
            os.unlink(path)

    def test_bill_number_uppercased(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("hb1234, monitor\n")
            path = f.name
        try:
            bills = read_bill_list(path)
            assert "HB1234" in bills
        finally:
            os.unlink(path)


class TestLoadOldData:
    def test_missing_file_returns_empty(self):
        old = load_old_data("/nonexistent/path.csv")
        assert old == {}

    def test_loads_csv(self):
        import pandas as pd
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            path = f.name
        df = pd.DataFrame([
            {"Bill Number": "HB1234", "Last Action": "Introduced"},
            {"Bill Number": "SB5678", "Last Action": "Passed"},
        ])
        df.to_csv(path, index=False)
        try:
            old = load_old_data(path)
            assert old["HB1234"] == "Introduced"
            assert old["SB5678"] == "Passed"
        finally:
            os.unlink(path)
