"""Offline operator tool. Never exposed through an HTTP endpoint."""
import argparse
import json
from main import db
from domain import COLLECTIONS

parser=argparse.ArgumentParser()
parser.add_argument('--admin-uid',required=True,help='UID of an existing Firebase Auth account')
parser.add_argument('--seed',help='Path to an exported library seed JSON file')
args=parser.parse_args()
client=db()
from firebase_admin import auth
auth.get_user(args.admin_uid)
profile=client.collection('users').document(args.admin_uid)
if not profile.get().exists: raise SystemExit('Register this account through UniLibrary first')
client.collection('user_roles').document(args.admin_uid).set({'role':'admin'})
if args.seed:
    with open(args.seed) as f: data=json.load(f)
    for key in ('books','copies','resources','reviews'):
        for row in data.get(key,[]):
            row=dict(row)
            if key=='reviews': continue # no fabricated verified borrowers in a live library
            client.collection(COLLECTIONS[key]).document(row['id']).set(row)
    client.collection('settings').document('library').set(data['settings'])
print('Administrator provisioned. Catalog seed imported if supplied; no demo member identities were imported.')
