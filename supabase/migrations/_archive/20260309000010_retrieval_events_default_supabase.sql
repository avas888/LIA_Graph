-- Update retriever default from 'jsonl' to 'supabase' (sole retriever post-LocalKeywordRetriever removal)
ALTER TABLE retrieval_events ALTER COLUMN retriever SET DEFAULT 'supabase';
