-- Table: sources
CREATE TABLE IF NOT EXISTS sources (
    source_id INT AUTO_INCREMENT PRIMARY KEY,
    source_name VARCHAR(255) NOT NULL UNIQUE,
    source_type VARCHAR(50) -- e.g., 'Supermercado', 'Banco', 'Tarjeta de Credito', 'Inversiones'
);

-- Table: main_categories
CREATE TABLE IF NOT EXISTS main_categories (
    main_category_id INT AUTO_INCREMENT PRIMARY KEY,
    main_category_name VARCHAR(255) NOT NULL UNIQUE,
    transaction_type ENUM('Ingreso', 'Gasto', 'Transferencia') NOT NULL
);

-- Table: sub_categories
CREATE TABLE IF NOT EXISTS sub_categories (
    sub_category_id INT AUTO_INCREMENT PRIMARY KEY,
    sub_category_name VARCHAR(255) NOT NULL,
    main_category_id INT NOT NULL,
    FOREIGN KEY (main_category_id) REFERENCES main_categories(main_category_id),
    UNIQUE (sub_category_name, main_category_id)
);

-- Table: bank_statement_metadata_raw
CREATE TABLE IF NOT EXISTS bank_statement_metadata_raw (
    metadata_id INT AUTO_INCREMENT PRIMARY KEY,
    source_id INT NOT NULL,
    account_holder_name VARCHAR(255),
    rut VARCHAR(20),
    account_number VARCHAR(50),
    currency VARCHAR(10),
    statement_issue_date DATE,
    statement_folio VARCHAR(50),
    accounting_balance DECIMAL(15, 2),
    retentions_24hrs DECIMAL(15, 2),
    retentions_48hrs DECIMAL(15, 2),
    initial_balance DECIMAL(15, 2),
    available_balance DECIMAL(15, 2),
    credit_line_amount DECIMAL(15, 2),
    card_type VARCHAR(255),
    card_status VARCHAR(50),
    billed_amount DECIMAL(15, 2),
    minimum_payment DECIMAL(15, 2),
    billing_date DATE,
    due_date DATE,
    original_filename VARCHAR(255),
    processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (source_id) REFERENCES sources(source_id)
);

-- Table: bank_account_transactions_raw
CREATE TABLE IF NOT EXISTS bank_account_transactions_raw (
    raw_id INT AUTO_INCREMENT PRIMARY KEY,
    source_id INT NOT NULL,
    metadata_id INT NOT NULL,
    transaction_date_str VARCHAR(10),
    transaction_description TEXT,
    channel_or_branch VARCHAR(255),
    charges_pesos DECIMAL(15, 2),
    credits_pesos DECIMAL(15, 2),
    balance_pesos DECIMAL(15, 2),
    original_line_data TEXT,
    processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (source_id) REFERENCES sources(source_id),
    FOREIGN KEY (metadata_id) REFERENCES bank_statement_metadata_raw(metadata_id)
);

-- Table: credit_card_transactions_raw
CREATE TABLE IF NOT EXISTS credit_card_transactions_raw (
    raw_id INT AUTO_INCREMENT PRIMARY KEY,
    source_id INT NOT NULL,
    metadata_id INT NOT NULL,
    transaction_date_str VARCHAR(10),
    transaction_description TEXT,
    installments VARCHAR(10),
    amount_pesos DECIMAL(15, 2),
    original_line_data TEXT,
    processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (source_id) REFERENCES sources(source_id),
    FOREIGN KEY (metadata_id) REFERENCES bank_statement_metadata_raw(metadata_id)
);

-- Table: transactions
CREATE TABLE IF NOT EXISTS transactions (
    transaction_id VARCHAR(255) PRIMARY KEY,
    source_id INT NOT NULL,
    original_raw_id INT,
    original_metadata_id INT,
    transaction_date DATE NOT NULL,
    transaction_time TIME,
    description TEXT NOT NULL,
    amount DECIMAL(15, 2) NOT NULL,
    transaction_type ENUM('Ingreso', 'Gasto', 'Transferencia') NOT NULL,
    main_category_id INT,
    sub_category_id INT,
    original_document_path VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (source_id) REFERENCES sources(source_id),
    FOREIGN KEY (original_metadata_id) REFERENCES bank_statement_metadata_raw(metadata_id),
    FOREIGN KEY (main_category_id) REFERENCES main_categories(main_category_id),
    FOREIGN KEY (sub_category_id) REFERENCES sub_categories(sub_category_id)
);

-- Table: transaction_items (for detailed receipt items, e.g., Jumbo)
CREATE TABLE IF NOT EXISTS transaction_items (
    item_id INT AUTO_INCREMENT PRIMARY KEY,
    transaction_id VARCHAR(255) NOT NULL,
    sku VARCHAR(255),
    product_description TEXT NOT NULL,
    quantity DECIMAL(10, 3),
    unit_price DECIMAL(15, 2),
    total_item_price DECIMAL(15, 2),
    offer_description TEXT,
    discount_amount DECIMAL(15, 2),
    FOREIGN KEY (transaction_id) REFERENCES transactions(transaction_id)
);
