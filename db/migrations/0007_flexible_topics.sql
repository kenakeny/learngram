-- Topics are now AI-judged rather than a fixed set of six. The extractor reuses
-- an existing topic when a concept fits, or coins a new lowercase-kebab topic.
-- Drop the CHECK that pinned nodes.topic to the original enum-like list.
ALTER TABLE nodes DROP CONSTRAINT IF EXISTS nodes_topic_check;
