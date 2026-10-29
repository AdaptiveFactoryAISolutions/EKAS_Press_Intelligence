# Fresh upstream setup evidence

Executed 2026-10-28 in the isolated full-stack-foundation worktree. This is setup/design evidence, not full-stack implementation acceptance.

- Downloaded both complete repositories with full nonshallow history through their original ScottDuncanAI Git URLs. HEAD and downloaded origin/main agree at HistorianSim 14e616c382a9db8026cbb4ab86bdd803d56ca72e and HistorianRCA 8d12a821395ce5f72e464dc78cc2c10d05cbb9ed.
- Both upstream tracked source trees remain clean; verify_upstreams.sh passed.
- Python 3.12.3; independent work/venv with full declared runtime/dev dependency lock installed, then editable native HistorianSim and EKAS. pip check reports no broken requirements; pip cache ownership warning is environmental and was not copied into requirements.
- Actual historiansim module resolves to this worktree's vendor/HistorianSim/src/historiansim, not the earlier checkout.
- Native historiansim list executed: two plants (15 CSTR and 19 tank causes), six scenarios, quick/standard/campaign profiles and rca-benchmark recipe.
- Native check-plant exothermic_cstr --stage 1 passed actual equilibrium, actuator headroom, cascade/ratio equilibrium and one-day quiet loop hold checks. This is the upstream required first-run smoke test, not the later five-stage/full-dataset qualification.
- Native check-plant heated_stirred_tank --stage 1 also passed equilibrium, actuator headroom, cascade equilibrium and one-day quiet loop hold checks.
- HistorianRCA original files opened with pandas/PyArrow: 90 tag records; 5,650,781 primary long-format records with tag/timestamp/value/quality; 129,600 regular-grid rows and 91 columns. Timestamp extent 2024-03-01 06:00:00Z to 2024-05-30 05:59:00Z. Process, challenge, template, PFD SVG/PNG, license and citation files exist. Public answer key is absent.
- Claude Code 2.1.289 is installed; local authentication status reports true. No account identity or credential content was emitted. Actual isolated blind-agent execution has not yet been qualified.
- Original milestone-1 checkout and loopback service were not changed.
- Ran the native historiansim new-plant stamping_press --equipment P-27 command in a full local authoring clone under ignored work/HistorianSim-authoring; filled its generated DESIGN.md with the approval document. Immutable vendor checkouts remain untouched. Generated template code is a scaffold, not an implemented plant.
- Independent builder review identified three material questions (hybrid gate semantics, qualification matrix, independent blind runtime). The revised design resolves them; follow-up review found no remaining planning blockers in those areas. Actual implementation/isolation/physics remain unqualified.

Followed source material: HistorianSim CLAUDE.md, README.md, .claude/skills/simulate/SKILL.md, fault_design.md, validation_checklist.md, both reference model patterns, UnitModel/Plant/registry/native gate contracts, and HistorianRCA README.md/CHALLENGE.md. New process design approval is required before implementation.
