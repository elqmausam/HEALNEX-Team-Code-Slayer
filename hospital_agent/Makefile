# Makefile
# Simplified commands for Hospital Agent Docker management

.PHONY: help build up down restart logs health test clean

# Default target
help:
	@echo "Hospital Agent - Docker Management"
	@echo "=================================="
	@echo ""
	@echo "Available commands:"
	@echo "  make setup      - Initial setup (build and start)"
	@echo "  make up         - Start all services"
	@echo "  make down       - Stop all services"
	@echo "  make restart    - Restart all services"
	@echo "  make logs       - View logs (follow mode)"
	@echo "  make health     - Check service health"
	@echo "  make test       - Run API tests"
	@echo "  make clean      - Stop and remove all containers/volumes"
	@echo "  make rebuild    - Rebuild and restart"
	@echo "  make shell      - Open shell in app container"
	@echo "  make db         - Connect to PostgreSQL"
	@echo "  make redis      - Connect to Redis CLI"
	@echo ""

# Initial setup
setup:
	@echo "🚀 Setting up Hospital Agent..."
	@chmod +x scripts/docker-setup.sh
	@./scripts/docker-setup.sh

# Build images
build:
	@echo "🔨 Building Docker images..."
	@docker-compose build

# Start services
up:
	@echo "▶️  Starting services..."
	@docker-compose up -d
	@echo "✅ Services started!"
	@echo "📡 API: http://localhost:8000/docs"

# Start with debug tools
debug:
	@echo "🐛 Starting with debug tools..."
	@docker-compose --profile debug up -d
	@echo "✅ Services started with debug tools!"
	@echo "📊 Redis Commander: http://localhost:8081"
	@echo "🗄️  pgAdmin: http://localhost:5050"

# Start with monitoring
monitor:
	@echo "📈 Starting with monitoring..."
	@docker-compose --profile monitoring up -d
	@echo "✅ Services started with monitoring!"
	@echo "📊 Prometheus: http://localhost:9090"
	@echo "📈 Grafana: http://localhost:3000"

# Stop services
down:
	@echo "⏹️  Stopping services..."
	@docker-compose down
	@echo "✅ Services stopped!"

# Restart services
restart:
	@echo "🔄 Restarting services..."
	@docker-compose restart
	@echo "✅ Services restarted!"

# View logs
logs:
	@docker-compose logs -f

# View logs for specific service
logs-app:
	@docker-compose logs -f hospital-agent

# Check health
health:
	@echo "🏥 Checking service health..."
	@echo ""
	@echo "Redis:"
	@docker-compose exec -T redis redis-cli ping || echo "❌ Redis not responding"
	@echo ""
	@echo "PostgreSQL:"
	@docker-compose exec -T postgres pg_isready -U postgres || echo "❌ PostgreSQL not responding"
	@echo ""
	@echo "Hospital Agent:"
	@curl -s http://localhost:8000/health | jq || echo "❌ App not responding"
	@echo ""

# Run tests
test:
	@echo "🧪 Running tests..."
	@curl -s -X POST http://localhost:8000/api/v1/chat/message \
		-H "Content-Type: application/json" \
		-d '{"message":"Hello","hospital_id":"H001"}' | jq
	@echo ""
	@echo "Testing FREE APIs..."
	@curl -s "http://localhost:8000/api/v1/demo/H001/simple?location=Mumbai" | jq

# Clean everything
clean:
	@echo "🧹 Cleaning up..."
	@docker-compose down -v
	@echo "✅ Cleanup complete!"

# Rebuild and restart
rebuild:
	@echo "🔨 Rebuilding..."
	@docker-compose build --no-cache
	@docker-compose up -d
	@echo "✅ Rebuild complete!"

# Open shell in app container
shell:
	@docker-compose exec hospital-agent /bin/bash

# Connect to PostgreSQL
db:
	@docker-compose exec postgres psql -U postgres -d hospital_agent

# Connect to Redis
redis:
	@docker-compose exec redis redis-cli

# Show status
status:
	@echo "📊 Container Status:"
	@docker-compose ps
	@echo ""
	@echo "💾 Volume Usage:"
	@docker volume ls | grep hospital

# Backup database
backup:
	@echo "💾 Creating database backup..."
	@mkdir -p backups
	@docker-compose exec -T postgres pg_dump -U postgres hospital_agent > backups/backup_$(shell date +%Y%m%d_%H%M%S).sql
	@echo "✅ Backup created in backups/"

# Restore database
restore:
	@echo "⚠️  This will restore the database from the latest backup"
	@read -p "Continue? [y/N] " -n 1 -r; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		docker-compose exec -T postgres psql -U postgres hospital_agent < backups/$(shell ls -t backups/*.sql | head -1); \
		echo "✅ Database restored"; \
	fi

# Update .env
env:
	@nano .env

# Show URLs
urls:
	@echo "📡 Access Points:"
	@echo "  API Docs:    http://localhost:8000/docs"
	@echo "  Health:      http://localhost:8000/health"
	@echo "  Redis:       localhost:6379"
	@echo "  PostgreSQL:  localhost:5432"
	@echo ""
	@echo "🧪 Test Endpoints:"
	@echo "  Demo:        http://localhost:8000/api/v1/demo/H001?location=Mumbai"
	@echo "  Mock HMIS:   http://localhost:8000/api/v1/mock/hmis/"
	@echo "  Mock Lab:    http://localhost:8000/api/v1/mock/lab/"