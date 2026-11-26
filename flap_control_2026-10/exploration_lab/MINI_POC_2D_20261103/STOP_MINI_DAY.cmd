@echo off
powershell -NoProfile -Command "[pscustomobject]@{source='manual_stop';reason='user_requested_day_pause';at=(Get-Date).ToString('o')} | ConvertTo-Json | Set-Content -LiteralPath 'F:\ntnu\flap_control\exploration_lab\MINI_POC_2D_20261103\STOP_MINI.json' -Encoding utf8"
echo Safe stop requested. Check STATUS before shutdown. W04 is untouched.
