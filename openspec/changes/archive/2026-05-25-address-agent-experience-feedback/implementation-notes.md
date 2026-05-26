## Baseline Notes

### Canonical legacy report reference

Selected reference:

- `03智能体输出成果参考报告/苏州轨道交通6号线金家堰站东北象限邻里中心地块与车站互联互通必要性评估与设计方案报告.docx`

Reason:

- It matches the existing demo project code `6-JJY-2026-001`.
- It is already present in the reference-output folder rather than the lower-priority early feedback copy.
- Its section structure is compact enough to use as a deterministic formal-report alignment target.

Expected top-level section order:

1. 项目概况
2. 联通必要性评估结论
3. 联通方式比选与推荐方案
4. 方案设计核心技术要求
5. 合规性校验说明
6. 设计优化与实施建议
7. 意向效果图输出指引

### Baseline export behavior observed on 2026-05-25

Report export baseline command:

```powershell
& 'C:\Users\R\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' 'outputs\interconnect_agent_system\tools\verify_export_contract.py'
```

Observed result:

- Existing verification failed before this change because it expected 4 returned files including PDFs.
- Current backend export generated 3 files for the demo project: evaluation snapshot JSON, formal report DOCX, and score-detail DOCX.
- PDF generation did not occur in this local run, so the updated contract should verify generated artifacts and treat PDFs as optional unless the runtime can actually create them.

PNG export baseline commands:

```powershell
$env:NODE_PATH='C:\Users\R\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\node_modules'
& 'C:\Users\R\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe' 'outputs\interconnect_agent_system\tools\verify_schematic_png_export_result_policy.cjs'
& 'C:\Users\R\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' 'outputs\interconnect_agent_system\tools\verify_schematic_png_export_subprocess.py'
```

Observed result:

- Result-policy verification passed.
- PNG subprocess output handling verification passed.
- Full browser screenshot export still needs a running local server and will be covered by the new metadata and runtime verification tasks.
