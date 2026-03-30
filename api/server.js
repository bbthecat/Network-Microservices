/**
 * Lab 7 — API Service Node
 * Enterprise Microservice with:
 *   - PostgreSQL (persistent data)
 *   - Redis (caching)
 *   - Structured logging (millisecond timestamps)
 *   - Health check endpoint
 *   - Security headers via Helmet
 */

'use strict';

const express    = require('express');
const { Pool }   = require('pg');
const Redis      = require('ioredis');
const winston    = require('winston');
const morgan     = require('morgan');
const helmet     = require('helmet');
const cors       = require('cors');
const os         = require('os');

// ─────────────────────────────────────────────────────────
// CONFIGURATION
// ─────────────────────────────────────────────────────────
const NODE_ID   = process.env.NODE_ID   || 'api-unknown';
const PORT      = parseInt(process.env.PORT || '3000', 10);
const DB_HOST   = process.env.DB_HOST   || 'postgres';
const DB_PORT   = parseInt(process.env.DB_PORT || '5432', 10);
const DB_NAME   = process.env.DB_NAME   || 'labdb';
const DB_USER   = process.env.DB_USER   || 'labuser';
const DB_PASS   = process.env.DB_PASSWORD;
const REDIS_HOST = process.env.REDIS_HOST || 'redis';
const REDIS_PORT = parseInt(process.env.REDIS_PORT || '6379', 10);
const REDIS_PASS = process.env.REDIS_PASSWORD;
const LOG_LEVEL  = process.env.LOG_LEVEL || 'info';

const startTime  = Date.now();

// ─────────────────────────────────────────────────────────
// LOGGER — Structured JSON with millisecond timestamps
// ─────────────────────────────────────────────────────────
const logger = winston.createLogger({
  level: LOG_LEVEL,
  format: winston.format.combine(
    winston.format.timestamp({ format: () => new Date().toISOString() }),  // ISO8601 ms
    winston.format.errors({ stack: true }),
    winston.format.json()
  ),
  defaultMeta: {
    service: 'api',
    node_id: NODE_ID,
    hostname: os.hostname(),
    zone: 'backend-secure'
  },
  transports: [
    new winston.transports.Console()
  ]
});

// ─────────────────────────────────────────────────────────
// DATABASE — PostgreSQL Connection Pool
// ─────────────────────────────────────────────────────────
const pgPool = new Pool({
  host:     DB_HOST,
  port:     DB_PORT,
  database: DB_NAME,
  user:     DB_USER,
  password: DB_PASS,
  max:      10,              // Connection pool size
  idleTimeoutMillis: 30000,
  connectionTimeoutMillis: 5000,
  ssl: false                 // Lab environment — no SSL required
});

pgPool.on('error', (err) => {
  logger.error('PostgreSQL pool error', { error: err.message });
});

// ─────────────────────────────────────────────────────────
// CACHE — Redis Client
// ─────────────────────────────────────────────────────────
const redis = new Redis({
  host:         REDIS_HOST,
  port:         REDIS_PORT,
  password:     REDIS_PASS,
  retryStrategy: (times) => Math.min(times * 100, 3000),
  enableOfflineQueue: true,
  lazyConnect:  false
});

redis.on('connect',   () => logger.info('Redis connected'));
redis.on('error',   (e) => logger.error('Redis error', { error: e.message }));
redis.on('reconnecting', () => logger.warn('Redis reconnecting...'));

// ─────────────────────────────────────────────────────────
// EXPRESS APP
// ─────────────────────────────────────────────────────────
const app = express();

// Security middleware
app.use(helmet({
  contentSecurityPolicy: false,  // API — no HTML served
}));
app.use(cors({
  origin: ['http://172.21.0.10', 'http://172.20.0.10'],  // Only from Nginx
  methods: ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
}));
app.use(express.json({ limit: '1mb' }));
app.use(express.urlencoded({ extended: false }));

// HTTP request logging via Morgan → Winston
app.use(morgan('combined', {
  stream: { write: (msg) => logger.http(msg.trim()) }
}));

// ─────────────────────────────────────────────────────────
// ROUTES
// ─────────────────────────────────────────────────────────

/**
 * GET /health
 * Health-check endpoint — used by Docker, Nginx, and scripts
 */
app.get('/health', async (req, res) => {
  const t0 = Date.now();

  let pgStatus   = 'unknown';
  let redisStatus = 'unknown';
  let pgLatencyMs = null;
  let redisLatencyMs = null;

  // Check PostgreSQL
  try {
    const pgT0 = Date.now();
    await pgPool.query('SELECT 1');
    pgLatencyMs = Date.now() - pgT0;
    pgStatus = 'healthy';
  } catch (e) {
    pgStatus = 'unhealthy';
    logger.warn('Health check: PostgreSQL unhealthy', { error: e.message });
  }

  // Check Redis
  try {
    const rT0 = Date.now();
    const pong = await redis.ping();
    redisLatencyMs = Date.now() - rT0;
    redisStatus = pong === 'PONG' ? 'healthy' : 'unhealthy';
  } catch (e) {
    redisStatus = 'unhealthy';
    logger.warn('Health check: Redis unhealthy', { error: e.message });
  }

  const overall = (pgStatus === 'healthy' && redisStatus === 'healthy') ? 'healthy' : 'degraded';
  const statusCode = overall === 'healthy' ? 200 : 503;

  const response = {
    status:    overall,
    node_id:   NODE_ID,
    hostname:  os.hostname(),
    zone:      'backend-secure',
    uptime_ms: Date.now() - startTime,
    timestamp: new Date().toISOString(),
    checks: {
      postgres:  { status: pgStatus,    latency_ms: pgLatencyMs },
      redis:     { status: redisStatus, latency_ms: redisLatencyMs }
    },
    response_ms: Date.now() - t0
  };

  logger.debug('Health check completed', response);
  return res.status(statusCode).json(response);
});

