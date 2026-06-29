# Decision Log

## 2026-06-29 — Refactor Storage Functions to be generalizable

### Decision

Storage functions are moved to central location and have been made generalizable.

### Reason

Generalizable functions are better when models can be used to analyze different regions.

### Alternatives considered

- keeping in notebook/non-generalizable

### Tradeoff

Codebase becomes larger and mroe difficult to wrangle with

### Revisit when

Unlikely to revisit.

## 2026-06-29 — Split weather downloads by state and calendar year

### Decision

Historical weather requests are divided into state+calendar-year periods for yearly weather pull.

### Reason

Smaller requests are easier to cache, retry, inspect, and resume after a failure.

### Alternatives considered

- Request the entire history at once.
- Divide the history into monthly requests.



### Tradeoff

Yearly requests create more API calls and local files than one large request, but significantly fewer than monthly requests. With free API limits, this will fail (unless time increased etc.)

### Revisit when

If yearly requests remain too slow, exceed API limits, or regularly fail.