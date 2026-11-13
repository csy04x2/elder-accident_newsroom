-- MySQL 8.x; README 5-table model. Apply once to a dedicated empty database.
CREATE TABLE IF NOT EXISTS analysis_snapshots (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  analysis_type VARCHAR(60) NOT NULL,
  filters_json JSON NOT NULL,
  facts_json JSON NOT NULL,
  source_info_json JSON NOT NULL,
  verification_status ENUM('PENDING','PASSED','FAILED') NOT NULL DEFAULT 'PENDING',
  data_as_of DATE NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS source_documents (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  title VARCHAR(500) NOT NULL,
  source_org VARCHAR(200) NOT NULL,
  source_type ENUM('STATISTIC','POLICY','PRESS','NEWS','RESEARCH') NOT NULL,
  source_url TEXT NOT NULL,
  published_at DATETIME NULL,
  retrieved_at DATETIME NOT NULL,
  content_excerpt TEXT NULL,
  content_hash CHAR(64) NULL UNIQUE,
  verification_status ENUM('VERIFIED','METADATA_ONLY','UNAVAILABLE') NOT NULL DEFAULT 'METADATA_ONLY'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS story_ideas (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  analysis_id BIGINT NOT NULL,
  title VARCHAR(500) NOT NULL,
  angle TEXT NOT NULL,
  news_value TEXT NULL,
  source_ids_json JSON NOT NULL,
  reporting_gaps_json JSON NOT NULL,
  readiness ENUM('READY','NEEDS_REPORTING') NOT NULL DEFAULT 'NEEDS_REPORTING',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_story_analysis FOREIGN KEY (analysis_id)
    REFERENCES analysis_snapshots(id) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS articles (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  story_idea_id BIGINT NOT NULL,
  title VARCHAR(500) NOT NULL,
  content LONGTEXT NOT NULL,
  status ENUM('검토대기','승인','보류') NOT NULL DEFAULT '검토대기',
  validation_passed BOOLEAN NOT NULL DEFAULT FALSE,
  validation_result JSON NULL,
  validated_hash CHAR(64) NULL,
  reviewed_by VARCHAR(100) NULL,
  reviewed_at DATETIME NULL,
  review_note TEXT NULL,
  published_at DATETIME NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT fk_article_idea FOREIGN KEY (story_idea_id)
    REFERENCES story_ideas(id) ON DELETE RESTRICT,
  CONSTRAINT chk_approval_metadata CHECK (
    status <> '승인' OR (
      validation_passed = TRUE AND validated_hash IS NOT NULL AND
      reviewed_by IS NOT NULL AND reviewed_at IS NOT NULL AND published_at IS NOT NULL
    )
  )
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS article_evidence (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  article_id BIGINT NOT NULL,
  analysis_id BIGINT NULL,
  source_document_id BIGINT NULL,
  evidence_role ENUM('STATISTIC','CONTEXT') NOT NULL,
  location_label VARCHAR(255) NULL,
  explanation TEXT NOT NULL,
  CONSTRAINT fk_evidence_article FOREIGN KEY (article_id)
    REFERENCES articles(id) ON DELETE RESTRICT,
  CONSTRAINT fk_evidence_analysis FOREIGN KEY (analysis_id)
    REFERENCES analysis_snapshots(id) ON DELETE RESTRICT,
  CONSTRAINT fk_evidence_source FOREIGN KEY (source_document_id)
    REFERENCES source_documents(id) ON DELETE RESTRICT,
  CONSTRAINT chk_evidence_target CHECK (
    (evidence_role = 'STATISTIC' AND analysis_id IS NOT NULL AND source_document_id IS NULL) OR
    (evidence_role = 'CONTEXT' AND analysis_id IS NULL AND source_document_id IS NOT NULL)
  )
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