/**
 * GET /api/info
 * Returns node metadata — useful for verifying load balancing
 */
app.get('/api/info', (req, res) => {
  return res.json({
    node_id:   NODE_ID,
    hostname:  os.hostname(),
    pid:       process.pid,
    zone:      'backend-secure',
    timestamp: new Date().toISOString(),
    uptime_ms: Date.now() - startTime,
    env: {
      db_host:    DB_HOST,
      redis_host: REDIS_HOST,
      port:       PORT
    }
  });
});

/**
 * GET /api/data
 * Returns data from DB (with Redis cache)
 * Cache TTL: 10 seconds
 */
app.get('/api/data', async (req, res) => {
  const cacheKey = 'lab7:data:latest';
  const t0 = Date.now();

  try {
    // Try Redis cache first
    const cached = await redis.get(cacheKey);
    if (cached) {
      logger.debug('Cache HIT', { key: cacheKey, node: NODE_ID });
      return res.json({
        source:     'cache',
        node_id:    NODE_ID,
        data:       JSON.parse(cached),
        cached_at:  new Date().toISOString(),
        latency_ms: Date.now() - t0
      });
    }

    // Cache MISS — query PostgreSQL
    logger.debug('Cache MISS — querying PostgreSQL', { key: cacheKey, node: NODE_ID });
    const result = await pgPool.query(`
      SELECT id, name, value, created_at
      FROM lab_data
      ORDER BY created_at DESC
      LIMIT 20
    `);

    const data = result.rows;

    // Store in cache for 10 seconds
    await redis.setex(cacheKey, 10, JSON.stringify(data));

    return res.json({
      source:     'database',
      node_id:    NODE_ID,
      data:       data,
      fetched_at: new Date().toISOString(),
      latency_ms: Date.now() - t0
    });
  } catch (err) {
    logger.error('GET /api/data failed', { error: err.message, node: NODE_ID });
    return res.status(500).json({
      error:     'Internal Server Error',
      node_id:   NODE_ID,
      message:   err.message,
      timestamp: new Date().toISOString()
    });
  }
});

/**
 * POST /api/data
 * Insert a record into the database
 */
app.post('/api/data', async (req, res) => {
  const { name, value } = req.body;

  if (!name || value === undefined) {
    return res.status(400).json({ error: 'Bad Request', message: 'name and value are required' });
  }

  try {
    const result = await pgPool.query(
      'INSERT INTO lab_data (name, value) VALUES ($1, $2) RETURNING *',
      [name, String(value)]
    );

    // Invalidate cache
    await redis.del('lab7:data:latest');

    logger.info('Record inserted', { name, node: NODE_ID });
    return res.status(201).json({
      success:   true,
      node_id:   NODE_ID,
      record:    result.rows[0],
      timestamp: new Date().toISOString()
    });
  } catch (err) {
    logger.error('POST /api/data failed', { error: err.message });
    return res.status(500).json({ error: 'Internal Server Error', message: err.message });
  }
});

/**
 * GET /api/cache/stats
 * Returns Redis cache statistics
 */
app.get('/api/cache/stats', async (req, res) => {
  try {
    const info = await redis.info('stats');
    const keyspace = await redis.info('keyspace');
    const memory = await redis.info('memory');
    return res.json({
      node_id:   NODE_ID,
      timestamp: new Date().toISOString(),
      redis: { stats: info, keyspace, memory }
    });
  } catch (err) {
    return res.status(500).json({ error: err.message });
  }
});

// 404 handler
app.use((req, res) => {
  res.status(404).json({
    error:   'Not Found',
    path:    req.path,
    node_id: NODE_ID
  });
});

// Error handler
app.use((err, req, res, next) => {
  logger.error('Unhandled error', { error: err.message, stack: err.stack });
  res.status(500).json({ error: 'Internal Server Error', node_id: NODE_ID });
});

// ─────────────────────────────────────────────────────────
// START SERVER
// ─────────────────────────────────────────────────────────
app.listen(PORT, '0.0.0.0', () => {
  logger.info(`API node started`, {
    node_id: NODE_ID,
    port:    PORT,
    zone:    'backend-secure',
    pid:     process.pid
  });
});

// Graceful shutdown
process.on('SIGTERM', async () => {
  logger.warn('SIGTERM received — shutting down gracefully');
  await pgPool.end();
  redis.disconnect();
  process.exit(0);
});

module.exports = app;
