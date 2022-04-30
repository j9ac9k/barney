# Contributing

## What should I know before I get started

### Barney and Friends

`Barney` is written in Python, and makes heavy use of the `Qt for Python` library (`pyqt5` module), `numpy`, and `pyqtgraph` for plotting.

Configuring the development environment is not trivial; as barney makes use of `venv`, and `pre-commit`.  A `Makefile` is provided to help get other developers up and running quickly.

## How Can I Contribute

### Reporting Bugs

Software Engineers/Developers are not the target users of barney, so linguists, and anyone else that is analyzing audio signal data can of great help by identifying bugs.  If a bug is found, please create a new issue, and describe the issue, and the steps to recreate.

#### Submitting a (Good) Bug Report

Please isolate a sequence of steps to reproduce this bug, and clearly state how the actual behavior is different from the intended behavior.  Developers being able to replicate bugs is critical for fixing them.

If a log is available, please provide that.

## Styleguides

Code styleguides are enforced through a variety of tools during the git commit stage via git hooks (or more specifically, by pre-commit).

### MyPy

`mypy` is a static code checker and linter.  It evaluates function declarations and variable type annotations, and checks to make sure the types are compatible.  As barney does make use of python's type annotations, `mypy` is the tool to mandate they are correct.

* [mypy](http://mypy-lang.org/)
* For more information on the variable type annotations check out [PEP 526](https://www.python.org/dev/peps/pep-0526/).
* Alternatively for a more thurough guide, take a look at [The State of Type Hints in Python](https://www.bernat.tech/the-state-of-type-hints-in-python/) blog post.

### Black

Black is a code formatter that adjusts the line breaks, spacing, etc within the code to make it (mostly) pep8 compatible.  The fantanstic thing about black is that it can remove any discussion/preferences/bike sheading about styling preferences.  Run python files through black, end of story.

* [Black - The uncompromising Python code formatter](https://github.com/ambv/black)

### flake8

Flake8 is a linter that checks for style consistency.  While it allows for a fair amount of customization, `barney` uses a near default implementation, with a slight exception for max-line-length.

Links

* [Flake8](http://flake8.pycqa.org/en/latest/)

### isort

`isort` checks to make sure that modules are imported in the correct order.  There has been some discussion about `black` doing this in the future, primarily because the developer of `black` does not believe `isort` does it correctly.

Links:

* [isort](https://github.com/timothycrosley/isort)

### pre-commit

`pre-commit` is a tool allowing easy integration of tasks into git hooks.  `barney` uses a variety of these tools such as ensuring files have a new-line character at the end, `mypy`, `flake8` and `black` checks all pass, and so on.

## Documentation

### Wiki

The wiki in the repository should store general application help.

### Sphinx

`sphinx` is a documentation build tool, for the time being `barney` does not have an external API, so the documentation is intended for application development usage.  Future versions of the applications will support a plugin mechanism, where this API should be better advertised.

## Dependencies

### GUI

For creating the cross compatible GUI, `barney` makes use of the Qt framework, and uses Qt for Python bindings (the `pyqt5` module) which at the time of this writing is in preview mode; but its first stable release is expected shortly.

### Plotting

For plotting, `barney` makes use of `pyqtgraph`, a plotting library that makes use of the Qt framework under the hood.  The plotting library integrates nicely into our GUI framework and makes use of `numpy` arrays.

## Testing

### PyTest

`pytest` is the most popular testing framework on python.  We utilize `pytest` in large part because we can easily test the GUI via the `pytest-qt` plugin.  The `pytest-qt` plugin gives us a fixture, qtbot, which can simulate mouse clicks, keyboard presses, and detect/capture qt signals.  This functionality is essential when testing the GUI.
