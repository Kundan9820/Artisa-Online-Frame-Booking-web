-- =============================================================================
-- Artista Frame — MySQL Database Schema
-- Use this if deploying with MySQL instead of the default SQLite.
-- Create the database, then run this file:
--   mysql -u youruser -p artista_frame < database.sql
-- (Flask-SQLAlchemy's db.create_all() in run.py will also auto-create these
--  tables on first run against an empty MySQL database, so this file is
--  provided mainly for manual setup / reference / production DBA review.)
-- =============================================================================

CREATE DATABASE IF NOT EXISTS artista_frame CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE artista_frame;

SET FOREIGN_KEY_CHECKS = 0;

-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS users (
  id INT AUTO_INCREMENT PRIMARY KEY,
  full_name VARCHAR(150) NOT NULL,
  email VARCHAR(150) NOT NULL UNIQUE,
  mobile VARCHAR(20) NOT NULL,
  password_hash VARCHAR(255) NOT NULL,
  is_admin BOOLEAN DEFAULT FALSE,
  is_active_account BOOLEAN DEFAULT TRUE,
  email_verified BOOLEAN DEFAULT FALSE,
  otp_code VARCHAR(10),
  otp_expires_at DATETIME,
  reset_token VARCHAR(255),
  reset_token_expires_at DATETIME,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS addresses (
  id INT AUTO_INCREMENT PRIMARY KEY,
  user_id INT NOT NULL,
  full_name VARCHAR(150) NOT NULL,
  mobile VARCHAR(20) NOT NULL,
  email VARCHAR(150),
  address_line VARCHAR(255) NOT NULL,
  city VARCHAR(100) NOT NULL,
  state VARCHAR(100) NOT NULL,
  pincode VARCHAR(10) NOT NULL,
  landmark VARCHAR(150),
  is_default BOOLEAN DEFAULT FALSE,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS categories (
  id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(120) NOT NULL UNIQUE,
  slug VARCHAR(140) NOT NULL UNIQUE,
  description TEXT,
  image VARCHAR(255),
  parent_id INT,
  is_active BOOLEAN DEFAULT TRUE,
  display_order INT DEFAULT 0,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (parent_id) REFERENCES categories(id) ON DELETE SET NULL
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS sizes (
  id INT AUTO_INCREMENT PRIMARY KEY,
  label VARCHAR(50) NOT NULL UNIQUE,
  is_custom BOOLEAN DEFAULT FALSE,
  display_order INT DEFAULT 0
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS products (
  id INT AUTO_INCREMENT PRIMARY KEY,
  sku VARCHAR(50) NOT NULL UNIQUE,
  name VARCHAR(200) NOT NULL,
  slug VARCHAR(220) NOT NULL UNIQUE,
  description TEXT,
  price DECIMAL(10,2) NOT NULL,
  discount_percent INT DEFAULT 0,
  stock INT DEFAULT 0,
  category_id INT NOT NULL,
  subcategory VARCHAR(120),
  frame_material VARCHAR(100),
  frame_color VARCHAR(60),
  delivery_time_days VARCHAR(50) DEFAULT '3-5 days',
  is_available BOOLEAN DEFAULT TRUE,
  is_featured BOOLEAN DEFAULT FALSE,
  is_new_arrival BOOLEAN DEFAULT FALSE,
  is_best_seller BOOLEAN DEFAULT FALSE,
  is_clearance BOOLEAN DEFAULT FALSE,
  is_customizable BOOLEAN DEFAULT FALSE,
  view_count INT DEFAULT 0,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  FOREIGN KEY (category_id) REFERENCES categories(id)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS product_sizes (
  product_id INT NOT NULL,
  size_id INT NOT NULL,
  PRIMARY KEY (product_id, size_id),
  FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE,
  FOREIGN KEY (size_id) REFERENCES sizes(id) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS product_images (
  id INT AUTO_INCREMENT PRIMARY KEY,
  product_id INT NOT NULL,
  image_path VARCHAR(255) NOT NULL,
  is_primary BOOLEAN DEFAULT FALSE,
  display_order INT DEFAULT 0,
  FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS cart_items (
  id INT AUTO_INCREMENT PRIMARY KEY,
  user_id INT NOT NULL,
  product_id INT NOT NULL,
  size_label VARCHAR(50),
  quantity INT DEFAULT 1,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
  FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS wishlist_items (
  id INT AUTO_INCREMENT PRIMARY KEY,
  user_id INT NOT NULL,
  product_id INT NOT NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
  FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS uploaded_photos (
  id INT AUTO_INCREMENT PRIMARY KEY,
  user_id INT,
  file_path VARCHAR(255) NOT NULL,
  frame_style VARCHAR(100),
  frame_color VARCHAR(60),
  frame_size VARCHAR(50),
  orientation VARCHAR(20),
  quantity INT DEFAULT 1,
  special_instructions TEXT,
  customer_name VARCHAR(150),
  customer_mobile VARCHAR(20),
  status VARCHAR(30) DEFAULT 'New',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS orders (
  id INT AUTO_INCREMENT PRIMARY KEY,
  order_number VARCHAR(30) NOT NULL UNIQUE,
  user_id INT,
  customer_name VARCHAR(150) NOT NULL,
  customer_mobile VARCHAR(20) NOT NULL,
  customer_email VARCHAR(150),
  address_line VARCHAR(255) NOT NULL,
  city VARCHAR(100) NOT NULL,
  state VARCHAR(100) NOT NULL,
  pincode VARCHAR(10) NOT NULL,
  landmark VARCHAR(150),
  subtotal DECIMAL(10,2) DEFAULT 0,
  discount_amount DECIMAL(10,2) DEFAULT 0,
  delivery_charge DECIMAL(10,2) DEFAULT 0,
  total_amount DECIMAL(10,2) DEFAULT 0,
  coupon_code VARCHAR(50),
  status VARCHAR(30) DEFAULT 'Pending',
  sent_via_whatsapp BOOLEAN DEFAULT FALSE,
  special_instructions TEXT,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS order_items (
  id INT AUTO_INCREMENT PRIMARY KEY,
  order_id INT NOT NULL,
  product_id INT,
  product_name VARCHAR(200) NOT NULL,
  size_label VARCHAR(50),
  quantity INT DEFAULT 1,
  unit_price DECIMAL(10,2) NOT NULL,
  is_custom BOOLEAN DEFAULT FALSE,
  custom_photo_id INT,
  FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE,
  FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE SET NULL,
  FOREIGN KEY (custom_photo_id) REFERENCES uploaded_photos(id) ON DELETE SET NULL
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS reviews (
  id INT AUTO_INCREMENT PRIMARY KEY,
  product_id INT NOT NULL,
  user_id INT NOT NULL,
  rating INT NOT NULL,
  comment TEXT,
  image VARCHAR(255),
  is_approved BOOLEAN DEFAULT FALSE,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE,
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS coupons (
  id INT AUTO_INCREMENT PRIMARY KEY,
  code VARCHAR(50) NOT NULL UNIQUE,
  discount_percent INT NOT NULL,
  max_discount_amount DECIMAL(10,2),
  min_order_amount DECIMAL(10,2) DEFAULT 0,
  valid_from DATETIME,
  valid_until DATETIME,
  usage_limit INT,
  times_used INT DEFAULT 0,
  is_active BOOLEAN DEFAULT TRUE
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS notifications (
  id INT AUTO_INCREMENT PRIMARY KEY,
  type VARCHAR(50) NOT NULL,
  message VARCHAR(255) NOT NULL,
  link VARCHAR(255),
  is_read BOOLEAN DEFAULT FALSE,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS testimonials (
  id INT AUTO_INCREMENT PRIMARY KEY,
  customer_name VARCHAR(150) NOT NULL,
  rating INT DEFAULT 5,
  comment TEXT NOT NULL,
  image VARCHAR(255),
  is_active BOOLEAN DEFAULT TRUE,
  display_order INT DEFAULT 0
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS sliders (
  id INT AUTO_INCREMENT PRIMARY KEY,
  title VARCHAR(200),
  subtitle VARCHAR(255),
  image VARCHAR(255) NOT NULL,
  link_url VARCHAR(255),
  button_text VARCHAR(60) DEFAULT 'Shop Now',
  is_active BOOLEAN DEFAULT TRUE,
  display_order INT DEFAULT 0
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS gallery_images (
  id INT AUTO_INCREMENT PRIMARY KEY,
  image VARCHAR(255) NOT NULL,
  caption VARCHAR(150),
  is_active BOOLEAN DEFAULT TRUE,
  display_order INT DEFAULT 0,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS settings (
  id INT AUTO_INCREMENT PRIMARY KEY,
  `key` VARCHAR(100) NOT NULL UNIQUE,
  value TEXT
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS inventory_logs (
  id INT AUTO_INCREMENT PRIMARY KEY,
  product_id INT NOT NULL,
  `change` INT NOT NULL,
  reason VARCHAR(150),
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
) ENGINE=InnoDB;

SET FOREIGN_KEY_CHECKS = 1;
