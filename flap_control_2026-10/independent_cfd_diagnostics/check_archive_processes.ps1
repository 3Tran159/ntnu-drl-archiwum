$ErrorActionPreference="Stop"
Get-CimInstance Win32_Process | Where-Object { $_.Name -match 'starccm|java' -or $_.CommandLine -match 'HF_mesh_v5_backup|mesh_screening_20261028|HF_012_C003_regular_waves_inlet30m' } | Select-Object ProcessId,Name,CommandLine | ConvertTo-Json -Depth 4
