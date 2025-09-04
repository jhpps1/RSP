-- PostgreSQL + pgvector 초기 설정
CREATE EXTENSION IF NOT EXISTS vector;

-- 논문 테이블 생성
CREATE TABLE papers (
    id SERIAL PRIMARY KEY,
    arxiv_id VARCHAR(50),
    openalex_id VARCHAR(255),
    doi VARCHAR(255),
    title TEXT NOT NULL,
    abstract TEXT,
    authors TEXT[],
    categories TEXT[],
    published_date DATE,
    publication_year INTEGER,
    pdf_url TEXT,
    journal_name TEXT,
    cited_by_count INTEGER DEFAULT 0,
    fwci DECIMAL(10,4),
    citation_percentile DECIMAL(5,2),
    open_access_status VARCHAR(20),
    concepts TEXT[],
    paper_source VARCHAR(20) DEFAULT 'arxiv',  -- 'arxiv' or 'openalex'
    embedding VECTOR(384),  -- all-MiniLM-L6-v2 모델 차원
    created_at TIMESTAMP DEFAULT NOW(),
    
    UNIQUE(arxiv_id),
    UNIQUE(openalex_id),
    UNIQUE(doi)
);

-- 벡터 검색용 HNSW 인덱스 (나중에 데이터 입력 후 생성)
-- CREATE INDEX papers_embedding_idx ON papers 
-- USING hnsw (embedding vector_cosine_ops) 
-- WITH (m = 16, ef_construction = 200);

-- 메타데이터 인덱스
CREATE INDEX papers_categories_idx ON papers USING GIN (categories);
CREATE INDEX papers_date_idx ON papers (published_date);
CREATE INDEX papers_title_idx ON papers USING GIN (to_tsvector('english', title));
CREATE INDEX papers_arxiv_id_idx ON papers (arxiv_id);
CREATE INDEX papers_openalex_id_idx ON papers (openalex_id);
CREATE INDEX papers_doi_idx ON papers (doi);
CREATE INDEX papers_journal_idx ON papers (journal_name);
CREATE INDEX papers_citations_idx ON papers (cited_by_count);
CREATE INDEX papers_concepts_idx ON papers USING GIN (concepts);
CREATE INDEX papers_source_idx ON papers (paper_source);

-- 샘플 데이터 (임베딩은 나중에 추가)
INSERT INTO papers (arxiv_id, title, abstract, authors, categories, published_date, pdf_url, publication_year, paper_source) VALUES
(
    '1706.03762',
    'Attention Is All You Need',
    'The dominant sequence transduction models are based on complex recurrent or convolutional neural networks in an encoder-decoder configuration. The best performing models also connect the encoder and decoder through an attention mechanism. We propose a new simple network architecture, the Transformer, based solely on attention mechanisms, dispensing with recurrence and convolutions entirely.',
    ARRAY['Ashish Vaswani', 'Noam Shazeer', 'Niki Parmar', 'Jakob Uszkoreit'],
    ARRAY['cs.CL', 'cs.AI'],
    '2017-06-12',
    'https://arxiv.org/abs/1706.03762',
    2017,
    'arxiv'
),
(
    '1810.04805',
    'BERT: Pre-training of Deep Bidirectional Transformers for Language Understanding',
    'We introduce a new language representation model called BERT, which stands for Bidirectional Encoder Representations from Transformers. Unlike recent language representation models, BERT is designed to pre-train deep bidirectional representations from unlabeled text by jointly conditioning on both left and right context in all layers.',
    ARRAY['Jacob Devlin', 'Ming-Wei Chang', 'Kenton Lee', 'Kristina Toutanova'],
    ARRAY['cs.CL'],
    '2018-10-11',
    'https://arxiv.org/abs/1810.04805',
    2018,
    'arxiv'
),
(
    '2005.14165',
    'Language Models are Few-Shot Learners',
    'Recent work has demonstrated substantial gains on many NLP tasks and benchmarks by pre-training on a large corpus of text followed by fine-tuning on a specific task. While typically task-agnostic in architecture, this method still requires task-specific fine-tuning datasets of thousands or tens of thousands of examples.',
    ARRAY['Tom B. Brown', 'Benjamin Mann', 'Nick Ryder', 'Melanie Subbiah'],
    ARRAY['cs.CL'],
    '2020-05-28',
    'https://arxiv.org/abs/2005.14165',
    2020,
    'arxiv'
);

-- 검색 통계 테이블
CREATE TABLE search_stats (
    id SERIAL PRIMARY KEY,
    query TEXT,
    results_count INTEGER,
    search_time_ms INTEGER,
    created_at TIMESTAMP DEFAULT NOW()
);