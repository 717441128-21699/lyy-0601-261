import os
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QTableWidget,
    QTableWidgetItem, QHeaderView, QLineEdit, QComboBox, QDateEdit,
    QDoubleSpinBox, QTextEdit, QFormLayout, QGroupBox, QSplitter,
    QMessageBox, QFileDialog, QAbstractItemView, QCheckBox
)
from PyQt6.QtCore import Qt, QDate
from PyQt6.QtGui import QPixmap

from core.services import InvoiceService, CategoryService, DepartmentService, ProjectService
from core.models import Invoice, STATUS_MAP


class InvoiceWindow(QWidget):
    def __init__(self):
        super().__init__()
        self._current_invoice_id = None
        self._init_ui()
        self.refresh()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        title = QLabel('票据识别核对')
        title.setStyleSheet('font-size: 20px; font-weight: bold; color: #2c3e50;')
        layout.addWidget(title)
        
        filter_layout = QHBoxLayout()
        
        filter_layout.addWidget(QLabel('关键字:'))
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText('搜索文件名/供应商/发票号/备注')
        self.search_input.setFixedWidth(250)
        self.search_input.textChanged.connect(lambda: self.refresh())
        filter_layout.addWidget(self.search_input)
        
        filter_layout.addWidget(QLabel('状态:'))
        self.status_combo = QComboBox()
        self.status_combo.addItem('全部', '')
        for k, v in STATUS_MAP.items():
            self.status_combo.addItem(v, k)
        self.status_combo.currentIndexChanged.connect(lambda: self.refresh())
        filter_layout.addWidget(self.status_combo)
        
        self.btn_search = QPushButton('🔍 搜索')
        self.btn_search.setStyleSheet(self._btn_style('#4a90d9'))
        self.btn_search.clicked.connect(self.refresh)
        filter_layout.addWidget(self.btn_search)
        
        self.btn_ocr = QPushButton('🤖 重新识别')
        self.btn_ocr.setStyleSheet(self._btn_style('#8e44ad'))
        self.btn_ocr.clicked.connect(self._re_ocr)
        filter_layout.addWidget(self.btn_ocr)
        
        filter_layout.addStretch()
        layout.addLayout(filter_layout)
        
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        
        self.table = QTableWidget(0, 10)
        self.table.setHorizontalHeaderLabels([
            'ID', '文件名', '发票号', '开票日期', '供应商', '价税合计', '类别', '部门', '状态', '是否重复'
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.itemSelectionChanged.connect(self._on_select_invoice)
        left_layout.addWidget(self.table, 1)
        
        splitter.addWidget(left_widget)
        
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        
        detail_group = QGroupBox('票据详情 (可编辑)')
        detail_form = QFormLayout(detail_group)
        
        self.preview_label = QLabel('图片预览')
        self.preview_label.setFixedHeight(180)
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_label.setStyleSheet('background-color: #f0f0f0; border: 1px dashed #ccc; border-radius: 4px;')
        detail_form.addRow(self.preview_label)
        
        self.file_name_edit = QLineEdit()
        self.file_name_edit.setReadOnly(True)
        detail_form.addRow('文件名:', self.file_name_edit)
        
        self.invoice_no_edit = QLineEdit()
        detail_form.addRow('发票号:', self.invoice_no_edit)
        
        self.invoice_code_edit = QLineEdit()
        detail_form.addRow('发票代码:', self.invoice_code_edit)
        
        self.invoice_date_edit = QDateEdit()
        self.invoice_date_edit.setCalendarPopup(True)
        self.invoice_date_edit.setDisplayFormat('yyyy-MM-dd')
        self.invoice_date_edit.setDate(QDate.currentDate())
        detail_form.addRow('开票日期:', self.invoice_date_edit)
        
        self.amount_edit = QDoubleSpinBox()
        self.amount_edit.setRange(0, 9999999)
        self.amount_edit.setDecimals(2)
        self.amount_edit.setPrefix('¥ ')
        detail_form.addRow('金额(不含税):', self.amount_edit)
        
        self.tax_amount_edit = QDoubleSpinBox()
        self.tax_amount_edit.setRange(0, 9999999)
        self.tax_amount_edit.setDecimals(2)
        self.tax_amount_edit.setPrefix('¥ ')
        detail_form.addRow('税额:', self.tax_amount_edit)
        
        self.total_amount_edit = QDoubleSpinBox()
        self.total_amount_edit.setRange(0, 9999999)
        self.total_amount_edit.setDecimals(2)
        self.total_amount_edit.setPrefix('¥ ')
        self.total_amount_edit.valueChanged.connect(self._on_total_changed)
        detail_form.addRow('价税合计:', self.total_amount_edit)
        
        self.supplier_edit = QLineEdit()
        detail_form.addRow('供应商(销售方):', self.supplier_edit)
        
        self.buyer_edit = QLineEdit()
        detail_form.addRow('购买方:', self.buyer_edit)
        
        self.category_combo = QComboBox()
        detail_form.addRow('费用类别:', self.category_combo)
        
        self.department_combo = QComboBox()
        detail_form.addRow('所属部门:', self.department_combo)
        
        self.project_combo = QComboBox()
        detail_form.addRow('所属项目:', self.project_combo)
        
        self.reimbursable_edit = QDoubleSpinBox()
        self.reimbursable_edit.setRange(0, 9999999)
        self.reimbursable_edit.setDecimals(2)
        self.reimbursable_edit.setPrefix('¥ ')
        detail_form.addRow('可报销金额:', self.reimbursable_edit)
        
        self.status_combo_edit = QComboBox()
        for k, v in STATUS_MAP.items():
            self.status_combo_edit.addItem(v, k)
        detail_form.addRow('状态:', self.status_combo_edit)
        
        self.dup_checkbox = QCheckBox('标记为重复票据')
        detail_form.addRow(self.dup_checkbox)
        
        self.attach_checkbox = QCheckBox('有附件')
        self.attach_checkbox.setChecked(True)
        detail_form.addRow(self.attach_checkbox)
        
        self.remark_edit = QLineEdit()
        detail_form.addRow('备注:', self.remark_edit)
        
        self.opinion_edit = QTextEdit()
        self.opinion_edit.setFixedHeight(60)
        detail_form.addRow('处理意见:', self.opinion_edit)
        
        self.ocr_result_edit = QTextEdit()
        self.ocr_result_edit.setReadOnly(True)
        self.ocr_result_edit.setFixedHeight(80)
        detail_form.addRow('OCR识别结果:', self.ocr_result_edit)
        
        right_layout.addWidget(detail_group)
        
        btn_layout = QHBoxLayout()
        self.btn_save = QPushButton('💾 保存修改')
        self.btn_save.setStyleSheet(self._btn_style('#27ae60'))
        self.btn_save.setFixedHeight(36)
        self.btn_save.clicked.connect(self._save_invoice)
        btn_layout.addWidget(self.btn_save)
        
        self.btn_delete = QPushButton('🗑️ 删除票据')
        self.btn_delete.setStyleSheet(self._btn_style('#e74c3c'))
        self.btn_delete.setFixedHeight(36)
        self.btn_delete.clicked.connect(self._delete_invoice)
        btn_layout.addWidget(self.btn_delete)
        
        right_layout.addLayout(btn_layout)
        
        splitter.addWidget(right_widget)
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
        
        invoices = InvoiceService.get_all(keyword=keyword, status=status)
        
        self.table.setRowCount(len(invoices))
        for row, inv in enumerate(invoices):
            self.table.setItem(row, 0, QTableWidgetItem(str(inv.id)))
            self.table.setItem(row, 1, QTableWidgetItem(inv.file_name))
            self.table.setItem(row, 2, QTableWidgetItem(inv.invoice_no))
            self.table.setItem(row, 3, QTableWidgetItem(inv.invoice_date))
            self.table.setItem(row, 4, QTableWidgetItem(inv.supplier))
            self.table.setItem(row, 5, QTableWidgetItem(f'{inv.total_amount:.2f}'))
            self.table.setItem(row, 6, QTableWidgetItem(inv.category))
            self.table.setItem(row, 7, QTableWidgetItem(inv.department))
            self.table.setItem(row, 8, QTableWidgetItem(STATUS_MAP.get(inv.status, inv.status)))
            self.table.setItem(row, 9, QTableWidgetItem('是' if inv.is_duplicate else '否'))
            if inv.is_duplicate:
                for col in range(10):
                    item = self.table.item(row, col)
                    if item:
                        item.setBackground(Qt.GlobalColor.lightGray)
        
        self._load_combos()

    def _load_combos(self):
        cur_cat = self.category_combo.currentText()
        self.category_combo.clear()
        self.category_combo.addItem('')
        self.category_combo.addItems(CategoryService.get_names())
        idx = self.category_combo.findText(cur_cat)
        if idx >= 0:
            self.category_combo.setCurrentIndex(idx)
        
        cur_dept = self.department_combo.currentText()
        self.department_combo.clear()
        self.department_combo.addItem('')
        self.department_combo.addItems(DepartmentService.get_names())
        idx = self.department_combo.findText(cur_dept)
        if idx >= 0:
            self.department_combo.setCurrentIndex(idx)
        
        cur_proj = self.project_combo.currentText()
        self.project_combo.clear()
        self.project_combo.addItem('')
        self.project_combo.addItems(ProjectService.get_names())
        idx = self.project_combo.findText(cur_proj)
        if idx >= 0:
            self.project_combo.setCurrentIndex(idx)

    def _on_select_invoice(self):
        items = self.table.selectedItems()
        if not items:
            return
        
        row = items[0].row()
        inv_id = int(self.table.item(row, 0).text())
        inv = InvoiceService.get_by_id(inv_id)
        if not inv:
            return
        
        self._current_invoice_id = inv_id
        self.file_name_edit.setText(inv.file_name)
        self.invoice_no_edit.setText(inv.invoice_no)
        self.invoice_code_edit.setText(inv.invoice_code)
        
        if inv.invoice_date:
            parts = inv.invoice_date.split('-')
            if len(parts) == 3:
                try:
                    self.invoice_date_edit.setDate(QDate(int(parts[0]), int(parts[1]), int(parts[2])))
                except ValueError:
                    pass
        
        self.amount_edit.setValue(inv.amount)
        self.tax_amount_edit.setValue(inv.tax_amount)
        self.total_amount_edit.setValue(inv.total_amount)
        self.supplier_edit.setText(inv.supplier)
        self.buyer_edit.setText(inv.buyer)
        
        idx = self.category_combo.findText(inv.category)
        self.category_combo.setCurrentIndex(idx if idx >= 0 else 0)
        
        idx = self.department_combo.findText(inv.department)
        self.department_combo.setCurrentIndex(idx if idx >= 0 else 0)
        
        idx = self.project_combo.findText(inv.project)
        self.project_combo.setCurrentIndex(idx if idx >= 0 else 0)
        
        self.reimbursable_edit.setValue(inv.reimbursable_amount)
        
        idx = self.status_combo_edit.findData(inv.status)
        self.status_combo_edit.setCurrentIndex(idx if idx >= 0 else 0)
        
        self.dup_checkbox.setChecked(inv.is_duplicate)
        self.attach_checkbox.setChecked(inv.has_attachment)
        self.remark_edit.setText(inv.remark)
        self.opinion_edit.setPlainText(inv.opinion)
        self.ocr_result_edit.setPlainText(inv.ocr_result)
        
        if inv.file_path and os.path.exists(inv.file_path):
            pixmap = QPixmap(inv.file_path)
            if not pixmap.isNull():
                pixmap = pixmap.scaled(300, 180, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                self.preview_label.setPixmap(pixmap)
            else:
                self.preview_label.setText('无法预览图片')
        else:
            self.preview_label.setText('图片预览\n(文件不存在)')

    def _on_total_changed(self):
        if self.reimbursable_edit.value() == 0:
            self.reimbursable_edit.setValue(self.total_amount_edit.value())

    def _re_ocr(self):
        if not self._current_invoice_id:
            QMessageBox.warning(self, '提示', '请先选择一张票据。')
            return
        QMessageBox.information(self, '提示', 'OCR重新识别功能（模拟）：已触发识别流程。\n实际使用时可接入PaddleOCR或其他OCR引擎。')

    def _save_invoice(self):
        if not self._current_invoice_id:
            QMessageBox.warning(self, '提示', '请先选择一张票据。')
            return
        
        data = {
            'invoice_no': self.invoice_no_edit.text().strip(),
            'invoice_code': self.invoice_code_edit.text().strip(),
            'invoice_date': self.invoice_date_edit.date().toString('yyyy-MM-dd'),
            'amount': self.amount_edit.value(),
            'tax_amount': self.tax_amount_edit.value(),
            'total_amount': self.total_amount_edit.value(),
            'supplier': self.supplier_edit.text().strip(),
            'buyer': self.buyer_edit.text().strip(),
            'category': self.category_combo.currentText(),
            'department': self.department_combo.currentText(),
            'project': self.project_combo.currentText(),
            'reimbursable_amount': self.reimbursable_edit.value(),
            'status': self.status_combo_edit.currentData(),
            'is_duplicate': int(self.dup_checkbox.isChecked()),
            'has_attachment': int(self.attach_checkbox.isChecked()),
            'remark': self.remark_edit.text().strip(),
            'opinion': self.opinion_edit.toPlainText().strip()
        }
        
        if InvoiceService.update(self._current_invoice_id, data):
            QMessageBox.information(self, '成功', '票据信息已保存。')
            self.refresh()
        else:
            QMessageBox.warning(self, '失败', '保存失败，请重试。')

    def _delete_invoice(self):
        if not self._current_invoice_id:
            QMessageBox.warning(self, '提示', '请先选择一张票据。')
            return
        
        reply = QMessageBox.question(self, '确认删除',
            '确定要删除这张票据吗？此操作不可恢复。',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        
        if reply == QMessageBox.StandardButton.Yes:
            if InvoiceService.delete(self._current_invoice_id):
                self._current_invoice_id = None
                self.refresh()
                QMessageBox.information(self, '成功', '票据已删除。')
