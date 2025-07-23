-- 创建数据库（如果不存在）
CREATE DATABASE IF NOT EXISTS invoice
    DEFAULT CHARACTER SET utf8mb4
    DEFAULT COLLATE utf8mb4_unicode_ci;

-- 使用invoice数据库
USE invoice;

-- 创建发票主表（存储发票基本信息）
CREATE TABLE IF NOT EXISTS invoice_master (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,  -- 替换 SERIAL，显式定义为 BIGINT UNSIGNED
    file_name VARCHAR(255) NOT NULL,
    invoice_title VARCHAR(255),
    invoice_code VARCHAR(50) UNIQUE,
    issue_date DATE,
    buyer_name VARCHAR(100),
    buyer_tax_id VARCHAR(50),
    seller_name VARCHAR(100),
    seller_tax_id VARCHAR(50),
    total_amount DECIMAL(10, 2),
    total_tax DECIMAL(10, 2),
    total_with_tax DECIMAL(10, 2),
    total_with_tax_in_words TEXT,
    remarks TEXT,
    issuer VARCHAR(50),
    create_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 创建发票商品明细表（存储发票中的商品/服务项）
CREATE TABLE IF NOT EXISTS invoice_items (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,  -- 明细表自身ID也建议用 BIGINT UNSIGNED
    invoice_id BIGINT UNSIGNED NOT NULL,  -- 与主表id类型一致（BIGINT UNSIGNED）
    item_name VARCHAR(255),
    specification VARCHAR(100),
    unit VARCHAR(20),
    quantity DECIMAL(10, 3),
    unit_price DECIMAL(10, 2),
    amount DECIMAL(10, 2),
    tax_rate DECIMAL(5, 2),
    tax_amount DECIMAL(10, 2),
    -- 外键约束：与主表id类型完全匹配
    FOREIGN KEY (invoice_id) REFERENCES invoice_master(id) ON DELETE CASCADE
);

-- 为主表添加索引
CREATE INDEX IF NOT EXISTS idx_invoice_code ON invoice_master(invoice_code);
CREATE INDEX IF NOT EXISTS idx_issue_date ON invoice_master(issue_date);
CREATE INDEX IF NOT EXISTS idx_buyer_tax_id ON invoice_master(buyer_tax_id);
CREATE INDEX IF NOT EXISTS idx_seller_tax_id ON invoice_master(seller_tax_id);

-- 为明细表添加索引
CREATE INDEX IF NOT EXISTS idx_invoice_id ON invoice_items(invoice_id);

-- 可选：创建用户并授权（取消注释以启用）
-- CREATE USER 'invoice_user'@'localhost' IDENTIFIED BY 'password';
-- GRANT ALL PRIVILEGES ON invoice.* TO 'invoice_user'@'localhost';
-- FLUSH PRIVILEGES;

-- 示例数据（可选）
-- INSERT INTO invoice_master (file_name, invoice_code, issue_date) VALUES ('test.jpg', '123456', '2023-01-01');