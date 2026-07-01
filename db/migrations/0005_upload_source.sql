-- Allow user-uploaded files (Markdown / PDF / etc.) as a document source.
ALTER TYPE source_type ADD VALUE IF NOT EXISTS 'upload';
