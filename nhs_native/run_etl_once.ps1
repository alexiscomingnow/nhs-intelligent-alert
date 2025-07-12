$here = Split-Path $MyInvocation.MyCommand.Path
. "$here\.venv\Scripts\Activate.ps1"
python "$here\runner.py"
