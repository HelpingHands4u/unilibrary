from datetime import datetime, timezone
import copy
import pytest
from domain import apply, COLLECTIONS, DEFAULTS
NOW=datetime(2026,10,27,tzinfo=timezone.utc)
def seed():
    s={k:[] for k in COLLECTIONS}; s['settings']=dict(DEFAULTS)
    s['users']=[dict(id=id,name=id,active=True,maxBorrowLimit=4) for id in ['student','other','staff']]
    s['books']=[dict(id='book',title='Algorithms',format='physical',borrowCount=0)]
    s['copies']=[dict(id='copy',bookId='book',barcode='UL1000',status='available',shelf='A')]
    return s

def test_student_cannot_issue():
    with pytest.raises(PermissionError): apply(seed(),'student','student','issue',['other','UL1000',14],NOW)
def test_four_loans_block_issue():
    s=seed(); s['loans']=[dict(id=str(i),userId='student',status='active') for i in range(4)]
    with pytest.raises(ValueError,match='limit'): apply(s,'staff','librarian','issue',['student','UL1000',14],NOW)
def test_default_due_is_fourteen_days():
    loan=apply(seed(),'staff','librarian','issue',['student','UL1000',14],NOW)
    assert loan['dueDate']=='2026-11-10T00:00:00+00:00'
def test_late_return_five_per_day_and_queue_hold():
    s=seed(); apply(s,'staff','librarian','issue',['student','UL1000',14],NOW)
    s['loans'][0]['dueDate']='2026-10-23T00:00:00+00:00'
    apply(s,'other','student','reserve',['book'],NOW)
    result=apply(s,'staff','librarian','returnCopy',['UL1000',False],NOW)
    assert result['amount']==20
    assert s['copies'][0]['status']=='on_hold'
    assert s['reservations'][0]['userId']=='other'
def test_student_cannot_pay_real_fine():
    with pytest.raises(PermissionError): apply(seed(),'student','student','payFine',['f'],NOW)
def test_cannot_cancel_another_students_reservation():
    s=seed(); apply(s,'other','student','reserve',['book'],NOW)
    with pytest.raises(PermissionError): apply(s,'student','student','cancelReservation',[s['reservations'][0]['id']],NOW)
def test_only_admin_assigns_roles():
    with pytest.raises(PermissionError): apply(seed(),'staff','librarian','setRole',['student','admin'],NOW)
def test_unborrowed_review_rejected():
    with pytest.raises(PermissionError): apply(seed(),'student','student','addReview',['book',5,'Good book'],NOW)
def test_pending_materials_cannot_be_approved_by_faculty():
    with pytest.raises(PermissionError): apply(seed(),'staff','faculty','approveResource',['r'],NOW)
def test_invalid_days_rejected():
    with pytest.raises(ValueError): apply(seed(),'staff','librarian','issue',['student','UL1000',0],NOW)
def test_100_fine_threshold():
    s=seed(); s['fines']=[dict(id='fine',userId='student',amount=101,status='unpaid')]
    with pytest.raises(ValueError,match='fines'): apply(s,'staff','librarian','issue',['student','UL1000',14],NOW)
