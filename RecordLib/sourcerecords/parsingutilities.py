from typing import Union, BinaryIO, Optional
import os
import re
import tempfile
import logging
from datetime import datetime


logger = logging.getLogger(__name__)


def get_text_from_pdf(pdf: Union[BinaryIO, str]) -> str:
    """
    Function which extracts the text from a pdf document.
    Args:
        pdf:  Either a file object or the location of a pdf document.
        tempdir:  Place to store intermediate files.


    Returns:
        The extracted text of the pdf.
    """
    with tempfile.TemporaryDirectory() as out_dir:
        if hasattr(pdf, "read"):
            # the pdf attribute is a file object,
            # and we need to write it out, for pdftotext to use it.
            pdf_path = os.path.join(out_dir, "tmp.pdf")
            with open(pdf_path, "wb") as f:
                f.write(pdf.read())
        else:
            pdf_path = pdf
        # TODO - remove the option of making tempdir anything other than a tempfile.
        #        Only doing it this way to avoid breaking old tests that send tempdir.
        # out_path = os.path.join(tempdir, "tmp.txt")
        out_path = os.path.join(out_dir, "tmp.txt")
        os.system(f'pdftotext -layout -enc "UTF-8" { pdf_path } { out_path }')
        try:
            with open(os.path.join(out_dir, "tmp.txt"), "r", encoding="utf8") as f:
                text = f.read()
                return text
        except IOError as e:
            logger.error("Cannot extract pdf text..")
            return ""


def date_or_none(date_text: str, fmtstr: str = r"%m/%d/%Y") -> datetime:
    """
    Return date or None given a string.
    """
    try:
        return datetime.strptime(date_text.strip(), fmtstr).date()
    except (ValueError, AttributeError):
        return None


def money_or_none(money_str: str) -> Optional[float]:
    try:
        return float(money_str.strip().replace(",", ""))
    except:
        return None


def word_starting_near(val: int, line: str, leading=1, trailing=1) -> Optional[str]:
    """
    Return the words starting near the index `val` in `line`. 
    There's a tolerance for error from `-leading` to `trailing`.

    Args:
        val(int): Integer of the column we're looking to fine the value of.
        line(str): The line of columnar text we're deconstructing
        leading(int): If columns don't quite line up, how many spaces before val are we willing to look? 
        trailing(int): If cols don't line up, how many spaces after val will we look for some text?

    Returns:
        Words in the right part of the line, or None.

    Example:
        line = "   The word      is pizza"
        assert(word_starting_near(4,line)) == "The word"
        assert(word_starting_near(18,line)) == "is pizza"
    """
    word_pattern = re.compile(r"^\s{0," + str(trailing) + r"}(\S+\s{0,2})*")
    start_with_index = val - leading if val > leading else 0
    match = word_pattern.search(line[start_with_index:])
    if match is None:
        return None
    else:
        return match.group(0).strip()


def map_line(line: str, col_dict: dict) -> dict:
    """
    Map a line of columnar data to the columns described in col_dict.

    Example: 
    col_dict = {
        'A': 0,
        'B': 20,
    }
    line = "Joe                 Smith"
    map_line(line, col_dict) == {
        'A': 'Joe',
        'B': 'Smith',
    }
    """

    mapped = dict()
    for key, val in col_dict.items():
        mapped[key] = word_starting_near(val, line)
    return mapped

