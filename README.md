# PayMore Chinook Operator Dashboard

Private Streamlit dashboard for the PayMore Chinook store. The app compares current actual performance against the built-in pro forma model, projects run rate, and models best, medium, and worst case scenarios.

## What it includes

- Executive dashboard with revenue, margin, cash, and forecast KPI cards
- Actual vs pro forma comparisons by month
- Scenario engine for best, medium, and worst case planning
- Cash planning with threshold, injection, and owner draw logic
- Editable actuals table plus CSV/XLSX uploads
- Built-in pro forma workbook: `PayMore_Chinook_Pro_Forma_v6.xlsx`

## Local run

```powershell
streamlit run app.py --server.headless true --server.port 8501
```

## Deploy privately on Streamlit Community Cloud

1. Push this repository to a private GitHub repository.
2. In Streamlit Community Cloud, create a new app from that private repo.
3. Use `app.py` as the entry point.
4. In the app sharing settings, restrict access to specific viewers and invite your partner by email.

## Notes

- The app uses the bundled pro forma workbook by default. No pro forma upload is required.
- PayMore actual sales reports can be uploaded from the sidebar to override monthly actual sales metrics.
- Operating inputs can also be edited directly in the app.
