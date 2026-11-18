Edit this file carefully. If you need to delete, suggest to the user. 

Read `./.pi/agent/AGENTS.md` for information about the environment.

Read `./docs/build-decisions.md` for build decisions.

Read `./docs/acceptance-criteria.md` for acceptance criteria

I'm going to build test-first: write one test. Run test to check it fails. Commit. Write code to make the test pass. Run test, fix code problems. Talk to the user if the test seems wrong. Commit.

Functions should be pure as far as possible.

Tests should be paramaterisable if possible, with shared fixtures 

To run the tests, activate the venv and `python -m pytest` from `starter-python`

The file handling will raise events to report problems to the user.

The user interface will respond to events.