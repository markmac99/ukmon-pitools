# powershell script to run tests
# Copyright (c) Mark McIntyre

$currloc = (get-location).path
Push-Location ../RMS 
$pypath=$env:pythonpath
$env:pythonpath="$pypath;$currloc"
pytest $currloc/ -v --cov-report term-missing:skip-covered --cov=$currloc/  --cov-config=$currloc/.coveragerc 
Pop-Location
$env:pythonpath="$pypath"
