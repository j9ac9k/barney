#! /usr/bin/env python3
import os
from distutils.core import Command
from typing import Dict

from setuptools import setup  # type: ignore

from src.barney import __version__


class AppendVersion(Command):

    description = "Append git commit ID to current version"
    user_options = []

    def run(self):
        import git

        repo = git.Repo(search_parent_directories=True)
        sha = repo.head.object.hexsha

        data: Dict[str, str]
        data = {"version": __version__.version}
        version_number, split, remainder = str(data["version"]).partition(".dev")

        modified_version = f"{version_number}.dev0+{sha[:7]}"

        version_file = os.path.abspath(__version__.__file__)
        with open(version_file, "w", encoding="utf-8") as f:
            f.write(f"version = '{modified_version}'")

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass


setup(
    name="Barney",
    cmdclass={"enhance_version": AppendVersion},
    version=__version__.version,
    test_suite="tests",
)
