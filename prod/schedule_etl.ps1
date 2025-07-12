$here     = Split-Path $MyInvocation.MyCommand.Path
$py       = "$here\.venv\Scripts\python.exe"
$action   = New-ScheduledTaskAction -Execute $py -Argument "$here\runner.py"
$trigger  = New-ScheduledTaskTrigger -Daily -At 03:00
Register-ScheduledTask -TaskName "NHS_ETL_Daily" -Action $action -Trigger $trigger `
    -Description "Daily NHS RTT provider ETL" -User $env:USERNAME -RunLevel Highest -Force
