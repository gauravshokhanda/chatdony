-- Already added in previous run:
-- ALTER TABLE users ADD COLUMN is_online BOOLEAN DEFAULT FALSE;
-- ALTER TABLE users ADD COLUMN last_seen DATETIME;
-- ALTER TABLE messages ADD COLUMN message_type ENUM('text', 'image') DEFAULT 'text';
-- ALTER TABLE messages ADD COLUMN file_url TEXT NULL;

-- Remaining statements to try
ALTER TABLE users ADD COLUMN gender VARCHAR(10) DEFAULT 'NotSpecified';
ALTER TABLE users ADD COLUMN description TEXT;
ALTER TABLE users ADD COLUMN phone_number VARCHAR(20);
ALTER TABLE users ADD COLUMN profile_pic TEXT;
ALTER TABLE users ADD COLUMN unique_udid VARCHAR(100);
ALTER TABLE users ADD COLUMN gender VARCHAR(100);
ALTER TABLE users ADD COLUMN password VARCHAR(100);
ALTER TABLE users ADD COLUMN is_active BOOLEAN DEFAULT TRUE;
ALTER TABLE users 
ADD COLUMN display_name VARCHAR(100),
ADD COLUMN date_of_birth DATE;


ALTER TABLE messages ADD COLUMN reply_to_message_id INT NULL;
ALTER TABLE messages ADD COLUMN is_deleted BOOLEAN DEFAULT FALSE;
ALTER TABLE messages ADD COLUMN status ENUM('sent', 'delivered', 'seen') DEFAULT 'sent';

-- Foreign key
ALTER TABLE messages
ADD CONSTRAINT fk_reply FOREIGN KEY (reply_to_message_id) REFERENCES messages(message_id);
