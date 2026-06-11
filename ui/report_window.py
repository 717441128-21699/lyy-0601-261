from datetime import datetime
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QTableWidget,
    QTableWidgetItem, QHeaderView, QDateEdit, QComboBox, QGroupBox,
    QFormLayout, QMessageBox, QFileDialog, QFrame, QGridLayout
)
from PyQt6.QtCore import Qt, QDate
from PyQt6.QtGui import QColor

from core.services import StatisticsService, InvoiceService, PaymentService
from core.models import STATUS_MAP, MATCH_STATUS_MAP


class ReportWindow(QWidget):
    def __init__(self):
        super().__init__()
        self._init_ui()
        self.refresh()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        title = QLabel('统计报表')
        title.setStyleSheet('font-size: 20px; font-weight: bold; color: #2c3e50;')
        layout.addWidget(title)
        
        filter_bar = QHBoxLayout()
        
        filter_bar.addWidget(QLabel('开始日期:'))
        self.start_date = QDateEdit()
        self.start_date.setCalendarPopup(True)
        self.start_date.setDisplayFormat('yyyy-MM-dd')
        self.start_date.setDate(QDate(QDate.currentDate().year(), 1, 1))
        self.start_date.dateChanged.connect(lambda: self.refresh())
        filter_bar.addWidget(self.start_date)
        
        filter_bar.addWidget(QLabel('结束日期:'))
        self.end_date = QDateEdit()
        self.end_date.setCalendarPopup(True)
        self.end_date.setDisplayFormat('yyyy-MM-dd')
        self.end_date.setDate(QDate.currentDate())
        self.end_date.dateChanged.connect(lambda: self.refresh())
        filter_bar.addWidget(self.end_date)
        
        filter_bar.addWidget(QLabel('年份:'))
        self.year_combo = QComboBox()
        cur_year = QDate.currentDate().year()
        for y in range(cur_year, cur_year - 5, -1):
            self.year_combo.addItem(f'{y}年', y)
        self.year_combo.currentIndexChanged.connect(lambda: self.refresh())
        filter_bar.addWidget(self.year_combo)
        
        filter_bar.addStretch()
        
        self.btn_export = QPushButton('📥 导出Excel报表')
        self.btn_export.setStyleSheet(self._btn_style('#27ae60'))
        self.btn_export.setFixedHeight(36)
        self.btn_export.clicked.connect(self._export_report)
        filter_bar.addWidget(self.btn_export)
        
        self.btn_refresh = QPushButton('🔄 刷新统计')
        self.btn_refresh.setStyleSheet(self._btn_style('#3498db'))
        self.btn_refresh.setFixedHeight(36)
        self.btn_refresh.clicked.connect(self.refresh)
        filter_bar.addWidget(self.btn_refresh)
        
        layout.addLayout(filter_bar)
        
        summary_group = QGroupBox('📊 汇总统计')
        summary_layout = QGridLayout(summary_group)
        
        self.summary_labels = {}
        summary_items = [
            ('invoice_count', '票据总数', '#2c3e50'),
            ('total_amount', '总金额 (¥)', '#2980b9'),
            ('reimbursable_amount', '可报销总金额 (¥)', '#27ae60'),
            ('matched_count', '已匹配数', '#8e44ad'),
            ('unmatched_count', '未匹配数', '#e67e22'),
            ('duplicate_count', '重复票据数', '#c0392b'),
            ('missing_attachment_count', '缺少附件数', '#d35400'),
            ('pending_count', '待处理数', '#f39c12'),
            ('approved_count', '已通过数', '#16a085'),
            ('rejected_count', '已驳回数', '#7f8c8d'),
        ]
        
        for i, (key, label_text, color) in enumerate(summary_items):
            row, col = divmod(i, 5)
            
            lbl_title = QLabel(label_text)
            lbl_title.setStyleSheet(f'font-size: 12px; color: {color}; font-weight: bold;')
            lbl_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
            summary_layout.addWidget(lbl_title, row * 2, col)
            
            lbl_value = QLabel('0')
            lbl_value.setStyleSheet(f'font-size: 22px; color: {color}; font-weight: bold;')
            lbl_value.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl_value.setMinimumHeight(40)
            summary_layout.addWidget(lbl_value, row * 2 + 1, col)
            self.summary_labels[key] = lbl_value
        
        layout.addWidget(summary_group)
        
        from PyQt6.QtWidgets import QTabWidget
        self.tabs = QTabWidget()
        
        self._init_monthly_tab()
        self._init_category_tab()
        self._init_department_tab()
        
        layout.addWidget(self.tabs, 1)

    def _init_monthly_tab(self):
        tab = QWidget()
        tab_layout = QVBoxLayout(tab)
        
        hint = QLabel('📅 月度费用趋势（按开票日期统计）')
        hint.setStyleSheet('font-weight: bold; color: #2c3e50; font-size: 14px;')
        tab_layout.addWidget(hint)
        
        self.monthly_table = QTableWidget(0, 4)
        self.monthly_table.setHorizontalHeaderLabels(['月份', '总金额 (¥)', '可报销金额 (¥)', '票据数量'])
        self.monthly_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.monthly_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        tab_layout.addWidget(self.monthly_table)
        
        self.tabs.addTab(tab, '📅 月度汇总')

    def _init_category_tab(self):
        tab = QWidget()
        tab_layout = QVBoxLayout(tab)
        
        hint = QLabel('🏷️ 按费用类别统计')
        hint.setStyleSheet('font-weight: bold; color: #2c3e50; font-size: 14px;')
        tab_layout.addWidget(hint)
        
        self.category_table = QTableWidget(0, 4)
        self.category_table.setHorizontalHeaderLabels(['费用类别', '总金额 (¥)', '可报销金额 (¥)', '票据数量'])
        self.category_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.category_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        tab_layout.addWidget(self.category_table)
        
        self.tabs.addTab(tab, '🏷️ 类别统计')

    def _init_department_tab(self):
        tab = QWidget()
        tab_layout = QVBoxLayout(tab)
        
        hint = QLabel('🏢 按部门统计')
        hint.setStyleSheet('font-weight: bold; color: #2c3e50; font-size: 14px;')
        tab_layout.addWidget(hint)
        
        self.dept_table = QTableWidget(0, 4)
        self.dept_table.setHorizontalHeaderLabels(['部门', '总金额 (¥)', '可报销金额 (¥)', '票据数量'])
        self.dept_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.dept_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        tab_layout.addWidget(self.dept_table)
        
        self.tabs.addTab(tab, '🏢 部门统计')

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

    def _get_date_range(self):
        start = self.start_date.date().toString('yyyy-MM-dd')
        end = self.end_date.date().toString('yyyy-MM-dd')
        return start, end

    def refresh(self):
        start, end = self._get_date_range()
        year = self.year_combo.currentData() or QDate.currentDate().year()
        
        summary = StatisticsService.get_summary(start, end)
        
        self.summary_labels['invoice_count'].setText(str(summary.invoice_count))
        self.summary_labels['total_amount'].setText(f'{summary.total_amount:,.2f}')
        self.summary_labels['reimbursable_amount'].setText(f'{summary.reimbursable_amount:,.2f}')
        self.summary_labels['matched_count'].setText(str(summary.matched_count))
        self.summary_labels['unmatched_count'].setText(str(summary.unmatched_count))
        self.summary_labels['duplicate_count'].setText(str(summary.duplicate_count))
        self.summary_labels['missing_attachment_count'].setText(str(summary.missing_attachment_count))
        self.summary_labels['pending_count'].setText(str(summary.pending_count))
        self.summary_labels['approved_count'].setText(str(summary.approved_count))
        self.summary_labels['rejected_count'].setText(str(summary.rejected_count))
        
        monthly = StatisticsService.get_monthly_summary(year)
        self.monthly_table.setRowCount(len(monthly))
        for row, data in enumerate(monthly):
            self.monthly_table.setItem(row, 0, QTableWidgetItem(data['month']))
            self.monthly_table.setItem(row, 1, QTableWidgetItem(f'{data["total_amount"]:,.2f}'))
            self.monthly_table.setItem(row, 2, QTableWidgetItem(f'{data["reimbursable_amount"]:,.2f}'))
            self.monthly_table.setItem(row, 3, QTableWidgetItem(str(data['count'])))
            
            if data['total_amount'] > 0:
                for col in range(4):
                    item = self.monthly_table.item(row, col)
                    if item:
                        item.setBackground(QColor(232, 246, 243))
        
        cat_data = StatisticsService.get_by_category(start, end)
        self.category_table.setRowCount(len(cat_data))
        for row, data in enumerate(cat_data):
            self.category_table.setItem(row, 0, QTableWidgetItem(data['category']))
            self.category_table.setItem(row, 1, QTableWidgetItem(f'{data["total_amount"]:,.2f}'))
            self.category_table.setItem(row, 2, QTableWidgetItem(f'{data["reimbursable_amount"]:,.2f}'))
            self.category_table.setItem(row, 3, QTableWidgetItem(str(data['count'])))
        
        dept_data = StatisticsService.get_by_department(start, end)
        self.dept_table.setRowCount(len(dept_data))
        for row, data in enumerate(dept_data):
            self.dept_table.setItem(row, 0, QTableWidgetItem(data['department']))
            self.dept_table.setItem(row, 1, QTableWidgetItem(f'{data["total_amount"]:,.2f}'))
            self.dept_table.setItem(row, 2, QTableWidgetItem(f'{data["reimbursable_amount"]:,.2f}'))
            self.dept_table.setItem(row, 3, QTableWidgetItem(str(data['count'])))

    def _export_report(self):
        start, end = self._get_date_range()
        default_name = f'财务报表_{start}_{end}.xlsx'
        file, _ = QFileDialog.getSaveFileName(
            self, '导出报表', default_name,
            'Excel文件 (*.xlsx)'
        )
        if file:
            try:
                StatisticsService.export_report(file, start, end)
                QMessageBox.information(self, '成功', f'报表已导出到：\n{file}')
            except Exception as e:
                QMessageBox.warning(self, '失败', f'导出失败：{str(e)}')
