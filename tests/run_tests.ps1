# powershell script to run tests
# Copyright (c) Mark McIntyre

$currloc = get-location
Push-Location ../RMS 
$pypath=$env:pythonpath
$env:pythonpath="$pypath;$currloc"
pytest $currloc -v --cov-report term-missing:skip-covered --cov=$currloc
Pop-Location
$env:pythonpath="$pypath"