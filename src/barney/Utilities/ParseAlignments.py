from __future__ import annotations

import re
from typing import Dict, List, NamedTuple


class Alignment(NamedTuple):

    start: int
    finish: int
    label: str
    score: float

    def __repr__(self) -> str:
        return (
            f"{self.label} score: {self.score} duration: {self.start} - {self.finish}"
        )

    @property
    def duration(self) -> int:
        return self.finish - self.start

    @property
    def normalizedScore(self) -> float:
        try:
            score = self.score / self.duration
        except ZeroDivisionError:
            score = 0
        return score


def parseAlignmentFields(data: Dict[str, str]) -> Dict[str, List[Alignment]]:
    partitionPattern = (
        r"{(?P<start>\d+) (?P<finish>\d+) (?P<label>\S+) (?P<score>-?\d+\.\d+?)}"
    )
    alignments = {}
    alignmentRegex = re.compile(partitionPattern)
    for field, values in data.items():
        if alignmentRegex.match(values) is not None:
            alignments[field] = [
                Alignment(
                    int(segment[0]), int(segment[1]), segment[2], float(segment[3])
                )
                for segment in alignmentRegex.findall(values)
            ]
    return alignments
