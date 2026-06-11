#!/usr/bin/with-contenv bashio
# ==============================================================================
# FamilyDaily — Start des Backends
# with-contenv laedt die vom Supervisor injizierten Env-Variablen (SUPERVISOR_TOKEN)
# ==============================================================================
bashio::log.info "Starte FamilyDaily..."
cd /app || exit 1
exec python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8099
