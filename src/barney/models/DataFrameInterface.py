from __future__ import annotations

import logging
import re
from collections import defaultdict
from itertools import count
from typing import TYPE_CHECKING

import numpy as np
import pandas as pd

from ..Utilities.parsers import normalizeRegex

if TYPE_CHECKING:
    from pathlib import Path
    from typing import Callable, Dict, List, Optional

    from ..Utilities.parsers import AudiotagEntry


logger = logging.getLogger(__name__)


class DataFrameInterface:

    keysOfInterest: Dict[str, type] = {
        "order": int,  # the order within the file this entry was
        "combinedscore": float,
        "score": float,
        "aggscore": float,  # legacy supported score calculation
        "snr": float,
        "filename": str,  # name of the file
        "filepath": str,  # locally accessible filepath
        "original": str,  # path to use for audiotag skipping
        "key": str,
        "speaker": str,
        "skip": bool,
        "flag": bool,
        "transcription": str,
        "phones": str,
        "words": str,
        "is_relative": bool,
        "orthography": str,
        "net": str,
        "nota": bool,
        "transcriber": str,
    }

    def __init__(self) -> None:
        super().__init__()
        self._df = pd.DataFrame(columns=self.keysOfInterest.keys())
        self.filterMatrix = np.full(tuple(max(dim, 1) for dim in self._df.shape), True)
        self.sourceData: Dict[str, Dict[str, str]] = {}
        self.audiotagData: Dict[str, Dict[str, AudiotagEntry]] = defaultdict(dict)
        # self.audiotagDataFrame = pd.DataFrame.from_dict({"skip": [], "flag": []})
        self.phraselists: Dict[str, str] = {}

    def clearData(self) -> None:
        self.df = pd.DataFrame(columns=self.keysOfInterest.keys())
        self.sourceData.clear()
        self.phraselists.clear()
        self.audiotagData.clear()

    @property
    def df(self) -> pd.DataFrame:
        return self._df

    @df.setter
    def df(self, df: pd.DataFrame) -> None:
        self._df = df
        newShape = tuple(max(length, 1) for length in df.shape)
        self.filterMatrix = np.full(newShape, True)

    def mergePhraselistContents(
        self, contents: Dict[str, str], phraselistDataFrame: pd.DataFrame
    ) -> None:
        self.phraselists.update(contents)
        self.df = (
            self.df.set_index("filepath")
            .replace(to_replace={"transcription": {"nan": None}})
            .combine_first(phraselistDataFrame)
            .reset_index()
            .rename(columns={"index": "filepath"})
        )
        anyTranscriptions = self.df["transcription"].any(axis=0, skipna=True)
        if not anyTranscriptions:
            logger.warning("No transcriptions added during merge")
        return None

    def updateAudiotags(self) -> None:
        skips = set()
        flags = set()

        for path, entry in self.audiotagData.items():
            for tagType in entry:
                if tagType == "skip":
                    skips.add(path)
                elif tagType == "flag":
                    flags.add(path)
                else:
                    raise RuntimeError

        self.df["skip"] = self.df["original"].isin(skips)
        self.df["flag"] = self.df["original"].isin(flags)

        return None

    def addEntries(
        self, fileList: List[Path], pathMapper: Callable[[Path], Optional[Path]] = None
    ) -> None:

        if not fileList:
            return None
        order = count(start=len(self.sourceData))
        contents = {}
        for filepath in fileList:
            name = filepath.as_posix()
            networkPath: Optional[Path]
            if pathMapper is not None:
                networkPath = pathMapper(filepath)
            else:
                networkPath = None
            contents[name] = {
                "order": str(next(order)),
                "filename": filepath.as_posix(),
                "key": name,
                "is_relative": "False",
                "original": networkPath.as_posix()
                if networkPath is not None
                else filepath.as_posix(),
            }
        self.sourceData.update(contents)
        self.df = pd.concat(
            [self.df, self.contentsToDataFrame(contents, normalizePaths=False)]
        )
        self.df = self.df.reset_index(drop=True)
        self.updateAudiotags()
        return None

    @staticmethod
    def phraselistToDataFrame(contents: Dict[str, str]) -> pd.DataFrame:
        phraselistDataFrame = (
            pd.DataFrame.from_dict(contents, orient="index", columns=["transcription"])
            .fillna(False)
            .astype(str)
        )
        return phraselistDataFrame

    @staticmethod
    def contentsToDataFrame(
        contents: Dict[str, Dict[str, str]], normalizePaths: bool = True
    ) -> pd.DataFrame:
        empty = False
        if not contents:
            contents[""] = {
                "key": ""
            }  # , "filename":""}  # dummy dict instead of empty
            empty = True

        df = pd.DataFrame.from_records(
            list(contents.values()), columns=DataFrameInterface.keysOfInterest
        )
        if empty:
            return df
        df = (
            df.drop("filepath", axis=1)
            .rename(index=str, columns={"filename": "filepath"})
            .assign(
                # get the filename from the path
                filename=lambda x: x["filepath"]
                .str.rpartition("/", expand=True)
                .iloc[:, 2],
                # extract the db value from snr and convert inf to 0
                snr=lambda x: (
                    x["snr"]
                    .fillna(value="0")
                    .replace({"inf": "0", "INF": "0"})
                    .str.partition("db")
                    .iloc[:, 0]
                ),
                score=lambda x: (x["score"].astype(float).fillna(value=float("-inf"))),
                combinedscore=lambda x: (
                    x["combinedscore"].astype(float).fillna(value=float("-inf"))
                ),
                nota=lambda x: (x["key"].astype(str).str.match(".*->__NOTA$")),
                is_relative=lambda x: x["is_relative"].str.match("True"),
            )
            .astype(
                {
                    "order": int,
                    "snr": float,
                    "speaker": str,
                    "skip": bool,
                    "flag": bool,
                    "transcription": str,
                    "key": str,
                    "orthography": str,
                    "nota": bool,
                    "original": object,
                    "net": object,
                    "words": str,
                    "phones": str,
                    "transcriber": str,
                }
            )
            .assign(skip=False, flag=False)
        )

        # series of elements
        partitionPattern = (
            r"{(?P<start>\d+) (?P<finish>\d+) (?P<label>\S+) (?P<score>-?\d+\.\d+?)}"
        )
        alignmentRegex = re.compile(partitionPattern)
        df["phoneScore"] = (
            df["phones"]
            .str.extractall(alignmentRegex)
            .astype({"start": int, "finish": int, "label": str, "score": float})
            .assign(
                normalizedScore=lambda x: (
                    x["score"] / x["finish"] - x["start"]
                ).replace(np.inf, 0)
            )
            .groupby(level=0)
            .sum()["normalizedScore"]
        )
        df["wordScore"] = (
            df["words"]
            .str.extractall(alignmentRegex)
            .astype({"start": int, "finish": int, "label": str, "score": float})
            .assign(
                normalizedScore=lambda x: (
                    x["score"] / x["finish"] - x["start"]
                ).replace(np.inf, 0)
            )
            .groupby(level=0)
            .sum()["normalizedScore"]
        )
        df["aggscore"] = df["wordScore"].fillna(df["phoneScore"]).fillna(-np.inf)

        # handle case of not having leading forward slashes for relative network paths
        if normalizePaths:
            df["filepath"] = df["filepath"].where(
                df["is_relative"],
                df["filepath"].str.replace(
                    normalizeRegex, r"//", case=True, regex=True
                ),
            )
            df["original"] = df["original"].where(
                df["original"].isnull(),
                df["original"].str.replace(
                    normalizeRegex, r"//", case=True, regex=True
                ),
            )
            df["net"] = df["net"].where(
                df["is_relative"] | df["net"].isnull(),
                df["net"].str.replace(normalizeRegex, r"//", case=True, regex=True),
            )
        df["original"] = df["original"].fillna(value=df["filepath"])
        return df
