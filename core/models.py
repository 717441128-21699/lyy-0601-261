from dataclasses import dataclass, field
from typing import Optional, List
from datetime import datetime


@dataclass
class Invoice:
    id: Optional[int] = None
    file_path: str = ''
    file_name: str = ''
    invoice_no: str = ''
    invoice_code: str = ''
    amount: float = 0.0
    tax_amount: float = 0.0
    total_amount: float = 0.0
    invoice_date: str = ''
    supplier: str = ''
    buyer: str = ''
    category: str = ''
    department: str = ''
    project: str = ''
    reimbursable_amount: float = 0.0
    status: str = 'pending'
    is_duplicate: bool = False
    has_attachment: bool = True
    remark: str = ''
    opinion: str = ''
    ocr_result: str = ''
    created_at: str = ''
    updated_at: str = ''


@dataclass
class Payment:
    id: Optional[int] = None
    payment_no: str = ''
    pay_date: str = ''
    pay_amount: float = 0.0
    payee: str = ''
    bank_account: str = ''
    bank_name: str = ''
    purpose: str = ''
    remark: str = ''
    invoice_id: Optional[int] = None
    matched_status: str = 'unmatched'
    created_at: str = ''
    updated_at: str = ''


@dataclass
class Category:
    id: Optional[int] = None
    name: str = ''
    parent_id: Optional[int] = None
    type: str = 'expense'
    description: str = ''
    created_at: str = ''


@dataclass
class Department:
    id: Optional[int] = None
    name: str = ''
    manager: str = ''
    description: str = ''
    created_at: str = ''


@dataclass
class Project:
    id: Optional[int] = None
    name: str = ''
    code: str = ''
    manager: str = ''
    description: str = ''
    start_date: str = ''
    end_date: str = ''
    created_at: str = ''


@dataclass
class Rule:
    id: Optional[int] = None
    name: str = ''
    rule_type: str = ''
    condition: str = ''
    action: str = ''
    value: str = ''
    priority: int = 0
    enabled: bool = True
    description: str = ''
    created_at: str = ''
    updated_at: str = ''


@dataclass
class OperationLog:
    id: Optional[int] = None
    operation_type: str = ''
    target_type: str = ''
    target_id: Optional[int] = None
    detail: str = ''
    operator: str = 'admin'
    created_at: str = ''


@dataclass
class ApprovalList:
    id: Optional[int] = None
    invoice_id: Optional[int] = None
    applicant: str = ''
    apply_date: str = ''
    amount: float = 0.0
    status: str = 'pending'
    approver: str = ''
    approval_date: str = ''
    approval_opinion: str = ''
    created_at: str = ''


@dataclass
class StatisticsSummary:
    total_amount: float = 0.0
    reimbursable_amount: float = 0.0
    invoice_count: int = 0
    matched_count: int = 0
    unmatched_count: int = 0
    duplicate_count: int = 0
    missing_attachment_count: int = 0
    pending_count: int = 0
    approved_count: int = 0
    rejected_count: int = 0


STATUS_MAP = {
    'pending': '待处理',
    'reviewing': '审核中',
    'approved': '已通过',
    'rejected': '已驳回',
    'archived': '已归档'
}

MATCH_STATUS_MAP = {
    'unmatched': '未匹配',
    'matched': '已匹配',
    'partial': '部分匹配',
    'conflict': '匹配冲突'
}

RULE_TYPE_MAP = {
    'category_auto': '自动分类',
    'amount_limit': '金额限制',
    'duplicate_detect': '重复检测',
    'reimburse_calc': '报销计算',
    'approval_flow': '审批流程',
    'custom': '自定义规则'
}
