from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QTableWidget,
    QTableWidgetItem, QHeaderView, QLineEdit, QComboBox, QTextEdit,
    QDoubleSpinBox, QFormLayout, QGroupBox, QMessageBox, QAbstractItemView,
    QSplitter, QInputDialog
)
from PyQt6.QtCore import Qt

from core.services import (
    InvoiceService, CategoryService, DepartmentService, ProjectService,
    RuleService, ApprovalService
)
from core.models import Invoice, STATUS_MAP


class CategoryWindow(QWidget):
    def __init__(self):
        super().__init__()
        self._current_invoice_ids = []
        self._init_ui()
        self.refresh()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        title = QLabel('报销归类')
        title.setStyleSheet('font-size: 20px; font-weight: bold; color: #2c3e50;')
        layout.addWidget(title)
        
        filter_layout = QHBoxLayout()
        
        filter_layout.addWidget(QLabel('关键字:'))
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText('搜索供应商/备注')
        self.search_input.setFixedWidth(250)
        self.search_input.textChanged.connect(lambda: self.refresh())
        filter_layout.addWidget(self.search_input)
        
        filter_layout.addWidget(QLabel('部门:'))
        self.dept_filter = QComboBox()
        self.dept_filter.currentIndexChanged.connect(lambda: self.refresh())
        filter_layout.addWidget(self.dept_filter)
        
        filter_layout.addWidget(QLabel('类别:'))
        self.cat_filter = QComboBox()
        self.cat_filter.currentIndexChanged.connect(lambda: self.refresh())
        filter_layout.addWidget(self.cat_filter)
        
        filter_layout.addStretch()
        layout.addLayout(filter_layout)
        
        splitter = QSplitter(Qt.Orientation.Vertical)
        
        table_group = QGroupBox('票据列表 (可多选进行批量归类)')
        table_layout = QVBoxLayout(table_group)
        
        self.table = QTableWidget(0, 11)
        self.table.setHorizontalHeaderLabels([
            '选择', 'ID', '文件名', '供应商', '开票日期', '价税合计',
            '可报销金额', '费用类别', '部门', '项目', '备注'
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.itemSelectionChanged.connect(self._on_selection_changed)
        table_layout.addWidget(self.table)
        
        select_bar = QHBoxLayout()
        self.btn_select_all = QPushButton('全选')
        self.btn_select_all.setStyleSheet(self._btn_style('#3498db'))
        self.btn_select_all.clicked.connect(self._select_all)
        select_bar.addWidget(self.btn_select_all)
        
        self.btn_select_none = QPushButton('取消全选')
        self.btn_select_none.setStyleSheet(self._btn_style('#95a5a6'))
        self.btn_select_none.clicked.connect(self._select_none)
        select_bar.addWidget(self.btn_select_none)
        
        self.selected_label = QLabel('已选择 0 项')
        self.selected_label.setStyleSheet('font-weight: bold; color: #e67e22; padding-left: 20px;')
        select_bar.addWidget(self.selected_label)
        select_bar.addStretch()
        table_layout.addLayout(select_bar)
        
        splitter.addWidget(table_group)
        
        classify_group = QGroupBox('批量归类设置')
        classify_layout = QVBoxLayout(classify_group)
        
        form_layout = QFormLayout()
        
        self.category_combo = QComboBox()
        form_layout.addRow('费用类别:', self.category_combo)
        
        self.department_combo = QComboBox()
        form_layout.addRow('所属部门:', self.department_combo)
        
        project_layout = QHBoxLayout()
        self.project_combo = QComboBox()
        project_layout.addWidget(self.project_combo, 1)
        self.btn_add_project = QPushButton('+ 新建项目')
        self.btn_add_project.setStyleSheet(self._btn_style('#3498db'))
        self.btn_add_project.clicked.connect(self._add_project)
        project_layout.addWidget(self.btn_add_project)
        form_layout.addRow('所属项目:', project_layout)
        
        rate_layout = QHBoxLayout()
        self.reimburse_rate = QDoubleSpinBox()
        self.reimburse_rate.setRange(0, 100)
        self.reimburse_rate.setSuffix(' %')
        self.reimburse_rate.setValue(100)
        self.reimburse_rate.setDecimals(1)
        rate_layout.addWidget(self.reimburse_rate)
        self.btn_calc_reimburse = QPushButton('按比例计算可报销金额')
        self.btn_calc_reimburse.setStyleSheet(self._btn_style('#8e44ad'))
        self.btn_calc_reimburse.clicked.connect(self._calc_reimbursable)
        rate_layout.addWidget(self.btn_calc_reimburse)
        form_layout.addRow('报销比例:', rate_layout)
        
        form_layout.addRow(QLabel(''))
        
        self.remark_edit = QLineEdit()
        form_layout.addRow('统一备注:', self.remark_edit)
        
        self.opinion_edit = QTextEdit()
        self.opinion_edit.setFixedHeight(60)
        form_layout.addRow('处理意见:', self.opinion_edit)
        
        classify_layout.addLayout(form_layout)
        
        btn_row = QHBoxLayout()
        self.btn_apply_category = QPushButton('🏷️ 应用类别/部门/项目')
        self.btn_apply_category.setStyleSheet(self._btn_style('#27ae60'))
        self.btn_apply_category.setFixedHeight(40)
        self.btn_apply_category.clicked.connect(self._apply_classification)
        btn_row.addWidget(self.btn_apply_category)
        
        self.btn_apply_rules = QPushButton('🤖 按规则自动归类')
        self.btn_apply_rules.setStyleSheet(self._btn_style('#e67e22'))
        self.btn_apply_rules.setFixedHeight(40)
        self.btn_apply_rules.clicked.connect(self._apply_auto_rules)
        btn_row.addWidget(self.btn_apply_rules)
        
        self.btn_submit_approval = QPushButton('📋 提交待审批')
        self.btn_submit_approval.setStyleSheet(self._btn_style('#4a90d9'))
        self.btn_submit_approval.setFixedHeight(40)
        self.btn_submit_approval.clicked.connect(self._submit_approval)
        btn_row.addWidget(self.btn_submit_approval)
        
        classify_layout.addLayout(btn_row)
        
        splitter.addWidget(classify_group)
        splitter.setSizes([400, 280])
        
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
        self._load_combos()
        
        keyword = self.search_input.text().strip()
        dept = self.dept_filter.currentData() or ''
        cat = self.cat_filter.currentData() or ''
        
        invoices = InvoiceService.get_all(keyword=keyword)
        if dept:
            invoices = [inv for inv in invoices if inv.department == dept]
        if cat:
            invoices = [inv for inv in invoices if inv.category == cat]
        
        self.table.setRowCount(len(invoices))
        for row, inv in enumerate(invoices):
            chk_item = QTableWidgetItem()
            chk_item.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
            chk_item.setCheckState(Qt.CheckState.Unchecked)
            self.table.setItem(row, 0, chk_item)
            
            self.table.setItem(row, 1, QTableWidgetItem(str(inv.id)))
            self.table.setItem(row, 2, QTableWidgetItem(inv.file_name))
            self.table.setItem(row, 3, QTableWidgetItem(inv.supplier))
            self.table.setItem(row, 4, QTableWidgetItem(inv.invoice_date))
            self.table.setItem(row, 5, QTableWidgetItem(f'{inv.total_amount:.2f}'))
            self.table.setItem(row, 6, QTableWidgetItem(f'{inv.reimbursable_amount:.2f}'))
            self.table.setItem(row, 7, QTableWidgetItem(inv.category))
            self.table.setItem(row, 8, QTableWidgetItem(inv.department))
            self.table.setItem(row, 9, QTableWidgetItem(inv.project))
            self.table.setItem(row, 10, QTableWidgetItem(inv.remark))

    def _load_combos(self):
        cur_dept = self.dept_filter.currentData()
        self.dept_filter.blockSignals(True)
        self.dept_filter.clear()
        self.dept_filter.addItem('全部部门', '')
        for name in DepartmentService.get_names():
            self.dept_filter.addItem(name, name)
        idx = self.dept_filter.findData(cur_dept)
        self.dept_filter.setCurrentIndex(idx if idx >= 0 else 0)
        self.dept_filter.blockSignals(False)
        
        cur_cat = self.cat_filter.currentData()
        self.cat_filter.blockSignals(True)
        self.cat_filter.clear()
        self.cat_filter.addItem('全部类别', '')
        for name in CategoryService.get_names():
            self.cat_filter.addItem(name, name)
        idx = self.cat_filter.findData(cur_cat)
        self.cat_filter.setCurrentIndex(idx if idx >= 0 else 0)
        self.cat_filter.blockSignals(False)
        
        self.category_combo.clear()
        self.category_combo.addItem('(不修改)')
        self.category_combo.addItems(CategoryService.get_names())
        
        self.department_combo.clear()
        self.department_combo.addItem('(不修改)')
        self.department_combo.addItems(DepartmentService.get_names())
        
        self.project_combo.clear()
        self.project_combo.addItem('(不修改)')
        self.project_combo.addItems(ProjectService.get_names())

    def _get_selected_ids(self):
        ids = []
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 0)
            if item and item.checkState() == Qt.CheckState.Checked:
                id_item = self.table.item(row, 1)
                if id_item:
                    ids.append(int(id_item.text()))
        self._current_invoice_ids = ids
        self.selected_label.setText(f'已选择 {len(ids)} 项')
        return ids

    def _on_selection_changed(self):
        pass

    def _select_all(self):
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 0)
            if item:
                item.setCheckState(Qt.CheckState.Checked)
        self._get_selected_ids()

    def _select_none(self):
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 0)
            if item:
                item.setCheckState(Qt.CheckState.Unchecked)
        self._get_selected_ids()

    def _select_project_by_name(self, name: str):
        for i in range(self.project_combo.count()):
            if self.project_combo.itemText(i) == name:
                self.project_combo.setCurrentIndex(i)
                return True
        return False

    def _add_project(self):
        name, ok = QInputDialog.getText(self, '新建项目', '请输入项目名称:')
        if not ok or not name.strip():
            return
        
        from core.models import Project
        proj_name = name.strip()
        existing = ProjectService.get_by_name(proj_name)
        if existing:
            self._load_combos()
            self._select_project_by_name(proj_name)
            QMessageBox.information(self, '提示', f'项目"{proj_name}"已存在，已直接选中。')
            return
        
        proj = Project(name=proj_name)
        new_id = ProjectService.create(proj)
        if new_id:
            self._load_combos()
            self._select_project_by_name(proj_name)
            QMessageBox.information(self, '成功', f'项目"{proj_name}"已创建并保存。')
        else:
            self._load_combos()
            self._select_project_by_name(proj_name)
            QMessageBox.information(self, '提示', f'项目"{proj_name}"已存在，已直接选中。')

    def _calc_reimbursable(self):
        ids = self._get_selected_ids()
        if not ids:
            QMessageBox.warning(self, '提示', '请先选择票据。')
            return
        rate = self.reimburse_rate.value() / 100
        count = 0
        for inv_id in ids:
            inv = InvoiceService.get_by_id(inv_id)
            if inv:
                new_val = round(inv.total_amount * rate, 2)
                InvoiceService.update(inv_id, {'reimbursable_amount': new_val})
                count += 1
        self.refresh()
        QMessageBox.information(self, '成功', f'已为 {count} 张票据按比例({rate*100:.1f}%)计算可报销金额。')

    def _apply_classification(self):
        ids = self._get_selected_ids()
        if not ids:
            QMessageBox.warning(self, '提示', '请先选择要归类的票据。')
            return
        
        data = {}
        if self.category_combo.currentIndex() > 0:
            data['category'] = self.category_combo.currentText()
        if self.department_combo.currentIndex() > 0:
            data['department'] = self.department_combo.currentText()
        if self.project_combo.currentIndex() > 0:
            data['project'] = self.project_combo.currentText()
        if self.remark_edit.text().strip():
            data['remark'] = self.remark_edit.text().strip()
        if self.opinion_edit.toPlainText().strip():
            data['opinion'] = self.opinion_edit.toPlainText().strip()
        
        if not data:
            QMessageBox.warning(self, '提示', '请至少设置一项归类内容。')
            return
        
        count = 0
        for inv_id in ids:
            if InvoiceService.update(inv_id, data):
                count += 1
        
        self.refresh()
        QMessageBox.information(self, '成功', f'已归类 {count} 张票据。')

    def _apply_auto_rules(self):
        ids = self._get_selected_ids()
        if not ids:
            QMessageBox.warning(self, '提示', '请先选择票据。')
            return
        
        from datetime import datetime
        count = 0
        for inv_id in ids:
            inv = InvoiceService.get_by_id(inv_id)
            if inv:
                inv = RuleService.apply_rules(inv)
                InvoiceService.update(inv_id, {
                    'category': inv.category,
                    'reimbursable_amount': inv.reimbursable_amount
                })
                count += 1
        
        self.refresh()
        QMessageBox.information(self, '成功', f'已对 {count} 张票据应用自动归类规则。\n（可在"规则设置"中配置规则）')

    def _submit_approval(self):
        ids = self._get_selected_ids()
        if not ids:
            QMessageBox.warning(self, '提示', '请先选择要提交审批的票据。')
            return
        
        reply = QMessageBox.question(self, '确认提交',
            f'确定将选中的 {len(ids)} 张票据合并提交审批？\n（将生成一张审批单，可在异常清单-待审批中查看）',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                batch_no, count, total = ApprovalService.batch_submit(ids, applicant='admin')
                if count > 0:
                    self.refresh()
                    QMessageBox.information(self, '成功',
                        f'提交成功！\n\n审批单批次号: {batch_no}\n包含票据: {count} 张\n申请总金额: ¥{total:.2f}\n\n可在"异常清单 → 待审批清单"中查看。')
                else:
                    QMessageBox.warning(self, '提示', '没有可提交的票据（可能已在审批中）。')
            except Exception as e:
                QMessageBox.critical(self, '失败', f'提交审批失败：{str(e)}')
