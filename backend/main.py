"""Separate FastAPI service: deploy on a Python host, not in the frontend worker."""
import copy
import json
import os
from functools import lru_cache
from fastapi import FastAPI, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import firebase_admin
from firebase_admin import auth, credentials, firestore
from domain import COLLECTIONS, DEFAULTS, apply

app = FastAPI(title='UniLibrary API')
app.add_middleware(CORSMiddleware, allow_origins=[x.strip() for x in os.getenv('ALLOWED_ORIGINS','http://localhost:8080').split(',')], allow_methods=['GET','POST'], allow_headers=['Authorization','Content-Type'])
bearer = HTTPBearer()

@lru_cache
def db():
    if not firebase_admin._apps:
        value=os.getenv('FIREBASE_SERVICE_ACCOUNT_JSON')
        firebase_admin.initialize_app(credentials.Certificate(json.loads(value)) if value else credentials.ApplicationDefault())
    return firestore.client()

def identity(token: HTTPAuthorizationCredentials = Depends(bearer)):
    db()
    try: return auth.verify_id_token(token.credentials, check_revoked=True)['uid']
    except Exception: raise HTTPException(401,'Please sign in again')

class Command(BaseModel):
    command: str = Field(min_length=1,max_length=40)
    args: list = Field(max_length=6)

@app.get('/health')
def health(): return {'status':'ok'}

@app.post('/commands')
def command(body: Command, uid: str = Depends(identity)):
    client=db(); transaction=client.transaction()
    @firestore.transactional
    def run(tx):
        # A shared revision serializes mutations; transaction retries re-evaluate eligibility.
        revision=client.collection('system').document('revision'); revision_snap=revision.get(transaction=tx)
        role_snap=client.collection('user_roles').document(uid).get(transaction=tx)
        role=(role_snap.to_dict() or {}).get('role','student')
        settings_doc=client.collection('settings').document('library'); settings_snap=settings_doc.get(transaction=tx)
        s={key:[dict(d.to_dict(),id=d.id) for d in tx.get(client.collection(path))] for key,path in COLLECTIONS.items()}
        s['settings']=settings_snap.to_dict() or dict(DEFAULTS)
        before=copy.deepcopy(s)
        result=apply(s,uid,role,body.command,body.args)
        writes=1
        for key,path in COLLECTIONS.items():
            old={r['id']:r for r in before[key]}; new={r['id']:r for r in s[key]}
            for id,row in new.items():
                if old.get(id)!=row: tx.set(client.collection(path).document(id),row); writes+=1
            for id in old.keys()-new.keys(): tx.delete(client.collection(path).document(id)); writes+=1
        if s['settings']!=before['settings']: tx.set(settings_doc,s['settings']); writes+=1
        if body.command=='setRole': tx.set(client.collection('user_roles').document(result['roleUserId']),{'role':result['role']}); writes+=1
        if writes>450: raise ValueError('Too many records changed in one request')
        tx.set(revision,{'value':(revision_snap.to_dict() or {}).get('value',0)+1})
        return result
    try: return {'result':run(transaction)}
    except PermissionError as e: raise HTTPException(403,str(e))
    except (ValueError,KeyError,IndexError,TypeError) as e: raise HTTPException(400,str(e) if isinstance(e,ValueError) else 'Invalid command arguments')
    except Exception: raise HTTPException(503,'Library service is temporarily unavailable')
