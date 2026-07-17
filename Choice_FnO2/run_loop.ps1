$endTime = (Get-Date).Date.AddHours(15).AddMinutes(40)

while ((Get-Date) -lt $endTime) {
    Write-Host "----------------------------------------"
    Write-Host "Starting Streamlit..."
    Write-Host "Time: $(Get-Date)"
    Write-Host "----------------------------------------"
    
    streamlit run dashboard.py --server.port 8502
    
    Write-Host "Streamlit stopped or crashed! Restarting in 2 seconds..."
    Start-Sleep -Seconds 2
}

Write-Host "Time is past 15:40. Auto-restart loop finished."
