#! /usr/bin/env python3

import logging
import os
import sys


def main() -> None:
    logger = logging.getLogger()
    console = logging.StreamHandler()
    console.setLevel(logging.DEBUG)
    formatter = logging.Formatter("%(name)-35s: %(levelname)-8s %(message)s")
    console.setFormatter(formatter)
    logger.addHandler(console)
    os.environ["QT_API"] = "pyqt5"
    from barney.BarneyApp import Barney

    app = Barney()
    app.qtapp.startBarney()
    sys.exit(app.qtapp.exec_())


if __name__ == "__main__":
    main()
