from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QTableWidget,
    QTableWidgetItem, QHeaderView, QLineEdit, QComboBox, QSplitter,
    QMessageBox, QAbstractItemView, QGroupBox, QFormLayout
)
from PyQt6.QtCore import Qt

from core.services import PaymentService, InvoiceService
from core.models import Payment, Invoice, MATCH_STATUS_MAP, STATUS_MAP


class PaymentMatchWindow(QWidget):
    def __init__(self):
        super().__init__()
        self._current_payment_id = None
        self._init_ui()
        self.refresh()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        title = QLabel('流水匹配')
        title.setStyleSheet('font-size: 20px; font-weight: bold; color: #2c3e50;')
        layout.addWidget(title)
        
        filter_layout = QHBoxLayout()
        
        filter_layout.addWidget(QLabel('关键字:'))
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText('搜索流水号/收款方/用途')
        self.search_input.setFixedWidth(250)
        self.search_input.textChanged.connect(lambda: self.refresh())
        filter_layout.addWidget(self.search_input)
        
        filter_layout.addWidget(QLabel('匹配状态:'))
        self.status_combo = QComboBox()
        self.status_combo.addItem('全部', '')
        for k, v in MATCH_STATUS_MAP.items():
            self.status_combo.addItem(v, k)
        self.status_combo.currentIndexChanged.connect(lambda: self.refresh())
        filter_layout.addWidget(self.status_combo)
        
        filter_layout.addWidget(QLabel('供应商筛选:'))
        self.supplier_combo = QComboBox()
        self.supplier_combo.currentIndexChanged.connect(lambda: self.refresh())
        filter_layout.addWidget(self.supplier_combo)
        
        filter_layout.addStretch()
        
        self.btn_auto_match = QPushButton('🤖 一键自动匹配')
        self.btn_auto_match.setStyleSheet(self._btn_style('#e67e22'))
        self.btn_auto_match.setFixedHeight(36)
        self.btn_auto_match.clicked.connect(self._auto_match)
        filter_layout.addWidget(self.btn_auto_match)
        
        layout.addLayout(filter_layout)
        
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        left_group = QGroupBox('付款流水列表')
        left_layout = QVBoxLayout(left_group)
        
        self.payment_table = QTableWidget(0, 9)
        self.payment_table.setHorizontalHeaderLabels([
            'ID', '流水号', '付款日期', '付款金额', '收款方', '开户行', '用途', '关联票据ID', '匹配状态'
        ])
        self.payment_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.payment_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.payment_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.payment_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.payment_table.itemSelectionChanged.connect(self._on_select_payment)
        left_layout.addWidget(self.payment_table)
        
        splitter.addWidget(left_group)
        
        right_group = QGroupBox('可匹配的票据')
        right_layout = QVBoxLayout(right_group)
        
        info_label = QLabel('选择左侧流水后，从下方选择对应票据进行匹配：')
        right_layout.addWidget(info_label)
        
        self.invoice_table = QTableWidget(0, 8)
        self.invoice_table.setHorizontalHeaderLabels([
            'ID', '文件名', '供应商', '开票日期', '价税合计', '类别', '部门', '状态'
        ])
        self.invoice_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.invoice_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.invoice_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.invoice_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        right_layout.addWidget(self.invoice_table, 1)
        
        btn_row = QHBoxLayout()
        self.btn_match = QPushButton('🔗 手动匹配')
        self.btn_match.setStyleSheet(self._btn_style('#27ae60'))
        self.btn_match.setFixedHeight(36)
        self.btn_match.clicked.connect(self._manual_match)
        btn_row.addWidget(self.btn_match)
        
        self.btn_unmatch = QPushButton('✂️ 解除匹配')
        self.btn_unmatch.setStyleSheet(self._btn_style('#e74c3c'))
        self.btn_unmatch.setFixedHeight(36)
        self.btn_unmatch.clicked.connect(self._unmatch)
        btn_row.addWidget(self.btn_unmatch)
        
        right_layout.addLayout(btn_row)
        
        matched_info = QGroupBox('当前流水匹配信息')
        matched_form = QFormLayout(matched_info)
        self.lbl_payment_no = QLabel('-')
        self.lbl_pay_amount = QLabel('-')
        self.lbl_payee = QLabel('-')
        self.lbl_invoice_id = QLabel('-')
        self.lbl_invoice_amount = QLabel('-')
        self.lbl_match_status = QLabel('-')
        matched_form.addRow('流水号:', self.lbl_payment_no)
        matched_form.addRow('付款金额:', self.lbl_pay_amount)
        matched_form.addRow('收款方:', self.lbl_payee)
        matched_form.addRow('匹配票据ID:', self.lbl_invoice_id)
        matched_form.addRow('票据金额:', self.lbl_invoice_amount)
        matched_form.addRow('匹配状态:', self.lbl_match_status)
        right_layout.addWidget(matched_info)
        
        splitter.addWidget(right_group)
        splitter.setSizes([700, 500])
        
        layout.addWidget(splitter, 1)

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
        keyword = self.search_input.text().strip()
        status = self.status_combo.currentData() or ''
        supplier = self.supplier_combo.currentText()
        
        cur_supplier = self.supplier_combo.currentText()
        self.supplier_combo.blockSignals(True)
        self.supplier_combo.clear()
        self.supplier_combo.addItem('全部供应商')
        for s in PaymentService.get_unmatched_suppliers():
            self.supplier_combo.addItem(s)
        idx = self.supplier_combo.findText(cur_supplier)
        self.supplier_combo.setCurrentIndex(idx if idx >= 0 else 0)
        self.supplier_combo.blockSignals(False)
        
        payments = PaymentService.get_all(keyword=keyword, matched_status=status)
        if supplier and supplier != '全部供应商':
            payments = [p for p in payments if supplier in (p.payee or '')]
        
        self.payment_table.setRowCount(len(payments))
        for row, pay in enumerate(payments):
            self.payment_table.setItem(row, 0, QTableWidgetItem(str(pay.id)))
            self.payment_table.setItem(row, 1, QTableWidgetItem(pay.payment_no))
            self.payment_table.setItem(row, 2, QTableWidgetItem(pay.pay_date))
            self.payment_table.setItem(row, 3, QTableWidgetItem(f'{pay.pay_amount:.2f}'))
            self.payment_table.setItem(row, 4, QTableWidgetItem(pay.payee))
            self.payment_table.setItem(row, 5, QTableWidgetItem(pay.bank_name))
            self.payment_table.setItem(row, 6, QTableWidgetItem(pay.purpose))
            self.payment_table.setItem(row, 7, QTableWidgetItem(str(pay.invoice_id) if pay.invoice_id else '-'))
            self.payment_table.setItem(row, 8, QTableWidgetItem(MATCH_STATUS_MAP.get(pay.matched_status, pay.matched_status)))
            
            if pay.matched_status == 'matched':
                for col in range(9):
                    item = self.payment_table.item(row, col)
                    if item:
                        item.setBackground(Qt.GlobalColor.lightGreen)
            elif pay.matched_status == 'conflict':
                for col in range(9):
                    item = self.payment_table.item(row, col)
                    if item:
                        item.setBackground(Qt.GlobalColor.yellow)
        
        self._load_invoice_table()

    def _load_invoice_table(self, payee_hint: str = ''):
        invoices = InvoiceService.get_all()
        matched_ids = set()
        payments = PaymentService.get_all()
        for p in payments:
            if p.invoice_id:
                matched_ids.add(p.invoice_id)
        
        unmatched = [inv for inv in invoices if inv.id not in matched_ids]
        if payee_hint:
            unmatched.sort(key=lambda inv: 0 if payee_hint in (inv.supplier or '') else 1)
        
        self.invoice_table.setRowCount(len(unmatched))
        for row, inv in enumerate(unmatched):
            self.invoice_table.setItem(row, 0, QTableWidgetItem(str(inv.id)))
            self.invoice_table.setItem(row, 1, QTableWidgetItem(inv.file_name))
            self.invoice_table.setItem(row, 2, QTableWidgetItem(inv.supplier))
            self.invoice_table.setItem(row, 3, QTableWidgetItem(inv.invoice_date))
            self.invoice_table.setItem(row, 4, QTableWidgetItem(f'{inv.total_amount:.2f}'))
            self.invoice_table.setItem(row, 5, QTableWidgetItem(inv.category))
            self.invoice_table.setItem(row, 6, QTableWidgetItem(inv.department))
            self.invoice_table.setItem(row, 7, QTableWidgetItem(STATUS_MAP.get(inv.status, inv.status)))

    def _on_select_payment(self):
        items = self.payment_table.selectedItems()
        if not items:
            return
        
        row = items[0].row()
        pay_id = int(self.payment_table.item(row, 0).text())
        pay = PaymentService.get_by_id(pay_id)
        if not pay:
            return
        
        self._current_payment_id = pay_id
        self.lbl_payment_no.setText(pay.payment_no or '-')
        self.lbl_pay_amount.setText(f'¥ {pay.pay_amount:.2f}')
        self.lbl_payee.setText(pay.payee or '-')
        self.lbl_invoice_id.setText(str(pay.invoice_id) if pay.invoice_id else '-')
        
        if pay.invoice_id:
            inv = InvoiceService.get_by_id(pay.invoice_id)
            if inv:
                self.lbl_invoice_amount.setText(f'¥ {inv.total_amount:.2f}')
            else:
                self.lbl_invoice_amount.setText('-')
        else:
            self.lbl_invoice_amount.setText('-')
        self.lbl_match_status.setText(MATCH_STATUS_MAP.get(pay.matched_status, pay.matched_status))
        
        self._load_invoice_table(pay.payee)

    def _auto_match(self):
        reply = QMessageBox.question(self, '确认',
            '将根据金额和收款方自动匹配流水与票据，是否继续？',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        result = PaymentService.auto_match()
        self.refresh()
        QMessageBox.information(self, '匹配完成',
            f'共处理 {result["total"]} 条未匹配流水，\n成功自动匹配 {result["matched"]} 条。')

    def _manual_match(self):
        if not self._current_payment_id:
            QMessageBox.warning(self, '提示', '请先选择一条付款流水。')
            return
        
        items = self.invoice_table.selectedItems()
        if not items:
            QMessageBox.warning(self, '提示', '请选择要匹配的票据。')
            return
        
        inv_row = items[0].row()
        inv_id = int(self.invoice_table.item(inv_row, 0).text())
        
        if PaymentService.match_payment_invoice(self._current_payment_id, inv_id):
            self.refresh()
            QMessageBox.information(self, '成功', '匹配成功！')
        else:
            QMessageBox.warning(self, '失败', '匹配失败，请重试。')

    def _unmatch(self):
        if not self._current_payment_id:
            QMessageBox.warning(self, '提示', '请先选择一条付款流水。')
            return
        
        pay = PaymentService.get_by_id(self._current_payment_id)
        if not pay or not pay.invoice_id:
            QMessageBox.warning(self, '提示', '该流水尚未匹配任何票据。')
            return
        
        reply = QMessageBox.question(self, '确认', '确定要解除该流水的匹配关系吗？',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        if PaymentService.update(self._current_payment_id, {
            'invoice_id': None,
            'matched_status': 'unmatched'
        }):
            self.refresh()
            QMessageBox.information(self, '成功', '已解除匹配。')
