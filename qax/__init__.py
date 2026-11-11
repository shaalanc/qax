"""qax — self-healing QA regression automation.

A self-contained CLI that turns an Excel test-case workbook into executed
Playwright browser tests, with an embedded agent core providing generation
(plan), self-healing (heal), and reporting (report). Runs completely
independently — all state lives under QAX_HOME (default ~/.qax).
"""

__version__ = "0.1.0"
