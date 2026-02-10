INVESTIGATION_PROMPT = """You are an expert software engineer investigating a code error.

## Error Information
- **Error Type**: {error_type}
- **Error Message**: {error_message}
- **File**: {file_path}
- **Line**: {line_number}
- **Environment**: {environment}

## Stacktrace
```
{stacktrace}
```

## Code Context
{code_context}

## Task
Analyze this error and provide a structured investigation. Identify:
1. The immediate cause of the error
2. Which files and functions are involved
3. Whether this is likely a regression (based on recent changes)
4. The likely root cause category
5. Your confidence level (0.0-1.0)

Respond in JSON format:
{{
    "immediate_cause": "description of what triggered the error",
    "affected_files": ["list", "of", "file", "paths"],
    "affected_functions": ["list", "of", "function", "names"],
    "is_regression": true,
    "root_cause_category": "one of: logic_error, type_error, null_reference, dependency_issue, configuration_error, race_condition, resource_exhaustion, api_mismatch, syntax_error, missing_import, test_assertion, build_configuration, lint_violation, other",
    "root_cause_description": "detailed explanation of the root cause",
    "confidence": 0.85,
    "suggested_fix_approach": "high-level description of how to fix"
}}"""


FIX_GENERATION_PROMPT = """You are an expert software engineer generating a minimal, correct code fix.

## Root Cause
- **Category**: {root_cause_category}
- **Description**: {root_cause_description}
- **File**: {file_path}
- **Lines**: {line_range}

## Current Code
{code_context}

{feedback_section}

## Requirements
1. Fix the root cause directly — no workarounds
2. Make the MINIMUM change necessary
3. Follow the existing code style
4. Do not add unnecessary comments, docstrings, or refactoring
5. Ensure the fix would pass existing tests

## Output Format
For each file that needs to change, output:

### FILE: path/to/file.ext
```
<complete file content with the fix applied>
```

Only include files that actually need to change."""


RCA_COUNCIL_PROMPT = """You are analyzing a software error to determine the root cause.

## Investigation Summary
{investigation_summary}

## Evidence
{evidence_summary}

## Error Details
- **Type**: {error_type}
- **Message**: {error_message}
- **Location**: {file_path}:{line_number}

## Question
What is the root cause of this error? Provide:
1. Root cause category (logic_error, type_error, null_reference, dependency_issue, configuration_error, syntax_error, missing_import, other)
2. Detailed description of the root cause
3. Confidence level (0.0-1.0)
4. Suggested fix approach

Be specific and technical."""
