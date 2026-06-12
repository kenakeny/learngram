-- Seed: 35 canonical system-design nodes across 6 topics
-- Columns: (name, slug, short_description, topic, depth_level)

INSERT INTO nodes (name, slug, short_description, topic, depth_level) VALUES
    -- networking
    ('Load Balancer',       'load-balancer',     'Distributes incoming traffic across multiple servers to prevent overload and ensure high availability.',                                                    'networking', 1),
    ('Reverse Proxy',       'reverse-proxy',     'Sits in front of web servers, forwarding client requests while providing SSL termination, caching, and load distribution.',                               'networking', 1),
    ('Forward Proxy',       'forward-proxy',     'An intermediary for outbound client requests to external servers, enabling anonymity, content filtering, and caching.',                                   'networking', 2),
    ('CDN',                 'cdn',               'A geographically distributed network that caches and delivers content from edge nodes closer to users, slashing latency.',                                'networking', 1),
    ('API Gateway',         'api-gateway',       'Single entry point for microservice traffic that handles routing, auth, rate limiting, and protocol translation.',                                        'networking', 2),
    ('Service Discovery',   'service-discovery', 'Mechanism by which services automatically register themselves and locate peers without hardcoded addresses (e.g. Consul, Eureka).',                       'networking', 3),
    ('Rate Limiting',       'rate-limiting',     'Controls request frequency per client using algorithms like token bucket or leaky bucket to prevent abuse and protect capacity.',                          'networking', 2),
    -- caching
    ('Caching',             'caching',           'Stores copies of frequently-accessed data in fast storage (memory) to reduce latency and backend load.',                                                  'caching', 1),
    ('Cache Eviction',      'cache-eviction',    'Policies—LRU, LFU, FIFO—that determine which items to remove when a cache reaches its capacity limit.',                                                  'caching', 2),
    ('Cache Strategies',    'cache-strategies',  'Write patterns: Cache-Aside (lazy populate), Write-Through (synchronous write), Write-Back (async write), each with different consistency tradeoffs.',    'caching', 3),
    ('Bloom Filter',        'bloom-filter',      'Space-efficient probabilistic data structure that tests set membership in O(1) with no false negatives but possible false positives.',                     'caching', 3),
    -- databases
    ('Sharding',            'sharding',          'Horizontal partitioning that splits a database across nodes so each holds a subset of rows, enabling linear write scaling.',                              'databases', 3),
    ('Replication',         'replication',       'Maintains copies of data across multiple nodes for fault tolerance and read scaling, trading some consistency for availability.',                         'databases', 2),
    ('Database Index',      'database-index',    'B-tree or hash structure that trades write overhead and storage for dramatically faster read lookups on indexed columns.',                                'databases', 2),
    ('SQL vs NoSQL',        'sql-vs-nosql',      'SQL offers ACID guarantees and relational schemas; NoSQL trades some guarantees for schema flexibility, massive scale, or specialized access patterns.',   'databases', 1),
    ('Key-Value Store',     'key-value-store',   'Simplest NoSQL model—stores arbitrary values addressed by a unique key with O(1) average-case reads; powers caches, session stores, feature flags.',     'databases', 2),
    ('Write-Ahead Log',     'write-ahead-log',   'Records every change to an append-only log before applying it to the database, enabling crash recovery and streaming replication.',                       'databases', 3),
    -- distributed-systems
    ('Consistent Hashing',  'consistent-hashing', 'Maps keys and nodes onto a ring so adding or removing a node remaps only K/N keys on average instead of nearly all of them.',                          'distributed-systems', 3),
    ('CAP Theorem',         'cap-theorem',        'A distributed system can provide at most two of: Consistency, Availability, and Partition tolerance simultaneously.',                                    'distributed-systems', 2),
    ('PACELC',              'pacelc',             'Extends CAP: even without a network partition, systems face a latency-vs-consistency tradeoff (L vs C) under normal operation.',                        'distributed-systems', 4),
    ('Consensus',           'consensus',          'The problem of getting distributed processes to agree on a single value despite failures and asynchronous message delivery.',                            'distributed-systems', 3),
    ('Raft',                'raft',               'Consensus algorithm designed for understandability: uses leader election and replicated log; basis for etcd, CockroachDB, and TiKV.',                   'distributed-systems', 4),
    ('Paxos',               'paxos',              'Classic two-phase consensus (Prepare/Accept) that tolerates fail-stop failures; notoriously hard to implement correctly.',                               'distributed-systems', 5),
    ('Two-Phase Commit',    'two-phase-commit',   'Atomic commitment protocol where a coordinator collects votes from all participants, committing only if every node agrees.',                              'distributed-systems', 3),
    ('Quorum',              'quorum',             'A minimum number of nodes (e.g. ⌊N/2⌋+1) that must participate in a read or write to ensure at least one up-to-date replica is involved.',             'distributed-systems', 3),
    ('Leader-Follower',     'leader-follower',    'Replication topology where one primary node accepts all writes and propagates them to read-only followers that can take over on failure.',               'distributed-systems', 2),
    -- consistency
    ('ACID',                'acid',              'Database transaction guarantees: Atomicity, Consistency, Isolation, Durability—ensuring reliable processing even under failure.',                         'consistency', 2),
    ('BASE',                'base',              'Distributed-system model: Basically Available, Soft state, Eventually consistent—trades ACID guarantees for scale and availability.',                     'consistency', 2),
    ('Eventual Consistency','eventual-consistency', 'Guarantee that if no new updates arrive, all replicas will converge to the same value—eventual, not immediate, agreement.',                           'consistency', 2),
    ('Strong Consistency',  'strong-consistency', 'Every read reflects the most recent write across all replicas; requires coordination overhead but simplifies application logic.',                        'consistency', 2),
    ('Idempotency',         'idempotency',        'Property where executing the same operation multiple times produces identical results to executing it once—critical for safe retries.',                   'consistency', 2),
    -- messaging
    ('Message Queue',       'message-queue',     'Asynchronous buffer that decouples producers from consumers, enabling load leveling, retries, and independent scaling.',                                  'messaging', 1),
    ('Kafka',               'kafka',             'Distributed log-structured broker that stores messages durably on disk in topics, enabling high-throughput ingestion and event replay.',                   'messaging', 2),
    ('Pub/Sub',             'pub-sub',           'Messaging pattern where publishers broadcast to topics and any number of independent subscribers receive each message asynchronously.',                    'messaging', 2),
    ('Backpressure',        'backpressure',      'Flow-control mechanism that slows producers when consumers cannot keep pace, preventing unbounded memory growth and cascading failures.',                  'messaging', 3);

