# powershell script to run tests
# Copyright (c) Mark McIntyre

$currloc = get-location
Push-Location ../RMS 
$pypath=$env:pythonpath
$env:pythonpath="$pypath;$currloc"
pytest $currloc -v -W ignore::DeprecationWarning
Pop-Location
$env:pythonpath="$pypath"