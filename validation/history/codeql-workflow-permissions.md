# Hosted CodeQL workflow review

CodeQL on candidate `60e0561` reported three workflow jobs without an explicit GITHUB_TOKEN permission limit. The workflow performs read-only checkout and test/artifact operations; no job needs repository write access. Added workflow-wide `permissions: {contents: read}`. The hosted rerun verifies checkout, test execution and artifact upload under that limit. No application or upstream source changed.
