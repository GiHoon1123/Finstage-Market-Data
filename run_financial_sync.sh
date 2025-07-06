# chmod +x run_financial_sync.sh
# ./run_financial_sync.sh

echo "▶ Starting financial sync..."
PYTHONPATH=. python app/company/service/financial_sync_service.py
