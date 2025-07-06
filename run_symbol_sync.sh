# chmod +x run_symbol_sync.sh
# ./run_symbol_sync.sh

echo "▶ Starting symbol sync..."
PYTHONPATH=. python app/company/service/symbol_sync_service.py
