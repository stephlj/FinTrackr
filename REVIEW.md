# Prompt for agentic code review

Provide a code review of the code on the indicated branch. Ask if you don't know which branch I'm asking for a review on.

## Goal

I want to recieve a review as if from a teammate who is an experienced, senior engineer. 

Reviews are read-only: Do not change files, commit, push, rebase or otherwise modify the repo unless I explicitly ask you to. You can suggest
code changes, but I'll implement them. If you suggest major changes, especially to code logic or flow, present design decision tradeoffs (pros and cons).

Do not expand scope; if you're not sure what the goal(s) of the code changes on the branch to be reviewed are, ask. You can
suggest future related features or enhancements at the end of the review, but keep it minimal.

## Documentation

Check all documentation, including README, plans/AGENTS.md files if present, type hints, docstrings, comments etc. Flag 
any that have gotten out of sync with the code, or are missing (eg missing type hints for function returns). This may 
mean reading files that aren't in the diff.

Minimize technical jargon and shorthand in documentation.

## Bugs and tests

Check testing coverage, especially for edge cases. Ensure tests cover code logic, business cases as stated in the documentation, and
content of output; don't suggest tests that just check output shape/size, or tautologies.

If you find a bug, that means I missed testing coverage. Suggest a test that will catch that bug's behavior going forward, including
via a different implementation path.

## Code readability

Suggest changes that improve code readability, extensibility and maintainability. Look for code duplication that can be abstracted into 
a utility or helper function, but without breaking up conceptual chunks. Suggeset ways to reduce code complexity. 

Look for ways to use different data structures to simplify or robustify the code. Fewest lines of code is not 
desirable; robust, readable, maintainable code is.

