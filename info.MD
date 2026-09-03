# startup backend
.venv-win/Scripts/python.exe -m uvicorn backend.main:app --host 0.0.0.0 --port 8000

#find windows tailsclae ip ps

Get-NetIPAddress -AddressFamily IPv4 |
  Where-Object { $_.IPAddress -like "100.*" } |
  Select-Object IPAddress, InterfaceAlias