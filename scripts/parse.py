import click
from RecordLib.sourcerecords.docket import Docket
from RecordLib.utilities.serializers import to_serializable
from ujs_search.services import searchujs
import json
import io
import logging
import sys
import urllib3
import yaml
import requests
from RecordLib.sourcerecords.docket.re_parse_cp_pdf import parse_cp_pdf
from RecordLib.sourcerecords.docket.re_parse_mdj_pdf import parse_mdj_pdf
from RecordLib.sourcerecords.summary.parse_pdf import parse_pdf as parse_summary_pdf


requests.packages.urllib3.util.ssl_.DEFAULT_CIPHERS += "HIGH:!DH:!aNULL"


def pick_pdf_parser(docket_num, doctype="docket"):
    """
    Choose the appropriate parser function to use, based on a docket number.
    
    For example, if the docket number is CP-12-CR-12345-2010, the common pleas parser would
    be the right choice.
    """
    parser = None
    if doctype == "docket":
        if "CP" in docket_num or "MC" in docket_num:
            parser = parse_cp_pdf
        elif "MJ" in docket_num:
            parser = parse_mdj_pdf
        else:
            logger.error(f"   Cannot determine the right parser for: {docket_num}")
    else:
        parser = parse_summary_pdf

    return parser


def download_file(url):
    resp = requests.get(url, headers={"User-Agent": "ExpungmentGeneratorTesting"})
    if resp.status_code == 200:
        return resp.content
    return None


@click.group()
def parse():
    pass


@parse.command()
@click.argument("path")
@click.option("--doctype", required=True, type=click.Choice(["summary", "docket"]))
@click.option("--court", required=False, default=None)
@click.option("--loglevel", "-l", required=False, default="DEBUG")
def pdf(path, doctype, court, loglevel):
    """
    Parse a pdf file. Probably only useful for testing.
    """
    root_logger = logging.getLogger()  # create root logger that submodules will inherit
    root_logger.setLevel(loglevel)
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(logging.Formatter("%(asctime)s %(name)s %(message)s"))
    handler.setLevel(loglevel)
    root_logger.addHandler(handler)
    root_logger.info("Logging is working")
    if doctype == "summary":
        d, errs = parse_summary_pdf
    elif doctype == "docket":
        d, errs = Docket.from_pdf(path, court=court)
        click.echo("---Errors---")
        click.echo(errs)
        click.echo("---Person---")
        click.echo(json.dumps(d._defendant, default=to_serializable, indent=4))
        click.echo("---Case---")
        click.echo(json.dumps(d._case, default=to_serializable, indent=4))
    click.echo("Done.")


@parse.command("docket-number")
@click.argument("docket_number")
@click.option(
    "--doctype",
    required=False,
    type=click.Choice(["summary", "docket"]),
    default="docket",
)
@click.option(
    "--save-docket",
    "-sd",
    required=False,
    default=None,
    help="Save the downloaded docket.",
)
@click.option(
    "--save-parsed",
    "-sp",
    required=False,
    default=None,
    help="Save the parsed results to a file.",
)
@click.option("--loglevel", "-l", required=False, default="DEBUG")
def docket_number(docket_number, doctype, loglevel, save_docket, save_parsed):
    """
    Parse a docket using just a docket number. This command will fetch that docket or summary from 
    the Internet.

    """
    root_logger = logging.getLogger()  # create root logger that submodules will inherit
    root_logger.setLevel(loglevel)
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(logging.Formatter("%(asctime)s %(name)s %(message)s"))
    handler.setLevel(loglevel)
    root_logger.addHandler(handler)
    root_logger.info("Logging is working")
    results, _ = searchujs.search_by_docket(docket_number)
    assert len(results) == 1, "Request for docket failed."
    if doctype == "summary":
        url = results[0]["summary_url"]
    else:
        url = results[0]["docket_sheet_url"]
    pdf = io.BytesIO(download_file(url))
    if save_docket:
        with open(save, "wb") as f:
            f.write(pdf)

    parser = pick_pdf_parser(docket_number)
    parsed = parser(pdf)
    person = parsed[0]
    cases = parsed[1]
    results = {
        "docket_number": docket_number,
        "url": url,
        "person": person,
        "cases": cases,
    }
    # click.echo(json.dumps(person, default=to_serializable, indent=4))
    if save_parsed:
        with open(save_parsed, "w") as f:
            f.write(yaml.dump(results, indent=4))
    click.echo(yaml.dump(results, indent=4))
    click.echo("Complete")

