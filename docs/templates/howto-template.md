# How to [Task Name]

**Difficulty**: Beginner | Intermediate | Advanced
**Time Required**: Approximately X minutes
**Last Updated**: YYYY-MM-DD

---

## Overview

Brief (2-3 sentence) description of what this guide accomplishes and when you would need it.

**What You'll Learn**:
- Learning outcome 1
- Learning outcome 2
- Learning outcome 3

---

## Prerequisites

### Required

- Prerequisite 1 (e.g., "Installed package with `pip install -e .`")
- Prerequisite 2 (e.g., "Python 3.9 or higher")
- Prerequisite 3 (e.g., "Completed [Setup Guide](../howto/setup.md)")

### Optional

- Optional prerequisite 1
- Optional prerequisite 2

### Assumptions

- Assumption 1 (e.g., "You have basic familiarity with the command line")
- Assumption 2

---

## Quick Start

For experienced users, here's the minimal example:

```python
# Quick example showing the essential code
from somali_dialect_classifier import Component

component = Component()
result = component.run()
print(f"Result: {result}")
```

**Expected Output**:
```
Result: Success message
```

For detailed walkthrough, continue to [Step-by-Step Guide](#step-by-step-guide).

---

## Step-by-Step Guide

### Step 1: [Action Name]

**Purpose**: Explain what this step accomplishes and why it's necessary.

**Instructions**:

1. Detailed instruction 1
2. Detailed instruction 2

```python
# Code example for this step
from module import Class

instance = Class(parameter="value")
```

**Verification**: How to confirm this step worked correctly.

```bash
# Command to verify
command --check
```

**Expected Output**:
```
Output showing success
```

**Common Issues**:
- Issue 1: Solution
- Issue 2: Solution

---

### Step 2: [Action Name]

**Purpose**: Explain what this step accomplishes.

**Instructions**:

```python
# Code example
result = instance.process()
```

**Verification**: How to verify this step.

---

### Step 3: [Action Name]

**Purpose**: Explain final step.

**Instructions**:

```python
# Final code
final_result = instance.finalize()
print(f"Complete: {final_result}")
```

**Expected Output**:
```
Complete: Success
```

---

## Complete Example

Here's a complete, runnable example incorporating all steps:

```python
#!/usr/bin/env python3
"""
Complete example: [Task Name]

This script demonstrates [what it demonstrates].
"""

from somali_dialect_classifier import Component1, Component2

def main():
    # Step 1: Initialize
    component = Component1(
        param1="value1",
        param2="value2"
    )

    # Step 2: Process
    result = component.process()
    print(f"Processing complete: {result}")

    # Step 3: Finalize
    final = component.finalize()
    print(f"Final result: {final}")

    return final

if __name__ == "__main__":
    result = main()
```

**To run this example**:

```bash
python example_script.py
```

**Expected output**:
```
Processing complete: 100 records
Final result: Success
```

---

## Configuration

### Environment Variables

If applicable, document configuration options:

```bash
# Set in .env file or export
COMPONENT_OPTION_1=value1
COMPONENT_OPTION_2=value2
```

### Configuration File

If using configuration files:

```yaml
# config.yaml
component:
  option1: value1
  option2: value2
```

---

## Advanced Usage

### Option 1: [Advanced Feature]

For users who need [specific capability]:

```python
# Advanced example
component = Component(advanced_option=True)
```

### Option 2: [Another Advanced Feature]

Description of another advanced use case:

```python
# Another advanced example
```

---

## Troubleshooting

### Issue: [Common Problem 1]

**Symptoms**:
- Symptom 1
- Symptom 2

**Error Message**:
```
Actual error message text
```

**Cause**: Explanation of what causes this

**Solution**:

```bash
# Command or code to fix
solution --command
```

**Prevention**: How to avoid this issue in the future

---

### Issue: [Common Problem 2]

[Same structure as above]

---

### Issue: [Common Problem 3]

[Same structure as above]

---

## Performance Tips

If applicable, include optimization suggestions:

- **Tip 1**: Performance optimization
- **Tip 2**: Memory management
- **Tip 3**: Scaling considerations

### Benchmarks

| Configuration | Time | Memory | Notes |
|--------------|------|--------|-------|
| Small dataset | 2 min | 500MB | 1000 records |
| Medium dataset | 10 min | 2GB | 10,000 records |
| Large dataset | 60 min | 8GB | 100,000 records |

---

## Next Steps

After completing this guide, you might want to:

1. **[Related Task 1]**: Link to related guide
2. **[Related Task 2]**: Link to related guide
3. **[Advanced Topic]**: Link to advanced documentation

---

## See Also

### Related How-To Guides

- [Guide 1](./guide1.md) - Brief description
- [Guide 2](./guide2.md) - Brief description

### Reference Documentation

- [API Reference](../reference/api.md) - Component API
- [Architecture](../overview/architecture.md) - System design

### External Resources

- [External Resource 1](https://example.com) - Description
- [External Resource 2](https://example.com) - Description

---

## Feedback

Found an issue with this guide? Please:

- Open an issue: [GitHub Issues](https://github.com/org/repo/issues)
- Suggest improvements: [GitHub Discussions](https://github.com/org/repo/discussions)
- Submit a fix: [Pull Requests](https://github.com/org/repo/pulls)

---

**Version**: 1.0
**Author**: [Your Name]
**Contributors**: [List contributors]
