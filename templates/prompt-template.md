# Prompt template

Use for anything you'll run more than once or that needs a reliable format. Delete sections you don't need.

```xml
<role>
You are a <role> working for <team/context>. Audience: <who reads the output>.
</role>

<context>
Why this task matters and what good looks like. Constraints (length, tone, must-include, must-avoid) with the reason for each.
</context>

<documents>
  <document index="1">
    <source>filename-or-url</source>
    <document_content>
    ...long input goes HERE, above the instructions...
    </document_content>
  </document>
</documents>

<examples>
  <example>
    <input>...</input>
    <output>...</output>
  </example>
  <!-- 3–5, diverse, covering edge cases -->
</examples>

<instructions>
1. First, quote the parts of the documents relevant to the task in <quotes> tags.
2. Then do <the task>. Be specific: <format>, <length>, <structure>.
3. Before finishing, verify against: <criteria>.
Write the final answer in <answer> tags.
</instructions>
```

Checklist:
- [ ] Would a colleague with no context understand exactly what to produce?
- [ ] Did I say *why* for each constraint?
- [ ] Are the examples diverse, not five variations of one case?
- [ ] Long material at the top, question at the bottom?
- [ ] Positive phrasing ("write prose") rather than prohibitions?
- [ ] Imperative verbs for actions I actually want taken?
