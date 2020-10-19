import logging
from RecordLib.sourcerecords.parsingutilities import (
    word_starting_near,
    map_line,
    find_index_for_pattern,
)

logger = logging.getLogger(__name__)


def test_word_starting_near():
    line = "   The word      is pizza"
    assert (word_starting_near(4, line)) == "The word"
    assert (word_starting_near(18, line)) == "is pizza"


def test_map_line():
    col_dict = {
        "A": {"idx": 0, "fmt": None},
        "B": {"idx": 20, "fmt": None},
    }
    line = "Joe                 Smith"
    assert map_line(line, col_dict) == {
        "A": "Joe",
        "B": "Smith",
    }


def test_find_index_for_pattern():
    text = "Seq.        Charge       Statute Description"
    assert find_index_for_pattern("Seq.", text) == 0
    assert find_index_for_pattern("Statute Description", text) == 25
    assert find_index_for_pattern("Something else", text) is None
