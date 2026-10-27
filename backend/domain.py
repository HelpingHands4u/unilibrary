"""Pure library commands. All callers supply a server-verified identity and role."""
from datetime import datetime, timedelta, timezone
from uuid import uuid4

COLLECTIONS = {'books':'books','copies':'book_copies','users':'users','loans':'loans','reservations':'reservations','fines':'fines','wishlists':'wishlists','notifications':'notifications','reviews':'reviews','resources':'resources','audit':'audit','recent':'recent'}
DEFAULTS = dict(loanDays=14, finePerDay=5, maxLoans=4, maxRenewals=2, fineBlockThreshold=100, reservationHoldDays=3)

def stamp(value):
    return datetime.fromisoformat(value.replace('Z', '+00:00'))

def late(due, now):
    return max(0, (now.date() - stamp(due).date()).days)

def apply(s, actor, role, command, args, now=None):
    now = now or datetime.now(timezone.utc)
    iso = now.isoformat()
    settings = s['settings']
    user = next((u for u in s['users'] if u['id'] == actor), None)
    if not user or not user.get('active'): raise ValueError('Account is inactive or missing')
    staff = role in ('librarian','admin')
    def need(*roles):
        if role not in roles: raise PermissionError('You do not have permission for this action')
    def find(key, id):
        row = next((r for r in s[key] if r['id'] == id), None)
        if row is None: raise ValueError('Record not found')
        return row
    def own(row):
        if row['userId'] != actor and not staff: raise PermissionError('This record belongs to another member')
    def add(key, data):
        data = dict(data, id=uuid4().hex); s[key].insert(0,data); return data
    def notify(uid, message, kind='info'):
        add('notifications',dict(userId=uid,message=message,type=kind,isRead=False,timestamp=iso))
    def days(n):
        if isinstance(n,bool) or not isinstance(n,int) or not 1 <= n <= 60: raise ValueError('Loan days must be 1–60')
        return n
    def text(value, minimum=1, maximum=500):
        if not isinstance(value,str) or not minimum <= len(value.strip()) <= maximum: raise ValueError('Invalid text value')
        return value.strip()
    result = None
    if command == 'toggleWishlist':
        book = find('books',args[0]); existing = next((w for w in s['wishlists'] if w['userId']==actor and w['bookId']==book['id']),None)
        if existing: s['wishlists'].remove(existing)
        else: add('wishlists',dict(userId=actor,bookId=book['id']))
    elif command == 'visit':
        find('books',args[0]); s['recent'] = [r for r in s['recent'] if not (r['userId']==actor and r['bookId']==args[0])]
        add('recent',dict(userId=actor,bookId=args[0],at=iso))
    elif command == 'reserve':
        book = find('books',args[0])
        if book['format'] != 'physical': raise ValueError('Only physical books may be reserved')
        if any(l['userId']==actor and l['bookId']==book['id'] and l['status']=='active' for l in s['loans']): raise ValueError('You already hold this book')
        if any(r['userId']==actor and r['bookId']==book['id'] and r['status'] in ('waiting','ready') for r in s['reservations']): raise ValueError('You already reserved this book')
        copy = next((c for c in s['copies'] if c['bookId']==book['id'] and c['status']=='available'),None)
        status = 'ready' if copy else 'waiting'
        if copy: copy['status']='on_hold'
        add('reservations',dict(userId=actor,bookId=book['id'],status=status,reservedAt=iso,expiresAt=(now+timedelta(days=settings['reservationHoldDays'] if copy else 7)).isoformat(),copyId=copy['id'] if copy else None))
        notify(actor, f'Reservation for {book["title"]}: {status}', 'reservation')
    elif command == 'cancelReservation':
        r=find('reservations',args[0]); own(r)
        if r['status'] not in ('waiting','ready'): raise ValueError('Reservation is no longer active')
        r['status']='cancelled'
        if r.get('copyId'):
            copy=find('copies',r['copyId']); copy['status']='available'
            waiting=sorted((x for x in s['reservations'] if x['bookId']==r['bookId'] and x['status']=='waiting'),key=lambda x:x['reservedAt'])
            if waiting:
                nxt=waiting[0]; nxt.update(status='ready',copyId=copy['id'],expiresAt=(now+timedelta(days=settings['reservationHoldDays'])).isoformat()); copy['status']='on_hold'; notify(nxt['userId'],'Your reserved book is ready for pickup','reservation')
    elif command == 'renew':
        l=find('loans',args[0])
        if l['userId']!=actor: raise PermissionError('Only the borrower may renew a loan')
        if l['status']!='active' or late(l['dueDate'],now) or l['renewals']>=settings['maxRenewals']: raise ValueError('This loan cannot be renewed')
        if any(r['bookId']==l['bookId'] and r['status']=='waiting' for r in s['reservations']): raise ValueError('Other students are waiting')
        l['dueDate']=(stamp(l['dueDate'])+timedelta(days=settings['loanDays'])).isoformat(); l['renewals']+=1
    elif command == 'issue':
        need('admin','librarian'); uid,barcode,n=args; n=days(n); borrower=find('users',uid)
        if not borrower.get('active'): raise ValueError('Account is inactive')
        count=sum(l['userId']==uid and l['status']=='active' for l in s['loans'])
        if count>=min(borrower['maxBorrowLimit'],settings['maxLoans']): raise ValueError('Loan limit reached')
        if sum(f['amount'] for f in s['fines'] if f['userId']==uid and f['status']=='unpaid')>settings['fineBlockThreshold']: raise ValueError('Unpaid fines exceed the borrowing threshold')
        copy=next((c for c in s['copies'] if c['barcode'].lower()==barcode.lower()),None)
        if not copy: raise ValueError('Copy not found')
        hold=next((r for r in s['reservations'] if r.get('copyId')==copy['id'] and r['status']=='ready'),None)
        if copy['status']=='on_hold' and (not hold or hold['userId']!=uid): raise ValueError('Copy is held for another student')
        if copy['status'] not in ('available','on_hold'): raise ValueError('Copy is not available')
        copy['status']='issued'
        result=add('loans',dict(userId=uid,bookId=copy['bookId'],copyId=copy['id'],issueDate=iso,dueDate=(now+timedelta(days=n)).isoformat(),status='active',renewals=0,fineAmount=0))
        find('books',copy['bookId'])['borrowCount']+=1
        for r in s['reservations']:
            if r['userId']==uid and r['bookId']==copy['bookId'] and r['status'] in ('ready','waiting'): r['status']='fulfilled'
        notify(uid,f'Book issued. Due {result["dueDate"]}')
    elif command == 'returnCopy':
        need('admin','librarian'); barcode,paid=args
        if not isinstance(paid,bool): raise ValueError('Invalid payment flag')
        copy=next((c for c in s['copies'] if c['barcode'].lower()==barcode.lower()),None)
        if not copy: raise ValueError('Copy not found')
        l=next((l for l in s['loans'] if l['copyId']==copy['id'] and l['status']=='active'),None)
        if not l: raise ValueError('No active loan for this copy')
        overdue=late(l['dueDate'],now); amount=overdue*settings['finePerDay']; l.update(status='returned',returnDate=iso,fineAmount=amount); copy['status']='available'
        if amount: add('fines',dict(loanId=l['id'],userId=l['userId'],amount=amount,daysOverdue=overdue,rate=settings['finePerDay'],status='paid' if paid else 'unpaid',createdAt=iso))
        queue=sorted((r for r in s['reservations'] if r['bookId']==copy['bookId'] and r['status']=='waiting'),key=lambda r:r['reservedAt'])
        if queue:
            nxt=queue[0]; nxt.update(status='ready',copyId=copy['id'],expiresAt=(now+timedelta(days=settings['reservationHoldDays'])).isoformat()); copy['status']='on_hold'; notify(nxt['userId'],'Your reserved book is ready for pickup','reservation')
        result=dict(late=overdue,amount=amount,heldFor=queue[0]['userId'] if queue else None)
    elif command in ('payFine','waiveFine'):
        need('admin','librarian'); f=find('fines',args[0]); f['status']='paid' if command=='payFine' else 'waived'
    elif command == 'markRead':
        if args[0]!=actor: raise PermissionError('Only your own notifications may be updated')
        for n in s['notifications']:
            if n['userId']==actor: n['isRead']=True
    elif command == 'addReview':
        bid,rating,review=args; find('books',bid)
        if not isinstance(rating,int) or not 1<=rating<=5: raise ValueError('Rating must be 1–5')
        if not any(l['userId']==actor and l['bookId']==bid for l in s['loans']): raise PermissionError('Only verified borrowers may review')
        if any(r['userId']==actor and r['bookId']==bid for r in s['reviews']): raise ValueError('You already reviewed this book')
        add('reviews',dict(bookId=bid,userId=actor,userName=user['name'],rating=rating,text=text(review,5,500),verified=True,createdAt=iso))
        reviews=[r for r in s['reviews'] if r['bookId']==bid]; b=find('books',bid); b['rating']=round(sum(r['rating'] for r in reviews)/len(reviews),1); b['reviewCount']=len(reviews)
    elif command == 'updateProfile':
        name,roll,dept=args; user.update(name=text(name,2,100),rollNumber=text(roll,4,15),department=text(dept,2,60))
    elif command == 'updateSettings':
        need('admin'); patch=args[0]
        for k,v in patch.items():
            if k not in DEFAULTS or isinstance(v,bool) or not isinstance(v,int) or not 0<=v<=10000: raise ValueError('Invalid setting')
            if k in ('loanDays','maxLoans','reservationHoldDays') and v<1: raise ValueError('Setting must be positive')
            settings[k]=v
    elif command in ('setRole','setActive'):
        need('admin'); uid,value=args
        if uid==actor: raise ValueError('You cannot change your own access')
        target=find('users',uid)
        if command=='setRole':
            if value not in ('student','faculty','librarian','admin'): raise ValueError('Invalid role')
            result={'roleUserId':uid,'role':value}
        else:
            if not isinstance(value,bool): raise ValueError('Invalid active value')
            target['active']=value
    elif command == 'addBook':
        need('admin','librarian'); data=args[0]; n=data['copies']
        if not isinstance(n,int) or not 1<=n<=50: raise ValueError('Copies must be 1–50')
        isbn=text(data['isbn13'],13,13)
        if not isbn.isdigit(): raise ValueError('ISBN must be 13 digits')
        if any(b['isbn13']==isbn for b in s['books']): raise ValueError('ISBN already exists')
        year=data['year']
        if not isinstance(year,int) or not 1450<=year<=now.year+1: raise ValueError('Invalid publication year')
        b=add('books',dict(title=text(data['title'],1,150),authors=[text(data['author'],1,150)],category=text(data['category'],1,100),subjects=[data['category']],publisher=text(data['publisher'],1,150),year=year,isbn13=isbn,isbn10=isbn[3:],edition='1st Edition',language='English',format='physical',rating=0,reviewCount=0,description=data['title'],topics=[],coverColor='cover-2',shelf=text(data['shelf'],1,150),borrowCount=0,addedAt=iso,tags=[]))
        for _ in range(n): add('copies',dict(bookId=b['id'],barcode='UL'+uuid4().hex[:12].upper(),shelf=b['shelf'],status='available'))
        result=b['id']
    elif command == 'updateBook':
        need('admin','librarian'); b=find('books',args[0]); patch=args[1]
        for k,v in patch.items():
            if k not in ('title','authors','category','publisher','description','shelf','year'): raise ValueError('Unsupported book field')
            if k=='authors':
                if not isinstance(v,list) or not v: raise ValueError('Authors are required')
                v=[text(a,1,150) for a in v]
            elif k=='year':
                if not isinstance(v,int) or not 1450<=v<=now.year+1: raise ValueError('Invalid year')
            else: v=text(v,1,2000)
            b[k]=v
    elif command == 'addCopy':
        need('admin','librarian'); b=find('books',args[0]); add('copies',dict(bookId=b['id'],barcode='UL'+uuid4().hex[:12].upper(),shelf=b['shelf'],status='available'))
    elif command == 'setCopyStatus':
        need('admin','librarian'); c=find('copies',args[0]); status=args[1]
        if c['status'] in ('issued','on_hold'): raise ValueError('Return or release this copy first')
        if status not in ('available','lost','damaged','maintenance'): raise ValueError('Invalid copy status')
        c['status']=status
    elif command == 'submitResource':
        need('faculty','admin','librarian'); title,kind,course,url=args
        if kind not in ('Lecture Notes','Past Paper','Syllabus'): raise ValueError('Invalid resource kind')
        from urllib.parse import urlparse
        parsed=urlparse(url)
        if parsed.scheme!='https' or not parsed.hostname or parsed.username: raise ValueError('Provide an HTTPS resource link')
        add('resources',dict(title=text(title,3,120),kind=kind,course=text(course,1,20),url=url,approved=role=='admin',submittedBy=actor))
    elif command == 'approveResource':
        need('admin'); find('resources',args[0])['approved']=True
    else: raise ValueError('Unknown command')
    if command not in ('visit','markRead','toggleWishlist'): add('audit',dict(actorId=actor,action=command,detail=command,timestamp=iso))
    return result
