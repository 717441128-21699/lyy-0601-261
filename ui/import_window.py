import os
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QFileDialog,
    QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox, QProgressBar,
    QGroupBox, QListWidget, QListWidgetItem, QAbstractItemView, QSplitter
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap

from core.services import FileImportService, InvoiceService, PaymentService
from core.models import Invoice, Payment


class ImportWindow(QWidget):
    def __init__(self):
        super().__init__()
        self._pending_invoices = []
        self._pending_payments = []
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        title = QLabel('文件导入')
        title.setStyleSheet('font-size: 20px; font-weight: bold; color: #2c3e50;')
        layout.addWidget(title)
        
        btn_layout = QHBoxLayout()
        
        self.btn_import_images = QPushButton('📷 批量导入图片')
        self.btn_import_images.setStyleSheet(self._btn_style('#4a90d9'))
        self.btn_import_images.setFixedHeight(40)
        self.btn_import_images.clicked.connect(self._import_images)
        btn_layout.addWidget(self.btn_import_images)
        
        self.btn_import_excel = QPushButton('📊 导入Excel表格')
        self.btn_import_excel.setStyleSheet(self._btn_style('#27ae60'))
        self.btn_import_excel.setFixedHeight(40)
        self.btn_import_excel.clicked.connect(self._import_excel)
        btn_layout.addWidget(self.btn_import_excel)
        
        self.btn_import_csv = QPushButton('📄 导入CSV文件')
        self.btn_import_csv.setStyleSheet(self._btn_style('#8e44ad'))
        self.btn_import_csv.setFixedHeight(40)
        self.btn_import_csv.clicked.connect(self._import_csv)
        btn_layout.addWidget(self.btn_import_csv)
        
        btn_layout.addStretch()
        
        self.btn_confirm = QPushButton('✅ 确认导入数据库')
        self.btn_confirm.setStyleSheet(self._btn_style('#e67e22'))
        self.btn_confirm.setFixedHeight(40)
        self.btn_confirm.clicked.connect(self._confirm_import)
        btn_layout.addWidget(self.btn_confirm)
        
        self.btn_clear = QPushButton('🗑️ 清空列表')
        self.btn_clear.setStyleSheet(self._btn_style('#95a5a6'))
        self.btn_clear.setFixedHeight(40)
        self.btn_clear.clicked.connect(self._clear_list)
        btn_layout.addWidget(self.btn_clear)
        
        layout.addLayout(btn_layout)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        splitter = QSplitter(Qt.Orientation.Vertical)
        
        invoice_group = QGroupBox(f'待导入票据 ({0})')
        invoice_group.setObjectName('invoiceGroup')
        invoice_layout = QVBoxLayout(invoice_group)
        
        self.invoice_table = QTableWidget(0, 8)
        self.invoice_table.setHorizontalHeaderLabels([
            '文件名', '发票号', '开票日期', '供应商', '金额', '税额', '价税合计', '备注'
        ])
        self.invoice_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.invoice_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.invoice_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        invoice_layout.addWidget(self.invoice_table)
        
        splitter.addWidget(invoice_group)
        
        payment_group = QGroupBox(f'待导入付款流水 ({0})')
        payment_group.setObjectName('paymentGroup')
        payment_layout = QVBoxLayout(payment_group)
        
        self.payment_table = QTableWidget(0, 6)
        self.payment_table.setHorizontalHeaderLabels([
            '流水号', '付款日期', '付款金额', '收款方', '开户行', '用途'
        ])
        self.payment_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.payment_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.payment_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        payment_layout.addWidget(self.payment_table)
        
        splitter.addWidget(payment_group)
        splitter.setSizes([300, 300])
        
        layout.addWidget(splitter, 1)

    def _btn_style(self, color: str) -> str:
        return f'''
            QPushButton {{
                background-color: {color};
                color: white;
                border: none;
                border-radius: 6px;
                padding: 0 20px;
                font-size: 13px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {color};
                opacity: 0.9;
            }}
            QPushButton:pressed {{
                background-color: {color};
                opacity: 0.8;
            }}
        '''

    def _import_images(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, '选择图片文件', '',
            '图片文件 (*.jpg *.jpeg *.png *.bmp *.gif *.tiff);;所有文件 (*.*)'
        )
        if files:
            invoices = FileImportService.import_images(files)
            self._pending_invoices.extend(invoices)
            self._refresh_invoice_table()
            QMessageBox.information(self, '成功', f'已导入 {len(invoices)} 张图片，可在列表中预览并核对。')

    def _import_excel(self):
        file, _ = QFileDialog.getOpenFileName(
            self, '选择Excel文件', '',
            'Excel文件 (*.xlsx *.xls);;所有文件 (*.*)'
        )
        if file:
            invoices, payments = FileImportService.import_excel(file)
            self._pending_invoices.extend(invoices)
            self._pending_payments.extend(payments)
            self._refresh_invoice_table()
            self._refresh_payment_table()
            QMessageBox.information(self, '成功', 
                f'已读取Excel文件：\n- 票据: {len(invoices)} 条\n- 付款流水: {len(payments)} 条')

    def _import_csv(self):
        file, _ = QFileDialog.getOpenFileName(
            self, '选择CSV文件', '',
            'CSV文件 (*.csv);;所有文件 (*.*)'
        )
        if file:
            invoices, payments = FileImportService.import_csv(file)
            self._pending_invoices.extend(invoices)
            self._pending_payments.extend(payments)
            self._refresh_invoice_table()
            self._refresh_payment_table()
            QMessageBox.information(self, '成功', 
                f'已读取CSV文件：\n- 票据: {len(invoices)} 条\n- 付款流水: {len(payments)} 条')

    def _refresh_invoice_table(self):
        self.invoice_table.setRowCount(len(self._pending_invoices))
        for row, inv in enumerate(self._pending_invoices):
            self.invoice_table.setItem(row, 0, QTableWidgetItem(inv.file_name))
            self.invoice_table.setItem(row, 1, QTableWidgetItem(inv.invoice_no))
            self.invoice_table.setItem(row, 2, QTableWidgetItem(inv.invoice_date))
            self.invoice_table.setItem(row, 3, QTableWidgetItem(inv.supplier))
            self.invoice_table.setItem(row, 4, QTableWidgetItem(f'{inv.amount:.2f}'))
            self.invoice_table.setItem(row, 5, QTableWidgetItem(f'{inv.tax_amount:.2f}'))
            self.invoice_table.setItem(row, 6, QTableWidgetItem(f'{inv.total_amount:.2f}'))
            self.invoice_table.setItem(row, 7, QTableWidgetItem(inv.remark))
        
        self.findChild(QGroupBox, 'invoiceGroup').setTitle(f'待导入票据 ({len(self._pending_invoices)})')

    def _refresh_payment_table(self):
        self.payment_table.setRowCount(len(self._pending_payments))
        for row, pay in enumerate(self._pending_payments):
            self.payment_table.setItem(row, 0, QTableWidgetItem(pay.payment_no))
            self.payment_table.setItem(row, 1, QTableWidgetItem(pay.pay_date))
            self.payment_table.setItem(row, 2, QTableWidgetItem(f'{pay.pay_amount:.2f}'))
            self.payment_table.setItem(row, 3, QTableWidgetItem(pay.payee))
            self.payment_table.setItem(row, 4, QTableWidgetItem(pay.bank_name))
            self.payment_table.setItem(row, 5, QTableWidgetItem(pay.purpose))
        
        self.findChild(QGroupBox, 'paymentGroup').setTitle(f'待导入付款流水 ({len(self._pending_payments)})')

    def _confirm_import(self):
        if not self._pending_invoices and not self._pending_payments:
            QMessageBox.warning(self, '提示', '没有可导入的数据，请先选择文件。')
            return
        
        reply = QMessageBox.question(self, '确认导入',
            f'确认导入以下数据到数据库？\n- 票据: {len(self._pending_invoices)} 条\n- 付款流水: {len(self._pending_payments)} 条',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        
        if reply == QMessageBox.StandardButton.Yes:
            self.progress_bar.setVisible(True)
            self.progress_bar.setMaximum(len(self._pending_invoices) + len(self._pending_payments))
            self.progress_bar.setValue(0)
            
            try:
                inv_count = 0
                if self._pending_invoices:
                    InvoiceService.batch_create(self._pending_invoices)
                    inv_count = len(self._pending_invoices)
                    self.progress_bar.setValue(inv_count)
                
                pay_count = 0
                if self._pending_payments:
                    PaymentService.batch_create(self._pending_payments)
                    pay_count = len(self._pending_payments)
                    self.progress_bar.setValue(inv_count + pay_count)
                
                self._pending_invoices.clear()
                self._pending_payments.clear()
                self._refresh_invoice_table()
                self._refresh_payment_table()
                
                self.progress_bar.setVisible(False)
                QMessageBox.information(self, '导入完成',
                    f'成功导入：\n- 票据: {inv_count} 条\n- 付款流水: {pay_count} 条\n请前往"票据识别核对"继续处理。')
            except Exception as e:
                self.progress_bar.setVisible(False)
                QMessageBox.critical(self, '导入失败', f'导入过程中出现错误，数据已回滚，未写入数据库：\n{str(e)}')

    def _clear_list(self):
        if self._pending_invoices or self._pending_payments:
            reply = QMessageBox.question(self, '确认清空',
                '确认清空待导入列表？',
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if reply != QMessageBox.StandardButton.Yes:
                return
        
        self._pending_invoices.clear()
        self._pending_payments.clear()
        self._refresh_invoice_table()
        self._refresh_payment_table()

    def refresh(self):
        pass
