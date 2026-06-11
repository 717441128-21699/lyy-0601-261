from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QTableWidget,
    QTableWidgetItem, QHeaderView, QTabWidget, QMessageBox, QAbstractItemView,
    QGroupBox, QFormLayout, QLineEdit, QComboBox, QTextEdit, QInputDialog
)
from PyQt6.QtCore import Qt

from core.services import (
    InvoiceService, ApprovalService, PaymentService
)
from core.models import STATUS_MAP, MATCH_STATUS_MAP


class ExceptionWindow(QWidget):
    def __init__(self):
        super().__init__()
        self._init_ui()
        self.refresh()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        title = QLabel('异常清单')
        title.setStyleSheet('font-size: 20px; font-weight: bold; color: #2c3e50;')
        layout.addWidget(title)
        
        summary_bar = QHBoxLayout()
        self.lbl_dup_count = QLabel('🔁 重复票据: 0')
        self.lbl_dup_count.setStyleSheet('font-size: 14px; font-weight: bold; color: #e67e22; padding: 8px 16px; background: #fff3e0; border-radius: 6px;')
        summary_bar.addWidget(self.lbl_dup_count)
        
        self.lbl_missing_count = QLabel('📎 缺少附件: 0')
        self.lbl_missing_count.setStyleSheet('font-size: 14px; font-weight: bold; color: #e74c3c; padding: 8px 16px; background: #ffebee; border-radius: 6px;')
        summary_bar.addWidget(self.lbl_missing_count)
        
        self.lbl_unmatched_count = QLabel('🔗 未匹配流水: 0')
        self.lbl_unmatched_count.setStyleSheet('font-size: 14px; font-weight: bold; color: #9b59b6; padding: 8px 16px; background: #f3e5f5; border-radius: 6px;')
        summary_bar.addWidget(self.lbl_unmatched_count)
        
        self.lbl_pending_count = QLabel('📋 待审批: 0')
        self.lbl_pending_count.setStyleSheet('font-size: 14px; font-weight: bold; color: #3498db; padding: 8px 16px; background: #e3f2fd; border-radius: 6px;')
        summary_bar.addWidget(self.lbl_pending_count)
        
        summary_bar.addStretch()
        layout.addLayout(summary_bar)
        
        self.tabs = QTabWidget()
        
        self._init_duplicate_tab()
        self._init_missing_tab()
        self._init_unmatched_tab()
        self._init_approval_tab()
        
        self.tabs.currentChanged.connect(self._on_tab_changed)
        layout.addWidget(self.tabs, 1)

    def _init_duplicate_tab(self):
        tab = QWidget()
        tab_layout = QVBoxLayout(tab)
        
        bar = QHBoxLayout()
        desc = QLabel('系统检测到可能重复的票据（相同发票号/相同日期金额供应商），请核实后处理。')
        desc.setStyleSheet('color: #666;')
        bar.addWidget(desc)
        bar.addStretch()
        
        self.btn_detect_dup = QPushButton('🔍 重新检测重复')
        self.btn_detect_dup.setStyleSheet(self._btn_style('#e67e22'))
        self.btn_detect_dup.clicked.connect(self._detect_duplicates)
        bar.addWidget(self.btn_detect_dup)
        
        self.btn_mark_dup = QPushButton('⚠️ 标记为重复')
        self.btn_mark_dup.setStyleSheet(self._btn_style('#e74c3c'))
        self.btn_mark_dup.clicked.connect(lambda: self._mark_dup(True))
        bar.addWidget(self.btn_mark_dup)
        
        self.btn_unmark_dup = QPushButton('✅ 取消重复标记')
        self.btn_unmark_dup.setStyleSheet(self._btn_style('#27ae60'))
        self.btn_unmark_dup.clicked.connect(lambda: self._mark_dup(False))
        bar.addWidget(self.btn_unmark_dup)
        
        tab_layout.addLayout(bar)
        
        self.dup_table = QTableWidget(0, 9)
        self.dup_table.setHorizontalHeaderLabels([
            'ID', '文件名', '发票号', '开票日期', '供应商', '价税合计', '类别', '是否重复', '备注'
        ])
        self.dup_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.dup_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.dup_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.dup_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        tab_layout.addWidget(self.dup_table)
        
        self.tabs.addTab(tab, '🔁 重复票据')

    def _init_missing_tab(self):
        tab = QWidget()
        tab_layout = QVBoxLayout(tab)
        
        bar = QHBoxLayout()
        desc = QLabel('缺少附件的票据清单，需补齐相关附件后再处理。')
        desc.setStyleSheet('color: #666;')
        bar.addWidget(desc)
        bar.addStretch()
        
        self.btn_mark_has_attach = QPushButton('📎 标记为已有附件')
        self.btn_mark_has_attach.setStyleSheet(self._btn_style('#27ae60'))
        self.btn_mark_has_attach.clicked.connect(lambda: self._toggle_attach(True))
        bar.addWidget(self.btn_mark_has_attach)
        
        self.btn_mark_no_attach = QPushButton('❌ 标记为缺少附件')
        self.btn_mark_no_attach.setStyleSheet(self._btn_style('#e74c3c'))
        self.btn_mark_no_attach.clicked.connect(lambda: self._toggle_attach(False))
        bar.addWidget(self.btn_mark_no_attach)
        
        tab_layout.addLayout(bar)
        
        self.missing_table = QTableWidget(0, 9)
        self.missing_table.setHorizontalHeaderLabels([
            'ID', '文件名', '发票号', '开票日期', '供应商', '价税合计', '类别', '有附件', '备注'
        ])
        self.missing_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.missing_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.missing_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.missing_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        tab_layout.addWidget(self.missing_table)
        
        self.tabs.addTab(tab, '📎 缺少附件')

    def _init_unmatched_tab(self):
        tab = QWidget()
        tab_layout = QVBoxLayout(tab)
        
        bar = QHBoxLayout()
        desc = QLabel('未匹配到票据的付款流水，请在"流水匹配"页面完成匹配。')
        desc.setStyleSheet('color: #666;')
        bar.addWidget(desc)
        bar.addStretch()
        tab_layout.addLayout(bar)
        
        self.unmatched_table = QTableWidget(0, 7)
        self.unmatched_table.setHorizontalHeaderLabels([
            'ID', '流水号', '付款日期', '付款金额', '收款方', '用途', '匹配状态'
        ])
        self.unmatched_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.unmatched_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.unmatched_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.unmatched_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        tab_layout.addWidget(self.unmatched_table)
        
        self.tabs.addTab(tab, '🔗 未匹配流水')

    def _init_approval_tab(self):
        tab = QWidget()
        tab_layout = QVBoxLayout(tab)
        
        bar = QHBoxLayout()
        self.approval_filter = QComboBox()
        self.approval_filter.addItem('全部状态', '')
        self.approval_filter.addItem('待审批', 'pending')
        self.approval_filter.addItem('已通过', 'approved')
        self.approval_filter.addItem('已驳回', 'rejected')
        self.approval_filter.currentIndexChanged.connect(lambda: self._refresh_approval())
        bar.addWidget(QLabel('状态筛选:'))
        bar.addWidget(self.approval_filter)
        bar.addStretch()
        
        self.btn_approve = QPushButton('✅ 通过审批')
        self.btn_approve.setStyleSheet(self._btn_style('#27ae60'))
        self.btn_approve.clicked.connect(lambda: self._approve_reject('approve'))
        bar.addWidget(self.btn_approve)
        
        self.btn_reject = QPushButton('❌ 驳回审批')
        self.btn_reject.setStyleSheet(self._btn_style('#e74c3c'))
        self.btn_reject.clicked.connect(lambda: self._approve_reject('reject'))
        bar.addWidget(self.btn_reject)
        
        tab_layout.addLayout(bar)
        
        self.approval_table = QTableWidget(0, 10)
        self.approval_table.setHorizontalHeaderLabels([
            'ID', '票据文件名', '申请人', '申请日期', '票据金额', '申请金额', '状态', '审批人', '审批日期', '审批意见'
        ])
        self.approval_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.approval_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.approval_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.approval_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.approval_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        tab_layout.addWidget(self.approval_table)
        
        self.tabs.addTab(tab, '📋 待审批清单')

    def _btn_style(self, color: str) -> str:
        return f'''
            QPushButton {{
                background-color: {color};
                color: white;
                border: none;
                border-radius: 6px;
                padding: 0 18px;
                font-size: 13px;
                font-weight: bold;
            }}
            QPushButton:hover {{ opacity: 0.9; }}
            QPushButton:pressed {{ opacity: 0.8; }}
        '''

    def refresh(self):
        self._refresh_duplicate()
        self._refresh_missing()
        self._refresh_unmatched()
        self._refresh_approval()
        
        dup_invoices = InvoiceService.get_all()
        dup_count = sum(1 for inv in dup_invoices if inv.is_duplicate)
        missing_count = sum(1 for inv in dup_invoices if not inv.has_attachment)
        unmatched_payments = PaymentService.get_all(matched_status='unmatched')
        pending_approvals = ApprovalService.get_all(status='pending')
        
        self.lbl_dup_count.setText(f'🔁 重复票据: {dup_count}')
        self.lbl_missing_count.setText(f'📎 缺少附件: {missing_count}')
        self.lbl_unmatched_count.setText(f'🔗 未匹配流水: {len(unmatched_payments)}')
        self.lbl_pending_count.setText(f'📋 待审批: {len(pending_approvals)}')

    def _on_tab_changed(self, index):
        self.refresh()

    def _refresh_duplicate(self):
        invoices = InvoiceService.get_all()
        dup_list = [inv for inv in invoices if inv.is_duplicate]
        
        self.dup_table.setRowCount(len(dup_list))
        for row, inv in enumerate(dup_list):
            self.dup_table.setItem(row, 0, QTableWidgetItem(str(inv.id)))
            self.dup_table.setItem(row, 1, QTableWidgetItem(inv.file_name))
            self.dup_table.setItem(row, 2, QTableWidgetItem(inv.invoice_no))
            self.dup_table.setItem(row, 3, QTableWidgetItem(inv.invoice_date))
            self.dup_table.setItem(row, 4, QTableWidgetItem(inv.supplier))
            self.dup_table.setItem(row, 5, QTableWidgetItem(f'{inv.total_amount:.2f}'))
            self.dup_table.setItem(row, 6, QTableWidgetItem(inv.category))
            self.dup_table.setItem(row, 7, QTableWidgetItem('是' if inv.is_duplicate else '否'))
            self.dup_table.setItem(row, 8, QTableWidgetItem(inv.remark))
            for col in range(9):
                item = self.dup_table.item(row, col)
                if item:
                    item.setBackground(Qt.GlobalColor.yellow)

    def _refresh_missing(self):
        invoices = InvoiceService.get_all()
        missing_list = [inv for inv in invoices if not inv.has_attachment]
        
        self.missing_table.setRowCount(len(missing_list))
        for row, inv in enumerate(missing_list):
            self.missing_table.setItem(row, 0, QTableWidgetItem(str(inv.id)))
            self.missing_table.setItem(row, 1, QTableWidgetItem(inv.file_name))
            self.missing_table.setItem(row, 2, QTableWidgetItem(inv.invoice_no))
            self.missing_table.setItem(row, 3, QTableWidgetItem(inv.invoice_date))
            self.missing_table.setItem(row, 4, QTableWidgetItem(inv.supplier))
            self.missing_table.setItem(row, 5, QTableWidgetItem(f'{inv.total_amount:.2f}'))
            self.missing_table.setItem(row, 6, QTableWidgetItem(inv.category))
            self.missing_table.setItem(row, 7, QTableWidgetItem('否' if not inv.has_attachment else '是'))
            self.missing_table.setItem(row, 8, QTableWidgetItem(inv.remark))
            for col in range(9):
                item = self.missing_table.item(row, col)
                if item:
                    item.setBackground(Qt.GlobalColor.red)

    def _refresh_unmatched(self):
        payments = PaymentService.get_all(matched_status='unmatched')
        
        self.unmatched_table.setRowCount(len(payments))
        for row, pay in enumerate(payments):
            self.unmatched_table.setItem(row, 0, QTableWidgetItem(str(pay.id)))
            self.unmatched_table.setItem(row, 1, QTableWidgetItem(pay.payment_no))
            self.unmatched_table.setItem(row, 2, QTableWidgetItem(pay.pay_date))
            self.unmatched_table.setItem(row, 3, QTableWidgetItem(f'{pay.pay_amount:.2f}'))
            self.unmatched_table.setItem(row, 4, QTableWidgetItem(pay.payee))
            self.unmatched_table.setItem(row, 5, QTableWidgetItem(pay.purpose))
            self.unmatched_table.setItem(row, 6, QTableWidgetItem(MATCH_STATUS_MAP.get(pay.matched_status, pay.matched_status)))

    def _refresh_approval(self):
        status = self.approval_filter.currentData() or ''
        approvals = ApprovalService.get_all(status=status)
        
        self.approval_table.setRowCount(len(approvals))
        for row, app in enumerate(approvals):
            self.approval_table.setItem(row, 0, QTableWidgetItem(str(app.id)))
            
            inv_file_name = '-'
            inv_total = 0.0
            if app.invoice_id:
                inv = InvoiceService.get_by_id(app.invoice_id)
                if inv:
                    inv_file_name = inv.file_name
                    inv_total = inv.total_amount
            self.approval_table.setItem(row, 1, QTableWidgetItem(inv_file_name))
            self.approval_table.setItem(row, 2, QTableWidgetItem(app.applicant))
            self.approval_table.setItem(row, 3, QTableWidgetItem(app.apply_date))
            self.approval_table.setItem(row, 4, QTableWidgetItem(f'{inv_total:.2f}'))
            self.approval_table.setItem(row, 5, QTableWidgetItem(f'{app.amount:.2f}'))
            
            status_text = {'pending': '待审批', 'approved': '已通过', 'rejected': '已驳回'}.get(app.status, app.status)
            status_item = QTableWidgetItem(status_text)
            if app.status == 'pending':
                status_item.setBackground(Qt.GlobalColor.yellow)
            elif app.status == 'approved':
                status_item.setBackground(Qt.GlobalColor.green)
            elif app.status == 'rejected':
                status_item.setBackground(Qt.GlobalColor.red)
            self.approval_table.setItem(row, 6, status_item)
            
            self.approval_table.setItem(row, 7, QTableWidgetItem(app.approver))
            self.approval_table.setItem(row, 8, QTableWidgetItem(app.approval_date))
            self.approval_table.setItem(row, 9, QTableWidgetItem(app.approval_opinion))

    def _detect_duplicates(self):
        duplicates = InvoiceService.detect_duplicates()
        count = sum(1 + len(dup_list) for _, dup_list in duplicates)
        self.refresh()
        if count > 0:
            QMessageBox.information(self, '检测完成', f'共检测到 {count} 张可能重复的票据（已重新按当前数据计算）。\n已不重复的记录已从清单中移除，请人工核实确认。')
        else:
            QMessageBox.information(self, '检测完成', '未检测到重复票据。所有记录均无重复。')

    def _get_selected_ids(self, table: QTableWidget, id_col: int = 0):
        ids = []
        items = table.selectedItems()
        if not items:
            return ids
        rows = set(item.row() for item in items)
        for row in rows:
            item = table.item(row, id_col)
            if item:
                ids.append(int(item.text()))
        return ids

    def _mark_dup(self, is_dup: bool):
        ids = self._get_selected_ids(self.dup_table)
        if not ids:
            QMessageBox.warning(self, '提示', '请先选择要处理的票据。')
            return
        for inv_id in ids:
            InvoiceService.update(inv_id, {'is_duplicate': int(is_dup)})
        self.refresh()
        QMessageBox.information(self, '成功', f'已{"标记" if is_dup else "取消标记"} {len(ids)} 张票据。')

    def _toggle_attach(self, has_attach: bool):
        ids = self._get_selected_ids(self.missing_table)
        if not ids:
            QMessageBox.warning(self, '提示', '请先选择要处理的票据。')
            return
        for inv_id in ids:
            InvoiceService.update(inv_id, {'has_attachment': int(has_attach)})
        self.refresh()
        QMessageBox.information(self, '成功', f'已更新 {len(ids)} 张票据的附件状态。')

    def _approve_reject(self, action: str):
        ids = self._get_selected_ids(self.approval_table)
        if not ids:
            QMessageBox.warning(self, '提示', '请先选择要审批的记录。')
            return
        
        if action == 'reject':
            opinion, ok = QInputDialog.getText(self, '驳回原因', '请输入驳回意见:')
            if not ok:
                return
        else:
            opinion, ok = QInputDialog.getText(self, '审批意见', '请输入审批意见（可选）:')
            opinion = opinion if ok else ''
        
        approver = 'admin'
        count = 0
        for app_id in ids:
            if action == 'approve':
                if ApprovalService.approve(app_id, approver, opinion):
                    count += 1
            else:
                if ApprovalService.reject(app_id, approver, opinion):
                    count += 1
        
        self.refresh()
        action_text = '通过' if action == 'approve' else '驳回'
        QMessageBox.information(self, '完成', f'已{action_text} {count} 条审批记录。')
