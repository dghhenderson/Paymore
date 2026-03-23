$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot
streamlit run app.py --server.headless true --server.port 8501
