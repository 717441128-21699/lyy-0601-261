import os
import re
import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import pandas as pd
from PIL import Image

from database.db_manager import get_db
from core.models import (
    Invoice, Payment, Category, Department, Project,
    Rule, OperationLog, ApprovalList, StatisticsSummary,
    ImportResult, ApprovalBatch,
    STATUS_MAP, MATCH_STATUS_MAP, RULE_TYPE_MAP
)


class InvoiceService:
    @staticmethod
    def _safe_log(db, op_type, target_type, target_id, detail):
        try:
            db.log_operation(op_type, target_type, target_id, detail)
        except Exception:
            pass

    @staticmethod
    def get_all(keyword: str = '', status: str = '', 
                start_date: str = '', end_date: str = '') -> List[Invoice]:
        db = get_db()
        sql = 'SELECT * FROM invoices WHERE 1=1'
        params = []
        
        if keyword:
            sql += ' AND (file_name LIKE ? OR supplier LIKE ? OR invoice_no LIKE ? OR remark LIKE ?)'
            kw = f'%{keyword}%'
            params.extend([kw, kw, kw, kw])
        if status:
            sql += ' AND status = ?'
            params.append(status)
        if start_date:
            sql += ' AND invoice_date >= ?'
            params.append(start_date)
        if end_date:
            sql += ' AND invoice_date <= ?'
            params.append(end_date)
        
        sql += ' ORDER BY created_at DESC'
        rows = db.query(sql, tuple(params))
        return [InvoiceService._row_to_invoice(r) for r in rows]

    @staticmethod
    def get_by_id(invoice_id: int) -> Optional[Invoice]:
        db = get_db()
        row = db.query_one('SELECT * FROM invoices WHERE id = ?', (invoice_id,))
        return InvoiceService._row_to_invoice(row) if row else None

    @staticmethod
    def _row_to_invoice(row) -> Invoice:
        return Invoice(
            id=row['id'],
            file_path=row['file_path'],
            file_name=row['file_name'] or '',
            invoice_no=row['invoice_no'] or '',
            invoice_code=row['invoice_code'] or '',
            amount=row['amount'] or 0,
            tax_amount=row['tax_amount'] or 0,
            total_amount=row['total_amount'] or 0,
            invoice_date=row['invoice_date'] or '',
            supplier=row['supplier'] or '',
            buyer=row['buyer'] or '',
            category=row['category'] or '',
            department=row['department'] or '',
            project=row['project'] or '',
            reimbursable_amount=row['reimbursable_amount'] or 0,
            status=row['status'] or 'pending',
            is_duplicate=bool(row['is_duplicate']),
            has_attachment=bool(row['has_attachment']),
            remark=row['remark'] or '',
            opinion=row['opinion'] or '',
            ocr_result=row['ocr_result'] or '',
            created_at=row['created_at'] or '',
            updated_at=row['updated_at'] or ''
        )

    @staticmethod
    def create(invoice: Invoice) -> int:
        db = get_db()
        data = {
            'file_path': invoice.file_path,
            'file_name': invoice.file_name,
            'invoice_no': invoice.invoice_no,
            'invoice_code': invoice.invoice_code,
            'amount': invoice.amount,
            'tax_amount': invoice.tax_amount,
            'total_amount': invoice.total_amount,
            'invoice_date': invoice.invoice_date,
            'supplier': invoice.supplier,
            'buyer': invoice.buyer,
            'category': invoice.category,
            'department': invoice.department,
            'project': invoice.project,
            'reimbursable_amount': invoice.reimbursable_amount,
            'status': invoice.status,
            'is_duplicate': int(invoice.is_duplicate),
            'has_attachment': int(invoice.has_attachment),
            'remark': invoice.remark,
            'opinion': invoice.opinion,
            'ocr_result': invoice.ocr_result
        }
        new_id = db.insert('invoices', data)
        InvoiceService._safe_log(db, 'create', 'invoice', new_id, f'新增票据: {invoice.file_name}')
        return new_id

    @staticmethod
    def create_in_transaction(db, invoice: Invoice) -> int:
        data = {
            'file_path': invoice.file_path,
            'file_name': invoice.file_name,
            'invoice_no': invoice.invoice_no,
            'invoice_code': invoice.invoice_code,
            'amount': invoice.amount,
            'tax_amount': invoice.tax_amount,
            'total_amount': invoice.total_amount,
            'invoice_date': invoice.invoice_date,
            'supplier': invoice.supplier,
            'buyer': invoice.buyer,
            'category': invoice.category,
            'department': invoice.department,
            'project': invoice.project,
            'reimbursable_amount': invoice.reimbursable_amount,
            'status': invoice.status,
            'is_duplicate': int(invoice.is_duplicate),
            'has_attachment': int(invoice.has_attachment),
            'remark': invoice.remark,
            'opinion': invoice.opinion,
            'ocr_result': invoice.ocr_result
        }
        return db.insert_raw('invoices', data)

    @staticmethod
    def update(invoice_id: int, data: Dict) -> bool:
        db = get_db()
        if 'is_duplicate' in data:
            data['is_duplicate'] = int(data['is_duplicate'])
        if 'has_attachment' in data:
            data['has_attachment'] = int(data['has_attachment'])
        rows = db.update('invoices', data, 'id = ?', (invoice_id,))
        if rows > 0:
            InvoiceService._safe_log(db, 'update', 'invoice', invoice_id, f'更新票据信息')
        return rows > 0

    @staticmethod
    def batch_update(ids: List[int], data: Dict) -> int:
        if not ids or not data:
            return 0
        db = get_db()
        if 'is_duplicate' in data:
            data['is_duplicate'] = int(data['is_duplicate'])
        if 'has_attachment' in data:
            data['has_attachment'] = int(data['has_attachment'])
        
        data['updated_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        placeholders = ','.join(['?'] * len(ids))
        set_clause = ', '.join([f'{k} = ?' for k in data.keys()])
        sql = f'UPDATE invoices SET {set_clause} WHERE id IN ({placeholders})'
        params = list(data.values()) + ids
        
        cursor = db.execute(sql, tuple(params))
        db.commit()
        rows = cursor.rowcount
        
        if rows > 0:
            InvoiceService._safe_log(db, 'batch_update', 'invoice', 0, 
                                      f'批量更新 {rows} 张票据')
        return rows

    @staticmethod
    def delete(invoice_id: int) -> bool:
        db = get_db()
        invoice = InvoiceService.get_by_id(invoice_id)
        rows = db.delete('invoices', 'id = ?', (invoice_id,))
        if rows > 0 and invoice:
            InvoiceService._safe_log(db, 'delete', 'invoice', invoice_id, f'删除票据: {invoice.file_name}')
        return rows > 0

    @staticmethod
    def batch_create(invoices: List[Invoice]) -> List[int]:
        db = get_db()
        db.begin_transaction()
        try:
            ids = []
            for inv in invoices:
                new_id = InvoiceService.create_in_transaction(db, inv)
                ids.append(new_id)
            db.commit()
        except Exception:
            db.rollback()
            raise
        for i, inv in enumerate(invoices):
            InvoiceService._safe_log(db, 'create', 'invoice', ids[i], f'批量新增票据: {inv.file_name}')
        return ids

    @staticmethod
    def detect_duplicates() -> List[Tuple[Invoice, List[Invoice]]]:
        db = get_db()
        db.execute('UPDATE invoices SET is_duplicate = 0')
        db.commit()

        rows = db.query('SELECT * FROM invoices ORDER BY invoice_date')
        invoices = [InvoiceService._row_to_invoice(r) for r in rows]
        
        dup_ids = set()
        duplicates = []
        for i, inv in enumerate(invoices):
            if inv.id in dup_ids:
                continue
            dup_list = []
            for j, other in enumerate(invoices):
                if i >= j:
                    continue
                if other.id in dup_ids:
                    continue
                is_dup = False
                if inv.invoice_no and other.invoice_no and inv.invoice_no == other.invoice_no and inv.invoice_code and inv.invoice_code == other.invoice_code:
                    is_dup = True
                elif inv.total_amount > 0 and abs(inv.total_amount - other.total_amount) < 0.01 and inv.invoice_date == other.invoice_date and inv.supplier and inv.supplier == other.supplier:
                    is_dup = True
                if is_dup:
                    dup_list.append(other)
                    dup_ids.add(other.id)
            if dup_list:
                dup_ids.add(inv.id)
                duplicates.append((inv, dup_list))

        for inv, dup_list in duplicates:
            db.update('invoices', {'is_duplicate': 1}, 'id = ?', (inv.id,))
            for d in dup_list:
                db.update('invoices', {'is_duplicate': 1}, 'id = ?', (d.id,))
        db.commit()
        
        return duplicates

    @staticmethod
    def mark_duplicate(invoice_id: int, is_dup: bool = True):
        InvoiceService.update(invoice_id, {'is_duplicate': int(is_dup)})

    @staticmethod
    def calculate_reimbursable(invoice: Invoice) -> float:
        return invoice.total_amount


class PaymentService:
    @staticmethod
    def get_all(keyword: str = '', matched_status: str = '',
                start_date: str = '', end_date: str = '') -> List[Payment]:
        db = get_db()
        sql = 'SELECT * FROM payments WHERE 1=1'
        params = []
        
        if keyword:
            sql += ' AND (payment_no LIKE ? OR payee LIKE ? OR purpose LIKE ? OR remark LIKE ?)'
            kw = f'%{keyword}%'
            params.extend([kw, kw, kw, kw])
        if matched_status:
            sql += ' AND matched_status = ?'
            params.append(matched_status)
        if start_date:
            sql += ' AND pay_date >= ?'
            params.append(start_date)
        if end_date:
            sql += ' AND pay_date <= ?'
            params.append(end_date)
        
        sql += ' ORDER BY created_at DESC'
        rows = db.query(sql, tuple(params))
        return [PaymentService._row_to_payment(r) for r in rows]

    @staticmethod
    def get_by_id(payment_id: int) -> Optional[Payment]:
        db = get_db()
        row = db.query_one('SELECT * FROM payments WHERE id = ?', (payment_id,))
        return PaymentService._row_to_payment(row) if row else None

    @staticmethod
    def _row_to_payment(row) -> Payment:
        return Payment(
            id=row['id'],
            payment_no=row['payment_no'] or '',
            pay_date=row['pay_date'] or '',
            pay_amount=row['pay_amount'] or 0,
            payee=row['payee'] or '',
            bank_account=row['bank_account'] or '',
            bank_name=row['bank_name'] or '',
            purpose=row['purpose'] or '',
            remark=row['remark'] or '',
            invoice_id=row['invoice_id'],
            matched_status=row['matched_status'] or 'unmatched',
            created_at=row['created_at'] or '',
            updated_at=row['updated_at'] or ''
        )

    @staticmethod
    def create(payment: Payment) -> int:
        db = get_db()
        data = {
            'payment_no': payment.payment_no,
            'pay_date': payment.pay_date,
            'pay_amount': payment.pay_amount,
            'payee': payment.payee,
            'bank_account': payment.bank_account,
            'bank_name': payment.bank_name,
            'purpose': payment.purpose,
            'remark': payment.remark,
            'invoice_id': payment.invoice_id,
            'matched_status': payment.matched_status
        }
        new_id = db.insert('payments', data)
        InvoiceService._safe_log(db, 'create', 'payment', new_id, f'新增付款记录: {payment.payment_no}')
        return new_id

    @staticmethod
    def create_in_transaction(db, payment: Payment) -> int:
        data = {
            'payment_no': payment.payment_no,
            'pay_date': payment.pay_date,
            'pay_amount': payment.pay_amount,
            'payee': payment.payee,
            'bank_account': payment.bank_account,
            'bank_name': payment.bank_name,
            'purpose': payment.purpose,
            'remark': payment.remark,
            'invoice_id': payment.invoice_id,
            'matched_status': payment.matched_status
        }
        return db.insert_raw('payments', data)

    @staticmethod
    def batch_create(payments: List[Payment]) -> List[int]:
        db = get_db()
        db.begin_transaction()
        try:
            ids = []
            for pay in payments:
                new_id = PaymentService.create_in_transaction(db, pay)
                ids.append(new_id)
            db.commit()
        except Exception:
            db.rollback()
            raise
        for i, pay in enumerate(payments):
            InvoiceService._safe_log(db, 'create', 'payment', ids[i], f'批量新增付款记录: {pay.payment_no}')
        return ids

    @staticmethod
    def update(payment_id: int, data: Dict) -> bool:
        db = get_db()
        rows = db.update('payments', data, 'id = ?', (payment_id,))
        if rows > 0:
            InvoiceService._safe_log(db, 'update', 'payment', payment_id, f'更新付款记录')
        return rows > 0

    @staticmethod
    def delete(payment_id: int) -> bool:
        db = get_db()
        payment = PaymentService.get_by_id(payment_id)
        rows = db.delete('payments', 'id = ?', (payment_id,))
        if rows > 0 and payment:
            InvoiceService._safe_log(db, 'delete', 'payment', payment_id, f'删除付款记录: {payment.payment_no}')
        return rows > 0

    @staticmethod
    def match_payment_invoice(payment_id: int, invoice_id: int) -> bool:
        db = get_db()
        rows = db.update('payments', {
            'invoice_id': invoice_id,
            'matched_status': 'matched'
        }, 'id = ?', (payment_id,))
        if rows > 0:
            InvoiceService._safe_log(db, 'match', 'payment', payment_id, f'匹配票据ID: {invoice_id}')
        return rows > 0

    @staticmethod
    def auto_match() -> Dict:
        payments = PaymentService.get_all(matched_status='unmatched')
        invoices = InvoiceService.get_all()
        
        matched_count = 0
        for payment in payments:
            for invoice in invoices:
                if abs(payment.pay_amount - invoice.total_amount) < 0.01 and payment.pay_amount > 0:
                    if payment.payee and invoice.supplier:
                        if payment.payee in invoice.supplier or invoice.supplier in payment.payee:
                            PaymentService.match_payment_invoice(payment.id, invoice.id)
                            matched_count += 1
                            break
        return {'matched': matched_count, 'total': len(payments)}

    @staticmethod
    def get_unmatched_suppliers() -> List[str]:
        db = get_db()
        rows = db.query("SELECT DISTINCT payee FROM payments WHERE matched_status = 'unmatched' AND payee IS NOT NULL AND payee != ''")
        return [r['payee'] for r in rows]


class CategoryService:
    @staticmethod
    def get_all() -> List[Category]:
        db = get_db()
        rows = db.query('SELECT * FROM categories ORDER BY id')
        return [Category(id=r['id'], name=r['name'], parent_id=r['parent_id'], 
                        type=r['type'], description=r['description'] or '', created_at=r['created_at'] or '') for r in rows]

    @staticmethod
    def get_names() -> List[str]:
        return [c.name for c in CategoryService.get_all()]


class DepartmentService:
    @staticmethod
    def get_all() -> List[Department]:
        db = get_db()
        rows = db.query('SELECT * FROM departments ORDER BY id')
        return [Department(id=r['id'], name=r['name'], manager=r['manager'] or '', 
                          description=r['description'] or '', created_at=r['created_at'] or '') for r in rows]

    @staticmethod
    def get_names() -> List[str]:
        return [d.name for d in DepartmentService.get_all()]


class ProjectService:
    @staticmethod
    def get_all() -> List[Project]:
        db = get_db()
        rows = db.query('SELECT * FROM projects ORDER BY id')
        return [Project(id=r['id'], name=r['name'], code=r['code'] or '', 
                       manager=r['manager'] or '', description=r['description'] or '',
                       start_date=r['start_date'] or '', end_date=r['end_date'] or '',
                       created_at=r['created_at'] or '') for r in rows]

    @staticmethod
    def get_names() -> List[str]:
        return [p.name for p in ProjectService.get_all()]

    @staticmethod
    def create(project: Project) -> int:
        db = get_db()
        existing = db.query_one('SELECT id FROM projects WHERE name = ?', (project.name,))
        if existing:
            return existing['id']
        data = {
            'name': project.name,
            'code': project.code,
            'manager': project.manager,
            'description': project.description,
            'start_date': project.start_date,
            'end_date': project.end_date
        }
        new_id = db.insert('projects', data)
        InvoiceService._safe_log(db, 'create', 'project', new_id, f'新增项目: {project.name}')
        return new_id

    @staticmethod
    def get_by_name(name: str) -> Optional[Project]:
        db = get_db()
        row = db.query_one('SELECT * FROM projects WHERE name = ?', (name,))
        if row:
            return Project(id=row['id'], name=row['name'], code=row['code'] or '',
                          manager=row['manager'] or '', description=row['description'] or '',
                          start_date=row['start_date'] or '', end_date=row['end_date'] or '',
                          created_at=row['created_at'] or '')
        return None


class RuleService:
    @staticmethod
    def get_all(enabled_only: bool = False) -> List[Rule]:
        db = get_db()
        sql = 'SELECT * FROM rules'
        if enabled_only:
            sql += ' WHERE enabled = 1'
        sql += ' ORDER BY priority DESC, id'
        rows = db.query(sql)
        return [RuleService._row_to_rule(r) for r in rows]

    @staticmethod
    def _row_to_rule(row) -> Rule:
        return Rule(
            id=row['id'],
            name=row['name'],
            rule_type=row['rule_type'],
            condition=row['condition'] or '',
            action=row['action'] or '',
            value=row['value'] or '',
            priority=row['priority'] or 0,
            enabled=bool(row['enabled']),
            description=row['description'] or '',
            created_at=row['created_at'] or '',
            updated_at=row['updated_at'] or ''
        )

    @staticmethod
    def create(rule: Rule) -> int:
        db = get_db()
        data = {
            'name': rule.name,
            'rule_type': rule.rule_type,
            'condition': rule.condition,
            'action': rule.action,
            'value': rule.value,
            'priority': rule.priority,
            'enabled': int(rule.enabled),
            'description': rule.description
        }
        new_id = db.insert('rules', data)
        db.log_operation('create', 'rule', new_id, f'新增规则: {rule.name}')
        return new_id

    @staticmethod
    def update(rule_id: int, data: Dict) -> bool:
        db = get_db()
        if 'enabled' in data:
            data['enabled'] = int(data['enabled'])
        rows = db.update('rules', data, 'id = ?', (rule_id,))
        if rows > 0:
            db.log_operation('update', 'rule', rule_id, f'更新规则')
        return rows > 0

    @staticmethod
    def delete(rule_id: int) -> bool:
        db = get_db()
        rows = db.delete('rules', 'id = ?', (rule_id,))
        return rows > 0

    @staticmethod
    def apply_rules(invoice: Invoice) -> Invoice:
        rules = RuleService.get_all(enabled_only=True)
        for rule in rules:
            if rule.rule_type == 'category_auto' and rule.value:
                if rule.condition and rule.condition in invoice.supplier:
                    invoice.category = rule.value
            elif rule.rule_type == 'reimburse_calc' and rule.value:
                try:
                    rate = float(rule.value) / 100
                    invoice.reimbursable_amount = round(invoice.total_amount * rate, 2)
                except (ValueError, ZeroDivisionError):
                    pass
        return invoice


class ApprovalService:
    @staticmethod
    def _gen_batch_no() -> str:
        now = datetime.now()
        return f'APV{now.strftime("%Y%m%d%H%M%S")}'

    @staticmethod
    def get_all(status: str = '') -> List[ApprovalList]:
        db = get_db()
        sql = 'SELECT * FROM approval_lists WHERE 1=1'
        params = []
        if status:
            sql += ' AND status = ?'
            params.append(status)
        sql += ' ORDER BY created_at DESC'
        rows = db.query(sql, tuple(params))
        return [ApprovalList(
            id=r['id'], invoice_id=r['invoice_id'],
            batch_no=r['batch_no'] or '',
            applicant=r['applicant'] or '', apply_date=r['apply_date'] or '',
            amount=r['amount'] or 0, status=r['status'] or 'pending',
            approver=r['approver'] or '', approval_date=r['approval_date'] or '',
            approval_opinion=r['approval_opinion'] or '', created_at=r['created_at'] or ''
        ) for r in rows]

    @staticmethod
    def get_batches(status: str = '') -> List[ApprovalBatch]:
        db = get_db()
        sql = '''SELECT batch_no, applicant, apply_date, 
                        COALESCE(SUM(amount), 0) as total_amount,
                        COUNT(*) as invoice_count,
                        status, approver, approval_date, approval_opinion
                 FROM approval_lists 
                 WHERE batch_no IS NOT NULL AND batch_no != ?'''
        params = ['']
        if status:
            sql += ' AND status = ?'
            params.append(status)
        sql += ' GROUP BY batch_no ORDER BY MAX(created_at) DESC'
        rows = db.query(sql, tuple(params))
        return [ApprovalBatch(
            batch_no=r['batch_no'] or '',
            applicant=r['applicant'] or '',
            apply_date=r['apply_date'] or '',
            total_amount=r['total_amount'] or 0,
            invoice_count=r['invoice_count'] or 0,
            status=r['status'] or 'pending',
            approver=r['approver'] or '',
            approval_date=r['approval_date'] or '',
            approval_opinion=r['approval_opinion'] or ''
        ) for r in rows]

    @staticmethod
    def get_by_batch(batch_no: str) -> List[ApprovalList]:
        db = get_db()
        rows = db.query('SELECT * FROM approval_lists WHERE batch_no = ? ORDER BY id', (batch_no,))
        return [ApprovalList(
            id=r['id'], invoice_id=r['invoice_id'],
            batch_no=r['batch_no'] or '',
            applicant=r['applicant'] or '', apply_date=r['apply_date'] or '',
            amount=r['amount'] or 0, status=r['status'] or 'pending',
            approver=r['approver'] or '', approval_date=r['approval_date'] or '',
            approval_opinion=r['approval_opinion'] or '', created_at=r['created_at'] or ''
        ) for r in rows]

    @staticmethod
    def create(approval: ApprovalList) -> int:
        db = get_db()
        data = {
            'invoice_id': approval.invoice_id,
            'batch_no': approval.batch_no,
            'applicant': approval.applicant,
            'apply_date': approval.apply_date,
            'amount': approval.amount,
            'status': approval.status
        }
        new_id = db.insert('approval_lists', data)
        if approval.invoice_id:
            InvoiceService.update(approval.invoice_id, {'status': 'reviewing'})
        InvoiceService._safe_log(db, 'create', 'approval', new_id, f'创建待审批清单')
        return new_id

    @staticmethod
    def batch_submit(invoice_ids: List[int], applicant: str = 'admin') -> Tuple[str, int, float]:
        db = get_db()
        if not invoice_ids:
            return '', 0, 0.0
        
        batch_no = ApprovalService._gen_batch_no()
        now = datetime.now()
        apply_date = now.strftime('%Y-%m-%d')
        
        total_amount = 0.0
        count = 0
        
        db.begin_transaction()
        try:
            for inv_id in invoice_ids:
                inv = InvoiceService.get_by_id(inv_id)
                if not inv:
                    continue
                amount = inv.reimbursable_amount if inv.reimbursable_amount > 0 else inv.total_amount
                db.insert_raw('approval_lists', {
                    'invoice_id': inv_id,
                    'batch_no': batch_no,
                    'applicant': applicant,
                    'apply_date': apply_date,
                    'amount': amount,
                    'status': 'pending'
                })
                db.execute('UPDATE invoices SET status = ? WHERE id = ?', ('reviewing', inv_id))
                total_amount += amount
                count += 1
            db.commit()
        except Exception:
            db.rollback()
            raise
        
        InvoiceService._safe_log(db, 'batch_submit', 'approval', 0, 
                                  f'批次[{batch_no}] 提交审批: {count}张票据, 合计{total_amount:.2f}元')
        
        return batch_no, count, total_amount

    @staticmethod
    def approve(approval_id: int, approver: str = '', opinion: str = '') -> bool:
        db = get_db()
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        rows = db.update('approval_lists', {
            'status': 'approved',
            'approver': approver,
            'approval_date': now,
            'approval_opinion': opinion
        }, 'id = ?', (approval_id,))
        if rows > 0:
            approval = db.query_one('SELECT * FROM approval_lists WHERE id = ?', (approval_id,))
            if approval and approval['invoice_id']:
                InvoiceService.update(approval['invoice_id'], {'status': 'approved'})
            InvoiceService._safe_log(db, 'approve', 'approval', approval_id, f'审批通过')
        return rows > 0

    @staticmethod
    def reject(approval_id: int, approver: str = '', opinion: str = '') -> bool:
        db = get_db()
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        rows = db.update('approval_lists', {
            'status': 'rejected',
            'approver': approver,
            'approval_date': now,
            'approval_opinion': opinion
        }, 'id = ?', (approval_id,))
        if rows > 0:
            approval = db.query_one('SELECT * FROM approval_lists WHERE id = ?', (approval_id,))
            if approval and approval['invoice_id']:
                InvoiceService.update(approval['invoice_id'], {'status': 'rejected'})
            InvoiceService._safe_log(db, 'reject', 'approval', approval_id, f'审批驳回')
        return rows > 0

    @staticmethod
    def approve_batch(batch_no: str, approver: str = '', opinion: str = '') -> int:
        db = get_db()
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        rows = db.update('approval_lists', {
            'status': 'approved',
            'approver': approver,
            'approval_date': now,
            'approval_opinion': opinion
        }, 'batch_no = ?', (batch_no,))
        
        if rows > 0:
            items = db.query('SELECT invoice_id FROM approval_lists WHERE batch_no = ?', (batch_no,))
            for item in items:
                if item['invoice_id']:
                    db.execute('UPDATE invoices SET status = ? WHERE id = ?', ('approved', item['invoice_id']))
            db.commit()
            InvoiceService._safe_log(db, 'approve_batch', 'approval', 0, 
                                      f'批次[{batch_no}] 审批通过: {rows}张票据')
        return rows

    @staticmethod
    def reject_batch(batch_no: str, approver: str = '', opinion: str = '') -> int:
        db = get_db()
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        rows = db.update('approval_lists', {
            'status': 'rejected',
            'approver': approver,
            'approval_date': now,
            'approval_opinion': opinion
        }, 'batch_no = ?', (batch_no,))
        
        if rows > 0:
            items = db.query('SELECT invoice_id FROM approval_lists WHERE batch_no = ?', (batch_no,))
            for item in items:
                if item['invoice_id']:
                    db.execute('UPDATE invoices SET status = ? WHERE id = ?', ('rejected', item['invoice_id']))
            db.commit()
            InvoiceService._safe_log(db, 'reject_batch', 'approval', 0, 
                                      f'批次[{batch_no}] 审批驳回: {rows}张票据')
        return rows


class StatisticsService:
    @staticmethod
    def get_summary(start_date: str = '', end_date: str = '') -> StatisticsSummary:
        db = get_db()
        sql = 'SELECT * FROM invoices WHERE 1=1'
        params = []
        if start_date:
            sql += ' AND invoice_date >= ?'
            params.append(start_date)
        if end_date:
            sql += ' AND invoice_date <= ?'
            params.append(end_date)
        
        invoices = [InvoiceService._row_to_invoice(r) for r in db.query(sql, tuple(params))]
        payments = PaymentService.get_all()
        
        summary = StatisticsSummary()
        summary.invoice_count = len(invoices)
        summary.total_amount = sum(inv.total_amount for inv in invoices)
        summary.reimbursable_amount = sum(inv.reimbursable_amount for inv in invoices)
        summary.duplicate_count = sum(1 for inv in invoices if inv.is_duplicate)
        summary.missing_attachment_count = sum(1 for inv in invoices if not inv.has_attachment)
        
        matched_ids = set(p.invoice_id for p in payments if p.invoice_id and p.matched_status == 'matched')
        summary.matched_count = sum(1 for inv in invoices if inv.id in matched_ids)
        summary.unmatched_count = summary.invoice_count - summary.matched_count
        
        summary.pending_count = sum(1 for inv in invoices if inv.status == 'pending')
        summary.approved_count = sum(1 for inv in invoices if inv.status == 'approved')
        summary.rejected_count = sum(1 for inv in invoices if inv.status == 'rejected')
        
        return summary

    @staticmethod
    def get_monthly_summary(year: int) -> List[Dict]:
        db = get_db()
        result = []
        for month in range(1, 13):
            month_str = f'{year}-{month:02d}'
            rows = db.query(
                "SELECT COALESCE(SUM(total_amount), 0) as total, COALESCE(SUM(reimbursable_amount), 0) as reimburse, COUNT(*) as cnt FROM invoices WHERE strftime('%Y-%m', invoice_date) = ?",
                (month_str,)
            )
            row = rows[0]
            result.append({
                'month': f'{year}年{month}月',
                'total_amount': row['total'],
                'reimbursable_amount': row['reimburse'],
                'count': row['cnt']
            })
        return result

    @staticmethod
    def get_by_category(start_date: str = '', end_date: str = '') -> List[Dict]:
        db = get_db()
        sql = """SELECT category, COALESCE(SUM(total_amount), 0) as total, 
                        COALESCE(SUM(reimbursable_amount), 0) as reimburse, COUNT(*) as cnt 
                 FROM invoices WHERE category IS NOT NULL AND category != ''"""
        params = []
        if start_date:
            sql += ' AND invoice_date >= ?'
            params.append(start_date)
        if end_date:
            sql += ' AND invoice_date <= ?'
            params.append(end_date)
        sql += ' GROUP BY category ORDER BY total DESC'
        rows = db.query(sql, tuple(params))
        return [{'category': r['category'] or '未分类', 'total_amount': r['total'], 
                 'reimbursable_amount': r['reimburse'], 'count': r['cnt']} for r in rows]

    @staticmethod
    def get_by_department(start_date: str = '', end_date: str = '') -> List[Dict]:
        db = get_db()
        sql = """SELECT department, COALESCE(SUM(total_amount), 0) as total, 
                        COALESCE(SUM(reimbursable_amount), 0) as reimburse, COUNT(*) as cnt 
                 FROM invoices WHERE department IS NOT NULL AND department != ''"""
        params = []
        if start_date:
            sql += ' AND invoice_date >= ?'
            params.append(start_date)
        if end_date:
            sql += ' AND invoice_date <= ?'
            params.append(end_date)
        sql += ' GROUP BY department ORDER BY total DESC'
        rows = db.query(sql, tuple(params))
        return [{'department': r['department'] or '未分配', 'total_amount': r['total'],
                 'reimbursable_amount': r['reimburse'], 'count': r['cnt']} for r in rows]

    @staticmethod
    def export_report(file_path: str, start_date: str = '', end_date: str = ''):
        invoices = InvoiceService.get_all(start_date=start_date, end_date=end_date)
        payments = PaymentService.get_all(start_date=start_date, end_date=end_date)
        
        with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
            df_invoices = pd.DataFrame([{
                'ID': inv.id,
                '文件名': inv.file_name,
                '发票号': inv.invoice_no,
                '发票代码': inv.invoice_code,
                '开票日期': inv.invoice_date,
                '供应商': inv.supplier,
                '购买方': inv.buyer,
                '金额': inv.amount,
                '税额': inv.tax_amount,
                '价税合计': inv.total_amount,
                '可报销金额': inv.reimbursable_amount,
                '费用类别': inv.category,
                '所属部门': inv.department,
                '所属项目': inv.project,
                '状态': STATUS_MAP.get(inv.status, inv.status),
                '是否重复': '是' if inv.is_duplicate else '否',
                '有附件': '是' if inv.has_attachment else '否',
                '备注': inv.remark,
                '处理意见': inv.opinion
            } for inv in invoices])
            df_invoices.to_excel(writer, sheet_name='票据明细', index=False)
            
            df_payments = pd.DataFrame([{
                'ID': pay.id,
                '流水号': pay.payment_no,
                '付款日期': pay.pay_date,
                '付款金额': pay.pay_amount,
                '收款方': pay.payee,
                '银行账号': pay.bank_account,
                '开户行': pay.bank_name,
                '用途': pay.purpose,
                '备注': pay.remark,
                '关联票据ID': pay.invoice_id or '',
                '匹配状态': MATCH_STATUS_MAP.get(pay.matched_status, pay.matched_status)
            } for pay in payments])
            df_payments.to_excel(writer, sheet_name='付款流水', index=False)
            
            summary = StatisticsService.get_summary(start_date, end_date)
            df_summary = pd.DataFrame([{
                '统计项': '票据总数',
                '数值': summary.invoice_count
            }, {
                '统计项': '总金额',
                '数值': summary.total_amount
            }, {
                '统计项': '可报销总金额',
                '数值': summary.reimbursable_amount
            }, {
                '统计项': '已匹配数',
                '数值': summary.matched_count
            }, {
                '统计项': '未匹配数',
                '数值': summary.unmatched_count
            }, {
                '统计项': '重复票据数',
                '数值': summary.duplicate_count
            }, {
                '统计项': '缺少附件数',
                '数值': summary.missing_attachment_count
            }, {
                '统计项': '待处理数',
                '数值': summary.pending_count
            }, {
                '统计项': '已通过数',
                '数值': summary.approved_count
            }, {
                '统计项': '已驳回数',
                '数值': summary.rejected_count
            }])
            df_summary.to_excel(writer, sheet_name='汇总统计', index=False)
            
            df_cat = pd.DataFrame(StatisticsService.get_by_category(start_date, end_date))
            if not df_cat.empty:
                df_cat.to_excel(writer, sheet_name='分类统计', index=False)


class OperationLogService:
    @staticmethod
    def get_all(limit: int = 200) -> List[OperationLog]:
        db = get_db()
        rows = db.query('SELECT * FROM operation_logs ORDER BY id DESC LIMIT ?', (limit,))
        return [OperationLog(
            id=r['id'], operation_type=r['operation_type'] or '',
            target_type=r['target_type'] or '', target_id=r['target_id'],
            detail=r['detail'] or '', operator=r['operator'] or '',
            created_at=r['created_at'] or ''
        ) for r in rows]


class OCRService:
    @staticmethod
    def _parse_filename(file_name: str) -> Dict:
        result = {
            'invoice_no': '',
            'invoice_code': '',
            'amount': 0.0,
            'tax_amount': 0.0,
            'total_amount': 0.0,
            'invoice_date': '',
            'supplier': '',
            'buyer': '',
            'raw_text': ''
        }

        name_no_ext = os.path.splitext(file_name)[0]
        result['raw_text'] = f'[文件名解析] {file_name}'

        date_match = re.search(r'(\d{4})[年\-./](\d{1,2})[月\-./](\d{1,2})日?', name_no_ext)
        if date_match:
            y, m, d = date_match.group(1), int(date_match.group(2)), int(date_match.group(3))
            result['invoice_date'] = f'{y}-{m:02d}-{d:02d}'
        else:
            date_match2 = re.search(r'(\d{4})(\d{2})(\d{2})', name_no_ext)
            if date_match2:
                y, m, d = date_match2.group(1), int(date_match2.group(2)), int(date_match2.group(3))
                if 1 <= m <= 12 and 1 <= d <= 31:
                    result['invoice_date'] = f'{y}-{m:02d}-{d:02d}'

        inv_no_match = re.search(r'(?:发票号|票号|No\.?|编号)[：:\s]*(\d{6,20})', name_no_ext, re.IGNORECASE)
        if inv_no_match:
            result['invoice_no'] = inv_no_match.group(1)

        cleaned = name_no_ext
        for pattern in [r'(\d{4})[年\-./](\d{1,2})[月\-./](\d{1,2})日?', r'(\d{4})(\d{2})(\d{2})',
                        r'(?:发票号|票号|No\.?|编号)[：:\s]*\d{6,20}',
                        r'(?:供应商|销方|收款方|收款人)[：:\s]*[^\s,，\-_]+']:
            cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE)

        amount_match = re.search(r'[¥￥]?\s*(\d+(?:\.\d{1,2})?)\s*元?', cleaned)
        if amount_match:
            val = float(amount_match.group(1))
            if val < 100000:
                result['total_amount'] = val
                result['amount'] = round(val / 1.06, 2) if val > 0 else 0.0
                result['tax_amount'] = round(val - result['amount'], 2)
        else:
            amount_match2 = re.search(r'[¥￥]\s*(\d+)', cleaned)
            if amount_match2:
                val = float(amount_match2.group(1))
                result['total_amount'] = val
                result['amount'] = round(val / 1.06, 2) if val > 0 else 0.0
                result['tax_amount'] = round(val - result['amount'], 2)

        supplier_match = re.search(r'(?:供应商|销方|收款方|收款人)[：:\s]*([^\s,，\-_]+)', name_no_ext)
        if supplier_match:
            result['supplier'] = supplier_match.group(1).strip()

        skip_words = ('发票号', '票号', '供应商', '销方', '收款方', '元', '年', '月', '日',
                      '报销', '差旅费', '办公费', '交通费', '招待费', '通讯费', '培训费', '福利费',
                      '其他费', '发票', '收据', '凭证', '附件', '回单', '账单')

        parts = re.split(r'[_\-\s]+', name_no_ext)
        if not result['supplier'] and len(parts) >= 2:
            for part in parts:
                cn = re.search(r'[\u4e00-\u9fff]{2,}(?:公司|有限|集团|科技|商贸|服务|咨询)', part)
                if cn:
                    result['supplier'] = cn.group(0)
                    break
        if not result['supplier'] and len(parts) >= 2:
            for part in parts:
                cn = re.search(r'[\u4e00-\u9fff]{2,}', part)
                if cn and cn.group(0) not in skip_words:
                    result['supplier'] = cn.group(0)
                    break

        if result['invoice_no'] or result['total_amount'] > 0 or result['invoice_date']:
            result['raw_text'] += f'\n解析结果: 发票号={result["invoice_no"]}, 金额={result["total_amount"]}, 日期={result["invoice_date"]}, 供应商={result["supplier"]}'

        return result

    @staticmethod
    def recognize(image_path: str) -> Dict:
        file_name = os.path.basename(image_path)
        result = OCRService._parse_filename(file_name)

        try:
            if os.path.exists(image_path):
                img = Image.open(image_path)
                result['raw_text'] += f'\n[图片信息] 尺寸: {img.size[0]}x{img.size[1]}, 格式: {img.format or "未知"}'
        except Exception as e:
            result['raw_text'] += f'\n[警告] 图片读取失败: {str(e)}'

        return result


