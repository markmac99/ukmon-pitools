# powershell script to run tests
# Copyright (c) Mark McIntyre

$currloc = get-location
Push-Location ../RMS 
pytest $currloc -W ignore::DeprecationWarning
Pop-Location