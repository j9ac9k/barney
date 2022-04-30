from __future__ import annotations

import logging
import os
import re
import sqlite3
import time
from collections import defaultdict
from getpass import getuser
from itertools import chain, count, groupby
from pathlib import Path
from timeit import default_timer as timer
from typing import TYPE_CHECKING, NamedTuple

from .PathMapper import PathMapper

if TYPE_CHECKING:
    from typing import DefaultDict, Dict

logger = logging.getLogger(__name__)


class AudiotagEntry(NamedTuple):
    tagType: str
    audioFile: str
    reason: str
    tagger: str
    comment: str
    timestamp: int


def makeAudiotagEntry(fpath: str, tagType: str, data: Dict[str, str]) -> AudiotagEntry:
    """Method takes the arguments needed to construct an audiotagdb3 entry, and returns
    a named tuple with the respective information.
    """
    return AudiotagEntry(
        tagType, fpath, data["reason"], getuser(), data["comment"], int(time.time())
    )


# this is kept separate due to pandas.str.replace method wanting a regex
# in SortFilterProxyModel
normalizeRegex = "^/smb/|^(?!" + re.escape(Path.home().as_posix()) + ")/?(?=[a-zA-Z]+)"


def normalizePath(p: str) -> str:
    newPath = re.sub(normalizeRegex, r"//", p)
    return newPath


def parseAudiotag(fname: Path) -> DefaultDict[str, Dict[str, AudiotagEntry]]:
    data: DefaultDict[str, Dict[str, AudiotagEntry]] = defaultdict(dict)

    conn = None
    cursor = None
    try:
        conn = sqlite3.connect(fname.as_posix())
        cursor = conn.cursor()
        cursor.execute("select * from tagTable")
        entries = map(AudiotagEntry._make, cursor.fetchall())

    except sqlite3.OperationalError as e:
        logger.error(f"sqlite error in parseAudiotag: {e}")
        if "no such table" in str(e):
            logger.error("The database may be empty. This is not an important error.")
            return data
        else:
            raise e

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

    for record in entries:
        normalizedPath = normalizePath(record.audioFile)
        data[normalizedPath][record.tagType] = record
    return data


def parsePhraselist(phraselistFile: Path) -> Dict[str, str]:
    entries: Dict[str, str] = {}
    pattern = re.compile(r"^.* {{(.*)} {(.*)}}$")
    with open(phraselistFile, "rt", encoding="utf-8") as f:
        for line in f:
            if line.startswith("#"):
                continue
            m = pattern.search(line)
            if m:
                transcription = m.group(1)
                filename = normalizePath(m.group(2))
                entries[filename] = transcription
    return entries


def parseDatabase(fname: Path) -> Dict[str, Dict[str, str]]:
    start_time = timer()
    counter = count()
    needed_keys = {"filename", "key"}
    entries: Dict[str, Dict[str, str]] = {}
    mapping: Dict[str, str] = {}
    pathMapper = PathMapper()
    parent_path = pathMapper.getNetworkFilepath(fname.parent)
    if parent_path is None:
        parent_path = fname.parent

    # if performance is unsatisfactory consider numpy.fromregex
    with open(fname, "rt", encoding="utf-8") as db_file:
        # skip commented out lines
        try:
            line = next(db_file)
        except StopIteration:
            logger.error(f"No contents in file {fname}")
            return {}

        while line.startswith("#"):
            line = next(db_file)

        for is_period, lines in groupby(
            (line.rstrip() for line in chain([line], db_file)), lambda line: line == "."
        ):
            if is_period:
                if needed_keys <= mapping.keys():
                    mapping["order"] = str(next(counter))
                    mapping["is_relative"] = str(is_relative(mapping["filename"]))
                    mapping["filename"] = is_absolute_pattern.sub(
                        (parent_path / mapping["filename"]).as_posix(),
                        os.fsdecode(mapping["filename"]),
                        count=1,
                    )
                    entries[mapping["key"]] = mapping
                else:
                    logger.warning(
                        "Database entry is missing either 'key' or 'filename' field."
                    )
                    continue
            mapping = {
                key.lower(): value
                for key, _, value in [line.partition(" = ") for line in lines]
            }

    finish_time = timer()
    logger.info(
        f"Parsing took {finish_time - start_time:{5}.{3}} seconds for {len(entries)} entries"
    )
    return entries


is_absolute_pattern = re.compile(
    r"""^(?!([a-z]:  # attempt to catch windows drive letters (C:)
            |[/\\]+)) # catch /Users or potentially \C:\Users
            .+  # anything after previous match""",
    flags=re.IGNORECASE | re.VERBOSE,
)


def is_relative(path_like: str) -> bool:
    r"""Method determines if the entry in a database field is relative or absolute"""
    return is_absolute_pattern.match(os.fsdecode(path_like)) is not None
