import sqlite3
import os
from datetime import datetime
from typing import List, Dict, Optional, Any


DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'finance.db')


def get_db_path():
    data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data')
    os.makedirs(data_dir, exist_ok=True)
    return os.path.join(data_dir, 'finance.db')


class DatabaseManager:
    _instance = None
    _conn = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if self._conn is None:
            self._conn = sqlite3.connect(get_db_path())
            self._conn.row_factory = sqlite3.Row
            self._init_tables()

    def _init_tables(self):
        cursor = self._conn.cursor()
        cursor.executescript('''
            CREATE TABLE IF NOT EXISTS invoices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_path TEXT NOT NULL,
                file_name TEXT,
                invoice_no TEXT,
                invoice_code TEXT,
                amount REAL DEFAULT 0,
                tax_amount REAL DEFAULT 0,
                total_amount REAL DEFAULT 0,
                invoice_date TEXT,
                supplier TEXT,
                buyer TEXT,
                category TEXT,
                department TEXT,
                project TEXT,
                reimbursable_amount REAL DEFAULT 0,
                status TEXT DEFAULT 'pending',
                is_duplicate INTEGER DEFAULT 0,
                has_attachment INTEGER DEFAULT 1,
                remark TEXT,
                opinion TEXT,
                ocr_result TEXT,
                created_at TEXT,
                updated_at TEXT
            );

            CREATE TABLE IF NOT EXISTS payments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                payment_no TEXT,
                pay_date TEXT,
                pay_amount REAL DEFAULT 0,
                payee TEXT,
                bank_account TEXT,
                bank_name TEXT,
                purpose TEXT,
                remark TEXT,
                invoice_id INTEGER,
                matched_status TEXT DEFAULT 'unmatched',
                created_at TEXT,
                updated_at TEXT,
                FOREIGN KEY (invoice_id) REFERENCES invoices(id)
            );

            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                parent_id INTEGER,
                type TEXT DEFAULT 'expense',
                description TEXT,
                created_at TEXT
            );

            CREATE TABLE IF NOT EXISTS departments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                manager TEXT,
                description TEXT,
                created_at TEXT
            );

            CREATE TABLE IF NOT EXISTS projects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                code TEXT,
                manager TEXT,
                description TEXT,
                start_date TEXT,
                end_date TEXT,
                created_at TEXT
            );

            CREATE TABLE IF NOT EXISTS rules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                rule_type TEXT NOT NULL,
                condition TEXT,
                action TEXT,
                value TEXT,
                priority INTEGER DEFAULT 0,
                enabled INTEGER DEFAULT 1,
                description TEXT,
                created_at TEXT,
                updated_at TEXT
            );

            CREATE TABLE IF NOT EXISTS operation_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                operation_type TEXT,
                target_type TEXT,
                target_id INTEGER,
                detail TEXT,
                operator TEXT DEFAULT 'admin',
                created_at TEXT
            );

            CREATE TABLE IF NOT EXISTS approval_lists (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                invoice_id INTEGER,
                applicant TEXT,
                apply_date TEXT,
                amount REAL DEFAULT 0,
                status TEXT DEFAULT 'pending',
                approver TEXT,
                approval_date TEXT,
                approval_opinion TEXT,
                created_at TEXT,
                FOREIGN KEY (invoice_id) REFERENCES invoices(id)
            );
        ''')
        self._conn.commit()
        self._init_default_data()

    def _init_default_data(self):
        cursor = self._conn.cursor()
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        default_categories = [
            ('差旅费', None, 'expense', '出差相关费用'),
            ('办公费', None, 'expense', '办公用品及耗材'),
            ('业务招待费', None, 'expense', '客户招待费用'),
            ('通讯费', None, 'expense', '电话网络费用'),
            ('交通费', None, 'expense', '市内交通费用'),
            ('培训费', None, 'expense', '员工培训费用'),
            ('福利费', None, 'expense', '员工福利费用'),
            ('其他费用', None, 'expense', '其他杂项费用')
        ]
        for name, parent_id, type_, desc in default_categories:
            cursor.execute('SELECT id FROM categories WHERE name = ?', (name,))
            if not cursor.fetchone():
                cursor.execute(
                    'INSERT INTO categories (name, parent_id, type, description, created_at) VALUES (?, ?, ?, ?, ?)',
                    (name, parent_id, type_, desc, now)
                )

        default_departments = [
            ('行政部', '行政经理', '行政管理部门'),
            ('财务部', '财务经理', '财务管理部门'),
            ('人事部', '人事经理', '人力资源部门'),
            ('销售部', '销售经理', '销售业务部门'),
            ('技术部', '技术经理', '技术研发部门'),
            ('市场部', '市场经理', '市场营销部门'),
            ('运营部', '运营经理', '运营管理部门')
        ]
        for name, manager, desc in default_departments:
            cursor.execute('SELECT id FROM departments WHERE name = ?', (name,))
            if not cursor.fetchone():
                cursor.execute(
                    'INSERT INTO departments (name, manager, description, created_at) VALUES (?, ?, ?, ?)',
                    (name, manager, desc, now)
                )

        self._conn.commit()

    def close(self):
        if self._conn:
            self._conn.close()
            self._conn = None

    def execute(self, sql: str, params: tuple = ()) -> sqlite3.Cursor:
        cursor = self._conn.cursor()
        cursor.execute(sql, params)
        return cursor

    def begin_transaction(self):
        self._conn.execute('BEGIN')

    def commit(self):
        self._conn.commit()

    def rollback(self):
        self._conn.rollback()

    def insert_raw(self, table: str, data: Dict[str, Any]) -> int:
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        if 'created_at' not in data:
            data['created_at'] = now
        if 'updated_at' not in data:
            data['updated_at'] = now
        columns = ', '.join(data.keys())
        placeholders = ', '.join(['?'] * len(data))
        sql = f'INSERT INTO {table} ({columns}) VALUES ({placeholders})'
        cursor = self.execute(sql, tuple(data.values()))
        return cursor.lastrowid

    def insert(self, table: str, data: Dict[str, Any]) -> int:
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        if 'created_at' not in data:
            data['created_at'] = now
        if 'updated_at' not in data:
            data['updated_at'] = now
        
        columns = ', '.join(data.keys())
        placeholders = ', '.join(['?'] * len(data))
        sql = f'INSERT INTO {table} ({columns}) VALUES ({placeholders})'
        cursor = self.execute(sql, tuple(data.values()))
        self.commit()
        return cursor.lastrowid

    def update(self, table: str, data: Dict[str, Any], where: str, where_params: tuple = ()) -> int:
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        if 'updated_at' not in data:
            data['updated_at'] = now
        
        set_clause = ', '.join([f'{k} = ?' for k in data.keys()])
        sql = f'UPDATE {table} SET {set_clause} WHERE {where}'
        cursor = self.execute(sql, tuple(data.values()) + where_params)
        self.commit()
        return cursor.rowcount

    def delete(self, table: str, where: str, where_params: tuple = ()) -> int:
        sql = f'DELETE FROM {table} WHERE {where}'
        cursor = self.execute(sql, where_params)
        self.commit()
        return cursor.rowcount

    def query(self, sql: str, params: tuple = ()) -> List[sqlite3.Row]:
        cursor = self.execute(sql, params)
        return cursor.fetchall()

    def query_one(self, sql: str, params: tuple = ()) -> Optional[sqlite3.Row]:
        cursor = self.execute(sql, params)
        return cursor.fetchone()

    def log_operation(self, op_type: str, target_type: str, target_id: int, detail: str, operator: str = 'admin'):
        self.insert('operation_logs', {
            'operation_type': op_type,
            'target_type': target_type,
            'target_id': target_id,
            'detail': detail,
            'operator': operator
        })


def get_db():
    return DatabaseManager()
