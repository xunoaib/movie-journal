import pytest

from parsers.log import (
    parse_and_remove_backfill,
    parse_and_remove_mark,
    parse_and_remove_tid,
    parse_line_entries,
    parse_movie_log,
    parse_single_entry,
)


class TestParseAndRemoveMark:
    def test_star_becomes_star_emoji(self):
        icon, line = parse_and_remove_mark("Blade Runner *")
        assert icon == "⭐"
        assert line == "Blade Runner"

    def test_check_becomes_check_emoji(self):
        icon, line = parse_and_remove_mark("Point Break ✓")
        assert icon == "✅"
        assert line == "Point Break"

    def test_bomb_becomes_bomb_emoji(self):
        icon, line = parse_and_remove_mark("Bad Film (bomb)")
        assert icon == "💣"
        assert line == "Bad Film"

    def test_no_mark_returns_none(self):
        icon, line = parse_and_remove_mark("Generic Film")
        assert icon is None
        assert line == "Generic Film"

    def test_multiple_marks_first_wins(self):
        # Star is checked first in the implementation
        icon, line = parse_and_remove_mark("Film * ✓")
        assert icon == "⭐"
        assert "*" not in line


class TestParseAndRemoveTid:
    def test_extracts_tt_tid(self):
        tid, line = parse_and_remove_tid("Film [tt1234567]")
        assert tid == "tt1234567"
        assert line == "Film"

    def test_no_tid_returns_none(self):
        tid, line = parse_and_remove_tid("Film without ID")
        assert tid is None
        assert line == "Film without ID"

    def test_tid_with_surrounding_text(self):
        tid, line = parse_and_remove_tid("Before [tt9876543] After")
        assert tid == "tt9876543"
        assert line == "Before After"


class TestParseAndRemoveBackfill:
    def test_extracts_backfill(self):
        bf, line = parse_and_remove_backfill("Film [bf:original]")
        assert bf == "original"
        assert line == "Film"

    def test_no_backfill_returns_none(self):
        bf, line = parse_and_remove_backfill("Film without backfill")
        assert bf is None
        assert line == "Film without backfill"

    def test_backfill_with_spaces(self):
        bf, line = parse_and_remove_backfill("Film [bf: some value ]")
        assert bf == "some value"
        assert line == "Film"


class TestParseSingleEntry:
    def test_plain_title_and_year(self):
        entry = parse_single_entry("Blade Runner ('1982)", 1, 0)
        assert entry.title == "Blade Runner"
        assert entry.year == "1982"
        assert entry.position == 1
        assert entry.subnum == 0
        assert entry.mark is None
        assert entry.tid is None
        assert entry.backfill is None

    def test_star_mark(self):
        entry = parse_single_entry("Blade Runner ('1982) *", 5, 0)
        assert entry.mark == "⭐"
        assert entry.title == "Blade Runner"
        assert entry.year == "1982"

    def test_check_mark(self):
        entry = parse_single_entry("Point Break ('1991) ✓", 3, 0)
        assert entry.mark == "✅"

    def test_bomb_mark(self):
        entry = parse_single_entry("Bad Film ('2020) (bomb)", 7, 0)
        assert entry.mark == "💣"

    def test_tid_and_backfill(self):
        entry = parse_single_entry("M ('1931) [tt0022100] [bf:original]", 10, 0)
        assert entry.title == "M"
        assert entry.year == "1931"
        assert entry.tid == "tt0022100"
        assert entry.backfill == "original"

    def test_curly_quote_year(self):
        entry = parse_single_entry("Film ('2019)", 1, 0)
        # The curly quote gets normalized to straight quote, then stripped
        assert entry.year == "2019"

    def test_two_digit_year(self):
        entry = parse_single_entry("Film ('99)", 1, 0)
        assert entry.year == "99"

    def test_no_year(self):
        entry = parse_single_entry("Film Without Year", 1, 0)
        assert entry.title == "Film Without Year"
        assert entry.year is None

    def test_title_with_apostrophe(self):
        entry = parse_single_entry("Von Ryan's Express ('1965)", 1, 0)
        assert entry.title == "Von Ryan's Express"
        assert entry.year == "1965"

    def test_title_with_comma(self):
        entry = parse_single_entry("The Good, the Bad and the Ugly ('1966)", 1, 0)
        assert entry.title == "The Good, the Bad and the Ugly"
        assert entry.year == "1966"

    def test_complex_entry(self):
        entry = parse_single_entry(
            "A Matter of Life and Death (aka Stairway to Heaven) ('1946) [tt0038733]",
            15,
            0,
        )
        assert entry.title == "A Matter of Life and Death (aka Stairway to Heaven)"
        assert entry.year == "1946"
        assert entry.tid == "tt0038733"


class TestParseLineEntries:
    def test_single_entry(self):
        entries = parse_line_entries("Blade Runner ('1982)", 1)
        assert len(entries) == 1
        assert entries[0].title == "Blade Runner"
        assert entries[0].subnum == 0

    def test_multiple_entries(self):
        entries = parse_line_entries("Film A ('1999) :: Film B ('2000)", 2)
        assert len(entries) == 2
        assert entries[0].title == "Film A"
        assert entries[0].year == "1999"
        assert entries[0].subnum == 0
        assert entries[1].title == "Film B"
        assert entries[1].year == "2000"
        assert entries[1].subnum == 1
        assert entries[0].position == entries[1].position == 2

    def test_multiple_entries_with_marks(self):
        entries = parse_line_entries("Film A * :: Film B ✓", 3)
        assert entries[0].mark == "⭐"
        assert entries[1].mark == "✅"


class TestParseMovieLog:
    def test_parse_from_string_via_temp_file(self, tmp_path):
        log_file = tmp_path / "movie_journal.txt"
        log_file.write_text(
            "Blade Runner ('1982) *\n"
            "Point Break ('1991) ✓\n"
            "\n"  # blank line should be skipped
            "Bad Film ('2020) (bomb)\n"
        )
        entries = parse_movie_log(log_file)
        assert len(entries) == 3
        assert entries[0].title == "Blade Runner"
        assert entries[0].mark == "⭐"
        assert entries[0].position == 1
        assert entries[1].title == "Point Break"
        assert entries[1].mark == "✅"
        assert entries[1].position == 2
        assert entries[2].title == "Bad Film"
        assert entries[2].mark == "💣"
        assert entries[2].position == 3

    def test_multiple_entries_on_one_line(self, tmp_path):
        log_file = tmp_path / "movie_journal.txt"
        log_file.write_text("Film A ('1999) :: Film B ('2000)\n")
        entries = parse_movie_log(log_file)
        assert len(entries) == 2
        assert entries[0].subnum == 0
        assert entries[1].subnum == 1
        assert entries[0].position == entries[1].position == 1