-- Edges (subqueries on slug avoid hardcoded UUIDs)
INSERT INTO edges (from_node_id, to_node_id, relationship_type, weight) VALUES
    -- caching relationships
    ((SELECT id FROM nodes WHERE slug='cache-strategies'),    (SELECT id FROM nodes WHERE slug='caching'),              'example_of',     1.0),
    ((SELECT id FROM nodes WHERE slug='cache-eviction'),      (SELECT id FROM nodes WHERE slug='caching'),              'used_in',        1.0),
    ((SELECT id FROM nodes WHERE slug='bloom-filter'),        (SELECT id FROM nodes WHERE slug='caching'),              'used_in',        0.8),
    ((SELECT id FROM nodes WHERE slug='cdn'),                 (SELECT id FROM nodes WHERE slug='caching'),              'example_of',     1.0),
    -- database relationships
    ((SELECT id FROM nodes WHERE slug='consistent-hashing'),  (SELECT id FROM nodes WHERE slug='sharding'),            'used_in',        1.2),
    ((SELECT id FROM nodes WHERE slug='sharding'),            (SELECT id FROM nodes WHERE slug='replication'),          'trades_off_with',1.0),
    ((SELECT id FROM nodes WHERE slug='write-ahead-log'),     (SELECT id FROM nodes WHERE slug='replication'),          'used_in',        1.0),
    ((SELECT id FROM nodes WHERE slug='write-ahead-log'),     (SELECT id FROM nodes WHERE slug='database-index'),       'used_in',        0.8),
    ((SELECT id FROM nodes WHERE slug='key-value-store'),     (SELECT id FROM nodes WHERE slug='sql-vs-nosql'),         'example_of',     1.0),
    ((SELECT id FROM nodes WHERE slug='database-index'),      (SELECT id FROM nodes WHERE slug='sharding'),             'used_in',        0.7),
    ((SELECT id FROM nodes WHERE slug='replication'),         (SELECT id FROM nodes WHERE slug='leader-follower'),      'used_in',        1.0),
    -- distributed-systems relationships
    ((SELECT id FROM nodes WHERE slug='raft'),                (SELECT id FROM nodes WHERE slug='paxos'),                'evolved_from',   1.2),
    ((SELECT id FROM nodes WHERE slug='raft'),                (SELECT id FROM nodes WHERE slug='paxos'),                'alternative_to', 1.0),
    ((SELECT id FROM nodes WHERE slug='pacelc'),              (SELECT id FROM nodes WHERE slug='cap-theorem'),          'evolved_from',   1.2),
    ((SELECT id FROM nodes WHERE slug='consensus'),           (SELECT id FROM nodes WHERE slug='raft'),                 'prerequisite_of',1.0),
    ((SELECT id FROM nodes WHERE slug='consensus'),           (SELECT id FROM nodes WHERE slug='paxos'),                'prerequisite_of',1.0),
    ((SELECT id FROM nodes WHERE slug='consensus'),           (SELECT id FROM nodes WHERE slug='two-phase-commit'),     'related_to',     0.8),
    ((SELECT id FROM nodes WHERE slug='quorum'),              (SELECT id FROM nodes WHERE slug='raft'),                 'used_in',        1.0),
    ((SELECT id FROM nodes WHERE slug='quorum'),              (SELECT id FROM nodes WHERE slug='paxos'),                'used_in',        1.0),
    ((SELECT id FROM nodes WHERE slug='leader-follower'),     (SELECT id FROM nodes WHERE slug='replication'),          'related_to',     1.0),
    ((SELECT id FROM nodes WHERE slug='cap-theorem'),         (SELECT id FROM nodes WHERE slug='pacelc'),               'prerequisite_of',1.0),
    ((SELECT id FROM nodes WHERE slug='two-phase-commit'),    (SELECT id FROM nodes WHERE slug='consensus'),            'example_of',     1.0),
    -- networking relationships
    ((SELECT id FROM nodes WHERE slug='api-gateway'),         (SELECT id FROM nodes WHERE slug='reverse-proxy'),        'related_to',     1.0),
    ((SELECT id FROM nodes WHERE slug='rate-limiting'),       (SELECT id FROM nodes WHERE slug='api-gateway'),          'used_in',        1.0),
    ((SELECT id FROM nodes WHERE slug='service-discovery'),   (SELECT id FROM nodes WHERE slug='api-gateway'),          'used_in',        0.9),
    ((SELECT id FROM nodes WHERE slug='service-discovery'),   (SELECT id FROM nodes WHERE slug='load-balancer'),        'related_to',     0.9),
    ((SELECT id FROM nodes WHERE slug='forward-proxy'),       (SELECT id FROM nodes WHERE slug='reverse-proxy'),        'related_to',     0.8),
    ((SELECT id FROM nodes WHERE slug='load-balancer'),       (SELECT id FROM nodes WHERE slug='reverse-proxy'),        'related_to',     0.9),
    -- consistency relationships
    ((SELECT id FROM nodes WHERE slug='acid'),                (SELECT id FROM nodes WHERE slug='base'),                 'alternative_to', 1.0),
    ((SELECT id FROM nodes WHERE slug='base'),                (SELECT id FROM nodes WHERE slug='acid'),                 'alternative_to', 1.0),
    ((SELECT id FROM nodes WHERE slug='eventual-consistency'),(SELECT id FROM nodes WHERE slug='strong-consistency'),   'alternative_to', 1.0),
    ((SELECT id FROM nodes WHERE slug='eventual-consistency'),(SELECT id FROM nodes WHERE slug='base'),                 'example_of',     1.0),
    ((SELECT id FROM nodes WHERE slug='strong-consistency'),  (SELECT id FROM nodes WHERE slug='acid'),                 'example_of',     1.0),
    ((SELECT id FROM nodes WHERE slug='idempotency'),         (SELECT id FROM nodes WHERE slug='message-queue'),        'used_in',        1.0),
    -- messaging relationships
    ((SELECT id FROM nodes WHERE slug='kafka'),               (SELECT id FROM nodes WHERE slug='message-queue'),        'example_of',     1.2),
    ((SELECT id FROM nodes WHERE slug='pub-sub'),             (SELECT id FROM nodes WHERE slug='message-queue'),        'example_of',     1.0),
    ((SELECT id FROM nodes WHERE slug='backpressure'),        (SELECT id FROM nodes WHERE slug='message-queue'),        'related_to',     1.0),
    ((SELECT id FROM nodes WHERE slug='kafka'),               (SELECT id FROM nodes WHERE slug='pub-sub'),              'example_of',     0.9),
    -- cross-topic
    ((SELECT id FROM nodes WHERE slug='consistent-hashing'),  (SELECT id FROM nodes WHERE slug='load-balancer'),        'used_in',        0.9),
    ((SELECT id FROM nodes WHERE slug='bloom-filter'),        (SELECT id FROM nodes WHERE slug='database-index'),       'related_to',     0.7),
    ((SELECT id FROM nodes WHERE slug='cap-theorem'),         (SELECT id FROM nodes WHERE slug='acid'),                 'related_to',     0.8),
    ((SELECT id FROM nodes WHERE slug='cap-theorem'),         (SELECT id FROM nodes WHERE slug='eventual-consistency'), 'prerequisite_of',1.0);
