# VBA Templates

Master macro-enabled workbooks for pdbtoexcel. The `.bin` files in
`src/athc/pdbtoexcel/resources/` are extracted from these and embedded into
generated `.xlsm` output by xlsxwriter. The templates themselves are not shipped.

| Template                        | Binary                      | Used when              |
| ------------------------------- | --------------------------- | ---------------------- |
| `PdbToExcel.xlsm`               | `vbaProject.bin`            | Normal output          |
| `PdbToExcelWithCategories.xlsm` | `vbaProject_categories.bin` | Category stats enabled |

## Updating VBA

1. Edit the VBA in the `.xlsm`, save.
2. From the repository root, extract and replace the binary (`vba_extract.py`
   ships with xlsxwriter):

```bat
uv run python .venv\Scripts\vba_extract.py src\athc\pdbtoexcel\excel-template\PdbToExcel.xlsm
move /y vbaProject.bin src\athc\pdbtoexcel\resources\vbaProject.bin
```

For categories:

```bat
uv run python .venv\Scripts\vba_extract.py src\athc\pdbtoexcel\excel-template\PdbToExcelWithCategories.xlsm
move /y vbaProject.bin src\athc\pdbtoexcel\resources\vbaProject_categories.bin
```
