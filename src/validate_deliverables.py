import json, sqlite3, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
DB=ROOT/'data/processed/collections.db'
con=sqlite3.connect(DB)
sql=(ROOT/'sql/collections_analytics.sql').read_text()
con.executescript(sql)
checks={
 'golden_rows':con.execute('SELECT COUNT(*) FROM golden_successful_payments').fetchone()[0],
 'gross_recovery':round(con.execute('SELECT SUM(amount) FROM golden_successful_payments').fetchone()[0],2),
 'payment_id_conflict_groups':con.execute('SELECT COUNT(*) FROM payment_id_conflict_groups').fetchone()[0],
 'monthly_rows':con.execute('SELECT COUNT(*) FROM monthly_recovery').fetchone()[0],
}
expected={'golden_rows':17534,'gross_recovery':1315583964.64,'payment_id_conflict_groups':0,'monthly_rows':8}
print(json.dumps({'actual':checks,'expected':expected},indent=2))
failed=[k for k,v in expected.items() if checks[k]!=v]
con.close()
if failed:
 print('FAILED:',', '.join(failed)); sys.exit(1)
print('PASS: SQL outputs reconcile to validated Golden Payment totals.')
