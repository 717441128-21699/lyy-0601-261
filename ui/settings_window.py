from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QTableWidget,
    QTableWidgetItem, QHeaderView, QTabWidget, QGroupBox, QFormLayout,
    QLineEdit, QComboBox, QTextEdit, QSpinBox, QCheckBox, QMessageBox,
    QAbstractItemView, QInputDialog
)
from PyQt6.QtCore import Qt

from core.services import RuleService, OperationLogService
from core.models import RULE_TYPE_MAP


class SettingsWindow(QWidget):
    def __init__(self):
        super().__init__()
        self._current_rule_id = None
        self._init_ui()
        self.refresh()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        title = QLabel('规则设置')
        title.setStyleSheet('font-size: 20px; font-weight: bold; color: #2c3e50;')
        layout.addWidget(title)
        
        self.tabs = QTabWidget()
        
        self._init_rules_tab()
        self._init_logs_tab()
        
        layout.addWidget(self.tabs, 1)

    def _init_rules_tab(self):
        tab = QWidget()
        tab_layout = QVBoxLayout(tab)
        
        from PyQt6.QtWidgets import QSplitter
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        left_group = QGroupBox('规则列表')
        left_layout = QVBoxLayout(left_group)
        
        btn_bar = QHBoxLayout()
        self.btn_new_rule = QPushButton('➕ 新建规则')
        self.btn_new_rule.setStyleSheet(self._btn_style('#27ae60'))
        self.btn_new_rule.clicked.connect(self._new_rule)
        btn_bar.addWidget(self.btn_new_rule)
        
        self.btn_delete_rule = QPushButton('🗑️ 删除规则')
        self.btn_delete_rule.setStyleSheet(self._btn_style('#e74c3c'))
        self.btn_delete_rule.clicked.connect(self._delete_rule)
        btn_bar.addWidget(self.btn_delete_rule)
        
        btn_bar.addStretch()
        left_layout.addLayout(btn_bar)
        
        self.rules_table = QTableWidget(0, 7)
        self.rules_table.setHorizontalHeaderLabels([
            'ID', '规则名称', '类型', '条件', '动作', '优先级', '启用'
        ])
        self.rules_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.rules_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.rules_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        self.rules_table.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)
        self.rules_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.rules_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.rules_table.itemSelectionChanged.connect(self._on_select_rule)
        left_layout.addWidget(self.rules_table)
        
        splitter.addWidget(left_group)
        
        right_group = QGroupBox('规则详情')
        right_layout = QVBoxLayout(right_group)
        
        form = QFormLayout()
        
        self.rule_name_edit = QLineEdit()
        form.addRow('规则名称*:', self.rule_name_edit)
        
        self.rule_type_combo = QComboBox()
        for k, v in RULE_TYPE_MAP.items():
            self.rule_type_combo.addItem(v, k)
        form.addRow('规则类型*:', self.rule_type_combo)
        
        self.rule_condition_edit = QLineEdit()
        self.rule_condition_edit.setPlaceholderText('例如：供应商名称包含"滴滴"')
        form.addRow('条件:', self.rule_condition_edit)
        
        self.rule_action_edit = QLineEdit()
        self.rule_action_edit.setPlaceholderText('例如：设置类别为')
        form.addRow('动作:', self.rule_action_edit)
        
        self.rule_value_edit = QLineEdit()
        self.rule_value_edit.setPlaceholderText('例如：交通费 或 100（百分比）')
        form.addRow('值:', self.rule_value_edit)
        
        self.rule_priority_spin = QSpinBox()
        self.rule_priority_spin.setRange(0, 100)
        form.addRow('优先级:', self.rule_priority_spin)
        
        self.rule_enabled_check = QCheckBox('启用该规则')
        self.rule_enabled_check.setChecked(True)
        form.addRow('', self.rule_enabled_check)
        
        self.rule_desc_edit = QTextEdit()
        self.rule_desc_edit.setFixedHeight(60)
        self.rule_desc_edit.setPlaceholderText('规则说明（可选）')
        form.addRow('描述:', self.rule_desc_edit)
        
        right_layout.addLayout(form)
        
        btn_row = QHBoxLayout()
        self.btn_save_rule = QPushButton('💾 保存规则')
        self.btn_save_rule.setStyleSheet(self._btn_style('#3498db'))
        self.btn_save_rule.setFixedHeight(36)
        self.btn_save_rule.clicked.connect(self._save_rule)
        btn_row.addWidget(self.btn_save_rule)
        
        right_layout.addLayout(btn_row)
        right_layout.addStretch()
        
        splitter.addWidget(right_group)
        splitter.setSizes([600, 500])
        
        tab_layout.addWidget(splitter)
        
        hint_box = QGroupBox('📖 使用说明')
        hint_layout = QVBoxLayout(hint_box)
        hints = [
            '【自动分类】条件填供应商关键词，值填费用类别名称（如：差旅费）',
            '【报销计算】值填报销比例百分比数字（如：80 表示按80%报销）',
            '【重复检测】用于检测相同发票号或同日期同金额同供应商的票据',
            '规则按优先级从高到低依次应用，数字越大优先级越高'
        ]
        for h in hints:
            lbl = QLabel('• ' + h)
            lbl.setStyleSheet('color: #555; padding: 3px 0;')
            hint_layout.addWidget(lbl)
        tab_layout.addWidget(hint_box)
        
        self.tabs.addTab(tab, '⚙️ 规则管理')

    def _init_logs_tab(self):
        tab = QWidget()
        tab_layout = QVBoxLayout(tab)
        
        bar = QHBoxLayout()
        desc = QLabel('📜 操作日志')
        desc.setStyleSheet('font-weight: bold; color: #2c3e50; font-size: 14px;')
        bar.addWidget(desc)
        
        bar.addWidget(QLabel('搜索:'))
        self.log_search_input = QLineEdit()
        self.log_search_input.setPlaceholderText('输入批次号/关键词搜索')
        self.log_search_input.setFixedWidth(250)
        self.log_search_input.textChanged.connect(self._refresh_logs)
        bar.addWidget(self.log_search_input)
        
        bar.addStretch()
        
        self.btn_refresh_log = QPushButton('🔄 刷新日志')
        self.btn_refresh_log.setStyleSheet(self._btn_style('#3498db'))
        self.btn_refresh_log.clicked.connect(self._refresh_logs)
        bar.addWidget(self.btn_refresh_log)
        
        tab_layout.addLayout(bar)
        
        self.logs_table = QTableWidget(0, 6)
        self.logs_table.setHorizontalHeaderLabels([
            'ID', '操作时间', '操作类型', '操作对象', '对象ID', '详情'
        ])
        self.logs_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.logs_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.logs_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.logs_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        tab_layout.addWidget(self.logs_table)
        
        self.tabs.addTab(tab, '📜 操作记录')

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
        self._refresh_rules()
        self._refresh_logs()

    def _refresh_rules(self):
        rules = RuleService.get_all()
        self.rules_table.setRowCount(len(rules))
        for row, rule in enumerate(rules):
            self.rules_table.setItem(row, 0, QTableWidgetItem(str(rule.id)))
            self.rules_table.setItem(row, 1, QTableWidgetItem(rule.name))
            self.rules_table.setItem(row, 2, QTableWidgetItem(RULE_TYPE_MAP.get(rule.rule_type, rule.rule_type)))
            self.rules_table.setItem(row, 3, QTableWidgetItem(rule.condition))
            self.rules_table.setItem(row, 4, QTableWidgetItem(rule.action))
            self.rules_table.setItem(row, 5, QTableWidgetItem(str(rule.priority)))
            
            enabled_text = '✅ 启用' if rule.enabled else '❌ 禁用'
            item = QTableWidgetItem(enabled_text)
            if not rule.enabled:
                item.setForeground(Qt.GlobalColor.gray)
            self.rules_table.setItem(row, 6, item)

    def _refresh_logs(self):
        keyword = self.log_search_input.text().strip() if hasattr(self, 'log_search_input') else ''
        if keyword:
            logs = OperationLogService.search(keyword=keyword, limit=500)
        else:
            logs = OperationLogService.get_all(limit=200)
        self.logs_table.setRowCount(len(logs))
        for row, log in enumerate(logs):
            self.logs_table.setItem(row, 0, QTableWidgetItem(str(log.id)))
            self.logs_table.setItem(row, 1, QTableWidgetItem(log.created_at))
            self.logs_table.setItem(row, 2, QTableWidgetItem(log.operation_type))
            self.logs_table.setItem(row, 3, QTableWidgetItem(log.target_type))
            self.logs_table.setItem(row, 4, QTableWidgetItem(str(log.target_id) if log.target_id else '-'))
            
            detail_item = QTableWidgetItem(log.detail)
            if keyword and keyword.upper() in log.detail.upper():
                detail_item.setBackground(Qt.GlobalColor.yellow)
            self.logs_table.setItem(row, 5, detail_item)

    def _on_select_rule(self):
        items = self.rules_table.selectedItems()
        if not items:
            return
        
        row = items[0].row()
        rule_id = int(self.rules_table.item(row, 0).text())
        rules = RuleService.get_all()
        rule = next((r for r in rules if r.id == rule_id), None)
        if not rule:
            return
        
        self._current_rule_id = rule_id
        self.rule_name_edit.setText(rule.name)
        
        idx = self.rule_type_combo.findData(rule.rule_type)
        self.rule_type_combo.setCurrentIndex(idx if idx >= 0 else 0)
        
        self.rule_condition_edit.setText(rule.condition)
        self.rule_action_edit.setText(rule.action)
        self.rule_value_edit.setText(rule.value)
        self.rule_priority_spin.setValue(rule.priority)
        self.rule_enabled_check.setChecked(rule.enabled)
        self.rule_desc_edit.setPlainText(rule.description)

    def _new_rule(self):
        self._current_rule_id = None
        self.rule_name_edit.clear()
        self.rule_type_combo.setCurrentIndex(0)
        self.rule_condition_edit.clear()
        self.rule_action_edit.clear()
        self.rule_value_edit.clear()
        self.rule_priority_spin.setValue(0)
        self.rule_enabled_check.setChecked(True)
        self.rule_desc_edit.clear()
        self.rules_table.clearSelection()

    def _save_rule(self):
        from core.models import Rule
        
        name = self.rule_name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, '提示', '请输入规则名称。')
            return
        
        rule_type = self.rule_type_combo.currentData()
        if not rule_type:
            QMessageBox.warning(self, '提示', '请选择规则类型。')
            return
        
        rule = Rule(
            name=name,
            rule_type=rule_type,
            condition=self.rule_condition_edit.text().strip(),
            action=self.rule_action_edit.text().strip(),
            value=self.rule_value_edit.text().strip(),
            priority=self.rule_priority_spin.value(),
            enabled=self.rule_enabled_check.isChecked(),
            description=self.rule_desc_edit.toPlainText().strip()
        )
        
        if self._current_rule_id:
            if RuleService.update(self._current_rule_id, {
                'name': rule.name,
                'rule_type': rule.rule_type,
                'condition': rule.condition,
                'action': rule.action,
                'value': rule.value,
                'priority': rule.priority,
                'enabled': rule.enabled,
                'description': rule.description
            }):
                QMessageBox.information(self, '成功', '规则已更新。')
            else:
                QMessageBox.warning(self, '失败', '更新失败，请重试。')
        else:
            new_id = RuleService.create(rule)
            if new_id:
                self._current_rule_id = new_id
                QMessageBox.information(self, '成功', '规则已创建。')
            else:
                QMessageBox.warning(self, '失败', '创建失败，请重试。')
        
        self._refresh_rules()

    def _delete_rule(self):
        if not self._current_rule_id:
            QMessageBox.warning(self, '提示', '请先选择要删除的规则。')
            return
        
        reply = QMessageBox.question(self, '确认删除',
            '确定要删除该规则吗？此操作不可恢复。',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        if RuleService.delete(self._current_rule_id):
            self._current_rule_id = None
            self._new_rule()
            self._refresh_rules()
            QMessageBox.information(self, '成功', '规则已删除。')
        else:
            QMessageBox.warning(self, '失败', '删除失败，请重试。')