class FileImportService:
    @staticmethod
    def _gen_batch_no(prefix: str = 'IMP') -> str:
        now = datetime.now()
        return f'{prefix}{now.strftime("%Y%m%d%H%M%S")}'

    @staticmethod
    def import_images(file_paths: List[str]) -> Tuple[List[Invoice], List[str]]:
        invoices = []
        skipped = []
        for i, path in enumerate(file_paths):
            if not os.path.exists(path):
                skipped.append(f'第{i+1}张: 文件不存在 - {os.path.basename(path)}')
                continue
            file_name = os.path.basename(path)
            ocr_result = OCRService.recognize(path)
            
            invoice = Invoice(
                file_path=path,
                file_name=file_name,
                invoice_no=ocr_result['invoice_no'],
                invoice_code=ocr_result['invoice_code'],
                amount=ocr_result['amount'],
                tax_amount=ocr_result['tax_amount'],
                total_amount=ocr_result['total_amount'],
                invoice_date=ocr_result['invoice_date'],
                supplier=ocr_result['supplier'],
                buyer=ocr_result['buyer'],
                reimbursable_amount=ocr_result['total_amount'],
                has_attachment=True,
                ocr_result=ocr_result['raw_text']
            )
            invoices.append(invoice)
        return invoices, skipped

    @staticmethod
    def import_excel(file_path: str) -> Tuple[List[Invoice], List[Payment], List[str]]:
        invoices = []
        payments = []
        skipped = []
        
        try:
            xls = pd.ExcelFile(file_path)
            for sheet_name in xls.sheet_names:
                df = pd.read_excel(file_path, sheet_name=sheet_name)
                if df.empty:
                    skipped.append(f'Sheet[{sheet_name}]: 空表，已跳过')
                    continue
                
                df.columns = [str(c).strip() for c in df.columns]
                has_invoice_cols = any(c in df.columns for c in ['发票号', '发票号码', 'invoice_no', 'invoice number'])
                has_payment_cols = any(c in df.columns for c in ['流水号', '付款流水号', 'payment_no'])

                if has_invoice_cols:
                    inv_skipped = 0
                    for idx, (_, row) in enumerate(df.iterrows()):
                        inv = Invoice()
                        has_data = False
                        for col in df.columns:
                            val = '' if pd.isna(row[col]) else str(row[col]).strip()
                            col_lower = col.lower()
                            if col in ['发票号', '发票号码'] or 'invoice_no' in col_lower or 'invoice number' in col_lower:
                                inv.invoice_no = val
                                if val:
                                    has_data = True
                            elif col in ['发票代码']:
                                inv.invoice_code = val
                            elif col in ['开票日期', '日期'] or 'date' in col_lower:
                                inv.invoice_date = val
                                if val:
                                    has_data = True
                            elif col in ['供应商', '销售方', '收款方'] or 'supplier' in col_lower:
                                inv.supplier = val
                                if val:
                                    has_data = True
                            elif col in ['购买方', '客户'] or 'buyer' in col_lower:
                                inv.buyer = val
                            elif col in ['金额', '不含税金额'] or 'amount' in col_lower:
                                try:
                                    v = float(val)
                                    inv.amount = v
                                    if v > 0:
                                        has_data = True
                                except ValueError:
                                    pass
                            elif col in ['税额'] or 'tax' in col_lower:
                                try:
                                    inv.tax_amount = float(val)
                                except ValueError:
                                    pass
                            elif col in ['价税合计', '总金额', '合计'] or 'total' in col_lower:
                                try:
                                    v = float(val)
                                    inv.total_amount = v
                                    if v > 0:
                                        has_data = True
                                except ValueError:
                                    pass
                            elif col in ['费用类别', '类别'] or 'category' in col_lower:
                                inv.category = val
                            elif col in ['部门'] or 'department' in col_lower:
                                inv.department = val
                            elif col in ['项目'] or 'project' in col_lower:
                                inv.project = val
                            elif col in ['备注'] or 'remark' in col_lower:
                                inv.remark = val
                        
                        if has_data and inv.total_amount > 0:
                            if inv.reimbursable_amount == 0:
                                inv.reimbursable_amount = inv.total_amount
                            invoices.append(inv)
                        else:
                            inv_skipped += 1
                    if inv_skipped > 0:
                        skipped.append(f'Sheet[{sheet_name}]-票据: 跳过 {inv_skipped} 条空行/无有效数据的行')

                if has_payment_cols:
                    pay_skipped = 0
                    for idx, (_, row) in enumerate(df.iterrows()):
                        pay = Payment()
                        has_data = False
                        for col in df.columns:
                            val = '' if pd.isna(row[col]) else str(row[col]).strip()
                            col_lower = col.lower()
                            if col in ['流水号', '付款流水号'] or 'payment_no' in col_lower:
                                pay.payment_no = val
                                if val:
                                    has_data = True
                            elif col in ['付款日期', '支付日期'] or 'pay_date' in col_lower or 'payment date' in col_lower:
                                pay.pay_date = val
                            elif col in ['付款金额', '支付金额'] or 'pay_amount' in col_lower or 'amount' in col_lower:
                                if 'total' in col_lower or '价税' in col or '合计' in col:
                                    continue
                                try:
                                    v = float(val)
                                    pay.pay_amount = v
                                    if v > 0:
                                        has_data = True
                                except ValueError:
                                    pass
                            elif col in ['收款方', '收款人', '供应商'] or 'payee' in col_lower:
                                pay.payee = val
                                if val:
                                    has_data = True
                            elif col in ['银行账号', '账号'] or 'account' in col_lower:
                                pay.bank_account = val
                            elif col in ['开户行', '开户银行'] or 'bank' in col_lower:
                                pay.bank_name = val
                            elif col in ['用途', '摘要'] or 'purpose' in col_lower:
                                pay.purpose = val
                            elif col in ['备注'] or 'remark' in col_lower:
                                pay.remark = val
                        
                        if has_data and pay.pay_amount > 0:
                            payments.append(pay)
                        else:
                            pay_skipped += 1
                    if pay_skipped > 0:
                        skipped.append(f'Sheet[{sheet_name}]-流水: 跳过 {pay_skipped} 条空行/无有效数据的行')

                if not has_invoice_cols and not has_payment_cols:
                    skipped.append(f'Sheet[{sheet_name}]: 未识别到票据或流水列，已跳过')
        except Exception as e:
            skipped.append(f'读取失败: {str(e)}')
        
        return invoices, payments, skipped

    @staticmethod
    def import_csv(file_path: str) -> Tuple[List[Invoice], List[Payment], List[str]]:
        invoices = []
        payments = []
        skipped = []
        try:
            df = pd.read_csv(file_path)
            temp_xlsx = file_path + '.xlsx'
            df.to_excel(temp_xlsx, index=False)
            invoices, payments, skipped = FileImportService.import_excel(temp_xlsx)
            if os.path.exists(temp_xlsx):
                os.remove(temp_xlsx)
        except Exception as e:
            skipped.append(f'CSV读取失败: {str(e)}')
        return invoices, payments, skipped

    @staticmethod
    def batch_import(invoices: List[Invoice], payments: List[Payment], source: str = '手动导入') -> ImportResult:
        db = get_db()
        batch_no = FileImportService._gen_batch_no()
        result = ImportResult(batch_no=batch_no)

        if not invoices and not payments:
            result.error_msg = '没有可导入的数据'
            return result

        db.begin_transaction()
        try:
            inv_ids = []
            for inv in invoices:
                new_id = InvoiceService.create_in_transaction(db, inv)
                inv_ids.append(new_id)
            result.invoice_count = len(inv_ids)

            pay_ids = []
            for pay in payments:
                new_id = PaymentService.create_in_transaction(db, pay)
                pay_ids.append(new_id)
            result.payment_count = len(pay_ids)

            db.commit()
            result.success = True
        except Exception as e:
            db.rollback()
            result.success = False
            result.error_msg = str(e)
            return result

        try:
            detail = f'批次[{batch_no}] {source}: 成功导入票据{result.invoice_count}张, 流水{result.payment_count}条'
            InvoiceService._safe_log(db, 'batch_import', 'import', 0, detail)
        except Exception:
            pass

        return result
